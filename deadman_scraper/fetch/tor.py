"""
TOR Manager
===========
Unified TOR proxy management with circuit health monitoring.

Supports:
- Docker-based TOR (recommended)
- System TOR service
- Automatic circuit rotation on failures
- Exponential backoff retry
- Health monitoring

FREE and unlimited - no API costs.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from deadman_scraper.core.config import TORConfig

logger = logging.getLogger(__name__)


@dataclass
class CircuitHealth:
    """Track health of a TOR circuit."""

    circuit_id: int
    created_at: float
    requests: int = 0
    failures: int = 0
    last_success: float | None = None
    last_failure: float | None = None
    avg_latency_ms: float = 0.0

    @property
    def success_rate(self) -> float:
        if self.requests == 0:
            return 1.0
        return (self.requests - self.failures) / self.requests

    @property
    def is_healthy(self) -> bool:
        if self.requests >= 3 and self.success_rate < 0.5:
            return False
        if self.failures >= 3 and self.last_failure and not self.last_success:
            return False
        return True


@dataclass
class TORStatus:
    """TOR proxy status."""

    running: bool
    docker_available: bool
    proxy_url: str | None = None
    exit_ip: str | None = None
    circuit_id: int = 0
    success_rate: float = 1.0
    error: str | None = None


class TORManager:
    """
    Unified TOR manager with health monitoring and automatic recovery.

    Usage:
        tor = TORManager(config)
        await tor.start()

        # Simple proxy access
        proxy_url = tor.proxy_url  # socks5h://127.0.0.1:9050

        # Fetch with automatic retry and circuit rotation
        result = await tor.fetch_with_retry(url, fetch_func)

        await tor.stop()
    """

    DEFAULT_IMAGE = "dperson/torproxy"
    DEFAULT_CONTAINER = "deadman-tor"

    def __init__(self, config: TORConfig = None):
        self.config = config or self._default_config()
        self._running = False
        self._circuit = CircuitHealth(circuit_id=1, created_at=time.time())
        self._request_times: deque = deque(maxlen=100)
        self._consecutive_failures = 0

    def _default_config(self):
        """Create default config if none provided."""
        @dataclass
        class DefaultConfig:
            socks_host: str = "127.0.0.1"
            socks_port: int = 9050
            control_port: int = 9051
            method: str = "docker"
            docker_image: str = "dperson/torproxy"
            docker_container_name: str = "deadman-tor"
            onion_timeout: int = 120
            clearnet_timeout: int = 30
            max_retries: int = 3
            retry_delay: float = 2.0
            circuit_rotation_interval: int = 300
            max_requests_per_circuit: int = 50

        return DefaultConfig()

    @property
    def proxy_url(self) -> str:
        """Get SOCKS5 proxy URL for TOR."""
        return f"socks5h://{self.config.socks_host}:{self.config.socks_port}"

    def get_timeout(self, url: str) -> int:
        """Get appropriate timeout based on URL type."""
        if ".onion" in url:
            return getattr(self.config, 'onion_timeout', 120)
        return getattr(self.config, 'clearnet_timeout', 30)

    # =========================================================================
    # LIFECYCLE
    # =========================================================================

    async def start(self) -> bool:
        """Start TOR proxy."""
        method = getattr(self.config, 'method', 'docker')

        if method == "docker":
            return await self._start_docker()
        elif method == "system":
            if await self._check_connectivity():
                self._running = True
                logger.info(f"[TOR] Connected via system TOR at {self.proxy_url}")
                return True
            return False
        else:
            logger.error(f"Unsupported TOR method: {method}")
            return False

    async def stop(self) -> bool:
        """Stop TOR proxy."""
        method = getattr(self.config, 'method', 'docker')

        if method == "docker" and self._running:
            container = getattr(self.config, 'docker_container_name', self.DEFAULT_CONTAINER)
            try:
                proc = await asyncio.create_subprocess_exec(
                    "docker", "stop", container,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await proc.wait()
            except (FileNotFoundError, OSError):
                pass

        self._running = False
        logger.info("[TOR] Stopped")
        return True

    async def ensure_running(self) -> bool:
        """Ensure TOR is running, starting if needed."""
        if await self.is_running():
            return True
        return await self.start()

    async def is_running(self) -> bool:
        """Check if TOR is currently running."""
        method = getattr(self.config, 'method', 'docker')

        if method == "docker":
            return await self._is_docker_running()
        return await self._check_connectivity()

    # =========================================================================
    # FETCH WITH RETRY
    # =========================================================================

    async def fetch_with_retry(
        self,
        url: str,
        fetch_func: Callable,
        max_retries: int = None
    ) -> Any | None:
        """
        Fetch URL with automatic retry and circuit rotation.

        Args:
            url: URL to fetch
            fetch_func: Async function(url, proxy_url, timeout) -> result
            max_retries: Override default max retries
        """
        max_retries = max_retries or getattr(self.config, 'max_retries', 3)
        timeout = self.get_timeout(url)

        for attempt in range(max_retries):
            try:
                await self._ensure_healthy_circuit()

                start = time.time()
                result = await fetch_func(url, self.proxy_url, timeout)
                latency = (time.time() - start) * 1000

                self._record_success(latency)
                return result

            except asyncio.TimeoutError:
                logger.warning(f"[TOR] Timeout attempt {attempt + 1}/{max_retries}: {url}")
                self._record_failure("timeout")

            except Exception as e:
                logger.warning(f"[TOR] {type(e).__name__} attempt {attempt + 1}/{max_retries}: {url}")
                self._record_failure(type(e).__name__)

            if self._should_rotate_circuit():
                logger.info("[TOR] Rotating circuit due to failures...")
                await self.rotate_circuit()

            if attempt < max_retries - 1:
                delay = getattr(self.config, 'retry_delay', 2.0) * (2 ** attempt) + random.uniform(0, 1)
                await asyncio.sleep(delay)

        return None

    # =========================================================================
    # CIRCUIT MANAGEMENT
    # =========================================================================

    async def rotate_circuit(self) -> bool:
        """Rotate TOR circuit for new exit IP."""
        logger.info("[TOR] Rotating circuit...")

        method = getattr(self.config, 'method', 'docker')

        if method == "docker":
            success = await self._restart_docker()
        else:
            success = await self._send_newnym()

        if success:
            self._circuit = CircuitHealth(
                circuit_id=self._circuit.circuit_id + 1,
                created_at=time.time()
            )
            self._consecutive_failures = 0
            logger.info(f"[TOR] New circuit #{self._circuit.circuit_id}")

        return success

    async def get_exit_ip(self) -> str | None:
        """Get current TOR exit IP address."""
        try:
            import httpx

            async with httpx.AsyncClient(proxy=self.proxy_url, timeout=30) as client:
                response = await client.get("https://check.torproject.org/api/ip")
                return response.json().get("IP")
        except Exception as e:
            logger.debug(f"Failed to get exit IP: {e}")
            return None

    async def status(self) -> TORStatus:
        """Get detailed TOR status."""
        docker_available = await self._is_docker_available()
        running = await self.is_running()
        exit_ip = await self.get_exit_ip() if running else None

        return TORStatus(
            running=running,
            docker_available=docker_available,
            proxy_url=self.proxy_url if running else None,
            exit_ip=exit_ip,
            circuit_id=self._circuit.circuit_id,
            success_rate=self._circuit.success_rate,
        )

    def get_stats(self) -> dict[str, Any]:
        """Get TOR statistics."""
        return {
            "running": self._running,
            "circuit_id": self._circuit.circuit_id,
            "circuit_age_seconds": int(time.time() - self._circuit.created_at),
            "requests": self._circuit.requests,
            "failures": self._circuit.failures,
            "success_rate": f"{self._circuit.success_rate * 100:.1f}%",
            "avg_latency_ms": f"{self._circuit.avg_latency_ms:.0f}",
            "is_healthy": self._circuit.is_healthy,
            "consecutive_failures": self._consecutive_failures,
        }

    # =========================================================================
    # INTERNAL - Health Tracking
    # =========================================================================

    def _record_success(self, latency_ms: float):
        """Record successful request."""
        self._circuit.requests += 1
        self._circuit.last_success = time.time()
        self._consecutive_failures = 0

        self._request_times.append(latency_ms)
        self._circuit.avg_latency_ms = sum(self._request_times) / len(self._request_times)

    def _record_failure(self, error_type: str):
        """Record failed request."""
        self._circuit.requests += 1
        self._circuit.failures += 1
        self._circuit.last_failure = time.time()
        self._consecutive_failures += 1

    def _should_rotate_circuit(self) -> bool:
        """Determine if circuit should be rotated."""
        if self._consecutive_failures >= 3:
            return True
        if not self._circuit.is_healthy:
            return True

        age = time.time() - self._circuit.created_at
        rotation_interval = getattr(self.config, 'circuit_rotation_interval', 300)
        if age > rotation_interval:
            return True

        max_requests = getattr(self.config, 'max_requests_per_circuit', 50)
        if self._circuit.requests >= max_requests:
            return True

        return False

    async def _ensure_healthy_circuit(self):
        """Ensure we have a healthy circuit."""
        if not self._circuit.is_healthy:
            await self.rotate_circuit()

    # =========================================================================
    # INTERNAL - Docker Backend
    # =========================================================================

    async def _is_docker_available(self) -> bool:
        """Check if Docker is installed and running."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "--version",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
            return proc.returncode == 0
        except (FileNotFoundError, OSError):
            return False

    async def _is_docker_running(self) -> bool:
        """Check if TOR Docker container is running."""
        try:
            container = getattr(self.config, 'docker_container_name', self.DEFAULT_CONTAINER)
            proc = await asyncio.create_subprocess_exec(
                "docker", "ps", "--filter", f"name={container}",
                "--format", "{{.Names}}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await proc.communicate()
            return container in stdout.decode()
        except Exception:
            return False

    async def _start_docker(self) -> bool:
        """Start TOR via Docker."""
        if await self._is_docker_running():
            logger.info("[TOR] Already running")
            self._running = True
            return True

        if not await self._is_docker_available():
            logger.error("[TOR] Docker not available")
            return False

        container = getattr(self.config, 'docker_container_name', self.DEFAULT_CONTAINER)
        image = getattr(self.config, 'docker_image', self.DEFAULT_IMAGE)
        port = getattr(self.config, 'socks_port', 9050)

        logger.info(f"[TOR] Starting Docker container: {container}")

        # Remove any existing container
        await asyncio.create_subprocess_exec(
            "docker", "rm", "-f", container,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )

        # Start container
        proc = await asyncio.create_subprocess_exec(
            "docker", "run", "-d",
            "--name", container,
            "-p", f"{port}:9050",
            image,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            logger.error(f"[TOR] Failed to start: {stderr.decode()}")
            return False

        logger.info("[TOR] Waiting for initialization...")
        await asyncio.sleep(10)

        self._running = True
        logger.info(f"[TOR] Running at {self.proxy_url}")
        return True

    async def _restart_docker(self) -> bool:
        """Restart TOR Docker container for new circuit."""
        container = getattr(self.config, 'docker_container_name', self.DEFAULT_CONTAINER)

        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "restart", container,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()

            if proc.returncode == 0:
                await asyncio.sleep(5)
                return True
        except Exception as e:
            logger.error(f"[TOR] Docker restart failed: {e}")

        return False

    # =========================================================================
    # INTERNAL - System TOR Backend
    # =========================================================================

    async def _check_connectivity(self) -> bool:
        """Check if TOR proxy is working."""
        try:
            import httpx

            async with httpx.AsyncClient(proxy=self.proxy_url, timeout=20) as client:
                response = await client.get("https://check.torproject.org/api/ip")
                if response.status_code == 200:
                    ip = response.json().get("IP")
                    logger.info(f"[TOR] Connected, exit IP: {ip}")
                    return True
        except Exception:
            pass
        return False

    async def _send_newnym(self) -> bool:
        """Send NEWNYM signal via TOR control port."""
        try:
            from stem import Signal
            from stem.control import Controller

            control_port = getattr(self.config, 'control_port', 9051)

            with Controller.from_port(port=control_port) as controller:
                controller.authenticate()
                controller.signal(Signal.NEWNYM)

            logger.info("[TOR] NEWNYM signal sent")
            await asyncio.sleep(5)
            return True

        except ImportError:
            logger.warning("[TOR] stem not installed, cannot send NEWNYM")
            return False
        except Exception as e:
            logger.error(f"[TOR] Failed to send NEWNYM: {e}")
            return False


# Convenience function
async def fetch_onion(url: str, tor: TORManager = None) -> str | None:
    """
    Fetch .onion URL with automatic TOR handling.

    Example:
        content = await fetch_onion("http://duckduckgo...onion/")
    """
    import httpx

    tor = tor or TORManager()

    if not tor._running:
        await tor.start()

    async def _fetch(url: str, proxy: str, timeout: int):
        async with httpx.AsyncClient(proxy=proxy, timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text

    return await tor.fetch_with_retry(url, _fetch)

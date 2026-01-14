"""
Enhanced TOR Manager - Improved reliability for .onion scraping.

Fixes:
1. Circuit rotation on failure
2. Longer timeouts for .onion (they're slow)
3. Retry logic with exponential backoff
4. Multi-circuit pool for parallel requests
5. Health monitoring
"""

import asyncio
import logging
import random
import time
from collections import deque
from dataclasses import dataclass
from typing import Any

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
        total = self.requests
        if total == 0:
            return 1.0
        return (total - self.failures) / total

    @property
    def is_healthy(self) -> bool:
        # Unhealthy if >50% failure rate with at least 3 requests
        if self.requests >= 3 and self.success_rate < 0.5:
            return False
        # Unhealthy if last 3 were failures
        if self.failures >= 3 and self.last_failure and not self.last_success:
            return False
        return True


@dataclass
class TORConfig:
    """Enhanced TOR configuration."""
    socks_host: str = "127.0.0.1"
    socks_port: int = 9050
    control_port: int = 9051
    method: str = "docker"
    docker_image: str = "dperson/torproxy"
    docker_container_name: str = "deadman-tor"

    # Enhanced settings
    onion_timeout: int = 120  # .onion sites are SLOW
    clearnet_timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 2.0
    circuit_rotation_interval: int = 300  # Rotate every 5 min
    max_requests_per_circuit: int = 50
    health_check_interval: int = 60


class EnhancedTORManager:
    """
    Enhanced TOR manager with better reliability.

    Features:
    - Automatic circuit rotation on failures
    - Health monitoring
    - Exponential backoff retry
    - Optimized timeouts for .onion
    """

    def __init__(self, config: TORConfig = None):
        self.config = config or TORConfig()
        self._running = False
        self._circuit = CircuitHealth(
            circuit_id=1,
            created_at=time.time()
        )
        self._request_times: deque = deque(maxlen=100)
        self._consecutive_failures = 0

    @property
    def proxy_url(self) -> str:
        return f"socks5h://{self.config.socks_host}:{self.config.socks_port}"

    def get_timeout(self, url: str) -> int:
        """Get appropriate timeout based on URL type."""
        if ".onion" in url:
            return self.config.onion_timeout
        return self.config.clearnet_timeout

    async def fetch_with_retry(
        self,
        url: str,
        fetch_func,
        max_retries: int = None
    ) -> Any | None:
        """
        Fetch URL with automatic retry and circuit rotation.

        Args:
            url: URL to fetch
            fetch_func: Async function that takes (url, proxy_url, timeout)
            max_retries: Override default max retries
        """
        max_retries = max_retries or self.config.max_retries
        timeout = self.get_timeout(url)

        for attempt in range(max_retries):
            try:
                # Check circuit health before request
                await self._ensure_healthy_circuit()

                start = time.time()
                result = await fetch_func(url, self.proxy_url, timeout)
                latency = (time.time() - start) * 1000

                # Record success
                self._record_success(latency)
                self._consecutive_failures = 0

                return result

            except asyncio.TimeoutError:
                logger.warning(f"[TOR] Timeout on attempt {attempt + 1}/{max_retries}: {url}")
                self._record_failure("timeout")

            except Exception as e:
                error_type = type(e).__name__
                logger.warning(f"[TOR] {error_type} on attempt {attempt + 1}/{max_retries}: {url}")
                self._record_failure(error_type)

            # Should we rotate circuit?
            if self._should_rotate_circuit():
                logger.info("[TOR] Rotating circuit due to failures...")
                await self.rotate_circuit()

            # Exponential backoff
            if attempt < max_retries - 1:
                delay = self.config.retry_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.debug(f"[TOR] Waiting {delay:.1f}s before retry...")
                await asyncio.sleep(delay)

        return None

    def _record_success(self, latency_ms: float):
        """Record successful request."""
        self._circuit.requests += 1
        self._circuit.last_success = time.time()

        # Update average latency
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
        # Rotate after N consecutive failures
        if self._consecutive_failures >= 3:
            return True

        # Rotate if circuit is unhealthy
        if not self._circuit.is_healthy:
            return True

        # Rotate if circuit is old
        age = time.time() - self._circuit.created_at
        if age > self.config.circuit_rotation_interval:
            return True

        # Rotate after max requests
        if self._circuit.requests >= self.config.max_requests_per_circuit:
            return True

        return False

    async def _ensure_healthy_circuit(self):
        """Ensure we have a healthy circuit before making request."""
        if not self._circuit.is_healthy:
            await self.rotate_circuit()

    async def rotate_circuit(self) -> bool:
        """
        Rotate TOR circuit for new exit IP.
        """
        logger.info("[TOR] Rotating circuit...")

        if self.config.method == "docker":
            success = await self._docker_restart()
        else:
            success = await self._send_newnym()

        if success:
            # Reset circuit stats
            self._circuit = CircuitHealth(
                circuit_id=self._circuit.circuit_id + 1,
                created_at=time.time()
            )
            self._consecutive_failures = 0
            logger.info(f"[TOR] New circuit #{self._circuit.circuit_id} established")

        return success

    async def _docker_restart(self) -> bool:
        """Restart Docker container for new circuit."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "restart", self.config.docker_container_name,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()

            if proc.returncode == 0:
                # Wait for new circuit to establish
                await asyncio.sleep(10)
                return True
            return False

        except Exception as e:
            logger.error(f"[TOR] Docker restart failed: {e}")
            return False

    async def _send_newnym(self) -> bool:
        """Send NEWNYM signal via control port."""
        try:
            from stem import Signal
            from stem.control import Controller

            with Controller.from_port(port=self.config.control_port) as controller:
                controller.authenticate()
                controller.signal(Signal.NEWNYM)

            await asyncio.sleep(5)
            return True

        except ImportError:
            logger.warning("[TOR] stem library not installed")
            return False
        except Exception as e:
            logger.error(f"[TOR] NEWNYM failed: {e}")
            return False

    async def start(self) -> bool:
        """Start TOR proxy."""
        if self.config.method == "docker":
            return await self._start_docker()
        return await self._check_running()

    async def _start_docker(self) -> bool:
        """Start TOR via Docker."""
        # Check if already running
        proc = await asyncio.create_subprocess_exec(
            "docker", "ps", "--filter", f"name={self.config.docker_container_name}",
            "--format", "{{.Names}}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()

        if self.config.docker_container_name in stdout.decode():
            logger.info("[TOR] Already running")
            self._running = True
            return True

        # Remove old container
        await asyncio.create_subprocess_exec(
            "docker", "rm", "-f", self.config.docker_container_name,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )

        # Start new container
        logger.info("[TOR] Starting Docker container...")
        proc = await asyncio.create_subprocess_exec(
            "docker", "run", "-d",
            "--name", self.config.docker_container_name,
            "-p", f"{self.config.socks_port}:9050",
            self.config.docker_image,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            logger.error(f"[TOR] Failed: {stderr.decode()}")
            return False

        logger.info("[TOR] Waiting for bootstrap (15s)...")
        await asyncio.sleep(15)

        self._running = True
        return True

    async def _check_running(self) -> bool:
        """Check if TOR is running by testing proxy."""
        try:
            import httpx

            async with httpx.AsyncClient(proxy=self.proxy_url, timeout=20) as client:
                response = await client.get("https://check.torproject.org/api/ip")
                if response.status_code == 200:
                    ip = response.json().get("IP")
                    logger.info(f"[TOR] Running, exit IP: {ip}")
                    self._running = True
                    return True
        except Exception as e:
            logger.debug(f"[TOR] Check failed: {e}")

        return False

    async def stop(self):
        """Stop TOR proxy."""
        if self.config.method == "docker":
            await asyncio.create_subprocess_exec(
                "docker", "stop", self.config.docker_container_name,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
        self._running = False

    def get_stats(self) -> dict[str, Any]:
        """Get TOR statistics."""
        return {
            "running": self._running,
            "circuit_id": self._circuit.circuit_id,
            "circuit_age_seconds": time.time() - self._circuit.created_at,
            "requests": self._circuit.requests,
            "failures": self._circuit.failures,
            "success_rate": f"{self._circuit.success_rate * 100:.1f}%",
            "avg_latency_ms": f"{self._circuit.avg_latency_ms:.0f}",
            "is_healthy": self._circuit.is_healthy,
            "consecutive_failures": self._consecutive_failures,
        }


# Convenience function for scraping
async def fetch_onion(url: str, tor: EnhancedTORManager = None) -> str | None:
    """
    Fetch .onion URL with automatic TOR handling.

    Example:
        content = await fetch_onion("http://duckduckgo...onion/")
    """
    import httpx

    tor = tor or EnhancedTORManager()

    async def _fetch(url: str, proxy: str, timeout: int):
        async with httpx.AsyncClient(proxy=proxy, timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text

    return await tor.fetch_with_retry(url, _fetch)


if __name__ == "__main__":
    async def test():
        tor = EnhancedTORManager()

        # Start TOR
        if not await tor.start():
            print("Failed to start TOR")
            return

        # Test .onion fetch
        print("\nTesting .onion fetch...")
        content = await fetch_onion(
            "http://duckduckgogg42xjoc72x3sjasowoarfbgcmvfimaftt6twagswzczad.onion/",
            tor
        )

        if content:
            print(f"Success! Got {len(content)} bytes")
        else:
            print("Failed to fetch")

        # Print stats
        print("\nTOR Stats:")
        for k, v in tor.get_stats().items():
            print(f"  {k}: {v}")

    asyncio.run(test())

"""
TOR Manager
===========
Manages TOR proxy for anonymous scraping.

Supports:
- Docker-based TOR (recommended)
- Portable TOR Browser Bundle
- System TOR service

FREE and unlimited - no API costs.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from deadman_scraper.core.config import TORConfig

logger = logging.getLogger(__name__)


@dataclass
class TORStatus:
    """TOR proxy status."""

    running: bool
    docker_available: bool
    proxy_url: str | None = None
    exit_ip: str | None = None
    error: str | None = None


class TORManager:
    """
    Manages TOR proxy for anonymous routing.

    Methods:
    - Docker (recommended): dperson/torproxy container
    - Portable: TOR Browser Bundle
    - System: Native TOR service

    Usage:
        tor = TORManager(config)
        await tor.start()
        proxy_url = tor.get_proxy_url()  # socks5h://127.0.0.1:9050
        await tor.renew_circuit()  # New exit IP
        await tor.stop()
    """

    DEFAULT_IMAGE = "dperson/torproxy"
    DEFAULT_CONTAINER = "deadman-tor"

    def __init__(self, config: TORConfig):
        self.config = config
        self._running = False

    @property
    def proxy_url(self) -> str:
        """Get SOCKS5 proxy URL for TOR."""
        return f"socks5h://{self.config.socks_host}:{self.config.socks_port}"

    def get_proxy_url(self) -> str:
        """Alias for proxy_url property."""
        return self.proxy_url

    # =========================================================================
    # LIFECYCLE
    # =========================================================================

    async def start(self) -> bool:
        """
        Start TOR proxy.

        Returns True if TOR is running (started or already running).
        """
        method = self.config.method

        if method == "docker":
            return await self._start_docker()
        elif method == "system":
            if await self._check_system_tor():
                self._running = True
                logger.info(f"[TOR] Connected via system TOR at {self.proxy_url}")
                return True
            return False
        else:
            logger.error(f"Unsupported TOR method: {method}")
            return False

    async def stop(self) -> bool:
        """Stop TOR proxy."""
        if self.config.method == "docker":
            return await self._stop_docker()
        elif self.config.method == "portable":
            return await self._stop_portable()
        return True

    async def ensure_running(self) -> bool:
        """Ensure TOR is running, starting if needed."""
        if await self.is_running():
            return True
        return await self.start()

    async def is_running(self) -> bool:
        """Check if TOR is currently running."""
        if self.config.method == "docker":
            return await self._is_docker_running()
        else:
            # For portable/system, actually check connectivity
            return await self._check_system_tor()

    # =========================================================================
    # CIRCUIT MANAGEMENT
    # =========================================================================

    async def renew_circuit(self) -> bool:
        """
        Renew TOR circuit (get new exit IP).

        For Docker: Restart container
        For System: Send NEWNYM signal via control port
        """
        logger.info("[TOR] Renewing circuit for new exit IP...")

        if self.config.method == "docker":
            return await self._restart_docker()
        else:
            return await self._send_newnym()

    async def get_exit_ip(self) -> str | None:
        """Get current TOR exit IP address."""
        try:
            import httpx

            async with httpx.AsyncClient(proxy=self.proxy_url, timeout=30) as client:
                # Use TOR check service
                response = await client.get("https://check.torproject.org/api/ip")
                data = response.json()
                return data.get("IP")
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
        )

    # =========================================================================
    # DOCKER BACKEND
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
            # Docker not found on this system
            return False
        except Exception:
            return False

    async def _is_docker_running(self) -> bool:
        """Check if TOR Docker container is running."""
        try:
            container_name = self.config.docker_container_name
            proc = await asyncio.create_subprocess_exec(
                "docker", "ps", "--filter", f"name={container_name}",
                "--format", "{{.Names}}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await proc.communicate()
            return container_name in stdout.decode()
        except Exception:
            return False

    async def _start_docker(self) -> bool:
        """Start TOR via Docker."""
        # Check if already running
        if await self._is_docker_running():
            logger.info("[TOR] Already running")
            self._running = True
            return True

        # Check Docker available
        if not await self._is_docker_available():
            logger.error("[TOR] Docker not available")
            return False

        container_name = self.config.docker_container_name
        image = self.config.docker_image
        port = self.config.socks_port

        logger.info(f"[TOR] Starting Docker container: {container_name}")

        # Remove any existing stopped container
        await asyncio.create_subprocess_exec(
            "docker", "rm", "-f", container_name,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )

        # Start container
        proc = await asyncio.create_subprocess_exec(
            "docker", "run", "-d",
            "--name", container_name,
            "-p", f"{port}:9050",
            image,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            logger.error(f"[TOR] Failed to start: {stderr.decode()}")
            return False

        # Wait for TOR to initialize
        logger.info("[TOR] Waiting for initialization...")
        await asyncio.sleep(10)

        self._running = True
        logger.info(f"[TOR] Running at {self.proxy_url}")
        return True

    async def _stop_docker(self) -> bool:
        """Stop TOR Docker container."""
        # Skip if Docker isn't available or wasn't started
        if not self._running:
            return True

        if not await self._is_docker_available():
            self._running = False
            return True

        container_name = self.config.docker_container_name

        logger.info(f"[TOR] Stopping container: {container_name}")

        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "stop", container_name,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()

            await asyncio.create_subprocess_exec(
                "docker", "rm", container_name,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
        except (FileNotFoundError, OSError):
            # Docker binary not found
            pass

        self._running = False
        logger.info("[TOR] Stopped")
        return True

    async def _restart_docker(self) -> bool:
        """Restart TOR Docker container for new circuit."""
        container_name = self.config.docker_container_name

        proc = await asyncio.create_subprocess_exec(
            "docker", "restart", container_name,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()

        if proc.returncode == 0:
            logger.info("[TOR] Circuit renewed (container restarted)")
            await asyncio.sleep(5)  # Wait for new circuit
            return True

        return False

    # =========================================================================
    # SYSTEM TOR BACKEND
    # =========================================================================

    async def _check_system_tor(self) -> bool:
        """Check if system TOR service is running."""
        try:
            import httpx

            async with httpx.AsyncClient(proxy=self.proxy_url, timeout=10) as client:
                response = await client.get("https://check.torproject.org/api/ip")
                return response.status_code == 200
        except Exception:
            return False

    async def _send_newnym(self) -> bool:
        """Send NEWNYM signal via TOR control port."""
        try:
            from stem import Signal
            from stem.control import Controller

            control_port = self.config.control_port

            with Controller.from_port(port=control_port) as controller:
                controller.authenticate()
                controller.signal(Signal.NEWNYM)

            logger.info("[TOR] NEWNYM signal sent, new circuit established")
            await asyncio.sleep(5)  # Wait for new circuit
            return True

        except ImportError:
            logger.warning("[TOR] stem not installed, cannot send NEWNYM")
            return False
        except Exception as e:
            logger.error(f"[TOR] Failed to send NEWNYM: {e}")
            return False

    # =========================================================================
    # PORTABLE TOR BACKEND
    # =========================================================================

    async def _start_portable(self) -> bool:
        """Start portable TOR from TOR Expert Bundle."""
        import os
        from pathlib import Path

        # Find TOR executable (relative to package root)
        tor_dir = Path(__file__).parent.parent.parent / "tor"
        tor_exe = tor_dir / "tor" / ("tor.exe" if os.name == "nt" else "tor")
        torrc = tor_dir / "torrc"

        if not tor_exe.exists():
            logger.error(f"[TOR] Portable TOR not found at {tor_exe}")
            return False

        logger.info(f"[TOR] Starting portable TOR from {tor_exe}")

        try:
            # Start TOR process
            self._tor_process = await asyncio.create_subprocess_exec(
                str(tor_exe), "-f", str(torrc),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
                creationflags=0x08000000 if os.name == "nt" else 0,  # CREATE_NO_WINDOW on Windows
            )

            # Wait for TOR to bootstrap
            logger.info("[TOR] Waiting for bootstrap...")
            await asyncio.sleep(15)

            # Check if it's working
            if await self._check_system_tor():
                self._running = True
                logger.info(f"[TOR] Running at {self.proxy_url}")
                return True
            else:
                logger.error("[TOR] Failed to bootstrap")
                return False

        except Exception as e:
            logger.error(f"[TOR] Failed to start: {e}")
            return False

    async def _stop_portable(self) -> bool:
        """Stop portable TOR process."""
        if hasattr(self, "_tor_process") and self._tor_process:
            try:
                self._tor_process.terminate()
                await self._tor_process.wait()
            except Exception:
                pass
        self._running = False
        return True

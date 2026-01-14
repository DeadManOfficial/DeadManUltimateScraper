"""
Proxy Manager
=============
Advanced proxy rotation and health tracking.
Supports datacenter, residential, and mobile proxies.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from deadman_scraper.core.config import Config

logger = logging.getLogger(__name__)


@dataclass
class ProxyHealth:
    url: str
    type: str
    success_count: int = 0
    fail_count: int = 0
    last_used: datetime | None = None
    is_blocked: bool = False


class ProxyManager:
    """
    Manages proxy rotation and health monitoring.
    NASA Standards: Highly modular, fault-tolerant.
    """

    def __init__(self, config: Config):
        self.config = config
        self.proxies: dict[str, ProxyHealth] = {}
        self.current_index = 0
        self._load_proxies()

    def _load_proxies(self):
        """Load proxies from config or files."""
        if not self.config.proxy.enabled:
            return

        # Load from list in config
        for p_url in self.config.proxy.proxy_list:
            self.proxies[p_url] = ProxyHealth(url=p_url, type=self.config.proxy.type)

        # Load from proxy_file
        if self.config.proxy.proxy_file:
            path = Path(self.config.proxy.proxy_file)
            if path.exists():
                with open(path, encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            self.proxies[line] = ProxyHealth(url=line, type=self.config.proxy.type)

    def get_proxy(self, proxy_type: str | None = None) -> str | None:
        """Get next healthy proxy in rotation."""
        if not self.config.proxy.enabled or not self.proxies:
            return None

        healthy_proxies = [
            p for p in self.proxies.values()
            if not p.is_blocked and (proxy_type is None or p.type == proxy_type)
        ]

        if not healthy_proxies:
            logger.warning(f"No healthy proxies available for type: {proxy_type}")
            return None

        # Round-robin rotation among healthy proxies
        selected = healthy_proxies[self.current_index % len(healthy_proxies)]
        self.current_index += 1

        selected.last_used = datetime.now()
        return selected.url

    async def renew_tor_circuit(self):
        """Request a new identity from TOR."""
        try:
            from stem import Signal
            from stem.control import Controller

            with Controller.from_port(port=self.config.tor.control_port) as controller:
                controller.authenticate(password=self.config.tor.control_port) # Placeholder for password
                controller.signal(Signal.NEWNYM)
                logger.info("[TOR] New identity requested")
                await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"[TOR] Identity renewal failed: {e}")

    def report_success(self, proxy_url: str):
        """Record a successful request with a proxy."""
        if proxy_url in self.proxies:
            self.proxies[proxy_url].success_count += 1
            self.proxies[proxy_url].is_blocked = False

    def report_failure(self, proxy_url: str, is_block: bool = False):
        """Record a failed request with a proxy."""
        if proxy_url in self.proxies:
            self.proxies[proxy_url].fail_count += 1
            if is_block:
                self.proxies[proxy_url].is_blocked = True
                logger.info(f"Proxy marked as blocked: {proxy_url}")

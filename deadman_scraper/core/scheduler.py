"""
Scheduler: Priority Queue + URL Fingerprinting + Deduplication
===============================================================
Manages request scheduling with domain-based concurrency control.
"""

from __future__ import annotations

import heapq
import secrets
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import TYPE_CHECKING, Any

import tldextract

if TYPE_CHECKING:
    from deadman_scraper.core.config import Config
    from deadman_scraper.core.signals import SignalManager


class Priority(IntEnum):
    """Request priorities."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


@dataclass(order=True)
class ScheduledRequest:
    """Represents a request in the scheduler."""
    priority: Priority
    timestamp: float = field(compare=True)  # For FIFO within same priority
    url: str = field(compare=False)
    headers: dict[str, str] = field(default_factory=dict, compare=False)
    meta: dict[str, Any] = field(default_factory=dict, compare=False)
    fingerprint: str = field(default="", compare=False)


class Scheduler:
    """
    Priority-aware request scheduler with domain-based rate limiting.
    NASA Standard: Non-blocking, deterministic, and verifiable.
    """

    def __init__(self, config: Config, signals: SignalManager | None = None):
        self.config = config
        self.signals = signals
        self._queue: list[ScheduledRequest] = []
        self._slots: dict[str, DomainSlot] = defaultdict(DomainSlot)
        self._active_requests: set[str] = set()

    async def enqueue(self, request: ScheduledRequest) -> bool:
        """Add a request to the priority queue."""
        heapq.heappush(self._queue, request)
        return True

    async def dequeue(self) -> ScheduledRequest | None:
        """Get the highest priority request that respects rate limits."""
        if not self._queue:
            return None

        # Try to find a request whose domain is not at capacity
        temp_list = []
        found_req = None

        while self._queue:
            req = heapq.heappop(self._queue)
            domain = self._get_domain(req.url)
            slot = self._slots[domain]

            if slot.active_count < self.config.fetch.max_concurrent_per_domain:
                found_req = req
                slot.active_count += 1
                break
            else:
                temp_list.append(req)

        # Put back requests that were skipped
        for req in temp_list:
            heapq.heappush(self._queue, req)

        return found_req

    def mark_complete(self, request: ScheduledRequest, success: bool = True):
        """Mark a request as finished to free up its domain slot."""
        domain = self._get_domain(request.url)
        slot = self._slots[domain]
        slot.active_count = max(0, slot.active_count - 1)
        slot.last_request_time = datetime.now().timestamp()

        if success:
            slot.total_success += 1
        else:
            slot.total_errors += 1

    def _get_domain(self, url: str) -> str:
        """Extract main domain from URL."""
        ext = tldextract.extract(url)
        return f"{ext.domain}.{ext.suffix}"

    async def get_delay(self, url: str) -> float:
        """Calculate necessary delay for a URL based on its domain history."""
        domain = self._get_domain(url)
        slot = self._slots[domain]

        base_delay = self.config.fetch.download_delay

        # Adaptive backoff if errors detected
        if slot.total_requests > 0:
            error_rate = slot.total_errors / slot.total_requests
            if error_rate > 0.2:
                base_delay *= (1 + error_rate * 5)
            base_delay = min(base_delay, 30.0)

        # Randomize
        if self.config.fetch.randomize_delay:
            variance = self.config.fetch.delay_variance
            multiplier = secrets.SystemRandom().uniform(1 - variance, 1 + variance)
            base_delay *= multiplier

        # Check time since last request
        now = datetime.now().timestamp()
        elapsed = now - slot.last_request_time
        remaining = max(0, base_delay - elapsed)

        return remaining

    def __len__(self) -> int:
        """Number of requests in queue."""
        return len(self._queue)

    @property
    def stats(self) -> dict[str, Any]:
        """Scheduler statistics."""
        return {
            "queue_size": len(self._queue),
            "active_domains": len([s for s in self._slots.values() if s.active_count > 0]),
            "total_slots": len(self._slots)
        }


class DomainSlot:
    """Tracks per-domain request state."""
    def __init__(self):
        self.active_count = 0
        self.last_request_time = 0.0
        self.total_success = 0
        self.total_errors = 0

    @property
    def total_requests(self) -> int:
        return self.total_success + self.total_errors

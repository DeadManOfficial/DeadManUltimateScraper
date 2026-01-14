"""
Event/Signals System (Scrapy pattern)
=====================================
Enables loose coupling between components through event-driven architecture.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, TypeAlias

# Signal handler types
SyncHandler: TypeAlias = Callable[..., Any]
AsyncHandler: TypeAlias = Callable[..., Awaitable[Any]]
Handler: TypeAlias = SyncHandler | AsyncHandler


class Signal(Enum):
    """All signals emitted by the scraper engine."""

    # Engine lifecycle
    ENGINE_STARTED = auto()
    ENGINE_STOPPED = auto()
    ENGINE_PAUSED = auto()
    ENGINE_RESUMED = auto()

    # Request lifecycle
    REQUEST_SCHEDULED = auto()
    REQUEST_DROPPED = auto()
    REQUEST_REACHED_DOWNLOADER = auto()
    REQUEST_LEFT_DOWNLOADER = auto()

    # Response lifecycle
    RESPONSE_RECEIVED = auto()
    RESPONSE_DOWNLOADED = auto()

    # Fetch layer signals
    FETCH_LAYER_1_STARTED = auto()  # curl_cffi
    FETCH_LAYER_2_STARTED = auto()  # Camoufox/Nodriver
    FETCH_LAYER_3_STARTED = auto()  # Undetected ChromeDriver
    FETCH_LAYER_4_STARTED = auto()  # TOR
    FETCH_LAYER_5_STARTED = auto()  # CAPTCHA Solver
    FETCH_FALLBACK = auto()
    FETCH_SUCCESS = auto()
    FETCH_FAILED = auto()

    # Browser pool
    BROWSER_ACQUIRED = auto()
    BROWSER_RELEASED = auto()
    BROWSER_POOL_EXHAUSTED = auto()

    # TOR signals
    TOR_STARTED = auto()
    TOR_STOPPED = auto()
    TOR_CIRCUIT_RENEWED = auto()
    TOR_CONNECTION_FAILED = auto()

    # Proxy signals
    PROXY_ROTATED = auto()
    PROXY_BLACKLISTED = auto()
    PROXY_POOL_EXHAUSTED = auto()

    # Extraction signals
    EXTRACTION_STARTED = auto()
    EXTRACTION_COMPLETED = auto()
    EXTRACTION_FAILED = auto()

    # AI/LLM signals
    LLM_REQUEST_STARTED = auto()
    LLM_REQUEST_COMPLETED = auto()
    LLM_QUOTA_WARNING = auto()
    LLM_PROVIDER_SWITCHED = auto()

    # Discovery signals
    SEARCH_STARTED = auto()
    SEARCH_COMPLETED = auto()
    SEARCH_ENGINE_FAILED = auto()

    # Output signals
    ITEM_SCRAPED = auto()
    ITEM_DROPPED = auto()
    ITEM_EXPORTED = auto()

    # Error signals
    ERROR_RECEIVED = auto()
    SPIDER_ERROR = auto()

    # Stats
    STATS_UPDATED = auto()


@dataclass
class SignalManager:
    """
    Central signal dispatcher.

    Usage:
        signals = SignalManager()

        # Connect handler
        @signals.connect(Signal.FETCH_SUCCESS)
        async def on_success(url: str, content: str):
            print(f"Fetched {url}")

        # Emit signal
        await signals.emit(Signal.FETCH_SUCCESS, url="https://...", content="...")
    """

    _handlers: dict[Signal, list[Handler]] = field(default_factory=lambda: defaultdict(list))
    _disabled: set[Signal] = field(default_factory=set)

    def connect(self, signal: Signal) -> Callable[[Handler], Handler]:
        """Decorator to connect a handler to a signal."""

        def decorator(handler: Handler) -> Handler:
            self._handlers[signal].append(handler)
            return handler

        return decorator

    def connect_handler(self, signal: Signal, handler: Handler) -> None:
        """Programmatically connect a handler to a signal."""
        self._handlers[signal].append(handler)

    def disconnect(self, signal: Signal, handler: Handler) -> bool:
        """Disconnect a handler from a signal. Returns True if found and removed."""
        handlers = self._handlers[signal]
        if handler in handlers:
            handlers.remove(handler)
            return True
        return False

    def disconnect_all(self, signal: Signal) -> int:
        """Disconnect all handlers from a signal. Returns count of removed handlers."""
        count = len(self._handlers[signal])
        self._handlers[signal].clear()
        return count

    def disable(self, signal: Signal) -> None:
        """Temporarily disable a signal (no handlers will be called)."""
        self._disabled.add(signal)

    def enable(self, signal: Signal) -> None:
        """Re-enable a disabled signal."""
        self._disabled.discard(signal)

    async def emit(self, signal: Signal, **kwargs: Any) -> list[Any]:
        """
        Emit a signal, calling all connected handlers.

        Returns list of handler return values.
        Handles both sync and async handlers.
        """
        if signal in self._disabled:
            return []

        results = []
        for handler in self._handlers[signal]:
            try:
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(**kwargs)
                else:
                    result = handler(**kwargs)
                results.append(result)
            except Exception as e:
                # Don't let one handler's error stop others
                results.append(e)

        return results

    def emit_sync(self, signal: Signal, **kwargs: Any) -> list[Any]:
        """
        Synchronously emit a signal (only calls sync handlers).

        For use in contexts where async is not available.
        """
        if signal in self._disabled:
            return []

        results = []
        for handler in self._handlers[signal]:
            if not asyncio.iscoroutinefunction(handler):
                try:
                    result = handler(**kwargs)
                    results.append(result)
                except Exception as e:
                    results.append(e)

        return results

    def handler_count(self, signal: Signal) -> int:
        """Get count of handlers connected to a signal."""
        return len(self._handlers[signal])

    def is_connected(self, signal: Signal, handler: Handler) -> bool:
        """Check if a handler is connected to a signal."""
        return handler in self._handlers[signal]


# Global signals instance (can be replaced per-engine)
Signals = SignalManager()

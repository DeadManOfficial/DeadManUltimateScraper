"""
Engine: Main Orchestrator
=========================
Central controller that coordinates all scraper components.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any

from deadman_scraper.core.config import Config
from deadman_scraper.core.scheduler import Priority, ScheduledRequest, Scheduler
from deadman_scraper.core.signals import Signal, SignalManager


class EngineState(Enum):
    """Engine lifecycle states."""

    IDLE = auto()
    STARTING = auto()
    RUNNING = auto()
    PAUSED = auto()
    STOPPING = auto()
    STOPPED = auto()


@dataclass
class ScrapeResult:
    """Result of a scrape operation."""

    url: str
    success: bool
    status_code: int | None = None
    content: str | None = None
    content_type: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    extracted: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    fetch_layer: int = 0  # Which layer succeeded (1-5)
    timing: dict[str, float] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)


class Engine:
    """
    DEADMAN ULTIMATE SCRAPER - Main Engine

    Coordinates:
    - Scheduler (priority queue + deduplication)
    - Fetch Layer (5-layer adaptive downloader)
    - Stealth (injection + behavioral)
    - Extraction (strategy pattern)
    - AI/LLM (free router)
    - Output Pipeline

    Usage:
        async with Engine() as engine:
            result = await engine.scrape("https://example.com")
            print(result.content)

        # Or batch
        async with Engine() as engine:
            async for result in engine.scrape_many(urls):
                process(result)
    """

    def __init__(self, config: Config | None = None):
        self.config = config or Config.from_env()
        self.signals = SignalManager()
        self.scheduler = Scheduler(self.config, self.signals)

        self._state = EngineState.IDLE
        self._workers: list[asyncio.Task] = []
        self._results_queue: asyncio.Queue[ScrapeResult] = asyncio.Queue()

        # Component instances (lazy loaded)
        self._downloader = None
        self._browser_pool = None
        self._tor_manager = None
        self._extractor = None
        self._llm_router = None
        self._output_pipeline = None

        # Stats
        self._stats = {
            "started_at": None,
            "requests_made": 0,
            "requests_success": 0,
            "requests_failed": 0,
            "bytes_downloaded": 0,
            "layer_usage": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
        }

    async def __aenter__(self) -> Engine:
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.stop()

    @property
    def state(self) -> EngineState:
        return self._state

    async def start(self) -> None:
        """Initialize and start the engine."""
        if self._state != EngineState.IDLE:
            return

        self._state = EngineState.STARTING
        self._stats["started_at"] = datetime.now().isoformat()

        # Initialize components
        await self._init_components()

        # Start worker tasks
        worker_count = self.config.fetch.max_concurrent
        for i in range(worker_count):
            task = asyncio.create_task(self._worker(i))
            self._workers.append(task)

        self._state = EngineState.RUNNING
        await self.signals.emit(Signal.ENGINE_STARTED)

    async def stop(self) -> None:
        """Gracefully stop the engine."""
        if self._state in (EngineState.STOPPED, EngineState.STOPPING):
            return

        self._state = EngineState.STOPPING

        # Cancel workers
        for task in self._workers:
            task.cancel()

        # Wait for workers to finish
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()

        # Cleanup components
        await self._cleanup_components()

        self._state = EngineState.STOPPED
        await self.signals.emit(Signal.ENGINE_STOPPED)

    async def pause(self) -> None:
        """Pause request processing."""
        if self._state == EngineState.RUNNING:
            self._state = EngineState.PAUSED
            await self.signals.emit(Signal.ENGINE_PAUSED)

    async def resume(self) -> None:
        """Resume request processing."""
        if self._state == EngineState.PAUSED:
            self._state = EngineState.RUNNING
            await self.signals.emit(Signal.ENGINE_RESUMED)

    async def scrape(
        self,
        url: str,
        *,
        priority: Priority = Priority.NORMAL,
        headers: dict[str, str] | None = None,
        extract_strategy: str | None = None,
        use_tor: bool = False,
        use_llm: bool = False,
        meta: dict[str, Any] | None = None,
    ) -> ScrapeResult:
        """
        Scrape a single URL.

        Args:
            url: Target URL
            priority: Request priority
            headers: Custom headers
            extract_strategy: Force extraction strategy (css/xpath/regex/llm)
            use_tor: Force TOR routing
            use_llm: Use LLM for extraction/filtering
            meta: Custom metadata passed through pipeline

        Returns:
            ScrapeResult with content and extracted data
        """
        # Build request
        request = ScheduledRequest(
            priority=priority,
            timestamp=datetime.now().timestamp(),
            url=url,
            headers=headers or {},
            meta={
                **(meta or {}),
                "extract_strategy": extract_strategy,
                "force_tor": use_tor,
                "use_llm": use_llm,
                "single_request": True,
            },
        )

        # For single requests, process directly
        return await self._process_request(request)

    async def scrape_many(
        self,
        urls: list[str],
        *,
        priority: Priority = Priority.NORMAL,
        **kwargs,
    ) -> AsyncIterator[ScrapeResult]:
        """
        Scrape multiple URLs concurrently.

        Yields results as they complete.
        """
        # Enqueue all requests
        for url in urls:
            request = ScheduledRequest(
                priority=priority,
                timestamp=datetime.now().timestamp(),
                url=url,
                meta=kwargs.get("meta", {}),
            )
            await self.scheduler.enqueue(request)

        # Yield results as they complete
        pending = len(urls)
        while pending > 0:
            result = await self._results_queue.get()
            pending -= 1
            yield result

    async def search_and_scrape(
        self,
        query: str,
        *,
        engines: list[str] | None = None,
        max_results: int = 20,
        scrape_top: int = 10,
        darkweb: bool = False,
        filter_llm: bool = False,
    ) -> AsyncIterator[ScrapeResult]:
        """
        Multi-engine search then scrape top results.

        This is the Robin pattern: search → scrape → filter → output
        """
        # Import discovery module
        from deadman_scraper.discovery.aggregator import SearchAggregator

        aggregator = SearchAggregator(self.config)

        # Perform search
        search_results = await aggregator.search(
            query,
            engines=engines,
            max_results=max_results,
            darkweb=darkweb,
        )

        # Filter with LLM if requested
        if filter_llm:
            from deadman_scraper.ai.relevance import filter_relevant

            search_results = await filter_relevant(
                query, search_results, self._llm_router, threshold=0.5
            )

        # Scrape top results
        urls = [r["url"] for r in search_results[:scrape_top]]
        async for result in self.scrape_many(urls, meta={"query": query}):
            yield result

    async def _init_components(self) -> None:
        """Initialize all components."""
        # Load API keys
        self.config.load_api_keys()

        # Initialize downloader (lazy - will import when needed)
        # Initialize browser pool (lazy)
        # Initialize TOR if enabled
        if self.config.tor.enabled:
            from deadman_scraper.fetch.tor_manager import TORManager

            self._tor_manager = TORManager(self.config.tor)
            await self._tor_manager.start()

        # Initialize LLM router
        from deadman_scraper.ai.llm_router import FreeLLMRouter

        self._llm_router = FreeLLMRouter(self.config.llm, self.config.api_keys)

    async def _cleanup_components(self) -> None:
        """Cleanup all components."""
        if self._browser_pool:
            await self._browser_pool.close()

        if self._tor_manager:
            await self._tor_manager.stop()

    async def _worker(self, worker_id: int) -> None:
        """Worker coroutine that processes requests from scheduler."""
        while self._state in (EngineState.RUNNING, EngineState.PAUSED):
            # Wait if paused
            while self._state == EngineState.PAUSED:
                await asyncio.sleep(0.1)

            # Get next request
            request = await self.scheduler.dequeue()
            if request is None:
                await asyncio.sleep(0.1)
                continue

            # Respect rate limiting
            delay = await self.scheduler.get_delay(request.url)
            if delay > 0:
                await asyncio.sleep(delay)

            # Process request
            try:
                result = await self._process_request(request)
                self.scheduler.mark_complete(request, success=result.success)

                # Only queue results for batch operations
                if not request.meta.get("single_request"):
                    await self._results_queue.put(result)

            except Exception as e:
                self.scheduler.mark_complete(request, success=False)
                result = ScrapeResult(
                    url=request.url,
                    success=False,
                    error=str(e),
                )
                if not request.meta.get("single_request"):
                    await self._results_queue.put(result)

    async def _process_request(self, request: ScheduledRequest) -> ScrapeResult:
        """Process a single request through the pipeline."""
        start_time = datetime.now().timestamp()
        self._stats["requests_made"] += 1

        # Signal: request reached downloader
        await self.signals.emit(Signal.REQUEST_REACHED_DOWNLOADER, request=request)

        # Determine if TOR required
        use_tor = request.meta.get("force_tor") or ".onion" in request.url

        # Import and use downloader
        from deadman_scraper.fetch.downloader import AdaptiveDownloader
        from deadman_scraper.fetch.proxy_manager import ProxyManager

        if not self._downloader:
            self._proxy_manager = ProxyManager(self.config)
            self._downloader = AdaptiveDownloader(
                self.config, self.signals, self._tor_manager, self._proxy_manager
            )

        # Fetch content
        fetch_result = await self._downloader.fetch(
            request.url,
            headers=request.headers,
            force_tor=use_tor,
        )

        if not fetch_result.success:
            self._stats["requests_failed"] += 1
            return ScrapeResult(
                url=request.url,
                success=False,
                error=fetch_result.error,
                fetch_layer=fetch_result.layer,
                timing={"total": datetime.now().timestamp() - start_time},
            )

        self._stats["requests_success"] += 1
        self._stats["layer_usage"][fetch_result.layer] += 1
        self._stats["bytes_downloaded"] += len(fetch_result.content or "")

        # Extract content if strategy specified
        extracted = {}
        strategy = request.meta.get("extract_strategy")
        if strategy and fetch_result.content:
            from deadman_scraper.extract.extractor import Extractor

            if not self._extractor:
                self._extractor = Extractor(self.config.extraction)

            extracted = await self._extractor.extract(
                fetch_result.content,
                strategy=strategy,
                url=request.url,
                llm_router=self._llm_router if request.meta.get("use_llm") else None,
            )

        # Signal: item scraped
        await self.signals.emit(
            Signal.ITEM_SCRAPED,
            url=request.url,
            content_length=len(fetch_result.content or ""),
        )

        return ScrapeResult(
            url=request.url,
            success=True,
            status_code=fetch_result.status_code,
            content=fetch_result.content,
            content_type=fetch_result.content_type,
            headers=fetch_result.headers,
            extracted=extracted,
            fetch_layer=fetch_result.layer,
            timing={
                "total": datetime.now().timestamp() - start_time,
                "fetch": fetch_result.timing,
            },
            meta=request.meta,
        )

    @property
    def stats(self) -> dict[str, Any]:
        """Get engine statistics."""
        return {
            **self._stats,
            "scheduler": self.scheduler.stats,
            "state": self._state.name,
        }

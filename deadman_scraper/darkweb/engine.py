"""
Dark Web Engine - Unified Orchestrator
=======================================

Integrates all dark web scraping capabilities:
- TorCrawl.py patterns (depth crawling)
- Darker patterns (14-engine meta-search)
- Fresh Onions patterns (validation, clone detection)
- DarkScrape patterns (media extraction)
- SpiderFoot patterns (OSINT collection)

ALL FREE FOREVER - DeadManOfficial
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable
import logging
import json

from .meta_search import DarkMetaSearch, SearchResult
from .crawler import OnionCrawler, CrawlConfig, CrawlResult
from .media import MediaExtractor, ExtractionConfig, MediaItem
from .validators import OnionValidator, CloneDetector, OnionStatus
from .osint import OSINTCollector, OSINTEntity, OSINTReport

logger = logging.getLogger(__name__)


@dataclass
class DarkWebConfig:
    """Configuration for DarkWebEngine."""
    # Search settings
    search_engines: list = field(default_factory=lambda: ["ahmia", "torch", "haystack"])
    search_max_results: int = 50

    # Crawl settings
    crawl_max_depth: int = 2
    crawl_max_pages: int = 100
    crawl_delay: float = 1.0

    # Media settings
    extract_media: bool = True
    download_media: bool = False
    media_path: str = "./darkweb_media"
    detect_faces: bool = False

    # OSINT settings
    osint_types: list = field(default_factory=lambda: [
        "email", "bitcoin", "onion_v3", "pgp_key_id"
    ])

    # Validation settings
    validate_onions: bool = True
    detect_clones: bool = True

    # Output settings
    output_format: str = "json"  # json, sqlite
    output_path: str = "./darkweb_results"

    # Performance settings
    max_concurrent: int = 5
    timeout: int = 120


@dataclass
class DarkWebResult:
    """Unified result from dark web operations."""
    operation: str
    target: str
    timestamp: str
    duration_seconds: float = 0

    # Search results
    search_results: list = field(default_factory=list)

    # Crawl results
    crawl_results: list = field(default_factory=list)
    crawl_stats: dict = field(default_factory=dict)

    # Media results
    media_items: list = field(default_factory=list)

    # OSINT results
    osint_entities: list = field(default_factory=list)
    osint_stats: dict = field(default_factory=dict)

    # Validation results
    validation_results: list = field(default_factory=list)
    clone_detections: list = field(default_factory=list)

    # Errors
    errors: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "operation": self.operation,
            "target": self.target,
            "timestamp": self.timestamp,
            "duration_seconds": self.duration_seconds,
            "search_results": [r.url if hasattr(r, 'url') else r for r in self.search_results],
            "crawl_stats": self.crawl_stats,
            "media_count": len(self.media_items),
            "osint_count": len(self.osint_entities),
            "osint_stats": self.osint_stats,
            "validation_count": len(self.validation_results),
            "clone_count": len(self.clone_detections),
            "errors": self.errors,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


class DarkWebEngine:
    """
    Unified dark web scraping engine.
    Orchestrates search, crawl, extract, and OSINT operations.
    """

    def __init__(
        self,
        tor_manager=None,
        fetch_func=None,
        scraper=None,
        config: DarkWebConfig = None,
    ):
        """
        Initialize DarkWebEngine.

        Args:
            tor_manager: TOR manager for .onion requests
            fetch_func: Async function for HTTP requests
            scraper: CentralScraper instance (optional)
            config: DarkWebConfig settings
        """
        self.tor_manager = tor_manager
        self.fetch_func = fetch_func
        self.scraper = scraper
        self.config = config or DarkWebConfig()

        # Initialize components
        self.meta_search = DarkMetaSearch(
            tor_manager=tor_manager,
            fetch_func=fetch_func,
            max_concurrent=self.config.max_concurrent,
            engines=self.config.search_engines,
        )

        self.validator = OnionValidator(
            tor_manager=tor_manager,
            fetch_func=fetch_func,
            timeout=self.config.timeout,
        )

        self.clone_detector = CloneDetector()

        self.osint_collector = OSINTCollector(
            tor_manager=tor_manager,
            fetch_func=fetch_func,
            meta_search=self.meta_search,
            extract_types=self.config.osint_types,
        )

        logger.info("[DarkWebEngine] Initialized with all components")

    async def search(
        self,
        query: str,
        max_results: int = None,
        scrape_results: bool = False,
    ) -> DarkWebResult:
        """
        Search across dark web search engines.

        Args:
            query: Search query
            max_results: Maximum results (default from config)
            scrape_results: Whether to scrape search results

        Returns:
            DarkWebResult with search results
        """
        start_time = asyncio.get_event_loop().time()
        result = DarkWebResult(
            operation="search",
            target=query,
            timestamp=datetime.utcnow().isoformat(),
        )

        try:
            max_results = max_results or self.config.search_max_results

            # Execute search
            search_results = await self.meta_search.search(
                query,
                max_results=max_results,
            )

            result.search_results = search_results

            # Optionally scrape results
            if scrape_results and self.scraper:
                scraped = await self.meta_search.search_and_scrape(
                    query,
                    scraper=self.scraper,
                    max_results=min(10, max_results),
                )
                # Add scraped content to results
                for item in scraped:
                    if "content" in item:
                        result.crawl_results.append(item)

            logger.info(f"[DarkWebEngine] Search found {len(search_results)} results")

        except Exception as e:
            logger.error(f"[DarkWebEngine] Search failed: {e}")
            result.errors.append(str(e))

        result.duration_seconds = asyncio.get_event_loop().time() - start_time
        return result

    async def crawl(
        self,
        seed_url: str,
        max_depth: int = None,
        max_pages: int = None,
        callback: Callable = None,
    ) -> DarkWebResult:
        """
        Crawl an onion site with depth control.

        Args:
            seed_url: Starting URL
            max_depth: Maximum crawl depth
            max_pages: Maximum pages to crawl
            callback: Optional callback for each page

        Returns:
            DarkWebResult with crawl results
        """
        start_time = asyncio.get_event_loop().time()
        result = DarkWebResult(
            operation="crawl",
            target=seed_url,
            timestamp=datetime.utcnow().isoformat(),
        )

        try:
            crawl_config = CrawlConfig(
                max_depth=max_depth or self.config.crawl_max_depth,
                max_pages=max_pages or self.config.crawl_max_pages,
                delay=self.config.crawl_delay,
                output_format=self.config.output_format,
                output_path=f"{self.config.output_path}/crawl_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{self.config.output_format}",
            )

            crawler = OnionCrawler(
                tor_manager=self.tor_manager,
                fetch_func=self.fetch_func,
                config=crawl_config,
            )

            crawl_results = await crawler.crawl(seed_url, callback=callback)

            result.crawl_results = crawl_results
            result.crawl_stats = crawler.get_stats()

            # Extract media from crawled pages
            if self.config.extract_media:
                media_config = ExtractionConfig(
                    download_media=self.config.download_media,
                    download_path=self.config.media_path,
                    detect_faces=self.config.detect_faces,
                )
                extractor = MediaExtractor(
                    tor_manager=self.tor_manager,
                    fetch_func=self.fetch_func,
                    config=media_config,
                )

                for crawl_result in crawl_results:
                    if crawl_result.status == "success" and crawl_result.html:
                        media_items = await extractor.extract_from_url(
                            crawl_result.url,
                            html=crawl_result.html,
                        )
                        result.media_items.extend(media_items)

            logger.info(f"[DarkWebEngine] Crawl complete: {len(crawl_results)} pages")

        except Exception as e:
            logger.error(f"[DarkWebEngine] Crawl failed: {e}")
            result.errors.append(str(e))

        result.duration_seconds = asyncio.get_event_loop().time() - start_time
        return result

    async def collect_osint(
        self,
        target: str,
        search_dark_web: bool = True,
    ) -> DarkWebResult:
        """
        Collect OSINT on a target.

        Args:
            target: Target to investigate
            search_dark_web: Whether to search dark web for target

        Returns:
            DarkWebResult with OSINT findings
        """
        start_time = asyncio.get_event_loop().time()
        result = DarkWebResult(
            operation="osint",
            target=target,
            timestamp=datetime.utcnow().isoformat(),
        )

        try:
            if search_dark_web:
                # Full investigation
                report = await self.osint_collector.investigate_target(target)
                result.osint_entities = report.entities
                result.osint_stats = report.stats
            else:
                # Just collect from URL
                entities = await self.osint_collector.collect_from_url(target)
                result.osint_entities = entities
                result.osint_stats = {
                    "total": len(entities),
                    "by_type": {},
                }
                for entity in entities:
                    if entity.entity_type not in result.osint_stats["by_type"]:
                        result.osint_stats["by_type"][entity.entity_type] = 0
                    result.osint_stats["by_type"][entity.entity_type] += 1

            logger.info(f"[DarkWebEngine] OSINT collected {len(result.osint_entities)} entities")

        except Exception as e:
            logger.error(f"[DarkWebEngine] OSINT failed: {e}")
            result.errors.append(str(e))

        result.duration_seconds = asyncio.get_event_loop().time() - start_time
        return result

    async def validate_onions(
        self,
        urls: list[str],
    ) -> DarkWebResult:
        """
        Validate multiple onion URLs.

        Args:
            urls: List of onion URLs to validate

        Returns:
            DarkWebResult with validation status
        """
        start_time = asyncio.get_event_loop().time()
        result = DarkWebResult(
            operation="validate",
            target=f"{len(urls)} onion URLs",
            timestamp=datetime.utcnow().isoformat(),
        )

        try:
            statuses = await self.validator.validate_batch(
                urls,
                max_concurrent=self.config.max_concurrent,
            )

            result.validation_results = statuses

            # Check for clones
            if self.config.detect_clones:
                for status in statuses:
                    if status.is_alive:
                        # Fetch content for clone check
                        html = await self._fetch(status.url)
                        if html:
                            is_clone, original, score = self.clone_detector.check_clone(
                                status.url,
                                html,
                            )
                            if is_clone:
                                result.clone_detections.append({
                                    "url": status.url,
                                    "clone_of": original,
                                    "similarity": score,
                                })

            alive_count = sum(1 for s in statuses if s.is_alive)
            logger.info(f"[DarkWebEngine] Validated {len(urls)} onions, {alive_count} alive")

        except Exception as e:
            logger.error(f"[DarkWebEngine] Validation failed: {e}")
            result.errors.append(str(e))

        result.duration_seconds = asyncio.get_event_loop().time() - start_time
        return result

    async def full_investigation(
        self,
        target: str,
        crawl_depth: int = 1,
        max_pages: int = 20,
    ) -> DarkWebResult:
        """
        Full dark web investigation combining all capabilities.

        Args:
            target: URL or search query
            crawl_depth: Depth to crawl discovered sites
            max_pages: Max pages per site

        Returns:
            Comprehensive DarkWebResult
        """
        start_time = asyncio.get_event_loop().time()
        result = DarkWebResult(
            operation="full_investigation",
            target=target,
            timestamp=datetime.utcnow().isoformat(),
        )

        try:
            # Step 1: Search if target is not a URL
            if not target.startswith("http"):
                logger.info("[DarkWebEngine] Step 1: Searching dark web...")
                search_result = await self.search(target, max_results=20)
                result.search_results = search_result.search_results

                # Get top URLs for crawling
                urls_to_crawl = [r.url for r in search_result.search_results[:5]]
            else:
                urls_to_crawl = [target]

            # Step 2: Validate discovered onions
            if self.config.validate_onions and urls_to_crawl:
                logger.info("[DarkWebEngine] Step 2: Validating onions...")
                onion_urls = [u for u in urls_to_crawl if ".onion" in u]
                if onion_urls:
                    validation_result = await self.validate_onions(onion_urls)
                    result.validation_results = validation_result.validation_results
                    result.clone_detections = validation_result.clone_detections

                    # Filter to alive sites
                    urls_to_crawl = [
                        s.url for s in validation_result.validation_results
                        if s.is_alive
                    ]

            # Step 3: Crawl alive sites
            logger.info("[DarkWebEngine] Step 3: Crawling sites...")
            for url in urls_to_crawl[:3]:  # Limit to top 3
                crawl_result = await self.crawl(
                    url,
                    max_depth=crawl_depth,
                    max_pages=max_pages,
                )
                result.crawl_results.extend(crawl_result.crawl_results)
                result.media_items.extend(crawl_result.media_items)
                result.crawl_stats.update(crawl_result.crawl_stats)

            # Step 4: Collect OSINT from all crawled content
            logger.info("[DarkWebEngine] Step 4: Collecting OSINT...")
            for crawl_result in result.crawl_results:
                if hasattr(crawl_result, 'html') and crawl_result.html:
                    entities = await self.osint_collector.collect_from_url(
                        crawl_result.url,
                        html=crawl_result.html,
                    )
                    result.osint_entities.extend(entities)

            # Calculate final stats
            result.osint_stats = {
                "total": len(result.osint_entities),
                "by_type": {},
            }
            for entity in result.osint_entities:
                if entity.entity_type not in result.osint_stats["by_type"]:
                    result.osint_stats["by_type"][entity.entity_type] = 0
                result.osint_stats["by_type"][entity.entity_type] += 1

            logger.info(f"[DarkWebEngine] Full investigation complete")

        except Exception as e:
            logger.error(f"[DarkWebEngine] Investigation failed: {e}")
            result.errors.append(str(e))

        result.duration_seconds = asyncio.get_event_loop().time() - start_time

        # Save results
        await self._save_result(result)

        return result

    async def _fetch(self, url: str) -> Optional[str]:
        """Fetch URL content."""
        try:
            if self.tor_manager:
                return await self._fetch_via_tor(url)
            elif self.fetch_func:
                return await self.fetch_func(url, timeout=self.config.timeout)
            return None
        except Exception:
            return None

    async def _fetch_via_tor(self, url: str) -> Optional[str]:
        """Fetch URL content via TOR proxy."""
        try:
            import httpx

            await self.tor_manager.ensure_running()
            proxy_url = self.tor_manager.proxy_url

            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout),
                proxy=proxy_url,
            ) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    return response.text
                return None
        except Exception as e:
            logger.error(f"TOR fetch failed for {url}: {e}")
            return None

    async def _save_result(self, result: DarkWebResult):
        """Save result to file."""
        try:
            output_path = Path(self.config.output_path)
            output_path.mkdir(parents=True, exist_ok=True)

            filename = f"{result.operation}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = output_path / filename

            filepath.write_text(result.to_json())
            logger.info(f"[DarkWebEngine] Results saved to {filepath}")

        except Exception as e:
            logger.error(f"[DarkWebEngine] Failed to save results: {e}")

    def register_legitimate_site(self, domain: str, html: str):
        """Register a legitimate site for clone detection."""
        self.clone_detector.register_legitimate(domain, html)


# Convenience function
async def investigate_dark_web(
    target: str,
    tor_manager=None,
    fetch_func=None,
) -> DarkWebResult:
    """Quick dark web investigation."""
    engine = DarkWebEngine(
        tor_manager=tor_manager,
        fetch_func=fetch_func,
    )
    return await engine.full_investigation(target)

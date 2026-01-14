"""
DEADMAN CENTRAL SCRAPER (GOD MODULE)
====================================
NASA-Grade Scraping Framework for Unlimited Freedom.

Adheres to NASA-8739.12 Standards:
- Highly modular and fault-tolerant.
- Comprehensive documentation.
- Integrated security and bypass logic.
- Adaptive multi-layer fetching.

Version: 2.0.0 (Absolute Freedom Edition)
"""

import asyncio
import logging
import sys
from pathlib import Path
from urllib.parse import urlparse

# Add token-optimization to path
sys.path.append(str(Path("G:/token-optimization")))

from collections.abc import AsyncIterator

from pydantic import BaseModel
from token_optimizer.core import TokenOptimizer

from deadman_scraper.ai.llm_router import FreeLLMRouter
from deadman_scraper.core.config import Config
from deadman_scraper.core.engine import Engine, ScrapeResult
from deadman_scraper.core.scheduler import Priority
from deadman_scraper.utils.sanitizer import InputSanitizer
from deadman_scraper.utils.traceability import AuditLogger

# === NASA STANDARD LOGGING ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d - %(message)s',
    handlers=[
        logging.FileHandler("central_scraper.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("CentralScraper")


class ScrapeRequest(BaseModel):
    """
    NASA Standard: Strict input validation via Pydantic.
    """
    url: str
    priority: Priority = Priority.NORMAL
    use_tor: bool = False
    use_llm: bool = False
    steal_session: bool = False
    extract_strategy: str | None = None
    headers: dict[str, str] = {}


class CentralScraper:
    """
    The "God" Module: Centralized entry point for ALL scraping logic.

    This module merges logic from over 60 specialized scripts into a
    unified, robust, and unstoppable scraping framework.
    """

    def __init__(self, config_path: str | Path | None = None):
        """
        Initialize the Central Scraper with optional custom configuration.

        Args:
            config_path: Path to YAML configuration file.
        """
        self.config = Config.from_yaml(config_path) if config_path else Config.from_env()
        self.engine: Engine | None = None
        logger.info("CentralScraper initialized with absolute freedom protocols.")

    async def __aenter__(self):
        self.engine = Engine(self.config)
        self.audit = AuditLogger(self.engine.signals)
        self.optimizer = TokenOptimizer(
            enable_caching=self.config.quota.enable_caching,
            cache_dir=self.config.quota.cache_dir
        )
        self.llm = FreeLLMRouter(self.config.llm, self.config.api_keys)
        await self.engine.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.engine:
            await self.engine.stop()

    async def scrape(self, request: ScrapeRequest) -> ScrapeResult:
        """
        Execute a single scrape operation with adaptive bypass and input sanitization.

        NASA Standard: Comprehensive error isolation and input validation.
        """
        if not self.engine:
            raise RuntimeError("Engine not started. Use 'async with' context manager.")

        # 1. Sanitize Inputs
        safe_url = InputSanitizer.sanitize_url(request.url)
        if not safe_url:
            return ScrapeResult(url=request.url, success=False, error="Input Sanitization Failed (Invalid URL)")

        request.url = safe_url
        request.headers = InputSanitizer.clean_headers(request.headers)

        # 2. Session Hijacking (if requested)
        if request.steal_session:
            from deadman_scraper.stealth.session import SessionStealer
            domain = urlparse(request.url).netloc
            cookies = SessionStealer().steal_cookies(domain)
            # Add to headers (simplified)
            if cookies:
                cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
                request.headers["Cookie"] = cookie_str

        try:
            logger.info(f"Initiating scrape for: {request.url}")
            result = await self.engine.scrape(
                url=request.url,
                priority=request.priority,
                headers=request.headers,
                extract_strategy=request.extract_strategy,
                use_tor=request.use_tor,
                use_llm=request.use_llm
            )

            if result.success:
                logger.info(f"Successfully scraped {request.url} via layer {result.fetch_layer}")
            else:
                logger.error(f"Failed to scrape {request.url}: {result.error}")

            return result

        except Exception as e:
            logger.exception(f"Critical failure during scrape of {request.url}")
            return ScrapeResult(url=request.url, success=False, error=str(e))

    async def scrape_batch(self, requests: list[ScrapeRequest]) -> AsyncIterator[ScrapeResult]:
        """
        Execute multiple scrape operations concurrently.

        Yields results as they are completed.
        """
        if not self.engine:
            raise RuntimeError("Engine not started.")

        urls = [req.url for req in requests]
        logger.info(f"Starting batch scrape for {len(urls)} targets.")

        async for result in self.engine.scrape_many(urls):
            yield result

    async def search_intelligence(self, query: str, darkweb: bool = False) -> AsyncIterator[ScrapeResult]:
        """
        Perform multi-engine search and intelligence gathering.

        This implements the "Robin" pattern: search -> scrape -> intelligence.
        """
        if not self.engine:
            raise RuntimeError("Engine not started.")

        logger.info(f"Gathering intelligence for query: {query} (Darkweb: {darkweb})")
        async for result in self.engine.search_and_scrape(query, darkweb=darkweb, filter_llm=True):
            yield result

    async def gather_intel_analysis(self, prompt: str, task_type: str = "analyze") -> str | None:
        """
        Perform AI-powered intelligence analysis on gathered data.
        Automatically applies NASA-standard token optimization.
        """
        if not self.optimizer or not self.llm:
            raise RuntimeError("Engine components not initialized.")

        # 1. Optimize Prompt
        clean_prompt = self.optimizer.optimize_prompt(prompt, compress=True)

        # 2. Check Cache
        cached = self.optimizer.check_cache(clean_prompt)
        if cached:
            logger.info("Intelligence cache hit. Skipping API request.")
            return cached

        # 3. Request LLM Analysis
        response = await self.llm.complete(clean_prompt)

        if response.success:
            # 4. Cache and Return
            self.optimizer.cache_response(clean_prompt, response.content, tokens=response.tokens_used)
            return response.content
        else:
            logger.error(f"Intelligence analysis failed: {response.error}")
            return None


# === CLI ENTRY POINT ===
if __name__ == "__main__":
    async def main():
        async with CentralScraper() as god:
            # Example: Scrape Reddit with LLM intelligence
            req = ScrapeRequest(
                url="https://www.reddit.com/r/WebScrapingTools/",
                use_llm=True,
                extract_strategy="auto"
            )
            result = await god.scrape(req)
            print(f"Status: {result.status_code}")
            print(f"Content Preview: {result.content[:200] if result.content else 'N/A'}")

    asyncio.run(main())

"""
Dark Web Meta-Search Engine
===========================

Aggregates results from 14+ dark web search engines.
Inspired by: github.com/saadejazz/darker

Engines:
- Ahmia, Torch, Haystack, DarkSearch, not Evil
- Candle, Tor66, Visitor, Onion Land, Deep Link
- Grams, multiVAC, Deep Paste, Phobos

ALL FREE FOREVER - DeadManOfficial
"""

import asyncio
import re
from dataclasses import dataclass, field
from typing import Optional, Callable, List
from urllib.parse import quote_plus, urljoin
from collections import Counter
import logging

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Single search result from dark web."""
    url: str
    title: str = ""
    description: str = ""
    source_engine: str = ""
    rank: int = 0
    occurrence_count: int = 1

    def __hash__(self):
        return hash(self.url)

    def __eq__(self, other):
        return self.url == other.url


@dataclass
class DarkSearchEngine:
    """Configuration for a dark web search engine."""
    name: str
    search_url: str
    requires_tor: bool = True
    result_selector: str = ""
    title_selector: str = ""
    link_selector: str = ""
    desc_selector: str = ""
    parser: Optional[Callable] = None
    enabled: bool = True


class DarkMetaSearch:
    """
    Meta-search engine for the dark web.
    Queries multiple engines in parallel and ranks results by frequency.
    """

    # 14 Dark Web Search Engines
    ENGINES = {
        # Clearnet gateways (work without TOR)
        "ahmia": DarkSearchEngine(
            name="Ahmia",
            search_url="https://ahmia.fi/search/?q={query}",
            requires_tor=False,
            result_selector="li.result",
            title_selector="h4",
            link_selector="a.onion",
            desc_selector="p",
        ),
        "darksearch": DarkSearchEngine(
            name="DarkSearch",
            search_url="https://darksearch.io/api/search?query={query}&page=1",
            requires_tor=False,
            parser="_parse_darksearch_api",
        ),

        # .onion engines (require TOR)
        "torch": DarkSearchEngine(
            name="Torch",
            search_url="http://xmh57jrknzkhv6y3ls3ubitzfqnkrwxhopf5aygthi7d6rplyvk3noyd.onion/cgi-bin/omega/omega?P={query}",
            requires_tor=True,
            result_selector="dl",
            title_selector="dt a",
            link_selector="dt a",
            desc_selector="dd",
        ),
        "haystack": DarkSearchEngine(
            name="Haystack",
            search_url="http://haystak5njsmn2hqkewecpaxetahtwhsbsa64jom2k22z5afxhnpxfid.onion/?q={query}",
            requires_tor=True,
            result_selector=".result",
            title_selector="a.title",
            link_selector="a.title",
            desc_selector=".description",
        ),
        "notevil": DarkSearchEngine(
            name="not Evil",
            search_url="http://notevilmtxf25uw7tskqxj6njlpebyrmlrerfv5hc4tuq7c7hilbyiqd.onion/index.php?q={query}",
            requires_tor=True,
            result_selector=".result",
            title_selector="a",
            link_selector="a",
            desc_selector="p",
        ),
        "candle": DarkSearchEngine(
            name="Candle",
            search_url="http://gjobqjj7wyczbqie.onion/search?q={query}",
            requires_tor=True,
            result_selector=".result",
            title_selector="a",
            link_selector="a",
            desc_selector=".desc",
        ),
        "tor66": DarkSearchEngine(
            name="Tor66",
            search_url="http://tor66sewebgixwhcqfnp5inzp5x5uohhdy3kvtnyfxc2e5mxiber6fnad.onion/search?q={query}",
            requires_tor=True,
            result_selector=".result",
            title_selector="h2 a",
            link_selector="h2 a",
            desc_selector="p",
        ),
        "onionland": DarkSearchEngine(
            name="Onion Land",
            search_url="http://3bbad7fauber4fqtl5a4hreebfjjgirb6yehvrgqkaxw6qzirbaoqiad.onion/search?q={query}",
            requires_tor=True,
            result_selector=".result-block",
            title_selector=".title a",
            link_selector=".title a",
            desc_selector=".desc",
        ),
        "deeplink": DarkSearchEngine(
            name="Deep Link",
            search_url="http://deeplinkdeatbml7.onion/search?q={query}",
            requires_tor=True,
            result_selector=".search-result",
            title_selector="a.title",
            link_selector="a.title",
            desc_selector=".snippet",
        ),
        "visitor": DarkSearchEngine(
            name="Visitor",
            search_url="http://visitorfi5kl7q4h.onion/search/?q={query}",
            requires_tor=True,
            result_selector="li.result",
            title_selector="a",
            link_selector="a",
            desc_selector="p",
        ),
        "grams": DarkSearchEngine(
            name="Grams",
            search_url="http://grams7ebnju7gwjl.onion/results.html?q={query}",
            requires_tor=True,
            result_selector=".result",
            title_selector="a",
            link_selector="a",
            desc_selector=".desc",
        ),
        "multivac": DarkSearchEngine(
            name="multiVAC",
            search_url="http://multivacigqzqqon.onion/search?q={query}",
            requires_tor=True,
            result_selector=".result",
            title_selector="h3 a",
            link_selector="h3 a",
            desc_selector="p",
        ),
        "deeppaste": DarkSearchEngine(
            name="Deep Paste",
            search_url="http://depastedihrn3jtw.onion/search?q={query}",
            requires_tor=True,
            result_selector=".paste-result",
            title_selector="a",
            link_selector="a",
            desc_selector=".content",
        ),
        "phobos": DarkSearchEngine(
            name="Phobos",
            search_url="http://phobosxilamwcg75xt22id7aywkzol6q6rfl2flipcqoc4e4ahima5id.onion/search?query={query}",
            requires_tor=True,
            result_selector=".search-result",
            title_selector="a.title",
            link_selector="a.title",
            desc_selector=".description",
        ),
    }

    def __init__(
        self,
        tor_manager=None,
        fetch_func=None,
        max_concurrent: int = 5,
        timeout: int = 60,
        engines: list[str] = None,
        exclude_engines: list[str] = None,
    ):
        """
        Initialize DarkMetaSearch.

        Args:
            tor_manager: TOR manager for .onion requests
            fetch_func: Async function for HTTP requests
            max_concurrent: Max parallel engine queries
            timeout: Request timeout in seconds
            engines: List of engine names to use (default: all)
            exclude_engines: List of engine names to exclude
        """
        self.tor_manager = tor_manager
        self.fetch_func = fetch_func
        self.max_concurrent = max_concurrent
        self.timeout = timeout

        # Filter engines
        self.active_engines = {}
        for name, engine in self.ENGINES.items():
            if engines and name not in engines:
                continue
            if exclude_engines and name in exclude_engines:
                continue
            if engine.enabled:
                self.active_engines[name] = engine

    async def search(
        self,
        query: str,
        max_results: int = 100,
        include_clearnet: bool = True,
        include_onion: bool = True,
    ) -> list[SearchResult]:
        """
        Search across all active engines.

        Args:
            query: Search query
            max_results: Maximum results to return
            include_clearnet: Include clearnet gateway results
            include_onion: Include .onion engine results (requires TOR)

        Returns:
            List of SearchResult objects ranked by occurrence frequency
        """
        logger.info(f"[DarkMetaSearch] Searching for: {query}")

        # Prepare tasks
        tasks = []
        engines_to_query = []

        for name, engine in self.active_engines.items():
            if engine.requires_tor and not include_onion:
                continue
            if not engine.requires_tor and not include_clearnet:
                continue
            if engine.requires_tor and not self.tor_manager:
                logger.warning(f"Skipping {name}: TOR not available")
                continue

            engines_to_query.append(name)
            tasks.append(self._search_engine(engine, query))

        logger.info(f"[DarkMetaSearch] Querying {len(tasks)} engines: {engines_to_query}")

        # Execute in parallel with semaphore
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def limited_search(coro):
            async with semaphore:
                return await coro

        results_lists = await asyncio.gather(
            *[limited_search(t) for t in tasks],
            return_exceptions=True
        )

        # Aggregate and rank results
        all_results = []
        url_counter = Counter()
        url_to_result = {}

        for i, results in enumerate(results_lists):
            if isinstance(results, Exception):
                logger.error(f"Engine {engines_to_query[i]} failed: {results}")
                continue

            for result in results:
                url_counter[result.url] += 1
                if result.url not in url_to_result:
                    url_to_result[result.url] = result
                else:
                    # Merge data from multiple sources
                    existing = url_to_result[result.url]
                    if not existing.title and result.title:
                        existing.title = result.title
                    if not existing.description and result.description:
                        existing.description = result.description

        # Rank by occurrence count
        for url, count in url_counter.most_common(max_results):
            result = url_to_result[url]
            result.occurrence_count = count
            all_results.append(result)

        logger.info(f"[DarkMetaSearch] Found {len(all_results)} unique results")
        return all_results

    async def _search_engine(
        self,
        engine: DarkSearchEngine,
        query: str,
    ) -> list[SearchResult]:
        """Search a single engine."""
        results = []

        try:
            url = engine.search_url.format(query=quote_plus(query))

            # Fetch content
            if engine.requires_tor and self.tor_manager:
                content = await self._fetch_via_tor(url)
            elif self.fetch_func:
                content = await self.fetch_func(url, timeout=self.timeout)
            else:
                logger.warning(f"No fetch function for {engine.name}")
                return []

            if not content:
                return []

            # Parse results
            if engine.parser:
                parse_method = getattr(self, engine.parser, None)
                if parse_method:
                    results = parse_method(content, engine)
            else:
                results = self._parse_html(content, engine)

            # Tag results with source
            for result in results:
                result.source_engine = engine.name

            logger.debug(f"[{engine.name}] Found {len(results)} results")

        except Exception as e:
            logger.error(f"[{engine.name}] Search failed: {e}")

        return results

    def _parse_html(
        self,
        html: str,
        engine: DarkSearchEngine,
    ) -> list[SearchResult]:
        """Parse HTML search results."""
        results = []
        soup = BeautifulSoup(html, "lxml")

        for item in soup.select(engine.result_selector)[:50]:
            try:
                # Extract title
                title_elem = item.select_one(engine.title_selector)
                title = title_elem.get_text(strip=True) if title_elem else ""

                # Extract URL
                link_elem = item.select_one(engine.link_selector)
                url = ""
                if link_elem:
                    url = link_elem.get("href", "")
                    # Handle relative URLs
                    if url and not url.startswith(("http://", "https://")):
                        url = urljoin(engine.search_url, url)

                # Extract description
                desc_elem = item.select_one(engine.desc_selector)
                description = desc_elem.get_text(strip=True) if desc_elem else ""

                if url and ".onion" in url:
                    results.append(SearchResult(
                        url=url,
                        title=title,
                        description=description[:500],
                    ))

            except Exception as e:
                logger.debug(f"Failed to parse result: {e}")
                continue

        return results

    def _parse_darksearch_api(
        self,
        content: str,
        engine: DarkSearchEngine,
    ) -> list[SearchResult]:
        """Parse DarkSearch JSON API response."""
        import json
        results = []

        try:
            data = json.loads(content)
            for item in data.get("data", []):
                results.append(SearchResult(
                    url=item.get("link", ""),
                    title=item.get("title", ""),
                    description=item.get("description", "")[:500],
                ))
        except Exception as e:
            logger.error(f"DarkSearch API parse error: {e}")

        return results

    async def search_and_scrape(
        self,
        query: str,
        scraper,
        max_results: int = 10,
        use_llm: bool = False,
    ) -> list[dict]:
        """
        Search and then scrape top results.

        Args:
            query: Search query
            scraper: CentralScraper instance
            max_results: How many results to scrape
            use_llm: Use LLM for analysis

        Returns:
            List of scraped content dicts
        """
        search_results = await self.search(query, max_results=max_results)

        scraped = []
        for result in search_results[:max_results]:
            try:
                from central_scraper import ScrapeRequest

                request = ScrapeRequest(
                    url=result.url,
                    use_tor=True,
                    use_llm=use_llm,
                )
                scrape_result = await scraper.scrape(request)

                scraped.append({
                    "search_result": result,
                    "content": scrape_result,
                })
            except Exception as e:
                logger.error(f"Failed to scrape {result.url}: {e}")

        return scraped

    async def _fetch_via_tor(self, url: str) -> Optional[str]:
        """Fetch URL content via TOR proxy."""
        try:
            import httpx

            await self.tor_manager.ensure_running()
            proxy_url = self.tor_manager.proxy_url

            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                proxy=proxy_url,
            ) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    return response.text
                return None
        except Exception as e:
            logger.error(f"TOR fetch failed for {url}: {e}")
            return None


# Convenience functions
async def dark_search(
    query: str,
    tor_manager=None,
    fetch_func=None,
    max_results: int = 50,
) -> list[SearchResult]:
    """Quick dark web search."""
    searcher = DarkMetaSearch(
        tor_manager=tor_manager,
        fetch_func=fetch_func,
    )
    return await searcher.search(query, max_results=max_results)

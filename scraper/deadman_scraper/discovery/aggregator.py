"""
Search Aggregator
=================
Multi-engine search aggregation (Robin pattern).

Clearnet Engines:
- Google, DuckDuckGo, Brave, Bing, GitHub, Archive.org

Darknet Engines:
- Ahmia, Torch, Haystak, DarkSearch
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any
from urllib.parse import quote_plus

if TYPE_CHECKING:
    from deadman_scraper.core.config import Config

logger = logging.getLogger(__name__)


class SearchAggregator:
    """
    Multi-engine search aggregator.

    Aggregates results from multiple search engines, deduplicates,
    and provides unified result format.

    Usage:
        aggregator = SearchAggregator(config)
        results = await aggregator.search("AI research", engines=["google", "duckduckgo"])
    """

    # Engine configurations
    CLEARNET_ENGINES = {
        "duckduckgo": {
            "url": "https://html.duckduckgo.com/html/?q={query}",
            "parser": "_parse_duckduckgo",
        },
        "brave": {
            "url": "https://search.brave.com/search?q={query}",
            "parser": "_parse_brave",
        },
        "bing": {
            "url": "https://www.bing.com/search?q={query}",
            "parser": "_parse_bing",
        },
        "github": {
            "url": "https://github.com/search?q={query}&type=repositories",
            "parser": "_parse_github",
        },
        "archive": {
            "url": "https://web.archive.org/web/*/https://*{query}*",
            "parser": "_parse_archive",
        },
    }

    DARKNET_ENGINES = {
        "ahmia": {
            "url": "https://ahmia.fi/search/?q={query}",
            "parser": "_parse_ahmia",
        },
        "torch": {
            "url": "http://xmh57jrknzkhv6y3ls3ubitzfqnkrwxhopf5aygthi7d6rplyvk3noyd.onion/cgi-bin/omega/omega?P={query}",
            "parser": "_parse_torch",
            "requires_tor": True,
        },
    }

    def __init__(self, config: Config):
        self.config = config
        self._seen_urls: set[str] = set()

    async def search(
        self,
        query: str,
        *,
        engines: list[str] | None = None,
        max_results: int = 50,
        darkweb: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Search across multiple engines.

        Args:
            query: Search query
            engines: Specific engines to use (default: all clearnet)
            max_results: Max results per engine
            darkweb: Include dark web engines

        Returns:
            Deduplicated list of search results
        """
        self._seen_urls.clear()

        # Determine engines to use
        if engines:
            engine_list = engines
        else:
            engine_list = list(self.CLEARNET_ENGINES.keys())
            if darkweb:
                engine_list.extend(self.DARKNET_ENGINES.keys())

        logger.info(f"Searching '{query}' across {len(engine_list)} engines")

        # Search concurrently
        tasks = []
        for engine in engine_list:
            tasks.append(self._search_engine(engine, query, max_results))

        results_lists = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten and deduplicate
        all_results = []
        for engine, results in zip(engine_list, results_lists):
            if isinstance(results, Exception):
                logger.warning(f"Engine {engine} failed: {results}")
                continue
            if results:
                all_results.extend(results)

        # Deduplicate by URL
        deduplicated = []
        for result in all_results:
            url = result.get("url", "")
            if url and url not in self._seen_urls:
                self._seen_urls.add(url)
                deduplicated.append(result)

        logger.info(f"Found {len(deduplicated)} unique results")
        return deduplicated

    async def _search_engine(
        self, engine: str, query: str, max_results: int
    ) -> list[dict[str, Any]]:
        """Search a single engine."""
        # Get engine config
        if engine in self.CLEARNET_ENGINES:
            engine_config = self.CLEARNET_ENGINES[engine]
        elif engine in self.DARKNET_ENGINES:
            engine_config = self.DARKNET_ENGINES[engine]
        else:
            logger.warning(f"Unknown engine: {engine}")
            return []

        # Check if TOR required
        requires_tor = engine_config.get("requires_tor", False)

        # Build URL
        url = engine_config["url"].format(query=quote_plus(query))

        # Fetch search page
        try:
            content = await self._fetch_search_page(url, use_tor=requires_tor)
            if not content:
                return []

            # Parse results
            parser_name = engine_config["parser"]
            parser = getattr(self, parser_name, None)
            if parser:
                results = parser(content, max_results)
                for r in results:
                    r["engine"] = engine
                return results
            else:
                logger.warning(f"No parser for engine: {engine}")
                return []

        except Exception as e:
            logger.error(f"Engine {engine} error: {e}")
            return []

    async def _fetch_search_page(self, url: str, use_tor: bool = False) -> str | None:
        """Fetch a search results page."""
        try:
            import httpx

            from deadman_scraper.stealth.headers import HeaderGenerator

            headers = HeaderGenerator.generate("chrome", "120")

            # Configure proxy for TOR
            proxy = None
            if use_tor and self.config.tor.enabled:
                proxy = f"socks5h://{self.config.tor.socks_host}:{self.config.tor.socks_port}"

            async with httpx.AsyncClient(proxy=proxy, timeout=30) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    return response.text
                else:
                    logger.debug(f"Search page returned {response.status_code}")
                    return None

        except Exception as e:
            logger.debug(f"Failed to fetch search page: {e}")
            return None

    # =========================================================================
    # PARSERS
    # =========================================================================

    def _parse_duckduckgo(self, content: str, max_results: int) -> list[dict[str, Any]]:
        """Parse DuckDuckGo HTML results."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(content, "lxml")
        results = []

        for result in soup.select(".result"):
            if len(results) >= max_results:
                break

            title_el = result.select_one(".result__title a")
            snippet_el = result.select_one(".result__snippet")

            if title_el:
                href = title_el.get("href", "")
                # DuckDuckGo wraps URLs
                if "uddg=" in href:
                    from urllib.parse import parse_qs, urlparse

                    parsed = urlparse(href)
                    params = parse_qs(parsed.query)
                    href = params.get("uddg", [href])[0]

                results.append({
                    "title": title_el.get_text(strip=True),
                    "url": href,
                    "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                })

        return results

    def _parse_brave(self, content: str, max_results: int) -> list[dict[str, Any]]:
        """Parse Brave Search results."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(content, "lxml")
        results = []

        for result in soup.select(".snippet"):
            if len(results) >= max_results:
                break

            title_el = result.select_one(".title")
            url_el = result.select_one(".url")
            snippet_el = result.select_one(".snippet-description")

            if title_el and url_el:
                results.append({
                    "title": title_el.get_text(strip=True),
                    "url": url_el.get_text(strip=True),
                    "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                })

        return results

    def _parse_bing(self, content: str, max_results: int) -> list[dict[str, Any]]:
        """Parse Bing search results."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(content, "lxml")
        results = []

        for result in soup.select(".b_algo"):
            if len(results) >= max_results:
                break

            title_el = result.select_one("h2 a")
            snippet_el = result.select_one(".b_caption p")

            if title_el:
                results.append({
                    "title": title_el.get_text(strip=True),
                    "url": title_el.get("href", ""),
                    "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                })

        return results

    def _parse_github(self, content: str, max_results: int) -> list[dict[str, Any]]:
        """Parse GitHub search results."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(content, "lxml")
        results = []

        for result in soup.select(".repo-list-item"):
            if len(results) >= max_results:
                break

            title_el = result.select_one(".v-align-middle")
            desc_el = result.select_one(".mb-1")

            if title_el:
                href = title_el.get("href", "")
                results.append({
                    "title": title_el.get_text(strip=True),
                    "url": f"https://github.com{href}" if href.startswith("/") else href,
                    "snippet": desc_el.get_text(strip=True) if desc_el else "",
                })

        return results

    def _parse_archive(self, content: str, max_results: int) -> list[dict[str, Any]]:
        """Parse Archive.org results."""
        # Archive.org requires API for proper results
        return []

    def _parse_ahmia(self, content: str, max_results: int) -> list[dict[str, Any]]:
        """Parse Ahmia dark web search results."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(content, "lxml")
        results = []

        for result in soup.select(".result"):
            if len(results) >= max_results:
                break

            title_el = result.select_one("h4 a")
            snippet_el = result.select_one(".result-description")

            if title_el:
                results.append({
                    "title": title_el.get_text(strip=True),
                    "url": title_el.get("href", ""),
                    "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                    "darkweb": True,
                })

        return results

    def _parse_torch(self, content: str, max_results: int) -> list[dict[str, Any]]:
        """Parse Torch dark web search results."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(content, "lxml")
        results = []

        for result in soup.select(".result"):
            if len(results) >= max_results:
                break

            title_el = result.select_one("a")

            if title_el:
                results.append({
                    "title": title_el.get_text(strip=True),
                    "url": title_el.get("href", ""),
                    "snippet": "",
                    "darkweb": True,
                })

        return results

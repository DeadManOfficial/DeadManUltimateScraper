"""
Onion Crawler - Dark Web Depth Crawling
========================================

Inspired by: github.com/MikeMeliz/TorCrawl.py

Features:
- Depth-controlled crawling
- YARA rules for content matching
- Link discovery and deduplication
- Multiple output formats (JSON, XML, SQLite)
- Respectful rate limiting

ALL FREE FOREVER - DeadManOfficial
"""

import asyncio
import re
import json
import sqlite3
import hashlib
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, Set, AsyncGenerator
from urllib.parse import urljoin, urlparse
import logging

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class CrawlResult:
    """Result from crawling a single page."""
    url: str
    status: str = "pending"  # pending, success, failed, skipped
    title: str = ""
    content: str = ""
    text: str = ""
    html: str = ""
    links: list = field(default_factory=list)
    onion_links: list = field(default_factory=list)
    emails: list = field(default_factory=list)
    bitcoin_addresses: list = field(default_factory=list)
    depth: int = 0
    parent_url: str = ""
    timestamp: str = ""
    response_code: int = 0
    content_hash: str = ""
    yara_matches: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "status": self.status,
            "title": self.title,
            "text": self.text[:5000] if self.text else "",
            "links_count": len(self.links),
            "onion_links": self.onion_links,
            "emails": self.emails,
            "bitcoin_addresses": self.bitcoin_addresses,
            "depth": self.depth,
            "parent_url": self.parent_url,
            "timestamp": self.timestamp,
            "response_code": self.response_code,
            "yara_matches": self.yara_matches,
        }


@dataclass
class CrawlConfig:
    """Configuration for crawling."""
    max_depth: int = 2
    max_pages: int = 100
    delay: float = 1.0
    delay_jitter: float = 0.5
    timeout: int = 120
    follow_external: bool = False
    extract_emails: bool = True
    extract_bitcoin: bool = True
    extract_onion_links: bool = True
    yara_rules: Optional[str] = None
    output_format: str = "json"  # json, xml, sqlite
    output_path: Optional[str] = None
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; rv:102.0) Gecko/20100101 Firefox/102.0"


class OnionCrawler:
    """
    Depth-controlled crawler for .onion sites.
    Uses BFS (Breadth-First Search) for level-by-level crawling.
    """

    # Patterns for extraction
    ONION_PATTERN = re.compile(
        r'(?:https?://)?([a-z2-7]{16,56}\.onion)(?:[:/].*)?',
        re.IGNORECASE
    )
    EMAIL_PATTERN = re.compile(
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        re.IGNORECASE
    )
    BITCOIN_PATTERN = re.compile(
        r'\b([13][a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[a-z0-9]{39,59})\b'
    )

    def __init__(
        self,
        tor_manager=None,
        fetch_func=None,
        config: CrawlConfig = None,
    ):
        """
        Initialize OnionCrawler.

        Args:
            tor_manager: TOR manager for circuit rotation
            fetch_func: Async function for HTTP requests
            config: Crawl configuration
        """
        self.tor_manager = tor_manager
        self.fetch_func = fetch_func
        self.config = config or CrawlConfig()

        # Crawl state
        self.visited: Set[str] = set()
        self.queue: deque = deque()
        self.results: list[CrawlResult] = []
        self.stats = {
            "pages_crawled": 0,
            "pages_failed": 0,
            "links_discovered": 0,
            "onions_discovered": set(),
            "start_time": None,
            "end_time": None,
        }

        # YARA support
        self.yara_rules = None
        if self.config.yara_rules:
            self._load_yara_rules()

    def _load_yara_rules(self):
        """Load YARA rules for content matching."""
        try:
            import yara
            if Path(self.config.yara_rules).exists():
                self.yara_rules = yara.compile(filepath=self.config.yara_rules)
            else:
                self.yara_rules = yara.compile(source=self.config.yara_rules)
            logger.info("[OnionCrawler] YARA rules loaded")
        except ImportError:
            logger.warning("YARA not installed. pip install yara-python")
        except Exception as e:
            logger.error(f"Failed to load YARA rules: {e}")

    async def crawl(
        self,
        seed_url: str,
        callback: Optional[Callable] = None,
    ) -> list[CrawlResult]:
        """
        Crawl starting from seed URL.

        Args:
            seed_url: Starting URL (.onion)
            callback: Optional callback for each crawled page

        Returns:
            List of CrawlResult objects
        """
        logger.info(f"[OnionCrawler] Starting crawl from: {seed_url}")
        logger.info(f"[OnionCrawler] Config: depth={self.config.max_depth}, max_pages={self.config.max_pages}")

        # Reset state
        self.visited.clear()
        self.queue.clear()
        self.results.clear()
        self.stats["start_time"] = datetime.utcnow().isoformat()
        self.stats["pages_crawled"] = 0
        self.stats["pages_failed"] = 0
        self.stats["onions_discovered"] = set()

        # Seed the queue
        self.queue.append((seed_url, 0, ""))  # (url, depth, parent)

        while self.queue and self.stats["pages_crawled"] < self.config.max_pages:
            url, depth, parent = self.queue.popleft()

            # Skip if already visited or exceeds depth
            url_normalized = self._normalize_url(url)
            if url_normalized in self.visited:
                continue
            if depth > self.config.max_depth:
                continue

            self.visited.add(url_normalized)

            # Crawl page
            result = await self._crawl_page(url, depth, parent)
            self.results.append(result)

            if result.status == "success":
                self.stats["pages_crawled"] += 1

                # Queue discovered links
                for link in result.links:
                    if self._should_follow(link, url):
                        self.queue.append((link, depth + 1, url))
                        self.stats["links_discovered"] += 1

                # Track discovered onions
                for onion in result.onion_links:
                    self.stats["onions_discovered"].add(onion)

                if callback:
                    await callback(result)

            else:
                self.stats["pages_failed"] += 1

            # Rate limiting
            await self._delay()

        self.stats["end_time"] = datetime.utcnow().isoformat()

        # Save results
        if self.config.output_path:
            await self._save_results()

        logger.info(f"[OnionCrawler] Crawl complete: {self.stats['pages_crawled']} pages, "
                   f"{len(self.stats['onions_discovered'])} unique onions discovered")

        return self.results

    async def crawl_stream(
        self,
        seed_url: str,
    ) -> AsyncGenerator[CrawlResult, None]:
        """
        Crawl with streaming results.

        Yields:
            CrawlResult objects as they are crawled
        """
        self.visited.clear()
        self.queue.clear()
        self.queue.append((seed_url, 0, ""))

        while self.queue and self.stats["pages_crawled"] < self.config.max_pages:
            url, depth, parent = self.queue.popleft()

            url_normalized = self._normalize_url(url)
            if url_normalized in self.visited or depth > self.config.max_depth:
                continue

            self.visited.add(url_normalized)
            result = await self._crawl_page(url, depth, parent)

            if result.status == "success":
                self.stats["pages_crawled"] += 1
                for link in result.links:
                    if self._should_follow(link, url):
                        self.queue.append((link, depth + 1, url))

            yield result
            await self._delay()

    async def _crawl_page(
        self,
        url: str,
        depth: int,
        parent: str,
    ) -> CrawlResult:
        """Crawl a single page."""
        result = CrawlResult(
            url=url,
            depth=depth,
            parent_url=parent,
            timestamp=datetime.utcnow().isoformat(),
        )

        try:
            logger.debug(f"[OnionCrawler] Crawling (depth={depth}): {url}")

            # Fetch content
            html = await self._fetch(url)
            if not html:
                result.status = "failed"
                return result

            result.html = html
            result.content_hash = hashlib.md5(html.encode()).hexdigest()

            # Parse HTML
            soup = BeautifulSoup(html, "lxml")

            # Extract title
            title_tag = soup.find("title")
            result.title = title_tag.get_text(strip=True) if title_tag else ""

            # Extract text
            for tag in soup(["script", "style", "meta", "noscript"]):
                tag.decompose()
            result.text = soup.get_text(separator=" ", strip=True)

            # Extract links
            result.links = self._extract_links(soup, url)

            # Extract .onion links
            if self.config.extract_onion_links:
                result.onion_links = list(set(self.ONION_PATTERN.findall(html)))

            # Extract emails
            if self.config.extract_emails:
                result.emails = list(set(self.EMAIL_PATTERN.findall(html)))

            # Extract bitcoin addresses
            if self.config.extract_bitcoin:
                result.bitcoin_addresses = list(set(self.BITCOIN_PATTERN.findall(html)))

            # Run YARA rules
            if self.yara_rules:
                matches = self.yara_rules.match(data=html)
                result.yara_matches = [m.rule for m in matches]

            result.status = "success"
            result.response_code = 200

        except Exception as e:
            logger.error(f"[OnionCrawler] Failed to crawl {url}: {e}")
            result.status = "failed"

        return result

    async def _fetch(self, url: str) -> Optional[str]:
        """Fetch URL content via TOR."""
        try:
            if self.tor_manager:
                return await self._fetch_via_tor(url)
            elif self.fetch_func:
                return await self.fetch_func(url, timeout=self.config.timeout)
            else:
                logger.error("No fetch function available")
                return None
        except Exception as e:
            logger.error(f"Fetch failed for {url}: {e}")
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

    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> list[str]:
        """Extract all links from page."""
        links = []
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue

            # Resolve relative URLs
            full_url = urljoin(base_url, href)
            links.append(full_url)

        return list(set(links))

    def _should_follow(self, url: str, current_url: str) -> bool:
        """Determine if link should be followed."""
        # Must be .onion
        if ".onion" not in url:
            return False

        # Already visited
        if self._normalize_url(url) in self.visited:
            return False

        # Check same domain
        if not self.config.follow_external:
            current_domain = urlparse(current_url).netloc
            link_domain = urlparse(url).netloc
            if current_domain != link_domain:
                return False

        return True

    def _normalize_url(self, url: str) -> str:
        """Normalize URL for deduplication."""
        parsed = urlparse(url)
        # Remove trailing slash, fragments
        path = parsed.path.rstrip("/") or "/"
        return f"{parsed.scheme}://{parsed.netloc}{path}"

    async def _delay(self):
        """Apply rate limiting delay."""
        import random
        delay = self.config.delay + random.uniform(0, self.config.delay_jitter)
        await asyncio.sleep(delay)

    async def _save_results(self):
        """Save crawl results to file."""
        output_path = Path(self.config.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if self.config.output_format == "json":
            await self._save_json(output_path)
        elif self.config.output_format == "xml":
            await self._save_xml(output_path)
        elif self.config.output_format == "sqlite":
            await self._save_sqlite(output_path)

    async def _save_json(self, path: Path):
        """Save as JSON."""
        data = {
            "stats": {
                **self.stats,
                "onions_discovered": list(self.stats["onions_discovered"]),
            },
            "results": [r.to_dict() for r in self.results],
        }
        path.write_text(json.dumps(data, indent=2))
        logger.info(f"[OnionCrawler] Results saved to {path}")

    async def _save_xml(self, path: Path):
        """Save as XML."""
        import xml.etree.ElementTree as ET

        root = ET.Element("crawl_results")

        # Stats
        stats_elem = ET.SubElement(root, "stats")
        for key, value in self.stats.items():
            if key == "onions_discovered":
                value = len(value)
            ET.SubElement(stats_elem, key).text = str(value)

        # Results
        results_elem = ET.SubElement(root, "results")
        for result in self.results:
            page = ET.SubElement(results_elem, "page")
            for key, value in result.to_dict().items():
                if isinstance(value, list):
                    value = ", ".join(str(v) for v in value)
                ET.SubElement(page, key).text = str(value)

        tree = ET.ElementTree(root)
        tree.write(str(path), encoding="unicode", xml_declaration=True)
        logger.info(f"[OnionCrawler] Results saved to {path}")

    async def _save_sqlite(self, path: Path):
        """Save to SQLite database."""
        conn = sqlite3.connect(str(path))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS crawl_results (
                id INTEGER PRIMARY KEY,
                url TEXT UNIQUE,
                status TEXT,
                title TEXT,
                text TEXT,
                depth INTEGER,
                parent_url TEXT,
                timestamp TEXT,
                content_hash TEXT,
                onion_links TEXT,
                emails TEXT,
                bitcoin_addresses TEXT,
                yara_matches TEXT
            )
        """)

        for result in self.results:
            cursor.execute("""
                INSERT OR REPLACE INTO crawl_results
                (url, status, title, text, depth, parent_url, timestamp, content_hash,
                 onion_links, emails, bitcoin_addresses, yara_matches)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.url,
                result.status,
                result.title,
                result.text[:10000],
                result.depth,
                result.parent_url,
                result.timestamp,
                result.content_hash,
                json.dumps(result.onion_links),
                json.dumps(result.emails),
                json.dumps(result.bitcoin_addresses),
                json.dumps(result.yara_matches),
            ))

        conn.commit()
        conn.close()
        logger.info(f"[OnionCrawler] Results saved to {path}")

    def get_stats(self) -> dict:
        """Get crawl statistics."""
        return {
            **self.stats,
            "onions_discovered": list(self.stats["onions_discovered"]),
            "onions_count": len(self.stats["onions_discovered"]),
        }


# Convenience function
async def crawl_onion(
    url: str,
    tor_manager=None,
    fetch_func=None,
    max_depth: int = 2,
    max_pages: int = 50,
) -> list[CrawlResult]:
    """Quick .onion crawl."""
    config = CrawlConfig(max_depth=max_depth, max_pages=max_pages)
    crawler = OnionCrawler(
        tor_manager=tor_manager,
        fetch_func=fetch_func,
        config=config,
    )
    return await crawler.crawl(url)

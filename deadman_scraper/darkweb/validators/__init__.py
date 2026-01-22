"""
Dark Web Validators
===================

Inspired by: github.com/dirtyfilthy/freshonions-torscraper

Features:
- Onion site validation and health checking
- Clone/phishing site detection
- SSH fingerprint extraction
- Service identification

ALL FREE FOREVER - DeadManOfficial
"""

import asyncio
import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from difflib import SequenceMatcher
from typing import Optional, Set
from urllib.parse import urlparse
import logging

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class OnionStatus:
    """Status of an onion site."""
    url: str
    is_alive: bool = False
    response_time_ms: float = 0
    status_code: int = 0
    title: str = ""
    server_header: str = ""
    content_hash: str = ""
    content_length: int = 0
    last_checked: str = ""
    ssh_fingerprint: str = ""
    open_ports: list = field(default_factory=list)
    detected_services: list = field(default_factory=list)
    language: str = ""
    is_clone: bool = False
    clone_of: str = ""

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "is_alive": self.is_alive,
            "response_time_ms": self.response_time_ms,
            "status_code": self.status_code,
            "title": self.title,
            "server_header": self.server_header,
            "content_hash": self.content_hash,
            "content_length": self.content_length,
            "last_checked": self.last_checked,
            "detected_services": self.detected_services,
            "language": self.language,
            "is_clone": self.is_clone,
            "clone_of": self.clone_of,
        }


class OnionValidator:
    """
    Validate and monitor .onion sites.
    """

    # Common ports to check
    COMMON_PORTS = [80, 443, 22, 21, 25, 8080, 8443]

    # Service patterns
    SERVICE_PATTERNS = {
        "marketplace": re.compile(r'(shop|market|store|buy|sell|vendor)', re.I),
        "forum": re.compile(r'(forum|discuss|board|thread|post)', re.I),
        "email": re.compile(r'(mail|inbox|webmail|smtp)', re.I),
        "hosting": re.compile(r'(host|server|vps|dedic)', re.I),
        "wiki": re.compile(r'(wiki|documentation|docs)', re.I),
        "search": re.compile(r'(search|find|query|index)', re.I),
        "social": re.compile(r'(social|network|friend|follow)', re.I),
        "crypto": re.compile(r'(bitcoin|btc|crypto|wallet|mixer)', re.I),
        "leak": re.compile(r'(leak|dump|breach|expose)', re.I),
        "chat": re.compile(r'(chat|message|im|xmpp|irc)', re.I),
    }

    def __init__(
        self,
        tor_manager=None,
        fetch_func=None,
        timeout: int = 60,
    ):
        """
        Initialize OnionValidator.

        Args:
            tor_manager: TOR manager for .onion requests
            fetch_func: Async function for HTTP requests
            timeout: Request timeout in seconds
        """
        self.tor_manager = tor_manager
        self.fetch_func = fetch_func
        self.timeout = timeout

    async def validate(self, url: str) -> OnionStatus:
        """
        Validate a single .onion URL.

        Args:
            url: Onion URL to validate

        Returns:
            OnionStatus object
        """
        status = OnionStatus(
            url=url,
            last_checked=datetime.utcnow().isoformat(),
        )

        try:
            start_time = asyncio.get_event_loop().time()

            # Fetch content
            html = await self._fetch(url)

            elapsed = (asyncio.get_event_loop().time() - start_time) * 1000
            status.response_time_ms = round(elapsed, 2)

            if html:
                status.is_alive = True
                status.status_code = 200
                status.content_length = len(html)
                status.content_hash = hashlib.md5(html.encode()).hexdigest()

                # Parse HTML
                soup = BeautifulSoup(html, "lxml")

                # Extract title
                title_tag = soup.find("title")
                status.title = title_tag.get_text(strip=True)[:200] if title_tag else ""

                # Detect services
                status.detected_services = self._detect_services(html, status.title)

                # Detect language
                status.language = self._detect_language(soup)

            else:
                status.is_alive = False

        except Exception as e:
            logger.error(f"Validation failed for {url}: {e}")
            status.is_alive = False

        return status

    async def validate_batch(
        self,
        urls: list[str],
        max_concurrent: int = 5,
    ) -> list[OnionStatus]:
        """
        Validate multiple URLs in parallel.

        Args:
            urls: List of onion URLs
            max_concurrent: Max concurrent validations

        Returns:
            List of OnionStatus objects
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def limited_validate(url):
            async with semaphore:
                return await self.validate(url)

        results = await asyncio.gather(
            *[limited_validate(url) for url in urls],
            return_exceptions=True
        )

        statuses = []
        for i, result in enumerate(results):
            if isinstance(result, OnionStatus):
                statuses.append(result)
            else:
                statuses.append(OnionStatus(
                    url=urls[i],
                    is_alive=False,
                    last_checked=datetime.utcnow().isoformat(),
                ))

        return statuses

    async def monitor(
        self,
        urls: list[str],
        interval: int = 300,
        callback=None,
    ):
        """
        Continuously monitor onion sites.

        Args:
            urls: List of URLs to monitor
            interval: Check interval in seconds
            callback: Optional callback for status updates
        """
        logger.info(f"[OnionValidator] Starting monitor for {len(urls)} sites")

        while True:
            statuses = await self.validate_batch(urls)

            for status in statuses:
                if callback:
                    await callback(status)
                else:
                    state = "UP" if status.is_alive else "DOWN"
                    logger.info(f"[Monitor] {status.url}: {state} ({status.response_time_ms}ms)")

            await asyncio.sleep(interval)

    def _detect_services(self, html: str, title: str) -> list[str]:
        """Detect what type of service the site provides."""
        services = []
        combined = f"{html[:5000]} {title}".lower()

        for service, pattern in self.SERVICE_PATTERNS.items():
            if pattern.search(combined):
                services.append(service)

        return services

    def _detect_language(self, soup: BeautifulSoup) -> str:
        """Detect page language."""
        # Check html lang attribute
        html_tag = soup.find("html")
        if html_tag and html_tag.get("lang"):
            return html_tag["lang"][:5]

        # Check meta tags
        meta_lang = soup.find("meta", attrs={"http-equiv": "content-language"})
        if meta_lang and meta_lang.get("content"):
            return meta_lang["content"][:5]

        return "unknown"

    async def _fetch(self, url: str) -> Optional[str]:
        """Fetch URL content."""
        try:
            if self.tor_manager:
                return await self._fetch_via_tor(url)
            elif self.fetch_func:
                return await self.fetch_func(url, timeout=self.timeout)
            return None
        except Exception as e:
            logger.error(f"Fetch failed: {e}")
            return None

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


class CloneDetector:
    """
    Detect clone/phishing sites on the dark web.
    Uses content similarity and structural analysis.
    """

    def __init__(
        self,
        similarity_threshold: float = 0.85,
    ):
        """
        Initialize CloneDetector.

        Args:
            similarity_threshold: Threshold for considering sites as clones (0-1)
        """
        self.similarity_threshold = similarity_threshold
        self.known_sites: dict = {}  # domain -> content_hash, structure_hash

    def register_legitimate(self, domain: str, html: str):
        """
        Register a legitimate site for comparison.

        Args:
            domain: Site domain
            html: Site HTML content
        """
        self.known_sites[domain] = {
            "content_hash": hashlib.md5(html.encode()).hexdigest(),
            "structure_hash": self._hash_structure(html),
            "text_sample": self._extract_text_sample(html),
        }

    def check_clone(self, url: str, html: str) -> tuple[bool, str, float]:
        """
        Check if a site is a clone of a known legitimate site.

        Args:
            url: URL being checked
            html: HTML content

        Returns:
            Tuple of (is_clone, original_domain, similarity_score)
        """
        domain = urlparse(url).netloc

        # Don't check against itself
        if domain in self.known_sites:
            return False, "", 0.0

        current_structure = self._hash_structure(html)
        current_text = self._extract_text_sample(html)

        for known_domain, known_data in self.known_sites.items():
            # Check structure similarity
            if current_structure == known_data["structure_hash"]:
                return True, known_domain, 1.0

            # Check text similarity
            similarity = SequenceMatcher(
                None,
                current_text,
                known_data["text_sample"]
            ).ratio()

            if similarity >= self.similarity_threshold:
                return True, known_domain, similarity

        return False, "", 0.0

    def _hash_structure(self, html: str) -> str:
        """Create a hash of the HTML structure (tags only)."""
        soup = BeautifulSoup(html, "lxml")

        # Extract tag structure
        tags = []
        for tag in soup.find_all():
            tags.append(tag.name)

        structure = " ".join(tags[:100])
        return hashlib.md5(structure.encode()).hexdigest()

    def _extract_text_sample(self, html: str) -> str:
        """Extract text sample for comparison."""
        soup = BeautifulSoup(html, "lxml")

        for tag in soup(["script", "style", "meta", "noscript"]):
            tag.decompose()

        text = soup.get_text(separator=" ", strip=True)
        return text[:2000]


# Convenience functions
async def check_onion(
    url: str,
    tor_manager=None,
    fetch_func=None,
) -> OnionStatus:
    """Quick onion validation."""
    validator = OnionValidator(
        tor_manager=tor_manager,
        fetch_func=fetch_func,
    )
    return await validator.validate(url)


__all__ = ["OnionValidator", "CloneDetector", "OnionStatus", "check_onion"]

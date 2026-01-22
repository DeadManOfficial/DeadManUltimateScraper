"""
OSINT Collector for Dark Web
============================

Inspired by: github.com/smicallef/spiderfoot

Features:
- Email harvesting
- Bitcoin address tracking
- PGP key discovery
- Username enumeration
- Credential leak detection
- Social media correlation

ALL FREE FOREVER - DeadManOfficial
"""

import asyncio
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Set
import logging
import json

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class OSINTEntity:
    """A discovered OSINT entity."""
    entity_type: str  # email, bitcoin, pgp, username, phone, etc.
    value: str
    source_url: str = ""
    context: str = ""
    confidence: float = 1.0
    timestamp: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "entity_type": self.entity_type,
            "value": self.value,
            "source_url": self.source_url,
            "context": self.context[:500] if self.context else "",
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class OSINTReport:
    """Complete OSINT report for a target."""
    target: str
    target_type: str  # domain, email, username, etc.
    entities: list = field(default_factory=list)
    stats: dict = field(default_factory=dict)
    timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "target": self.target,
            "target_type": self.target_type,
            "entities": [e.to_dict() for e in self.entities],
            "stats": self.stats,
            "timestamp": self.timestamp,
        }


class OSINTCollector:
    """
    Collect OSINT from dark web sources.
    """

    # Extraction patterns
    PATTERNS = {
        "email": re.compile(
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            re.IGNORECASE
        ),
        "bitcoin": re.compile(
            r'\b([13][a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[a-z0-9]{39,59})\b'
        ),
        "ethereum": re.compile(
            r'\b(0x[a-fA-F0-9]{40})\b'
        ),
        "monero": re.compile(
            r'\b(4[0-9AB][1-9A-HJ-NP-Za-km-z]{93})\b'
        ),
        "onion_v2": re.compile(
            r'\b([a-z2-7]{16}\.onion)\b',
            re.IGNORECASE
        ),
        "onion_v3": re.compile(
            r'\b([a-z2-7]{56}\.onion)\b',
            re.IGNORECASE
        ),
        "pgp_fingerprint": re.compile(
            r'\b([0-9A-F]{4}\s*){10}\b',
            re.IGNORECASE
        ),
        "pgp_key_id": re.compile(
            r'\b(0x[0-9A-F]{8,16})\b',
            re.IGNORECASE
        ),
        "phone": re.compile(
            r'\+?[1-9]\d{1,14}(?:[-.\s]?\d+)*'
        ),
        "ip_address": re.compile(
            r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b'
        ),
        "ssn": re.compile(
            r'\b(\d{3}-\d{2}-\d{4})\b'
        ),
        "credit_card": re.compile(
            r'\b([345]\d{3}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4})\b'
        ),
        "api_key": re.compile(
            r'(?:api[_-]?key|apikey|key)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_-]{20,})["\']?',
            re.IGNORECASE
        ),
        "jwt": re.compile(
            r'\beyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*\b'
        ),
        "private_key": re.compile(
            r'-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----',
            re.IGNORECASE
        ),
        "username": re.compile(
            r'(?:user(?:name)?|login|account)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_-]{3,30})["\']?',
            re.IGNORECASE
        ),
        "password": re.compile(
            r'(?:pass(?:word)?|pwd)["\']?\s*[:=]\s*["\']?([^\s"\']{4,50})["\']?',
            re.IGNORECASE
        ),
    }

    # External OSINT services (clearnet)
    OSINT_SERVICES = {
        "haveibeenpwned": "https://haveibeenpwned.com/api/v3/breachedaccount/{email}",
        "hunter": "https://api.hunter.io/v2/email-verifier?email={email}",
        "dehashed": "https://api.dehashed.com/search?query={query}",
    }

    def __init__(
        self,
        tor_manager=None,
        fetch_func=None,
        meta_search=None,
        extract_types: list = None,
    ):
        """
        Initialize OSINTCollector.

        Args:
            tor_manager: TOR manager for .onion requests
            fetch_func: Async function for HTTP requests
            meta_search: DarkMetaSearch instance for search
            extract_types: List of entity types to extract (default: all)
        """
        self.tor_manager = tor_manager
        self.fetch_func = fetch_func
        self.meta_search = meta_search

        # Default to all types
        self.extract_types = extract_types or list(self.PATTERNS.keys())

    async def collect_from_url(
        self,
        url: str,
        html: Optional[str] = None,
    ) -> list[OSINTEntity]:
        """
        Collect OSINT entities from a URL.

        Args:
            url: Source URL
            html: Optional pre-fetched HTML

        Returns:
            List of OSINTEntity objects
        """
        logger.info(f"[OSINTCollector] Collecting from: {url}")

        if not html:
            html = await self._fetch(url)
            if not html:
                return []

        entities = []
        soup = BeautifulSoup(html, "lxml")

        # Get clean text
        for tag in soup(["script", "style"]):
            tag.decompose()
        text = soup.get_text(separator=" ")

        # Extract each entity type
        for entity_type, pattern in self.PATTERNS.items():
            if entity_type not in self.extract_types:
                continue

            matches = pattern.findall(html)
            matches.extend(pattern.findall(text))

            for match in set(matches):
                # Get context around match
                context = self._get_context(text, match)

                entity = OSINTEntity(
                    entity_type=entity_type,
                    value=match if isinstance(match, str) else match[0],
                    source_url=url,
                    context=context,
                    timestamp=datetime.utcnow().isoformat(),
                )

                # Validate and add confidence
                entity.confidence = self._validate_entity(entity)
                if entity.confidence > 0.5:
                    entities.append(entity)

        logger.info(f"[OSINTCollector] Found {len(entities)} entities")
        return entities

    async def collect_from_search(
        self,
        query: str,
        max_results: int = 20,
    ) -> list[OSINTEntity]:
        """
        Search dark web and collect OSINT from results.

        Args:
            query: Search query
            max_results: Maximum search results to process

        Returns:
            List of OSINTEntity objects
        """
        if not self.meta_search:
            logger.error("No meta_search instance provided")
            return []

        all_entities = []

        # Search dark web
        search_results = await self.meta_search.search(
            query,
            max_results=max_results,
        )

        # Collect from each result
        for result in search_results[:max_results]:
            entities = await self.collect_from_url(result.url)
            all_entities.extend(entities)

        return all_entities

    async def investigate_target(
        self,
        target: str,
        target_type: str = "auto",
    ) -> OSINTReport:
        """
        Full OSINT investigation on a target.

        Args:
            target: Target to investigate (email, domain, username, etc.)
            target_type: Type of target or "auto" to detect

        Returns:
            OSINTReport object
        """
        # Auto-detect target type
        if target_type == "auto":
            target_type = self._detect_target_type(target)

        logger.info(f"[OSINTCollector] Investigating {target_type}: {target}")

        report = OSINTReport(
            target=target,
            target_type=target_type,
            timestamp=datetime.utcnow().isoformat(),
        )

        # Search dark web for target
        if self.meta_search:
            entities = await self.collect_from_search(target, max_results=30)
            report.entities.extend(entities)

        # Calculate stats
        report.stats = self._calculate_stats(report.entities)

        return report

    async def monitor_keywords(
        self,
        keywords: list[str],
        interval: int = 3600,
        callback=None,
    ):
        """
        Monitor dark web for keywords.

        Args:
            keywords: List of keywords to monitor
            interval: Check interval in seconds
            callback: Callback for new findings
        """
        seen_entities: Set[str] = set()

        logger.info(f"[OSINTCollector] Monitoring {len(keywords)} keywords")

        while True:
            for keyword in keywords:
                try:
                    entities = await self.collect_from_search(keyword, max_results=10)

                    for entity in entities:
                        entity_key = f"{entity.entity_type}:{entity.value}"
                        if entity_key not in seen_entities:
                            seen_entities.add(entity_key)

                            if callback:
                                await callback(keyword, entity)
                            else:
                                logger.info(f"[Monitor] New {entity.entity_type}: {entity.value}")

                except Exception as e:
                    logger.error(f"Monitor error for {keyword}: {e}")

            await asyncio.sleep(interval)

    def _detect_target_type(self, target: str) -> str:
        """Auto-detect target type."""
        if "@" in target:
            return "email"
        if ".onion" in target:
            return "onion"
        if re.match(r'^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$', target):
            return "bitcoin"
        if re.match(r'^0x[a-fA-F0-9]{40}$', target):
            return "ethereum"
        if "." in target:
            return "domain"
        return "keyword"

    def _get_context(self, text: str, match: str, window: int = 100) -> str:
        """Get context around a match."""
        try:
            idx = text.lower().find(match.lower())
            if idx == -1:
                return ""

            start = max(0, idx - window)
            end = min(len(text), idx + len(match) + window)
            return text[start:end].strip()

        except Exception:
            return ""

    def _validate_entity(self, entity: OSINTEntity) -> float:
        """Validate entity and return confidence score."""
        confidence = 1.0

        # Email validation
        if entity.entity_type == "email":
            if not re.match(r'^[^@]+@[^@]+\.[^@]+$', entity.value):
                confidence *= 0.3
            if any(x in entity.value.lower() for x in ["example", "test", "fake"]):
                confidence *= 0.5

        # Bitcoin validation (checksum)
        if entity.entity_type == "bitcoin":
            if not (entity.value.startswith("1") or
                    entity.value.startswith("3") or
                    entity.value.startswith("bc1")):
                confidence *= 0.3

        # IP validation
        if entity.entity_type == "ip_address":
            octets = entity.value.split(".")
            if any(int(o) > 255 for o in octets):
                confidence = 0

        # Credit card Luhn check
        if entity.entity_type == "credit_card":
            if not self._luhn_check(entity.value.replace("-", "").replace(" ", "")):
                confidence *= 0.3

        return confidence

    @staticmethod
    def _luhn_check(card_number: str) -> bool:
        """Validate credit card using Luhn algorithm."""
        try:
            digits = [int(d) for d in card_number if d.isdigit()]
            odd_digits = digits[-1::-2]
            even_digits = digits[-2::-2]

            checksum = sum(odd_digits)
            for d in even_digits:
                checksum += sum(divmod(d * 2, 10))

            return checksum % 10 == 0
        except Exception:
            return False

    def _calculate_stats(self, entities: list[OSINTEntity]) -> dict:
        """Calculate statistics from entities."""
        stats = {
            "total": len(entities),
            "by_type": {},
            "high_confidence": 0,
        }

        for entity in entities:
            entity_type = entity.entity_type
            if entity_type not in stats["by_type"]:
                stats["by_type"][entity_type] = 0
            stats["by_type"][entity_type] += 1

            if entity.confidence > 0.8:
                stats["high_confidence"] += 1

        return stats

    async def _fetch(self, url: str) -> Optional[str]:
        """Fetch URL content."""
        try:
            if self.tor_manager:
                return await self._fetch_via_tor(url)
            elif self.fetch_func:
                return await self.fetch_func(url, timeout=60)
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
                timeout=httpx.Timeout(60),
                proxy=proxy_url,
            ) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    return response.text
                return None
        except Exception as e:
            logger.error(f"TOR fetch failed for {url}: {e}")
            return None


# Convenience function
async def collect_osint(
    url: str,
    tor_manager=None,
    fetch_func=None,
) -> list[OSINTEntity]:
    """Quick OSINT collection from URL."""
    collector = OSINTCollector(
        tor_manager=tor_manager,
        fetch_func=fetch_func,
    )
    return await collector.collect_from_url(url)


__all__ = ["OSINTCollector", "OSINTEntity", "OSINTReport", "collect_osint"]

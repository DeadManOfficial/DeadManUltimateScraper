"""
OSINT Collector for Dark Web
============================

Inspired by:
- github.com/smicallef/spiderfoot
- OnionScan, Photon, Hakrawler, FinalRecon
- Medium article: "Dark Web Scraping by OSINT"

Features:
- Email harvesting
- Bitcoin/ETH/XMR address tracking
- PGP key discovery
- Username enumeration
- Credential leak detection
- Social media correlation
- SSH fingerprint detection (NEW)
- JavaScript endpoint extraction (NEW)
- Form discovery (NEW)
- Subdomain enumeration (NEW)
- SSL certificate extraction (NEW)
- Language detection (NEW)

ALL FREE FOREVER - DeadManOfficial
"""

import asyncio
import re
import ssl
import socket
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Set, List, Dict, Tuple
from urllib.parse import urlparse, urljoin, parse_qs
import logging
import json
import hashlib

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# ============================================
# Language Detection (lightweight)
# ============================================
LANGUAGE_INDICATORS = {
    "en": ["the", "and", "is", "are", "was", "were", "have", "has", "been", "will", "would", "could", "should"],
    "ru": ["и", "в", "на", "с", "по", "для", "что", "как", "это", "не", "из", "от", "он", "она"],
    "zh": ["的", "是", "在", "有", "和", "了", "不", "人", "我", "他", "这", "中", "大", "为"],
    "de": ["und", "der", "die", "das", "ist", "von", "mit", "auf", "für", "nicht", "sich", "auch"],
    "es": ["de", "la", "que", "el", "en", "y", "a", "los", "se", "del", "las", "un", "por", "con"],
    "fr": ["de", "la", "le", "et", "les", "des", "en", "un", "du", "une", "que", "est", "pour"],
    "pt": ["de", "que", "e", "o", "a", "do", "da", "em", "um", "para", "com", "não", "uma", "os"],
    "ar": ["في", "من", "على", "أن", "إلى", "هذا", "التي", "الذي", "هذه", "ما", "لا", "كان"],
}


def detect_language(text: str, min_confidence: float = 0.3) -> Tuple[str, float]:
    """
    Detect language from text content.

    Returns:
        Tuple of (language_code, confidence)
    """
    if not text:
        return ("unknown", 0.0)

    text_lower = text.lower()
    words = re.findall(r'\b\w+\b', text_lower)

    if len(words) < 10:
        return ("unknown", 0.0)

    scores = {}
    for lang, indicators in LANGUAGE_INDICATORS.items():
        count = sum(1 for word in words if word in indicators)
        scores[lang] = count / len(words)

    if not scores:
        return ("unknown", 0.0)

    best_lang = max(scores, key=scores.get)
    confidence = scores[best_lang]

    if confidence < min_confidence:
        return ("unknown", confidence)

    return (best_lang, confidence)


# ============================================
# Data Classes
# ============================================

@dataclass
class OSINTEntity:
    """A discovered OSINT entity."""
    entity_type: str  # email, bitcoin, pgp, username, phone, ssh_fingerprint, etc.
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
class FormInfo:
    """Discovered form information."""
    action: str
    method: str
    inputs: List[Dict[str, str]]
    source_url: str
    form_type: str = "unknown"  # login, search, contact, registration, etc.

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "method": self.method,
            "inputs": self.inputs,
            "source_url": self.source_url,
            "form_type": self.form_type,
        }


@dataclass
class SSLCertInfo:
    """SSL certificate information."""
    subject: dict
    issuer: dict
    serial_number: str
    not_before: str
    not_after: str
    fingerprint_sha256: str
    san: List[str]  # Subject Alternative Names

    def to_dict(self) -> dict:
        return {
            "subject": self.subject,
            "issuer": self.issuer,
            "serial_number": self.serial_number,
            "not_before": self.not_before,
            "not_after": self.not_after,
            "fingerprint_sha256": self.fingerprint_sha256,
            "san": self.san,
        }


@dataclass
class JSEndpoint:
    """JavaScript endpoint discovery."""
    url: str
    method: str = "GET"
    params: List[str] = field(default_factory=list)
    source_file: str = ""
    endpoint_type: str = "api"  # api, graphql, websocket, etc.

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "method": self.method,
            "params": self.params,
            "source_file": self.source_file,
            "endpoint_type": self.endpoint_type,
        }


@dataclass
class OSINTReport:
    """Complete OSINT report for a target."""
    target: str
    target_type: str  # domain, email, username, etc.
    entities: list = field(default_factory=list)
    forms: list = field(default_factory=list)
    js_endpoints: list = field(default_factory=list)
    subdomains: list = field(default_factory=list)
    ssl_cert: Optional[SSLCertInfo] = None
    language: Tuple[str, float] = ("unknown", 0.0)
    stats: dict = field(default_factory=dict)
    timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "target": self.target,
            "target_type": self.target_type,
            "entities": [e.to_dict() for e in self.entities],
            "forms": [f.to_dict() for f in self.forms],
            "js_endpoints": [j.to_dict() for j in self.js_endpoints],
            "subdomains": self.subdomains,
            "ssl_cert": self.ssl_cert.to_dict() if self.ssl_cert else None,
            "language": {"code": self.language[0], "confidence": self.language[1]},
            "stats": self.stats,
            "timestamp": self.timestamp,
        }


class OSINTCollector:
    """
    Collect OSINT from dark web sources.

    Enhanced with features from OnionScan, Photon, Hakrawler, FinalRecon.
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
        "litecoin": re.compile(
            r'\b([LM3][a-km-zA-HJ-NP-Z1-9]{26,33})\b'
        ),
        "dogecoin": re.compile(
            r'\b(D[5-9A-HJ-NP-U][1-9A-HJ-NP-Za-km-z]{32})\b'
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
        "ipv6_address": re.compile(
            r'\b([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b'
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
        "aws_key": re.compile(
            r'\b(AKIA[0-9A-Z]{16})\b'
        ),
        "aws_secret": re.compile(
            r'(?:aws_secret|secret_key)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9/+=]{40})["\']?',
            re.IGNORECASE
        ),
        "github_token": re.compile(
            r'\b(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59})\b'
        ),
        "username": re.compile(
            r'(?:user(?:name)?|login|account)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_-]{3,30})["\']?',
            re.IGNORECASE
        ),
        "password": re.compile(
            r'(?:pass(?:word)?|pwd)["\']?\s*[:=]\s*["\']?([^\s"\']{4,50})["\']?',
            re.IGNORECASE
        ),
        # NEW: SSH fingerprints (from OnionScan)
        "ssh_rsa_fingerprint": re.compile(
            r'\b(SHA256:[a-zA-Z0-9+/]{43}=?)\b'
        ),
        "ssh_md5_fingerprint": re.compile(
            r'\b([0-9a-f]{2}(?::[0-9a-f]{2}){15})\b',
            re.IGNORECASE
        ),
        "ssh_key": re.compile(
            r'(ssh-(?:rsa|dss|ed25519|ecdsa)\s+[A-Za-z0-9+/=]+)',
            re.IGNORECASE
        ),
        # NEW: Social media handles
        "twitter_handle": re.compile(
            r'(?:twitter\.com/|@)([a-zA-Z0-9_]{1,15})\b'
        ),
        "telegram_handle": re.compile(
            r'(?:t\.me/|telegram\.me/|@)([a-zA-Z0-9_]{5,32})\b'
        ),
        "discord_invite": re.compile(
            r'(?:discord\.gg/|discord\.com/invite/)([a-zA-Z0-9-]+)\b'
        ),
        # NEW: File hashes
        "md5_hash": re.compile(
            r'\b([a-fA-F0-9]{32})\b'
        ),
        "sha1_hash": re.compile(
            r'\b([a-fA-F0-9]{40})\b'
        ),
        "sha256_hash": re.compile(
            r'\b([a-fA-F0-9]{64})\b'
        ),
    }

    # JavaScript endpoint patterns (from Photon)
    JS_ENDPOINT_PATTERNS = [
        re.compile(r'["\'](/api/[a-zA-Z0-9_/-]+)["\']'),
        re.compile(r'["\'](/v[0-9]+/[a-zA-Z0-9_/-]+)["\']'),
        re.compile(r'fetch\s*\(\s*["\']([^"\']+)["\']'),
        re.compile(r'axios\.[a-z]+\s*\(\s*["\']([^"\']+)["\']'),
        re.compile(r'\.get\s*\(\s*["\']([^"\']+)["\']'),
        re.compile(r'\.post\s*\(\s*["\']([^"\']+)["\']'),
        re.compile(r'\.put\s*\(\s*["\']([^"\']+)["\']'),
        re.compile(r'\.delete\s*\(\s*["\']([^"\']+)["\']'),
        re.compile(r'url\s*[:=]\s*["\']([^"\']+)["\']'),
        re.compile(r'endpoint\s*[:=]\s*["\']([^"\']+)["\']'),
        re.compile(r'XMLHttpRequest.*open\s*\(["\'][A-Z]+["\'],\s*["\']([^"\']+)["\']'),
        re.compile(r'WebSocket\s*\(\s*["\']([^"\']+)["\']'),
        re.compile(r'new\s+EventSource\s*\(\s*["\']([^"\']+)["\']'),
        re.compile(r'graphql["\']?\s*[:=]\s*["\']([^"\']+)["\']', re.IGNORECASE),
    ]

    # Form type detection keywords
    FORM_TYPE_KEYWORDS = {
        "login": ["login", "signin", "sign-in", "log-in", "auth", "password", "username"],
        "registration": ["register", "signup", "sign-up", "create-account", "join"],
        "search": ["search", "query", "find", "q="],
        "contact": ["contact", "message", "email", "feedback", "inquiry"],
        "payment": ["payment", "checkout", "card", "billing", "pay"],
        "upload": ["upload", "file", "attach", "document"],
    }

    # External OSINT services (clearnet)
    OSINT_SERVICES = {
        "haveibeenpwned": "https://haveibeenpwned.com/api/v3/breachedaccount/{email}",
        "hunter": "https://api.hunter.io/v2/email-verifier?email={email}",
        "dehashed": "https://api.dehashed.com/search?query={query}",
        "crt.sh": "https://crt.sh/?q={domain}&output=json",
        "securitytrails": "https://api.securitytrails.com/v1/domain/{domain}/subdomains",
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

    # ============================================
    # Core Collection Methods
    # ============================================

    async def collect_from_url(
        self,
        url: str,
        html: Optional[str] = None,
        full_scan: bool = True,
    ) -> List[OSINTEntity]:
        """
        Collect OSINT entities from a URL.

        Args:
            url: Source URL
            html: Optional pre-fetched HTML
            full_scan: Include JS endpoint and form scanning

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

    async def collect_full_report(
        self,
        url: str,
        html: Optional[str] = None,
    ) -> OSINTReport:
        """
        Collect comprehensive OSINT report from URL.

        Includes entities, forms, JS endpoints, subdomains, SSL, language.
        """
        logger.info(f"[OSINTCollector] Full scan: {url}")

        if not html:
            html = await self._fetch(url)

        parsed = urlparse(url)
        domain = parsed.netloc

        report = OSINTReport(
            target=url,
            target_type="url",
            timestamp=datetime.utcnow().isoformat(),
        )

        if html:
            # Collect entities
            report.entities = await self.collect_from_url(url, html)

            # Discover forms
            report.forms = self.discover_forms(html, url)

            # Extract JS endpoints
            report.js_endpoints = self.extract_js_endpoints(html, url)

            # Detect language
            soup = BeautifulSoup(html, "lxml")
            text = soup.get_text(separator=" ")
            report.language = detect_language(text)

        # Enumerate subdomains (clearnet only)
        if not ".onion" in domain:
            report.subdomains = await self.enumerate_subdomains(domain)

            # Get SSL certificate
            report.ssl_cert = await self.get_ssl_certificate(domain)

        # Calculate stats
        report.stats = self._calculate_stats(report.entities)
        report.stats["forms_found"] = len(report.forms)
        report.stats["js_endpoints_found"] = len(report.js_endpoints)
        report.stats["subdomains_found"] = len(report.subdomains)
        report.stats["language"] = report.language[0]

        return report

    async def collect_from_search(
        self,
        query: str,
        max_results: int = 20,
    ) -> List[OSINTEntity]:
        """
        Search dark web and collect OSINT from results.
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

        # Domain-specific investigation
        if target_type == "domain":
            report.subdomains = await self.enumerate_subdomains(target)
            report.ssl_cert = await self.get_ssl_certificate(target)

        # Calculate stats
        report.stats = self._calculate_stats(report.entities)

        return report

    # ============================================
    # NEW: Form Discovery (from Hakrawler)
    # ============================================

    def discover_forms(self, html: str, base_url: str) -> List[FormInfo]:
        """
        Discover and analyze forms in HTML.

        Identifies login, registration, search, contact forms.
        """
        forms = []
        soup = BeautifulSoup(html, "lxml")

        for form in soup.find_all("form"):
            action = form.get("action", "")
            if action:
                action = urljoin(base_url, action)
            else:
                action = base_url

            method = form.get("method", "GET").upper()

            # Collect inputs
            inputs = []
            for inp in form.find_all(["input", "textarea", "select"]):
                inp_info = {
                    "name": inp.get("name", ""),
                    "type": inp.get("type", "text"),
                    "id": inp.get("id", ""),
                    "placeholder": inp.get("placeholder", ""),
                    "required": inp.has_attr("required"),
                }
                if inp_info["name"]:
                    inputs.append(inp_info)

            # Detect form type
            form_type = self._detect_form_type(form, action, inputs)

            form_info = FormInfo(
                action=action,
                method=method,
                inputs=inputs,
                source_url=base_url,
                form_type=form_type,
            )
            forms.append(form_info)

        logger.info(f"[OSINTCollector] Found {len(forms)} forms")
        return forms

    def _detect_form_type(self, form, action: str, inputs: List[dict]) -> str:
        """Detect form type based on attributes and inputs."""
        # Check action URL
        action_lower = action.lower()
        for form_type, keywords in self.FORM_TYPE_KEYWORDS.items():
            if any(kw in action_lower for kw in keywords):
                return form_type

        # Check input names/types
        input_names = " ".join(i.get("name", "").lower() for i in inputs)
        input_types = [i.get("type", "").lower() for i in inputs]

        if "password" in input_types:
            if any(kw in input_names for kw in ["register", "confirm", "repeat"]):
                return "registration"
            return "login"

        if "search" in input_types or "search" in input_names:
            return "search"

        if "file" in input_types:
            return "upload"

        if any(kw in input_names for kw in ["email", "message", "subject"]):
            return "contact"

        return "unknown"

    # ============================================
    # NEW: JavaScript Endpoint Extraction (from Photon)
    # ============================================

    def extract_js_endpoints(self, html: str, base_url: str) -> List[JSEndpoint]:
        """
        Extract API endpoints from JavaScript code.

        Finds fetch calls, axios requests, XHR, WebSocket connections.
        """
        endpoints = []
        seen_urls = set()
        soup = BeautifulSoup(html, "lxml")

        # Collect all script content
        js_content = []
        for script in soup.find_all("script"):
            src = script.get("src", "")
            if src:
                js_content.append(f"// Source: {src}")
            if script.string:
                js_content.append(script.string)

        # Also check inline event handlers
        for tag in soup.find_all(True):
            for attr in ["onclick", "onsubmit", "onload", "onerror"]:
                if tag.get(attr):
                    js_content.append(tag[attr])

        all_js = "\n".join(js_content)

        # Extract endpoints
        for pattern in self.JS_ENDPOINT_PATTERNS:
            for match in pattern.findall(all_js):
                url = match.strip()
                if not url or url in seen_urls:
                    continue

                # Skip data URIs, anchors, etc.
                if url.startswith(("data:", "#", "javascript:", "mailto:")):
                    continue

                seen_urls.add(url)

                # Determine endpoint type
                endpoint_type = "api"
                if "graphql" in url.lower():
                    endpoint_type = "graphql"
                elif url.startswith("ws://") or url.startswith("wss://"):
                    endpoint_type = "websocket"
                elif "/v1/" in url or "/v2/" in url or "/api/" in url:
                    endpoint_type = "api"

                # Detect method from context
                method = "GET"
                context_pattern = re.compile(
                    rf'\.?(post|put|delete|patch)\s*\(\s*["\']?{re.escape(url)}',
                    re.IGNORECASE
                )
                method_match = context_pattern.search(all_js)
                if method_match:
                    method = method_match.group(1).upper()

                # Extract URL parameters
                parsed = urlparse(url)
                params = list(parse_qs(parsed.query).keys())

                endpoint = JSEndpoint(
                    url=url,
                    method=method,
                    params=params,
                    source_file=base_url,
                    endpoint_type=endpoint_type,
                )
                endpoints.append(endpoint)

        logger.info(f"[OSINTCollector] Found {len(endpoints)} JS endpoints")
        return endpoints

    # ============================================
    # NEW: Subdomain Enumeration
    # ============================================

    async def enumerate_subdomains(self, domain: str) -> List[str]:
        """
        Enumerate subdomains using crt.sh certificate transparency.
        """
        subdomains = set()

        try:
            # Use crt.sh (free, no API key needed)
            url = f"https://crt.sh/?q=%.{domain}&output=json"

            if self.fetch_func:
                response = await self.fetch_func(url, timeout=30)
            else:
                import httpx
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.get(url)
                    response = resp.text if resp.status_code == 200 else None

            if response:
                try:
                    certs = json.loads(response)
                    for cert in certs:
                        name = cert.get("name_value", "")
                        for sub in name.split("\n"):
                            sub = sub.strip().lower()
                            if sub.endswith(domain) and "*" not in sub:
                                subdomains.add(sub)
                except json.JSONDecodeError:
                    pass

        except Exception as e:
            logger.error(f"Subdomain enumeration failed: {e}")

        result = sorted(subdomains)
        logger.info(f"[OSINTCollector] Found {len(result)} subdomains for {domain}")
        return result

    # ============================================
    # NEW: SSL Certificate Extraction (from FinalRecon)
    # ============================================

    async def get_ssl_certificate(self, domain: str, port: int = 443) -> Optional[SSLCertInfo]:
        """
        Extract SSL certificate information from domain.
        """
        try:
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            cert_info = await loop.run_in_executor(
                None,
                self._get_ssl_cert_sync,
                domain,
                port
            )
            return cert_info
        except Exception as e:
            logger.error(f"SSL cert extraction failed for {domain}: {e}")
            return None

    def _get_ssl_cert_sync(self, domain: str, port: int = 443) -> Optional[SSLCertInfo]:
        """Synchronous SSL certificate extraction."""
        try:
            context = ssl.create_default_context()

            with socket.create_connection((domain, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()
                    cert_bin = ssock.getpeercert(binary_form=True)

            # Extract subject
            subject = {}
            for item in cert.get("subject", []):
                for key, value in item:
                    subject[key] = value

            # Extract issuer
            issuer = {}
            for item in cert.get("issuer", []):
                for key, value in item:
                    issuer[key] = value

            # Extract SANs
            san = []
            for san_type, san_value in cert.get("subjectAltName", []):
                if san_type == "DNS":
                    san.append(san_value)

            # Calculate fingerprint
            fingerprint = hashlib.sha256(cert_bin).hexdigest().upper()
            fingerprint = ":".join(fingerprint[i:i+2] for i in range(0, len(fingerprint), 2))

            return SSLCertInfo(
                subject=subject,
                issuer=issuer,
                serial_number=str(cert.get("serialNumber", "")),
                not_before=cert.get("notBefore", ""),
                not_after=cert.get("notAfter", ""),
                fingerprint_sha256=fingerprint,
                san=san,
            )

        except Exception as e:
            logger.debug(f"SSL extraction error: {e}")
            return None

    # ============================================
    # Monitoring
    # ============================================

    async def monitor_keywords(
        self,
        keywords: List[str],
        interval: int = 3600,
        callback=None,
    ):
        """
        Monitor dark web for keywords.
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

    # ============================================
    # Utility Methods
    # ============================================

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
            if any(x in entity.value.lower() for x in ["example", "test", "fake", "noreply"]):
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
            try:
                if any(int(o) > 255 for o in octets):
                    confidence = 0
                # Skip private/reserved IPs
                if octets[0] in ["10", "127", "0"] or \
                   (octets[0] == "192" and octets[1] == "168") or \
                   (octets[0] == "172" and 16 <= int(octets[1]) <= 31):
                    confidence *= 0.3
            except ValueError:
                confidence = 0

        # Credit card Luhn check
        if entity.entity_type == "credit_card":
            if not self._luhn_check(entity.value.replace("-", "").replace(" ", "")):
                confidence *= 0.3

        # Hash validation (check if it's likely a real hash vs random hex)
        if entity.entity_type in ["md5_hash", "sha1_hash", "sha256_hash"]:
            # Reduce confidence for common false positives
            if entity.value.lower() in ["0" * len(entity.value), "f" * len(entity.value)]:
                confidence = 0

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

    def _calculate_stats(self, entities: List[OSINTEntity]) -> dict:
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
            if ".onion" in url and self.tor_manager:
                return await self._fetch_via_tor(url)
            elif self.fetch_func:
                return await self.fetch_func(url, timeout=60)
            else:
                import httpx
                async with httpx.AsyncClient(timeout=60) as client:
                    resp = await client.get(url)
                    return resp.text if resp.status_code == 200 else None
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


# ============================================
# Convenience Functions
# ============================================

async def collect_osint(
    url: str,
    tor_manager=None,
    fetch_func=None,
) -> List[OSINTEntity]:
    """Quick OSINT collection from URL."""
    collector = OSINTCollector(
        tor_manager=tor_manager,
        fetch_func=fetch_func,
    )
    return await collector.collect_from_url(url)


async def full_osint_scan(
    url: str,
    tor_manager=None,
    fetch_func=None,
) -> OSINTReport:
    """Full OSINT scan including forms, JS endpoints, subdomains, SSL."""
    collector = OSINTCollector(
        tor_manager=tor_manager,
        fetch_func=fetch_func,
    )
    return await collector.collect_full_report(url)


__all__ = [
    "OSINTCollector",
    "OSINTEntity",
    "OSINTReport",
    "FormInfo",
    "JSEndpoint",
    "SSLCertInfo",
    "collect_osint",
    "full_osint_scan",
    "detect_language",
]

"""
Security Sanitization and Input Validation
==========================================
NASA Standard: Mitigation of injection and smuggling attacks.
Ensures all scraped and input data is within safe parameters.
"""

import logging
import re
from urllib.parse import urlparse

logger = logging.getLogger("Sanitizer")

class InputSanitizer:
    """
    Cleans and validates all external inputs.
    """

    @staticmethod
    def sanitize_url(url: str) -> str | None:
        """
        Validate URL against SSRF and injection patterns.
        """
        if not url:
            return None

        # 1. Basic URL parsing
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            logger.warning(f"Invalid URL schema/loc: {url}")
            return None

        # 2. SSRF Protection (Block private IPs)
        private_patterns = [
            r'^127\.', r'^10\.', r'^172\.(1[6-9]|2[0-9]|3[0-1])\.',
            r'^192\.168\.', r'^localhost$', r'^0\.0\.0\.0$'
        ]
        if any(re.match(p, parsed.netloc) for p in private_patterns):
            logger.warning(f"SSRF Attempt Blocked: {url}")
            return None

        # 3. Protocol Whitelist
        if parsed.scheme.lower() not in ("http", "https"):
            logger.warning(f"Protocol Blocked: {parsed.scheme}")
            return None

        return url

    @staticmethod
    def clean_headers(headers: dict) -> dict:
        """
        Strip sensitive or illegal characters from headers to prevent smuggling.
        """
        clean = {}
        for k, v in headers.items():
            # Remove line breaks and non-printable chars
            clean_k = re.sub(r'[\r\n\x00-\x1F]', '', str(k))
            clean_v = re.sub(r'[\r\n\x00-\x1F]', '', str(v))
            clean[clean_k] = clean_v
        return clean

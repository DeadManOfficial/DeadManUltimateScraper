"""
Cookie Manager for Authenticated Scraping
==========================================
Handles Netscape cookie files and session management.
"""

import logging
import os
from http.cookiejar import MozillaCookieJar
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger("CookieManager")


class CookieManager:
    """Manages cookies for authenticated scraping."""

    def __init__(self, cookie_file: str | Path | None = None):
        self.cookie_file = Path(cookie_file) if cookie_file else None
        self.cookies: dict[str, dict[str, str]] = {}  # domain -> {name: value}

        if self.cookie_file and self.cookie_file.exists():
            self._load_cookies()

    def _load_cookies(self):
        """Load cookies from Netscape format file."""
        try:
            with open(self.cookie_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue

                    parts = line.split('\t')
                    if len(parts) >= 7:
                        domain = parts[0].lstrip('.')
                        name = parts[5]
                        value = parts[6]

                        if domain not in self.cookies:
                            self.cookies[domain] = {}
                        self.cookies[domain][name] = value

            logger.info(f"Loaded cookies for {len(self.cookies)} domains")
        except Exception as e:
            logger.error(f"Failed to load cookies: {e}")

    def get_cookies_for_url(self, url: str) -> dict[str, str]:
        """Get all cookies matching a URL's domain."""
        domain = urlparse(url).netloc
        result = {}

        # Check exact domain and parent domains
        parts = domain.split('.')
        for i in range(len(parts)):
            check_domain = '.'.join(parts[i:])
            if check_domain in self.cookies:
                result.update(self.cookies[check_domain])

        return result

    def get_cookie_header(self, url: str) -> str:
        """Get Cookie header value for a URL."""
        cookies = self.get_cookies_for_url(url)
        return '; '.join(f"{k}={v}" for k, v in cookies.items())

    def add_cookie(self, domain: str, name: str, value: str):
        """Add a cookie manually."""
        if domain not in self.cookies:
            self.cookies[domain] = {}
        self.cookies[domain][name] = value

    def has_cookies_for(self, url: str) -> bool:
        """Check if we have cookies for a URL."""
        return bool(self.get_cookies_for_url(url))


# Pre-configured OutlawPrompts cookies (from user's export)
OUTLAWPROMPTS_COOKIES = {
    "app.outlawprompts.com": {
        "__Secure-better-auth.session_token": "bYUWwogks8Sb6HREiI7kGn4bR5tZ1Vgl.mqUhX7RYH3AopDA0sVfAcU8KvvbkzrS0WGdCuSgIOUg=",
    },
    "outlawprompts.com": {
        "cf_clearance": "DwjyKM88TJhhp.vfu5isKs9rZYTAfrBDI6pcTosPPOs-1769043068-1.2.1.1-ZDMbUY.f3ty7WZIJuO71bbW984q5R0X2p_Pehi7rzhH3CBWunETVO3bxhAIBPhyaGg1vEAMh0gdxdqJaWXo7e6eTzDVdbir.lmX_cb10foq4q7XVJfHZn0aOVDd3__q4YNjDcl.fgVnwf38I8IVV9ty2jmPdi7sio0a4q0b8X.5OG1plpCEjlAhobt8W4DTP.7aycXl6SLEHgUhyqQOuS3KDbwcF9s4lyANPENEVcDE",
    }
}


def get_outlawprompts_manager() -> CookieManager:
    """Get a CookieManager pre-loaded with OutlawPrompts cookies."""
    manager = CookieManager()
    for domain, cookies in OUTLAWPROMPTS_COOKIES.items():
        for name, value in cookies.items():
            manager.add_cookie(domain, name, value)
    return manager

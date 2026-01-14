"""
Header Generation
=================
Generates realistic browser headers to avoid detection.
"""

from __future__ import annotations

import random
from typing import Literal


class HeaderGenerator:
    """
    Generates realistic HTTP headers matching real browser behavior.

    Features:
    - Proper header ordering (browsers have consistent order)
    - Realistic Accept headers
    - Matching Sec-CH-UA with User-Agent
    - Random but valid Accept-Language
    """

    # Chrome header templates (order matters!)
    CHROME_HEADERS_ORDER = [
        "Host",
        "Connection",
        "sec-ch-ua",
        "sec-ch-ua-mobile",
        "sec-ch-ua-platform",
        "Upgrade-Insecure-Requests",
        "User-Agent",
        "Accept",
        "Sec-Fetch-Site",
        "Sec-Fetch-Mode",
        "Sec-Fetch-User",
        "Sec-Fetch-Dest",
        "Accept-Encoding",
        "Accept-Language",
    ]

    # Sec-CH-UA values matching Chrome versions
    SEC_CH_UA = {
        "120": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "121": '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
        "122": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        "123": '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
    }

    # Accept headers for different content types
    ACCEPT_HTML = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
    ACCEPT_JSON = "application/json, text/plain, */*"
    ACCEPT_ANY = "*/*"

    # Accept-Language variations
    ACCEPT_LANGUAGES = [
        "en-US,en;q=0.9",
        "en-US,en;q=0.9,es;q=0.8",
        "en-GB,en;q=0.9,en-US;q=0.8",
        "en-US,en;q=0.9,de;q=0.8,fr;q=0.7",
    ]

    @classmethod
    def generate(
        cls,
        browser: Literal["chrome", "firefox", "safari", "edge"] = "chrome",
        version: str = "120",
        content_type: Literal["html", "json", "any"] = "html",
        referer: str | None = None,
        origin: str | None = None,
    ) -> dict[str, str]:
        """
        Generate realistic browser headers.

        Args:
            browser: Target browser
            version: Browser version
            content_type: Expected response type
            referer: Optional referer header
            origin: Optional origin header

        Returns:
            Dictionary of headers in correct order
        """
        if browser == "chrome":
            return cls._generate_chrome_headers(version, content_type, referer, origin)
        elif browser == "firefox":
            return cls._generate_firefox_headers(version, content_type, referer, origin)
        else:
            return cls._generate_chrome_headers(version, content_type, referer, origin)

    @classmethod
    def _generate_chrome_headers(
        cls,
        version: str,
        content_type: str,
        referer: str | None,
        origin: str | None,
    ) -> dict[str, str]:
        """Generate Chrome-specific headers."""
        # Select Accept header
        if content_type == "html":
            accept = cls.ACCEPT_HTML
        elif content_type == "json":
            accept = cls.ACCEPT_JSON
        else:
            accept = cls.ACCEPT_ANY

        # User agent
        user_agent = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version}.0.0.0 Safari/537.36"

        # Sec-CH-UA
        sec_ch_ua = cls.SEC_CH_UA.get(version, cls.SEC_CH_UA["120"])

        headers = {
            "Connection": "keep-alive",
            "sec-ch-ua": sec_ch_ua,
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": user_agent,
            "Accept": accept,
            "Sec-Fetch-Site": "none" if not referer else "same-origin",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-User": "?1",
            "Sec-Fetch-Dest": "document",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": random.choice(cls.ACCEPT_LANGUAGES),
        }

        if referer:
            headers["Referer"] = referer
        if origin:
            headers["Origin"] = origin

        return headers

    @classmethod
    def _generate_firefox_headers(
        cls,
        version: str,
        content_type: str,
        referer: str | None,
        origin: str | None,
    ) -> dict[str, str]:
        """Generate Firefox-specific headers."""
        if content_type == "html":
            accept = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
        elif content_type == "json":
            accept = "application/json, text/plain, */*"
        else:
            accept = "*/*"

        user_agent = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{version}.0) Gecko/20100101 Firefox/{version}.0"

        headers = {
            "User-Agent": user_agent,
            "Accept": accept,
            "Accept-Language": random.choice(cls.ACCEPT_LANGUAGES),
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none" if not referer else "same-origin",
            "Sec-Fetch-User": "?1",
        }

        if referer:
            headers["Referer"] = referer
        if origin:
            headers["Origin"] = origin

        return headers

    @classmethod
    def generate_api_headers(
        cls,
        browser: Literal["chrome", "firefox"] = "chrome",
        version: str = "120",
        content_type: str = "application/json",
    ) -> dict[str, str]:
        """Generate headers for API requests (XHR/Fetch)."""
        base = cls.generate(browser, version, "json")

        # Modify for API request pattern
        base["Sec-Fetch-Dest"] = "empty"
        base["Sec-Fetch-Mode"] = "cors"
        base["Sec-Fetch-Site"] = "same-origin"
        base.pop("Sec-Fetch-User", None)
        base.pop("Upgrade-Insecure-Requests", None)

        if content_type:
            base["Content-Type"] = content_type

        return base

    @classmethod
    def add_cookies(cls, headers: dict[str, str], cookies: dict[str, str]) -> dict[str, str]:
        """Add cookies to headers."""
        if cookies:
            cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
            headers["Cookie"] = cookie_str
        return headers

    @classmethod
    def randomize_order(cls, headers: dict[str, str]) -> dict[str, str]:
        """
        Randomize header order while keeping important ones first.

        Some detection looks at header ordering.
        """
        # Keep these first (common across browsers)
        priority = ["Host", "Connection", "User-Agent"]

        result = {}
        for key in priority:
            if key in headers:
                result[key] = headers[key]

        # Randomize the rest
        remaining = [k for k in headers if k not in priority]
        random.shuffle(remaining)

        for key in remaining:
            result[key] = headers[key]

        return result

"""
Fingerprint Spoofing
====================
TLS (JA3/JA4), Canvas, WebGL, and browser fingerprint spoofing.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class BrowserFingerprint:
    """Represents a complete browser fingerprint."""

    # User Agent
    user_agent: str = ""
    platform: str = ""
    vendor: str = ""

    # Screen
    screen_width: int = 1920
    screen_height: int = 1080
    color_depth: int = 24
    pixel_ratio: float = 1.0

    # Hardware
    hardware_concurrency: int = 8
    device_memory: int = 8

    # WebGL
    webgl_vendor: str = "Intel Inc."
    webgl_renderer: str = "Intel Iris OpenGL Engine"

    # Locale
    language: str = "en-US"
    languages: list[str] = field(default_factory=lambda: ["en-US", "en"])
    timezone: str = "America/New_York"

    # Browser features
    plugins: list[str] = field(
        default_factory=lambda: ["Chrome PDF Plugin", "Chrome PDF Viewer", "Native Client"]
    )
    do_not_track: str | None = None
    cookies_enabled: bool = True


class FingerprintSpoofer:
    """
    Generates and manages browser fingerprints for stealth.

    Supports:
    - Chrome, Firefox, Safari, Edge impersonation
    - TLS fingerprint (JA3/JA4) for curl_cffi
    - Consistent fingerprint across sessions
    """

    # Common screen resolutions
    SCREEN_RESOLUTIONS = [
        (1920, 1080), (1366, 768), (1536, 864), (1440, 900),
        (1280, 720), (2560, 1440), (3840, 2160), (1600, 900),
        (1680, 1050), (1280, 800), (1024, 768), (1280, 1024)
    ]

    # WebGL vendors and renderers
    WEBGL_CONFIGS = [
        ("Intel Inc.", "Intel Iris OpenGL Engine"),
        ("Intel Inc.", "Intel(R) UHD Graphics 620"),
        ("Intel Inc.", "Intel(R) HD Graphics 630"),
        ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA GeForce GTX 1060)"),
        ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA GeForce RTX 3060)"),
        ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA GeForce RTX 4070)"),
        ("Google Inc. (AMD)", "ANGLE (AMD Radeon RX 580)"),
        ("Google Inc. (AMD)", "ANGLE (AMD Radeon RX 6700 XT)"),
        ("Apple Inc.", "Apple GPU"),
        ("Microsoft", "Microsoft Basic Render Driver")
    ]

    @classmethod
    def generate_ja4(cls, browser: str = "chrome") -> str:
        """
        Generate a realistic JA4 TLS fingerprint.

        Format: t{protocol}{extensions}{cipher_count}{ciphers}{hash}
        Example: t13d1516h2_8daaf6152771_498c0309f995
        """
        if browser == "chrome":
            return f"t13d1516h2_{cls._rand_hex(12)}_{cls._rand_hex(12)}"
        elif browser == "firefox":
            return f"t13d1715h2_{cls._rand_hex(12)}_{cls._rand_hex(12)}"
        return f"t13d1516h2_{cls._rand_hex(12)}_{cls._rand_hex(12)}"

    @staticmethod
    def _rand_hex(length: int) -> str:
        return "".join(secrets.choice("0123456789abcdef") for _ in range(length))

    # Chrome versions with matching user agents
    CHROME_VERSIONS = {
        "120": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "121": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "122": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "123": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    }

    FIREFOX_VERSIONS = {
        "121": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "122": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
        "123": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    }

    # TLS fingerprints for curl_cffi impersonation
    CURL_CFFI_IMPERSONATIONS = [
        "chrome120",
        "chrome119",
        "chrome110",
        "chrome107",
        "chrome104",
        "edge101",
        "safari15_5",
    ]

    @classmethod
    def generate_fingerprint(
        cls,
        browser: Literal["chrome", "firefox", "safari", "edge"] = "chrome",
        version: str | None = None,
    ) -> BrowserFingerprint:
        """
        Generate a consistent browser fingerprint.

        Args:
            browser: Target browser to impersonate
            version: Specific version (random if not specified)

        Returns:
            Complete BrowserFingerprint
        """
        # Select version
        if browser == "chrome":
            versions = cls.CHROME_VERSIONS
            if version is None:
                version = secrets.choice(list(versions.keys()))
            user_agent = versions.get(version, versions["120"])
            platform = "Win32"
            vendor = "Google Inc."
        elif browser == "firefox":
            versions = cls.FIREFOX_VERSIONS
            if version is None:
                version = secrets.choice(list(versions.keys()))
            user_agent = versions.get(version, versions["121"])
            platform = "Win32"
            vendor = ""
        else:
            # Default to Chrome
            user_agent = cls.CHROME_VERSIONS["120"]
            platform = "Win32"
            vendor = "Google Inc."

        # Select screen resolution
        width, height = secrets.choice(cls.SCREEN_RESOLUTIONS)

        # Select WebGL config
        webgl_vendor, webgl_renderer = secrets.choice(cls.WEBGL_CONFIGS)

        # Hardware specs
        hardware_concurrency = secrets.choice([4, 6, 8, 12, 16])
        device_memory = secrets.choice([4, 8, 16, 32])

        return BrowserFingerprint(
            user_agent=user_agent,
            platform=platform,
            vendor=vendor,
            screen_width=width,
            screen_height=height,
            color_depth=24,
                            pixel_ratio=secrets.SystemRandom().choice([1.0, 1.25, 1.5, 2.0]),
                            hardware_concurrency=hardware_concurrency,
                            device_memory=device_memory,
                            webgl_vendor=webgl_vendor,
                            webgl_renderer=webgl_renderer,
                            language="en-US",
                            languages=["en-US", "en"],
                            timezone="America/New_York",
                        )

    @classmethod
    def get_curl_cffi_impersonate(
        cls,
        browser: Literal["chrome", "firefox", "safari", "edge"] = "chrome",
    ) -> str:
        """
        Get curl_cffi impersonation string for TLS fingerprinting.

        This makes HTTP requests have the same TLS fingerprint (JA3/JA4)
        as a real browser.
        """
        if browser == "chrome":
            return secrets.choice(["chrome120", "chrome119", "chrome110"])
        elif browser == "edge":
            return "edge101"
        elif browser == "safari":
            return "safari15_5"
        else:
            return "chrome120"

    @classmethod
    def get_fingerprint_js(cls, fingerprint: BrowserFingerprint) -> str:
        """
        Generate JavaScript to apply fingerprint to browser session.
        """
        return f"""
        // Apply custom fingerprint
        Object.defineProperty(navigator, 'userAgent', {{
            get: () => '{fingerprint.user_agent}'
        }});
        Object.defineProperty(navigator, 'platform', {{
            get: () => '{fingerprint.platform}'
        }});
        Object.defineProperty(navigator, 'vendor', {{
            get: () => '{fingerprint.vendor}'
        }});
        Object.defineProperty(navigator, 'hardwareConcurrency', {{
            get: () => {fingerprint.hardware_concurrency}
        }});
        Object.defineProperty(navigator, 'deviceMemory', {{
            get: () => {fingerprint.device_memory}
        }});
        Object.defineProperty(navigator, 'language', {{
            get: () => '{fingerprint.language}'
        }});
        Object.defineProperty(navigator, 'languages', {{
            get: () => {fingerprint.languages}
        }});
        Object.defineProperty(screen, 'width', {{
            get: () => {fingerprint.screen_width}
        }});
        Object.defineProperty(screen, 'height', {{
            get: () => {fingerprint.screen_height}
        }});
        Object.defineProperty(screen, 'colorDepth', {{
            get: () => {fingerprint.color_depth}
        }});
        Object.defineProperty(window, 'devicePixelRatio', {{
            get: () => {fingerprint.pixel_ratio}
        }});

        // WebGL fingerprint
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {{
            if (parameter === 37445) return '{fingerprint.webgl_vendor}';
            if (parameter === 37446) return '{fingerprint.webgl_renderer}';
            return getParameter.apply(this, arguments);
        }};
        """

    @classmethod
    def generate_canvas_noise_js(cls) -> str:
        """
        Generate JavaScript for canvas fingerprint randomization.

        Adds tiny noise to canvas operations to break fingerprinting
        while maintaining visual appearance.
        """
        return """
        // Canvas noise
        const toDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function(type) {
            if (type === 'image/png' || type === undefined) {
                const ctx = this.getContext('2d');
                if (ctx) {
                    const imageData = ctx.getImageData(0, 0, this.width, this.height);
                    for (let i = 0; i < imageData.data.length; i += 4) {
                        imageData.data[i] += Math.floor(Math.random() * 2);
                    }
                    ctx.putImageData(imageData, 0, 0);
                }
            }
            return toDataURL.apply(this, arguments);
        };

        const toBlob = HTMLCanvasElement.prototype.toBlob;
        HTMLCanvasElement.prototype.toBlob = function(callback, type, quality) {
            if (type === 'image/png' || type === undefined) {
                const ctx = this.getContext('2d');
                if (ctx) {
                    const imageData = ctx.getImageData(0, 0, this.width, this.height);
                    for (let i = 0; i < imageData.data.length; i += 4) {
                        imageData.data[i] += Math.floor(Math.random() * 2);
                    }
                    ctx.putImageData(imageData, 0, 0);
                }
            }
            return toBlob.apply(this, arguments);
        };
        """

"""
Adaptive Downloader
===================
5-Layer fetch system with automatic fallback:
1. curl_cffi (TLS fingerprint spoofing, fastest)
2. Camoufox/Nodriver (C++ stealth browsers)
3. Undetected ChromeDriver (Selenium stealth)
4. TOR Circuit (identity isolation)
5. CAPTCHA Solver (last resort)
"""

from __future__ import annotations

import asyncio
import logging
import socket
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from requests.adapters import HTTPAdapter
from urllib3.connection import HTTPConnection
from urllib3.util import Retry

if TYPE_CHECKING:
    from deadman_scraper.core.config import Config
    from deadman_scraper.core.signals import SignalManager
    from deadman_scraper.fetch.proxy_manager import ProxyManager
    from deadman_scraper.fetch.tor import TORManager

logger = logging.getLogger(__name__)


class AggressiveRetry(Retry):
    """
    ULTRA-AGGRESSIVE retry mechanism for NASA-grade reliability.
    """
    def __init__(self, **kwargs):
        kwargs.setdefault('total', 10)
        kwargs.setdefault('connect', 5)
        kwargs.setdefault('read', 5)
        kwargs.setdefault('backoff_factor', 0.5)
        kwargs.setdefault('status_forcelist', [429, 500, 502, 503, 504, 522, 524])
        super().__init__(**kwargs)


class TCPKeepAliveAdapter(HTTPAdapter):
    """
    HTTPAdapter with TCP keepalive enabled to prevent ECONNRESET.
    """
    def __init__(self, *args, **kwargs):
        self.socket_options = HTTPConnection.default_socket_options + [
            (socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1),
            (socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 45),
            (socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10),
            (socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 6),
        ]
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        kwargs['socket_options'] = self.socket_options
        return super().init_poolmanager(*args, **kwargs)


@dataclass
class FetchResult:
    """Result of a fetch operation."""

    success: bool
    url: str
    status_code: int | None = None
    content: str | None = None
    content_type: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    error: str | None = None
    layer: int = 0  # Which layer succeeded (1-5)
    timing: float = 0.0
    method: str = ""
    proxy_used: str | None = None


class AdaptiveDownloader:
    """
    5-Layer Adaptive Downloader.

    Automatically falls back through layers until success:
    1. curl_cffi - Fast HTTP with TLS fingerprint spoofing (JA3/JA4)
    2. Camoufox/Nodriver - C++ stealth browser automation
    3. Undetected ChromeDriver - Selenium with stealth patches
    4. TOR - Onion routing for identity isolation
    5. CAPTCHA Solver - 2Captcha/Anti-Captcha integration

    Usage:
        downloader = AdaptiveDownloader(config, signals, tor_manager, proxy_manager)
        result = await downloader.fetch("https://example.com")
    """

    def __init__(
        self,
        config: Config,
        signals: SignalManager | None = None,
        tor_manager: TORManager | None = None,
        proxy_manager: ProxyManager | None = None,
    ):
        self.config = config
        self.signals = signals
        self.tor_manager = tor_manager
        self.proxy_manager = proxy_manager

        # Lazy-loaded clients
        self._curl_session = None
        self._browser_pool = None

    async def fetch(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        force_tor: bool = False,
        force_layer: int | None = None,
    ) -> FetchResult:
        """
        Fetch URL using adaptive layer strategy.

        Args:
            url: Target URL
            headers: Custom headers (merged with generated)
            force_tor: Force TOR routing
            force_layer: Force specific layer (1-5)

        Returns:
            FetchResult with content and metadata
        """
        start_time = datetime.now().timestamp()

        # .onion sites always use TOR
        if ".onion" in url or force_tor:
            return await self._fetch_with_tor(url, headers)

        # If specific layer forced
        if force_layer:
            return await self._fetch_layer(force_layer, url, headers)

        # Adaptive fallback through layers
        layers = self.config.fetch.layers
        for i, layer in enumerate(layers, 1):
            if self.signals:
                await self.signals.emit(f"FETCH_LAYER_{i}_STARTED", url=url)

            result = await self._fetch_layer_by_name(layer, url, headers)

            if result.success:
                result.timing = datetime.now().timestamp() - start_time
                if self.signals:
                    await self.signals.emit("FETCH_SUCCESS", url=url, layer=i)
                return result

            logger.info(f"[LAYER {i}] {layer} failed for {url}, trying next...")
            if self.signals:
                await self.signals.emit("FETCH_FALLBACK", url=url, from_layer=i)

        # All layers failed
        return FetchResult(
            success=False,
            url=url,
            error="All fetch layers exhausted",
            timing=datetime.now().timestamp() - start_time,
        )

    async def _fetch_layer(self, layer: int, url: str, headers: dict | None) -> FetchResult:
        """Fetch using specific layer number."""
        layer_map = {
            1: "curl_cffi",
            2: "camoufox",
            3: "chromedriver",
            4: "tor",
            5: "captcha",
        }
        layer_name = layer_map.get(layer, "curl_cffi")
        return await self._fetch_layer_by_name(layer_name, url, headers)

    async def _fetch_layer_by_name(
        self, layer: str, url: str, headers: dict | None
    ) -> FetchResult:
        """Fetch using layer by name."""
        if layer == "curl_cffi":
            return await self._fetch_with_curl_cffi(url, headers)
        elif layer in ("camoufox", "nodriver"):
            return await self._fetch_with_nodriver(url, headers)
        elif layer == "chromedriver":
            return await self._fetch_with_chromedriver(url, headers)
        elif layer == "tor":
            return await self._fetch_with_tor(url, headers)
        elif layer == "captcha":
            return await self._fetch_with_captcha_solver(url, headers)
        else:
            return FetchResult(success=False, url=url, error=f"Unknown layer: {layer}")

    # =========================================================================
    # LAYER 1: curl_cffi (TLS Fingerprint Spoofing)
    # =========================================================================

    async def _fetch_with_curl_cffi(
        self, url: str, headers: dict | None
    ) -> FetchResult:
        """
        Layer 1: curl_cffi with TLS fingerprint spoofing.

        Uses JA3/JA4 fingerprint impersonation to appear as real browser.
        Fastest option, works for most sites.
        """
        try:
            from curl_cffi import requests as curl_requests

            from deadman_scraper.stealth.fingerprint import FingerprintSpoofer
            from deadman_scraper.stealth.headers import HeaderGenerator

            # Generate headers
            browser = self.config.stealth.impersonate_browser
            version = self.config.stealth.impersonate_version
            gen_headers = HeaderGenerator.generate(browser, version)
            if headers:
                gen_headers.update(headers)

            # Get impersonation string
            impersonate = FingerprintSpoofer.get_curl_cffi_impersonate(browser)

            logger.debug(f"[CURL_CFFI] Fetching {url} as {impersonate}")

            # Make request
            response = await asyncio.to_thread(
                curl_requests.get,
                url,
                impersonate=impersonate,
                headers=gen_headers,
                timeout=self.config.fetch.request_timeout,
            )

            return FetchResult(
                success=True,
                url=url,
                status_code=response.status_code,
                content=response.text,
                content_type=response.headers.get("content-type", ""),
                headers=dict(response.headers),
                layer=1,
                method="curl_cffi",
            )

        except ImportError:
            return FetchResult(
                success=False, url=url, error="curl_cffi not installed", layer=1
            )
        except Exception as e:
            logger.debug(f"[CURL_CFFI] Failed: {e}")
            return FetchResult(success=False, url=url, error=str(e), layer=1)

    # =========================================================================
    # LAYER 2: Nodriver (C++ Stealth Browser)
    # =========================================================================

    async def _fetch_with_nodriver(
        self, url: str, headers: dict | None
    ) -> FetchResult:
        """
        Layer 2: nodriver - undetected browser automation.

        C++ based, very stealthy, handles most bot detection.
        """
        try:
            import nodriver as uc

            from deadman_scraper.stealth.injector import StealthInjector

            logger.debug(f"[NODRIVER] Fetching {url}")

            # Start browser
            browser = await uc.start(
                headless=self.config.browser_pool.headless,
            )

            try:
                # Create page and inject stealth
                page = await browser.get(url)

                # Inject additional stealth
                await StealthInjector.inject_nodriver(page)

                # Wait for content
                await asyncio.sleep(2)

                # Get content
                content = await page.get_content()

                return FetchResult(
                    success=True,
                    url=url,
                    status_code=200,  # nodriver doesn't expose status
                    content=content,
                    content_type="text/html",
                    layer=2,
                    method="nodriver",
                )

            finally:
                await browser.stop()

        except ImportError:
            return FetchResult(
                success=False, url=url, error="nodriver not installed", layer=2
            )
        except Exception as e:
            logger.debug(f"[NODRIVER] Failed: {e}")
            return FetchResult(success=False, url=url, error=str(e), layer=2)

    # =========================================================================
    # LAYER 3: Undetected ChromeDriver (Selenium Stealth)
    # =========================================================================

    async def _fetch_with_chromedriver(
        self, url: str, headers: dict | None
    ) -> FetchResult:
        """
        Layer 3: Undetected ChromeDriver with stealth patches.

        Uses Selenium with stealth injection for maximum compatibility.
        """
        try:
            import undetected_chromedriver as uc
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support import expected_conditions as ec
            from selenium.webdriver.support.ui import WebDriverWait

            from deadman_scraper.stealth.behavior import BehavioralSimulator
            from deadman_scraper.stealth.injector import StealthInjector

            logger.debug(f"[CHROMEDRIVER] Fetching {url}")

            # Chrome options
            options = uc.ChromeOptions()
            if self.config.browser_pool.headless:
                options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")

            driver = await asyncio.to_thread(
                uc.Chrome, options=options, use_subprocess=True
            )

            try:
                # Inject stealth
                StealthInjector.inject_selenium(driver)

                # Navigate
                await asyncio.to_thread(driver.get, url)

                # Wait for page load
                await asyncio.to_thread(
                    WebDriverWait(driver, self.config.fetch.page_load_timeout).until,
                    ec.presence_of_element_located((By.TAG_NAME, "body")),
                )

                # Human simulation
                if self.config.stealth.simulate_human:
                    BehavioralSimulator.scroll_page_sync(driver)
                    BehavioralSimulator.human_delay_sync(1, 2)

                # Get content
                content = await asyncio.to_thread(
                    lambda: driver.page_source
                )

                return FetchResult(
                    success=True,
                    url=url,
                    status_code=200,
                    content=content,
                    content_type="text/html",
                    layer=3,
                    method="undetected_chromedriver",
                )

            finally:
                await asyncio.to_thread(driver.quit)

        except ImportError:
            return FetchResult(
                success=False,
                url=url,
                error="undetected-chromedriver not installed",
                layer=3,
            )
        except Exception as e:
            logger.debug(f"[CHROMEDRIVER] Failed: {e}")
            return FetchResult(success=False, url=url, error=str(e), layer=3)

    # =========================================================================
    # LAYER 4: TOR (Identity Isolation)
    # =========================================================================

    async def _fetch_with_tor(self, url: str, headers: dict | None) -> FetchResult:
        """
        Layer 4: TOR network routing.

        Essential for .onion sites and when IP is blocked.
        """
        try:
            import httpx

            logger.debug(f"[TOR] Fetching {url}")

            # Ensure TOR is running
            if self.tor_manager:
                await self.tor_manager.ensure_running()

            # TOR proxy configuration
            tor_host = self.config.tor.socks_host
            tor_port = self.config.tor.socks_port
            proxy_url = f"socks5h://{tor_host}:{tor_port}"

            # Generate headers
            from deadman_scraper.stealth.headers import HeaderGenerator

            gen_headers = HeaderGenerator.generate("firefox", "121")
            if headers:
                gen_headers.update(headers)

            async with httpx.AsyncClient(
                proxy=proxy_url,
                timeout=self.config.tor.connect_timeout,
            ) as client:
                response = await client.get(url, headers=gen_headers)

                return FetchResult(
                    success=True,
                    url=url,
                    status_code=response.status_code,
                    content=response.text,
                    content_type=response.headers.get("content-type", ""),
                    headers=dict(response.headers),
                    layer=4,
                    method="tor",
                )

        except ImportError:
            return FetchResult(
                success=False, url=url, error="httpx not installed", layer=4
            )
        except Exception as e:
            logger.debug(f"[TOR] Failed: {e}")
            return FetchResult(success=False, url=url, error=str(e), layer=4)

    # =========================================================================
    # LAYER 5: CAPTCHA Solver (Last Resort)
    # =========================================================================

    async def _fetch_with_captcha_solver(
        self, url: str, headers: dict | None
    ) -> FetchResult:
        """
        Layer 5: Full browser with CAPTCHA solving.

        Uses ChromeDriver + 2Captcha/Anti-Captcha API.
        Most expensive (in time), but handles everything.
        """
        try:
            import undetected_chromedriver as uc

            from deadman_scraper.stealth.injector import StealthInjector

            logger.debug(f"[CAPTCHA] Fetching {url}")

            options = uc.ChromeOptions()
            options.add_argument("--no-sandbox")
            # Not headless - some CAPTCHAs detect headless

            driver = await asyncio.to_thread(
                uc.Chrome, options=options, use_subprocess=True
            )

            try:
                StealthInjector.inject_selenium(driver)
                await asyncio.to_thread(driver.get, url)

                # Wait for page to settle
                await asyncio.sleep(3)

                # Check for CAPTCHA
                captcha_detected = await asyncio.to_thread(
                    self._detect_captcha, driver
                )

                if captcha_detected:
                    logger.info("[CAPTCHA] CAPTCHA detected, attempting solve...")
                    solved = await self._solve_captcha(driver)
                    if not solved:
                        return FetchResult(
                            success=False,
                            url=url,
                            error="CAPTCHA solving failed",
                            layer=5,
                        )
                    # Wait for redirect after solving
                    await asyncio.sleep(3)

                content = await asyncio.to_thread(lambda: driver.page_source)

                return FetchResult(
                    success=True,
                    url=url,
                    status_code=200,
                    content=content,
                    content_type="text/html",
                    layer=5,
                    method="captcha_solver",
                )

            finally:
                await asyncio.to_thread(driver.quit)

        except Exception as e:
            logger.debug(f"[CAPTCHA] Failed: {e}")
            return FetchResult(success=False, url=url, error=str(e), layer=5)

    def _detect_captcha(self, driver: Any) -> bool:
        """Detect CAPTCHA presence on page."""
        captcha_selectors = [
            'iframe[src*="captcha"]',
            'iframe[src*="recaptcha"]',
            'iframe[title*="reCAPTCHA"]',
            "#cf-challenge-running",
            ".g-recaptcha",
            "#challenge-form",
            '[name="cf-turnstile-response"]',
            ".h-captcha",
        ]

        try:
            from selenium.webdriver.common.by import By

            for selector in captcha_selectors:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    return True
            return False
        except Exception:
            return False

    async def _solve_captcha(self, driver: Any) -> bool:
        """
        Solve CAPTCHA using 2Captcha service.
        NASA Standard: External service integration with error isolation.
        """
        if not self.config.captcha.enabled or not self.config.captcha.api_key:
            logger.warning("[CAPTCHA] Service disabled or API key missing.")
            return False

        try:
            from twocaptcha import TwoCaptcha
            solver = TwoCaptcha(self.config.captcha.api_key)

            url = driver.current_url
            # Detect sitekey from page
            sitekey = driver.execute_script("""
                const elem = document.querySelector('[data-sitekey]');
                return elem ? elem.getAttribute('data-sitekey') : null;
            """)

            if not sitekey:
                logger.error("[CAPTCHA] Could not find sitekey on page.")
                return False

            logger.info(f"[CAPTCHA] Sending request to 2Captcha for {url}")

            # Use to_thread for blocking SDK call
            result = await asyncio.to_thread(
                solver.recaptcha,
                sitekey=sitekey,
                url=url
            )

            if result and 'code' in result:
                logger.info("[CAPTCHA] Challenge solved successfully.")
                # Inject response
                driver.execute_script(f"""
                    document.getElementById('g-recaptcha-response').innerHTML = '{result['code']}';
                """)
                return True

            return False

        except Exception as e:
            logger.error(f"[CAPTCHA] Solving failed: {e}")
            return False

"""
Bypass Chain
============
8-method bypass chain for protected sites.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Any

from .cookies import CookieManager
from .extract import ContentExtractor

logger = logging.getLogger("BypassChain")


@dataclass
class BypassResult:
    """Result from a bypass attempt."""
    success: bool
    method: str | None = None
    html: str | None = None
    status_code: int | None = None
    error: str | None = None
    methods_tried: list[str] = field(default_factory=list)
    extracted: Any = None


class BypassChain:
    """
    Chain of bypass methods for Cloudflare and bot protection.

    Methods (in order of speed):
    1. curl_cffi - TLS fingerprint impersonation
    2. curl_cffi + TOR - Anonymous + fingerprint
    3. cloudscraper - JavaScript challenge solver
    4. FlareSolverr - Headless browser service
    5. undetected-chromedriver - Stealth Chrome
    6. nodriver - Modern undetected driver
    7. playwright-stealth - Playwright with stealth
    8. botasaurus - Anti-detect framework
    """

    def __init__(
        self,
        cookies: CookieManager | None = None,
        flaresolverr_url: str = "http://localhost:8191",
        tor_proxy: str = "socks5h://127.0.0.1:9050",
        render_only: bool = False,
        timeout: int = 30
    ):
        self.cookies = cookies
        self.flaresolverr_url = flaresolverr_url
        self.tor_proxy = tor_proxy
        self.render_only = render_only
        self.timeout = timeout

    async def scrape(self, url: str, extract_mode: str = 'all') -> BypassResult:
        """
        Attempt to scrape URL using bypass chain.

        Args:
            url: Target URL
            extract_mode: Extraction mode (all, text, links, json, prompts, or CSS selector)

        Returns:
            BypassResult with HTML and extracted content
        """
        result = BypassResult(success=False)

        methods = self._get_methods()

        for name, method in methods:
            result.methods_tried.append(name)
            logger.info(f"Trying {name}...")

            try:
                html = await self._try_method(method, url)

                if html and len(html) > 1000:
                    result.success = True
                    result.method = name
                    result.html = html

                    # Extract content
                    extractor = ContentExtractor(html)
                    result.extracted = extractor.extract(extract_mode)

                    logger.info(f"SUCCESS with {name}!")
                    return result

            except Exception as e:
                logger.warning(f"{name} failed: {e}")

        logger.error("All bypass methods failed")
        return result

    def _get_methods(self) -> list[tuple[str, Callable]]:
        """Get list of bypass methods based on settings."""
        all_methods = [
            ('curl_cffi', self._curl_cffi),
            ('curl_cffi_tor', self._curl_cffi_tor),
            ('cloudscraper', self._cloudscraper),
            ('flaresolverr', self._flaresolverr),
            ('undetected_chrome', self._undetected_chrome),
            ('nodriver', self._nodriver),
            ('playwright_stealth', self._playwright_stealth),
            ('botasaurus', self._botasaurus),
        ]

        if self.render_only:
            # Only browser-based methods for JavaScript SPAs
            browser_methods = ['flaresolverr', 'undetected_chrome', 'nodriver', 'playwright_stealth', 'botasaurus']
            return [(n, m) for n, m in all_methods if n in browser_methods]

        return all_methods

    async def _try_method(self, method: Callable, url: str) -> str | None:
        """Try a bypass method, handling sync/async."""
        if asyncio.iscoroutinefunction(method):
            return await method(url)
        else:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, method, url)

    def _get_headers(self, url: str) -> dict[str, str]:
        """Get headers including cookies if available."""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }

        if self.cookies:
            cookie_header = self.cookies.get_cookie_header(url)
            if cookie_header:
                headers['Cookie'] = cookie_header

        return headers

    # === BYPASS METHODS ===

    async def _curl_cffi(self, url: str) -> str | None:
        """curl_cffi with Chrome TLS fingerprint."""
        try:
            from curl_cffi.requests import AsyncSession

            headers = self._get_headers(url)
            async with AsyncSession(impersonate='chrome120') as s:
                resp = await s.get(url, headers=headers, timeout=self.timeout)
                logger.info(f"curl_cffi status: {resp.status_code}")
                if resp.status_code == 200:
                    return resp.text
        except ImportError:
            logger.warning("curl_cffi not installed")
        except Exception as e:
            logger.warning(f"curl_cffi error: {e}")
        return None

    async def _curl_cffi_tor(self, url: str) -> str | None:
        """curl_cffi through TOR."""
        try:
            from curl_cffi.requests import AsyncSession

            headers = self._get_headers(url)
            async with AsyncSession(impersonate='chrome120', proxy=self.tor_proxy) as s:
                resp = await s.get(url, headers=headers, timeout=self.timeout)
                logger.info(f"curl_cffi+TOR status: {resp.status_code}")
                if resp.status_code == 200:
                    return resp.text
        except Exception as e:
            logger.warning(f"curl_cffi+TOR error: {e}")
        return None

    def _cloudscraper(self, url: str) -> str | None:
        """cloudscraper for JavaScript challenges."""
        try:
            import cloudscraper

            scraper = cloudscraper.create_scraper(
                browser={'browser': 'chrome', 'platform': 'linux', 'mobile': False}
            )

            headers = self._get_headers(url)
            resp = scraper.get(url, headers=headers, timeout=self.timeout + 15)
            logger.info(f"cloudscraper status: {resp.status_code}")
            if resp.status_code == 200:
                return resp.text
        except ImportError:
            logger.warning("cloudscraper not installed")
        except Exception as e:
            logger.warning(f"cloudscraper error: {e}")
        return None

    def _flaresolverr(self, url: str) -> str | None:
        """FlareSolverr headless browser service."""
        try:
            import requests

            payload = {
                'cmd': 'request.get',
                'url': url,
                'maxTimeout': 60000
            }

            if self.cookies:
                cookies = self.cookies.get_cookies_for_url(url)
                if cookies:
                    payload['cookies'] = [
                        {'name': k, 'value': v} for k, v in cookies.items()
                    ]

            resp = requests.post(
                f"{self.flaresolverr_url}/v1",
                json=payload,
                timeout=90
            )
            data = resp.json()
            logger.info(f"FlareSolverr status: {data.get('status')}")

            if data.get('status') == 'ok':
                return data['solution']['response']
        except Exception as e:
            logger.warning(f"FlareSolverr error: {e}")
        return None

    def _undetected_chrome(self, url: str) -> str | None:
        """undetected-chromedriver."""
        try:
            import undetected_chromedriver as uc

            options = uc.ChromeOptions()
            options.add_argument('--headless=new')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')

            driver = uc.Chrome(options=options)

            # Add cookies if available
            if self.cookies:
                driver.get(url.split('/')[0] + '//' + url.split('/')[2])
                for name, value in self.cookies.get_cookies_for_url(url).items():
                    driver.add_cookie({'name': name, 'value': value})

            driver.get(url)
            time.sleep(8)
            html = driver.page_source
            driver.quit()

            logger.info(f"undetected-chrome got {len(html)} bytes")
            return html if len(html) > 1000 else None
        except ImportError:
            logger.warning("undetected-chromedriver not installed")
        except Exception as e:
            logger.warning(f"undetected-chrome error: {e}")
        return None

    async def _nodriver(self, url: str) -> str | None:
        """nodriver - modern undetected browser."""
        try:
            import nodriver as nd

            browser = await nd.start(headless=True)

            # Add cookies if available
            if self.cookies:
                for name, value in self.cookies.get_cookies_for_url(url).items():
                    await browser.cookies.set(name, value)

            page = await browser.get(url)
            await asyncio.sleep(8)
            html = await page.get_content()
            await browser.stop()

            logger.info(f"nodriver got {len(html)} bytes")
            return html if len(html) > 1000 else None
        except ImportError:
            logger.warning("nodriver not installed")
        except Exception as e:
            logger.warning(f"nodriver error: {e}")
        return None

    async def _playwright_stealth(self, url: str) -> str | None:
        """Playwright with stealth mode."""
        try:
            from playwright.async_api import async_playwright
            from playwright_stealth import stealth_async

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )

                # Add cookies if available
                if self.cookies:
                    cookies_list = []
                    for name, value in self.cookies.get_cookies_for_url(url).items():
                        cookies_list.append({
                            'name': name,
                            'value': value,
                            'domain': url.split('/')[2],
                            'path': '/'
                        })
                    if cookies_list:
                        await context.add_cookies(cookies_list)

                page = await context.new_page()
                await stealth_async(page)
                await page.goto(url, wait_until='networkidle', timeout=60000)
                await asyncio.sleep(3)
                html = await page.content()
                await browser.close()

                logger.info(f"playwright-stealth got {len(html)} bytes")
                return html if len(html) > 1000 else None
        except ImportError:
            logger.warning("playwright or playwright-stealth not installed")
        except Exception as e:
            logger.warning(f"playwright-stealth error: {e}")
        return None

    def _botasaurus(self, url: str) -> str | None:
        """botasaurus anti-detect framework."""
        try:
            from botasaurus import browser, AntiDetectDriver

            cookies = self.cookies.get_cookies_for_url(url) if self.cookies else {}

            @browser(headless=True)
            def scrape(driver: AntiDetectDriver, data):
                # Add cookies
                if cookies:
                    driver.get(url.split('/')[0] + '//' + url.split('/')[2])
                    for name, value in cookies.items():
                        driver.add_cookie({'name': name, 'value': value})

                driver.get(url)
                driver.sleep(5)
                return driver.page_source

            html = scrape()
            logger.info(f"botasaurus got {len(html)} bytes")
            return html if len(html) > 1000 else None
        except ImportError:
            logger.warning("botasaurus not installed")
        except Exception as e:
            logger.warning(f"botasaurus error: {e}")
        return None

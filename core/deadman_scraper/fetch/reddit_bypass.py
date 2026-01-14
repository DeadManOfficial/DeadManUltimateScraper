"""
Reddit Rate Limit Bypass - Handle Reddit's aggressive rate limiting.

Reddit implements several layers of protection:
1. IP-based rate limits (429 Too Many Requests)
2. User-agent filtering (blocks non-browser agents)
3. OAuth token requirements for API endpoints
4. Cloudflare protection on some endpoints

Bypass Strategies:
1. Rotate User-Agents to mimic real browsers
2. Use old.reddit.com (less protected)
3. Add realistic delays between requests
4. Use TOR for IP rotation on 429s
5. Handle OAuth for API endpoints
"""

import asyncio
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any


@dataclass
class RedditConfig:
    """Reddit scraping configuration."""
    # Timing
    min_delay: float = 2.0  # Min seconds between requests
    max_delay: float = 5.0  # Max seconds between requests
    rate_limit_backoff: float = 60.0  # Wait on 429

    # Endpoints
    use_old_reddit: bool = True  # old.reddit.com has less protection
    prefer_json: bool = True  # Append .json for structured data

    # TOR settings
    use_tor: bool = False
    tor_rotate_on_429: bool = True

    # OAuth (for API)
    client_id: str | None = None
    client_secret: str | None = None
    username: str | None = None
    password: str | None = None


# Realistic browser User-Agents (2025-2026)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]


@dataclass
class RequestStats:
    """Track request statistics."""
    total_requests: int = 0
    successful: int = 0
    rate_limited: int = 0
    errors: int = 0
    last_request: float | None = None
    last_429: float | None = None


class RedditBypass:
    """
    Reddit scraping with rate limit bypass.

    Usage:
        bypass = RedditBypass()
        content = await bypass.fetch("https://reddit.com/r/python")
    """

    def __init__(self, config: RedditConfig = None, tor_manager=None):
        self.config = config or RedditConfig()
        self.tor = tor_manager
        self.stats = RequestStats()
        self._oauth_token: str | None = None
        self._token_expiry: datetime | None = None
        self._current_ua = secrets.choice(USER_AGENTS)

    def _get_headers(self) -> dict[str, str]:
        """Generate realistic browser headers."""
        return {
            "User-Agent": self._current_ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }

    def _transform_url(self, url: str) -> str:
        """Transform URL for better success rate."""
        # Use old.reddit.com
        if self.config.use_old_reddit:
            url = url.replace("www.reddit.com", "old.reddit.com")
            url = url.replace("reddit.com", "old.reddit.com")

        # Append .json for structured data (if not search)
        if self.config.prefer_json and "/search" not in url and not url.endswith(".json"):
            if "?" in url:
                url = url.replace("?", ".json?")
            else:
                url = url.rstrip("/") + ".json"

        return url

    async def _wait_for_rate_limit(self):
        """Wait appropriate time between requests."""
        if self.stats.last_request:
            elapsed = time.time() - self.stats.last_request
            min_wait = self.config.min_delay

            # Longer wait after 429
            if self.stats.last_429 and time.time() - self.stats.last_429 < 300:
                min_wait = max(min_wait, 10.0)

            if elapsed < min_wait:
                wait = secrets.SystemRandom().uniform(min_wait, self.config.max_delay)
                await asyncio.sleep(wait - elapsed)

    async def _handle_429(self):
        """Handle rate limit response."""
        self.stats.rate_limited += 1
        self.stats.last_429 = time.time()

        # Rotate User-Agent
        self._current_ua = secrets.choice(USER_AGENTS)

        # Rotate TOR circuit if available
        if self.config.tor_rotate_on_429 and self.tor:
            print("[Reddit] Rate limited - rotating TOR circuit...")
            await self.tor.rotate_circuit()

        # Wait before retry
        wait_time = self.config.rate_limit_backoff + secrets.SystemRandom().uniform(0, 30)
        print(f"[Reddit] Rate limited - waiting {wait_time:.0f}s...")
        await asyncio.sleep(wait_time)

    async def fetch(
        self,
        url: str,
        max_retries: int = 3,
        use_api: bool = False
    ) -> str | None:
        """
        Fetch Reddit URL with rate limit bypass.

        Args:
            url: Reddit URL to fetch
            max_retries: Max retry attempts
            use_api: Use OAuth API (requires credentials)

        Returns:
            Page content or None on failure
        """
        import httpx

        url = self._transform_url(url)

        for attempt in range(max_retries):
            await self._wait_for_rate_limit()

            try:
                self.stats.total_requests += 1
                self.stats.last_request = time.time()

                # Prepare request
                headers = self._get_headers()
                proxy = None
                timeout = 30.0

                # Use TOR if configured
                if self.config.use_tor and self.tor:
                    proxy = self.tor.proxy_url
                    timeout = 60.0

                # Make request
                async with httpx.AsyncClient(proxy=proxy, timeout=timeout) as client:
                    response = await client.get(url, headers=headers, follow_redirects=True)

                    # Handle rate limit
                    if response.status_code == 429:
                        await self._handle_429()
                        continue

                    # Handle other errors
                    if response.status_code >= 400:
                        self.stats.errors += 1
                        print(f"[Reddit] Error {response.status_code}: {url}")
                        continue

                    self.stats.successful += 1
                    return response.text

            except httpx.TimeoutException:
                print(f"[Reddit] Timeout on attempt {attempt + 1}: {url}")
                self.stats.errors += 1

            except Exception as e:
                print(f"[Reddit] Error on attempt {attempt + 1}: {e}")
                self.stats.errors += 1

        return None

    async def fetch_subreddit(
        self,
        subreddit: str,
        sort: str = "hot",
        limit: int = 25,
        after: str | None = None
    ) -> dict[str, Any] | None:
        """
        Fetch subreddit posts.

        Args:
            subreddit: Subreddit name (without r/)
            sort: hot, new, top, rising
            limit: Posts per page (max 100)
            after: Pagination token
        """
        url = f"https://reddit.com/r/{subreddit}/{sort}.json?limit={limit}"
        if after:
            url += f"&after={after}"

        content = await self.fetch(url)
        if content:
            import json
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return None
        return None

    async def fetch_post(self, url: str) -> dict[str, Any] | None:
        """Fetch a single post with comments."""
        content = await self.fetch(url)
        if content:
            import json
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return None
        return None

    async def search(
        self,
        query: str,
        subreddit: str | None = None,
        sort: str = "relevance",
        time_filter: str = "all",
        limit: int = 25
    ) -> dict[str, Any] | None:
        """
        Search Reddit.

        Args:
            query: Search query
            subreddit: Limit to subreddit (optional)
            sort: relevance, hot, top, new, comments
            time_filter: hour, day, week, month, year, all
            limit: Results per page
        """
        import urllib.parse

        encoded_query = urllib.parse.quote(query)

        if subreddit:
            url = f"https://reddit.com/r/{subreddit}/search.json?q={encoded_query}&restrict_sr=on"
        else:
            url = f"https://reddit.com/search.json?q={encoded_query}"

        url += f"&sort={sort}&t={time_filter}&limit={limit}"

        content = await self.fetch(url)
        if content:
            import json
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return None
        return None

    def get_stats(self) -> dict[str, Any]:
        """Get scraping statistics."""
        return {
            "total_requests": self.stats.total_requests,
            "successful": self.stats.successful,
            "rate_limited": self.stats.rate_limited,
            "errors": self.stats.errors,
            "success_rate": f"{(self.stats.successful / max(1, self.stats.total_requests)) * 100:.1f}%",
            "current_user_agent": self._current_ua[:50] + "...",
        }


# OAuth support for API endpoints
class RedditOAuth:
    """
    Reddit OAuth for API access.

    Requires app credentials from https://www.reddit.com/prefs/apps
    """

    def __init__(self, client_id: str, client_secret: str, user_agent: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent
        self._token: str | None = None
        self._expiry: datetime | None = None

    async def get_token(self, username: str = None, password: str = None) -> str | None:
        """Get OAuth token."""
        import base64

        import httpx

        if self._token and self._expiry and datetime.now() < self._expiry:
            return self._token

        auth = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()

        headers = {
            "Authorization": f"Basic {auth}",
            "User-Agent": self.user_agent,
            "Content-Type": "application/x-www-form-urlencoded",
        }

        # Script app (with user credentials)
        if username and password:
            data = {
                "grant_type": "password",
                "username": username,
                "password": password,
            }
        else:
            # App-only (client credentials)
            data = {
                "grant_type": "client_credentials",
            }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://www.reddit.com/api/v1/access_token",
                    headers=headers,
                    data=data
                )

                if response.status_code == 200:
                    result = response.json()
                    self._token = result.get("access_token")
                    expires_in = result.get("expires_in", 3600)
                    self._expiry = datetime.now() + timedelta(seconds=expires_in - 60)
                    return self._token

        except Exception as e:
            print(f"[Reddit OAuth] Error: {e}")

        return None

    async def api_request(
        self,
        endpoint: str,
        method: str = "GET",
        params: dict = None,
        data: dict = None
    ) -> dict | None:
        """Make authenticated API request."""
        import httpx

        token = await self.get_token()
        if not token:
            return None

        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": self.user_agent,
        }

        url = f"https://oauth.reddit.com{endpoint}"

        try:
            async with httpx.AsyncClient() as client:
                if method == "GET":
                    response = await client.get(url, headers=headers, params=params)
                else:
                    response = await client.post(url, headers=headers, data=data)

                if response.status_code == 200:
                    return response.json()

        except Exception as e:
            print(f"[Reddit API] Error: {e}")

        return None


# Demo
async def demo():
    """Demo Reddit bypass."""
    bypass = RedditBypass(RedditConfig(
        use_old_reddit=True,
        min_delay=3.0,
        max_delay=6.0,
    ))

    print("Fetching r/python...")
    data = await bypass.fetch_subreddit("python", limit=5)

    if data and "data" in data:
        posts = data["data"].get("children", [])
        print(f"Got {len(posts)} posts:")
        for post in posts[:3]:
            title = post["data"].get("title", "")[:60]
            print(f"  - {title}")

    print(f"\nStats: {bypass.get_stats()}")


if __name__ == "__main__":
    asyncio.run(demo())

"""
DeadMan Ultimate Scraper - Modal Cloud Deployment
================================================
Run scrapes directly from GitHub without any local setup.

Usage:
    # From CLI (anywhere)
    modal run DeadManOfficial/DeadManUltimateScraper::scrape --url "https://example.com"

    # Batch scrape
    modal run DeadManOfficial/DeadManUltimateScraper::scrape_batch --urls '["url1", "url2"]'

    # Intelligence gathering
    modal run DeadManOfficial/DeadManUltimateScraper::search --query "your search query"
"""

import modal
from typing import Optional

# === MODAL IMAGE SETUP ===
# This defines the cloud environment - Python + all dependencies + browser
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install_from_requirements("requirements.txt")
    .run_commands(
        "playwright install chromium",
        "playwright install-deps chromium"
    )
)

# === MODAL APP ===
app = modal.App(
    name="deadman-scraper",
    image=image,
    secrets=[
        modal.Secret.from_name("scraper-secrets", required=False)  # Optional API keys
    ]
)

# === STORAGE ===
# Persistent volume for caching scraped data
volume = modal.Volume.from_name("scraper-cache", create_if_missing=True)


@app.function(
    timeout=300,  # 5 minute timeout per scrape
    volumes={"/cache": volume},
    cpu=1.0,
    memory=2048
)
def scrape(
    url: str,
    use_llm: bool = False,
    use_tor: bool = False,
    extract_strategy: Optional[str] = "auto",
    headers: Optional[dict] = None
) -> dict:
    """
    Scrape a single URL and return results.

    Args:
        url: Target URL to scrape
        use_llm: Enable AI-powered content extraction
        use_tor: Route through TOR network (slower but anonymous)
        extract_strategy: 'auto', 'html', 'json', 'text', or custom
        headers: Custom headers to send with request

    Returns:
        dict with keys: success, content, status_code, fetch_layer, error
    """
    import asyncio
    from central_scraper import CentralScraper, ScrapeRequest

    async def run_scrape():
        async with CentralScraper() as scraper:
            request = ScrapeRequest(
                url=url,
                use_llm=use_llm,
                use_tor=use_tor,
                extract_strategy=extract_strategy,
                headers=headers or {}
            )
            result = await scraper.scrape(request)
            return {
                "success": result.success,
                "content": result.content[:50000] if result.content else None,  # Limit size
                "status_code": result.status_code,
                "fetch_layer": result.fetch_layer,
                "error": result.error
            }

    return asyncio.run(run_scrape())


@app.function(
    timeout=600,  # 10 minute timeout for batch
    volumes={"/cache": volume},
    cpu=2.0,
    memory=4096
)
def scrape_batch(urls: list[str]) -> list[dict]:
    """
    Scrape multiple URLs concurrently.

    Args:
        urls: List of URLs to scrape

    Returns:
        List of result dicts
    """
    import asyncio
    from central_scraper import CentralScraper, ScrapeRequest

    async def run_batch():
        async with CentralScraper() as scraper:
            requests = [ScrapeRequest(url=url) for url in urls]
            results = []
            async for result in scraper.scrape_batch(requests):
                results.append({
                    "url": result.url,
                    "success": result.success,
                    "content": result.content[:10000] if result.content else None,
                    "status_code": result.status_code,
                    "error": result.error
                })
            return results

    return asyncio.run(run_batch())


@app.function(
    timeout=900,  # 15 minute timeout for search
    volumes={"/cache": volume},
    cpu=2.0,
    memory=4096
)
def search(query: str, darkweb: bool = False, max_results: int = 10) -> list[dict]:
    """
    Multi-engine search and intelligence gathering.

    Args:
        query: Search query
        darkweb: Include dark web sources
        max_results: Maximum results to return

    Returns:
        List of scraped search results
    """
    import asyncio
    from central_scraper import CentralScraper

    async def run_search():
        async with CentralScraper() as scraper:
            results = []
            async for result in scraper.search_intelligence(query, darkweb=darkweb):
                results.append({
                    "url": result.url,
                    "success": result.success,
                    "content": result.content[:5000] if result.content else None,
                    "status_code": result.status_code
                })
                if len(results) >= max_results:
                    break
            return results

    return asyncio.run(run_search())


@app.function(timeout=60)
def health() -> dict:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "name": "DeadMan Ultimate Scraper"
    }


# === LOCAL ENTRYPOINT ===
@app.local_entrypoint()
def main(
    url: str = "https://example.com",
    batch: bool = False,
    search_query: str = None
):
    """
    Local CLI entrypoint for testing.

    Examples:
        modal run modal_app.py --url "https://reddit.com"
        modal run modal_app.py --search-query "web scraping tools"
    """
    if search_query:
        print(f"Searching: {search_query}")
        results = search.remote(search_query)
        for r in results:
            print(f"  [{r['success']}] {r['url']}")
    elif batch:
        print("Batch mode requires --urls flag")
    else:
        print(f"Scraping: {url}")
        result = scrape.remote(url)
        print(f"Success: {result['success']}")
        print(f"Layer: {result['fetch_layer']}")
        if result['content']:
            print(f"Content preview: {result['content'][:200]}...")

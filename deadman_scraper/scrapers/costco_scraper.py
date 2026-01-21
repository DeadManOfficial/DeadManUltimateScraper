"""
Costco Scraper - Using DeadMan Stealth Stack
=============================================
TOR + curl_cffi for Akamai bypass - 100% FREE
"""

import asyncio
import json
import logging
from pathlib import Path

# Use relative imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from deadman_scraper.stealth.fingerprint import FingerprintSpoofer
from deadman_scraper.fetch.tor_manager import TORManager
from deadman_scraper.core.config import Config

logger = logging.getLogger(__name__)

OUTPUT_FILE = Path(__file__).parent.parent.parent.parent / "web" / "src" / "data" / "deals.json"

# Category mapping
CATEGORY_MAP = {
    'appliances': 'Home', 'refrigerator': 'Kitchen', 'tv': 'Electronics',
    'computer': 'Electronics', 'laptop': 'Electronics', 'tablet': 'Electronics',
    'phone': 'Electronics', 'audio': 'Electronics', 'furniture': 'Home',
    'mattress': 'Home', 'outdoor': 'Outdoor', 'patio': 'Outdoor', 'grill': 'Outdoor',
    'tire': 'Auto', 'toy': 'Toys', 'clothing': 'Clothing', 'jewelry': 'Jewelry',
    'vitamin': 'Health', 'cleaning': 'Cleaning', 'office': 'Office', 'pet': 'Pet',
    'kitchen': 'Kitchen', 'cookware': 'Kitchen',
}


def get_category(name: str) -> str:
    lower = name.lower()
    for kw, cat in CATEGORY_MAP.items():
        if kw in lower:
            return cat
    return 'Other'


def get_price_code(price: float) -> str:
    s = f"{price:.2f}"
    if s.endswith('.97'): return '.97'
    if s.endswith('.00') or s.endswith('.90'): return '.00'
    if s.endswith('.88') or s.endswith('.77'): return '.88'
    return 'regular'


async def scrape_costco_with_tor(keyword: str = "deals", limit: int = 50) -> list[dict]:
    """
    Scrape Costco using TOR + curl_cffi for Akamai bypass.
    """
    products = []
    url = f"https://www.costco.com/CatalogSearch?dept=All&keyword={keyword}"

    print(f"\n🛒 Costco Scraper (DeadMan Stack)")
    print(f"   Keyword: {keyword}")
    print(f"   URL: {url}")

    # Get fingerprint for curl_cffi
    impersonate = FingerprintSpoofer.get_curl_cffi_impersonate("chrome")
    fingerprint = FingerprintSpoofer.generate_fingerprint("chrome")

    print(f"   Impersonate: {impersonate}")
    print(f"   User-Agent: {fingerprint.user_agent[:50]}...")

    try:
        # Try curl_cffi with TLS spoofing first
        from curl_cffi.requests import AsyncSession

        # Initialize TOR if available
        config = Config.from_env()
        tor = TORManager(config.tor)

        tor_available = await tor.start()
        proxy = tor.get_proxy_url() if tor_available else None

        if tor_available:
            exit_ip = await tor.get_exit_ip()
            print(f"   TOR Exit IP: {exit_ip}")
        else:
            print("   TOR: Not available, using direct connection")

        async with AsyncSession(impersonate=impersonate, proxy=proxy) as session:
            headers = {
                "User-Agent": fingerprint.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
            }

            print(f"   Fetching...")
            response = await session.get(url, headers=headers, timeout=30)

            print(f"   Status: {response.status_code}")

            if response.status_code == 200:
                html = response.text
                products = parse_costco_html(html, limit)
                print(f"   Found: {len(products)} products")

                # Renew circuit for next request
                if tor_available:
                    await tor.renew_circuit()
            else:
                print(f"   Error: HTTP {response.status_code}")
                if "Access Denied" in response.text:
                    print("   Blocked by Akamai")

        if tor_available:
            await tor.stop()

    except ImportError:
        print("   curl_cffi not installed, trying httpx...")
        products = await scrape_costco_httpx(url, limit)
    except Exception as e:
        print(f"   Error: {e}")
        logger.exception("Scrape failed")

    return products


async def scrape_costco_httpx(url: str, limit: int) -> list[dict]:
    """Fallback scraper using httpx."""
    import httpx

    fingerprint = FingerprintSpoofer.generate_fingerprint("chrome")

    async with httpx.AsyncClient(timeout=30) as client:
        headers = {
            "User-Agent": fingerprint.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        response = await client.get(url, headers=headers)

        if response.status_code == 200:
            return parse_costco_html(response.text, limit)

    return []


def parse_costco_html(html: str, limit: int) -> list[dict]:
    """Parse Costco search results HTML."""
    from bs4 import BeautifulSoup

    products = []
    soup = BeautifulSoup(html, 'html.parser')

    # Try multiple selectors
    selectors = [
        '.product-tile-set .product',
        '.product-list .product',
        '.product-tile',
        '[data-testid="product"]',
        '.product',
    ]

    for sel in selectors:
        items = soup.select(sel)
        if items:
            for i, item in enumerate(items):
                if len(products) >= limit:
                    break

                name_el = item.select_one('.description, .product-title, h3, h2, a')
                price_el = item.select_one('.price, .product-price')
                link_el = item.select_one('a')
                img_el = item.select_one('img')

                name = name_el.get_text(strip=True) if name_el else None
                price_text = price_el.get_text(strip=True) if price_el else "0"

                # Parse price
                import re
                price_match = re.search(r'\$?([\d,]+\.?\d*)', price_text)
                price = float(price_match.group(1).replace(',', '')) if price_match else 0

                if name and price > 0:
                    link = link_el.get('href', '') if link_el else ''
                    img = img_el.get('src') or img_el.get('data-src', '') if img_el else ''

                    # Extract item ID
                    id_match = re.search(r'\.(\d+)\.html|product\.(\d+)', link)
                    item_id = id_match.group(1) or id_match.group(2) if id_match else str(i)

                    products.append({
                        'id': item_id,
                        'name': name,
                        'brand': name.split()[0] if name else '',
                        'originalPrice': round(price * 1.15, 2),
                        'salePrice': price,
                        'priceCode': get_price_code(price),
                        'category': get_category(name),
                        'storesCount': 1,
                        'states': [],
                        'markdownType': ['online_deal'],
                        'url': f"https://www.costco.com{link}" if link.startswith('/') else link,
                        'image': f"https:{img}" if img.startswith('//') else img,
                        'rating': None,
                    })
            break

    # Try JSON-LD fallback
    if not products:
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string)
                if data.get('@type') == 'ItemList':
                    for item in data.get('itemListElement', []):
                        if len(products) >= limit:
                            break
                        p = item.get('item', item)
                        if p.get('name'):
                            products.append({
                                'id': p.get('sku', str(len(products))),
                                'name': p['name'],
                                'brand': p.get('brand', {}).get('name', ''),
                                'originalPrice': p.get('offers', {}).get('highPrice', 0),
                                'salePrice': p.get('offers', {}).get('lowPrice', 0),
                                'priceCode': 'regular',
                                'category': get_category(p['name']),
                                'storesCount': 1,
                                'states': [],
                                'markdownType': ['online_deal'],
                                'url': p.get('url', ''),
                                'image': p.get('image', ''),
                                'rating': p.get('aggregateRating', {}).get('ratingValue'),
                            })
            except (json.JSONDecodeError, TypeError):
                continue

    return products


async def scrape_all_keywords(keywords: list[str] = None, limit: int = 100) -> list[dict]:
    """Scrape multiple keywords and dedupe."""
    if keywords is None:
        keywords = ['clearance', 'deals', 'sale', 'savings']

    all_products = {}
    per_keyword = limit // len(keywords) + 1

    for kw in keywords:
        products = await scrape_costco_with_tor(kw, per_keyword)
        for p in products:
            if p['id'] not in all_products:
                all_products[p['id']] = p

        # Wait between requests
        await asyncio.sleep(5)

    # Sort by discount
    result = list(all_products.values())
    result.sort(key=lambda p: (p['originalPrice'] - p['salePrice']) / max(p['originalPrice'], 1), reverse=True)

    return result[:limit]


def save_deals(deals: list[dict]) -> dict:
    """Save deals to JSON file."""
    from datetime import datetime

    output = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'source': 'DeadMan Scraper (TOR + curl_cffi)',
        'count': len(deals),
        'deals': deals,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(output, indent=2))

    print(f"\n✅ Saved {len(deals)} deals to {OUTPUT_FILE}")
    return output


# CLI
if __name__ == "__main__":
    import sys

    print("═" * 60)
    print("  DEADMAN SCRAPER - Costco (TOR + curl_cffi)")
    print("═" * 60)

    keyword = sys.argv[1] if len(sys.argv) > 1 else None

    if keyword == "--full":
        deals = asyncio.run(scrape_all_keywords())
    elif keyword:
        deals = asyncio.run(scrape_costco_with_tor(keyword))
    else:
        deals = asyncio.run(scrape_costco_with_tor("deals"))

    if deals:
        save_deals(deals)
    else:
        print("\n❌ No products found")

#!/usr/bin/env python3
"""DeadMan Scraper - Integrated bypass chain for protected sites."""

import asyncio
import json
import os
import sys
import time
import logging
from urllib.parse import urlparse, quote

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('DeadManScraper')

# === CONFIG from environment ===
TARGET = os.environ.get('INPUT_TARGET', 'reddit')
QUERY = os.environ.get('INPUT_QUERY', 'free api')
LIMIT = int(os.environ.get('INPUT_LIMIT', '25'))
EXTRACT = os.environ.get('INPUT_EXTRACT', 'all')
RENDER = os.environ.get('INPUT_RENDER', 'false') == 'true'
USE_COOKIES = os.environ.get('INPUT_USE_COOKIES', 'false') == 'true'

FLARESOLVERR_URL = 'http://localhost:8191'
TOR_PROXY = 'socks5h://127.0.0.1:9050'

# Pre-configured cookies for authenticated sites
SITE_COOKIES = {
    'outlawprompts.com': {
        '__Secure-better-auth.session_token': 'bYUWwogks8Sb6HREiI7kGn4bR5tZ1Vgl.mqUhX7RYH3AopDA0sVfAcU8KvvbkzrS0WGdCuSgIOUg=',
        'cf_clearance': 'DwjyKM88TJhhp.vfu5isKs9rZYTAfrBDI6pcTosPPOs-1769043068-1.2.1.1-ZDMbUY.f3ty7WZIJuO71bbW984q5R0X2p_Pehi7rzhH3CBWunETVO3bxhAIBPhyaGg1vEAMh0gdxdqJaWXo7e6eTzDVdbir.lmX_cb10foq4q7XVJfHZn0aOVDd3__q4YNjDcl.fgVnwf38I8IVV9ty2jmPdi7sio0a4q0b8X.5OG1plpCEjlAhobt8W4DTP.7aycXl6SLEHgUhyqQOuS3KDbwcF9s4lyANPENEVcDE',
    },
    'app.outlawprompts.com': {
        '__Secure-better-auth.session_token': 'bYUWwogks8Sb6HREiI7kGn4bR5tZ1Vgl.mqUhX7RYH3AopDA0sVfAcU8KvvbkzrS0WGdCuSgIOUg=',
    }
}

results = {
    'target': TARGET,
    'query': QUERY,
    'extract': EXTRACT,
    'render': RENDER,
    'use_cookies': USE_COOKIES,
    'methods_tried': [],
    'success': False,
    'method_used': None,
    'count': 0,
    'results': []
}


def get_cookies_for_url(url):
    if not USE_COOKIES:
        return {}
    domain = urlparse(url).netloc
    cookies = {}
    for site_domain, site_cookies in SITE_COOKIES.items():
        if site_domain in domain or domain in site_domain:
            cookies.update(site_cookies)
    return cookies


def get_cookie_header(url):
    cookies = get_cookies_for_url(url)
    return '; '.join(f'{k}={v}' for k, v in cookies.items())


# === EXTRACTION ===
def extract_content(html, mode):
    from bs4 import BeautifulSoup
    import re
    soup = BeautifulSoup(html, 'lxml')

    if mode == 'text':
        return soup.get_text(separator='\n', strip=True)
    elif mode == 'links':
        return [{'text': a.get_text(strip=True)[:100], 'href': a.get('href')} for a in soup.find_all('a', href=True)][:500]
    elif mode == 'json':
        json_data = []
        for script in soup.find_all('script'):
            if script.string:
                for pattern in [r'window\.__[A-Z_]+__\s*=\s*({.*?});', r'type="application/json">([^<]+)<']:
                    for m in re.findall(pattern, str(script), re.DOTALL):
                        try:
                            json_data.append(json.loads(m))
                        except:
                            pass
        return json_data
    elif mode == 'prompts':
        # Specialized prompt extraction
        prompts = []
        for el in soup.select('.prompt-card, .prompt-item, .prompt, [data-prompt], article, .card'):
            title = el.select_one('h1, h2, h3, h4, .title, .name')
            content = el.select_one('.content, .body, .text, .description, p')
            if title or content:
                prompts.append({
                    'title': title.get_text(strip=True) if title else None,
                    'content': content.get_text(strip=True)[:500] if content else el.get_text(strip=True)[:500]
                })
        return prompts
    elif mode.startswith('.') or mode.startswith('#') or mode.startswith('['):
        return [{'html': str(e)[:500], 'text': e.get_text(strip=True)[:200]} for e in soup.select(mode)][:100]
    else:
        return {
            'title': soup.title.string if soup.title else None,
            'text': soup.get_text(separator='\n', strip=True)[:15000],
            'links': [{'text': a.get_text(strip=True)[:50], 'href': a.get('href')} for a in soup.find_all('a', href=True)][:100],
            'html_length': len(html)
        }


# === BYPASS METHODS ===
async def try_curl_cffi(url, use_tor=False):
    logger.info(f'curl_cffi (TOR={use_tor})...')
    try:
        from curl_cffi.requests import AsyncSession
        proxy = TOR_PROXY if use_tor else None
        headers = {'Cookie': get_cookie_header(url)} if USE_COOKIES else {}
        async with AsyncSession(impersonate='chrome120', proxy=proxy) as s:
            resp = await s.get(url, headers=headers, timeout=30)
            logger.info(f'  Status: {resp.status_code}')
            if resp.status_code == 200 and len(resp.text) > 1000:
                return resp.text
    except Exception as e:
        logger.warning(f'  Failed: {e}')
    return None


def try_cloudscraper(url):
    logger.info('cloudscraper...')
    try:
        import cloudscraper
        scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'linux'})
        headers = {'Cookie': get_cookie_header(url)} if USE_COOKIES else {}
        resp = scraper.get(url, headers=headers, timeout=45)
        logger.info(f'  Status: {resp.status_code}')
        if resp.status_code == 200 and len(resp.text) > 1000:
            return resp.text
    except Exception as e:
        logger.warning(f'  Failed: {e}')
    return None


def try_flaresolverr(url):
    logger.info('FlareSolverr...')
    try:
        import requests
        payload = {'cmd': 'request.get', 'url': url, 'maxTimeout': 60000}
        if USE_COOKIES:
            cookies = get_cookies_for_url(url)
            if cookies:
                payload['cookies'] = [{'name': k, 'value': v} for k, v in cookies.items()]
        resp = requests.post(f'{FLARESOLVERR_URL}/v1', json=payload, timeout=90)
        data = resp.json()
        status = data.get('status')
        logger.info(f'  Status: {status}')
        if status == 'ok':
            html = data['solution']['response']
            if len(html) > 1000:
                return html
    except Exception as e:
        logger.warning(f'  Failed: {e}')
    return None


def try_undetected_chrome(url):
    logger.info('undetected-chromedriver...')
    try:
        import undetected_chromedriver as uc
        options = uc.ChromeOptions()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        driver = uc.Chrome(options=options)
        if USE_COOKIES:
            base_url = url.rsplit('/', 1)[0] if '/' in url[8:] else url
            driver.get(base_url)
            for name, value in get_cookies_for_url(url).items():
                driver.add_cookie({'name': name, 'value': value, 'domain': urlparse(url).netloc})
        driver.get(url)
        time.sleep(8)
        html = driver.page_source
        driver.quit()
        logger.info(f'  Got {len(html)} bytes')
        if len(html) > 1000:
            return html
    except Exception as e:
        logger.warning(f'  Failed: {e}')
    return None


async def try_playwright_stealth(url):
    logger.info('playwright-stealth...')
    try:
        from playwright.async_api import async_playwright
        from playwright_stealth import stealth_async
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
            if USE_COOKIES:
                cookies = [{'name': k, 'value': v, 'domain': urlparse(url).netloc, 'path': '/'} for k, v in get_cookies_for_url(url).items()]
                if cookies:
                    await context.add_cookies(cookies)
            page = await context.new_page()
            await stealth_async(page)
            await page.goto(url, wait_until='networkidle', timeout=60000)
            await asyncio.sleep(5)
            html = await page.content()
            await browser.close()
            logger.info(f'  Got {len(html)} bytes')
            if len(html) > 1000:
                return html
    except Exception as e:
        logger.warning(f'  Failed: {e}')
    return None


# === API SCRAPERS ===
async def scrape_api(target, query, limit):
    try:
        from curl_cffi.requests import AsyncSession
        async with AsyncSession(impersonate='chrome120', proxy=TOR_PROXY) as session:
            urls = {
                'reddit': f'https://www.reddit.com/search.json?q={quote(query)}&limit={limit}',
                'hackernews': f'https://hn.algolia.com/api/v1/search?query={quote(query)}&hitsPerPage={limit}',
                'stackoverflow': f'https://api.stackexchange.com/2.3/search?order=desc&sort=relevance&intitle={quote(query)}&site=stackoverflow&pagesize={limit}',
                'github': f'https://api.github.com/search/repositories?q={quote(query)}&per_page={limit}',
            }
            if target not in urls:
                return None
            resp = await session.get(urls[target], timeout=30)
            logger.info(f'{target}: {resp.status_code}')
            if resp.status_code != 200:
                return None
            data = resp.json()
            if target == 'reddit':
                return [{'title': p['data']['title'], 'url': p['data']['url']} for p in data['data']['children']]
            elif target == 'hackernews':
                return [{'title': h['title'], 'url': h.get('url', f"https://news.ycombinator.com/item?id={h['objectID']}")} for h in data['hits']]
            elif target == 'stackoverflow':
                return [{'title': q['title'], 'url': q['link']} for q in data['items']]
            elif target == 'github':
                return [{'title': r['full_name'], 'url': r['html_url'], 'stars': r['stargazers_count']} for r in data['items']]
    except Exception as e:
        logger.error(f'API error: {e}')
    return None


# === MAIN ===
async def main():
    logger.info('=' * 60)
    logger.info(f'Target: {TARGET}')
    logger.info(f'Render: {RENDER}, Cookies: {USE_COOKIES}')
    logger.info('=' * 60)

    is_url = TARGET.startswith('http')

    if not is_url:
        api_results = await scrape_api(TARGET, QUERY, LIMIT)
        if api_results:
            results['success'] = True
            results['method_used'] = f'{TARGET}_api'
            results['results'] = api_results
            results['count'] = len(api_results)
    else:
        methods = [
            ('curl_cffi', lambda: try_curl_cffi(TARGET)),
            ('curl_cffi_tor', lambda: try_curl_cffi(TARGET, use_tor=True)),
            ('cloudscraper', lambda: asyncio.get_event_loop().run_in_executor(None, try_cloudscraper, TARGET)),
            ('flaresolverr', lambda: asyncio.get_event_loop().run_in_executor(None, try_flaresolverr, TARGET)),
            ('undetected_chrome', lambda: asyncio.get_event_loop().run_in_executor(None, try_undetected_chrome, TARGET)),
            ('playwright_stealth', lambda: try_playwright_stealth(TARGET)),
        ]

        if RENDER:
            methods = [(n, m) for n, m in methods if n in ('flaresolverr', 'undetected_chrome', 'playwright_stealth')]
            logger.info('RENDER mode: browser methods only')

        for name, method in methods:
            results['methods_tried'].append(name)
            try:
                if asyncio.iscoroutinefunction(method):
                    html = await method()
                else:
                    html = await method()
                if html and len(html) > 1000:
                    results['success'] = True
                    results['method_used'] = name
                    extracted = extract_content(html, EXTRACT)
                    results['results'] = extracted if isinstance(extracted, list) else [extracted]
                    results['count'] = len(results['results']) if isinstance(results['results'], list) else 1
                    logger.info(f'SUCCESS with {name}!')
                    break
            except Exception as e:
                logger.error(f'{name} error: {e}')

    logger.info('=' * 60)
    logger.info(f'Success: {results["success"]}')
    logger.info(f'Method: {results["method_used"]}')
    logger.info(f'Count: {results["count"]}')

    with open('scrape_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)


if __name__ == '__main__':
    asyncio.run(main())

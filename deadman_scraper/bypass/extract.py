"""
Content Extractor
=================
Extract structured data from HTML.
"""

import json
import re
import logging
from typing import Any

logger = logging.getLogger("ContentExtractor")


class ContentExtractor:
    """Extract structured content from HTML."""

    def __init__(self, html: str):
        self.html = html
        self._soup = None

    @property
    def soup(self):
        if self._soup is None:
            from bs4 import BeautifulSoup
            self._soup = BeautifulSoup(self.html, 'lxml')
        return self._soup

    def extract(self, mode: str = 'all') -> Any:
        """Extract content based on mode."""
        if mode == 'text':
            return self.extract_text()
        elif mode == 'links':
            return self.extract_links()
        elif mode == 'json':
            return self.extract_json()
        elif mode == 'prompts':
            return self.extract_prompts()
        elif mode.startswith('.') or mode.startswith('#') or mode.startswith('['):
            return self.extract_selector(mode)
        else:
            return self.extract_all()

    def extract_text(self) -> str:
        """Extract all text content."""
        return self.soup.get_text(separator='\n', strip=True)

    def extract_links(self, limit: int = 500) -> list[dict]:
        """Extract all links."""
        links = []
        for a in self.soup.find_all('a', href=True)[:limit]:
            links.append({
                'text': a.get_text(strip=True)[:100],
                'href': a.get('href')
            })
        return links

    def extract_json(self) -> list[dict]:
        """Extract embedded JSON data from scripts."""
        json_data = []

        # Look for common patterns
        patterns = [
            r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
            r'window\.__DATA__\s*=\s*({.*?});',
            r'window\.__PRELOADED_STATE__\s*=\s*({.*?});',
            r'<script[^>]*id="__NEXT_DATA__"[^>]*>([^<]+)</script>',
            r'<script[^>]*type="application/json"[^>]*>([^<]+)</script>',
            r'<script[^>]*type="application/ld\+json"[^>]*>([^<]+)</script>',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, self.html, re.DOTALL)
            for match in matches:
                try:
                    data = json.loads(match)
                    json_data.append(data)
                except json.JSONDecodeError:
                    pass

        # Also try script tags
        for script in self.soup.find_all('script'):
            if script.string:
                try:
                    # Try to find JSON objects in script content
                    content = script.string.strip()
                    if content.startswith('{') or content.startswith('['):
                        data = json.loads(content)
                        json_data.append(data)
                except:
                    pass

        return json_data

    def extract_prompts(self) -> list[dict]:
        """Extract prompts - specialized for prompt library sites."""
        prompts = []

        # Try JSON first (SPAs often embed data)
        json_data = self.extract_json()
        for data in json_data:
            prompts.extend(self._find_prompts_in_json(data))

        # Try common selectors for prompts
        selectors = [
            '.prompt-card', '.prompt-item', '.prompt',
            '[data-prompt]', '[data-testid*="prompt"]',
            '.card', '.item', 'article'
        ]

        for selector in selectors:
            elements = self.soup.select(selector)
            for el in elements:
                title = el.select_one('h1, h2, h3, h4, .title, .name')
                content = el.select_one('.content, .body, .text, .description, p')

                if title or content:
                    prompts.append({
                        'title': title.get_text(strip=True) if title else None,
                        'content': content.get_text(strip=True) if content else el.get_text(strip=True)[:500],
                        'html': str(el)[:1000]
                    })

        return prompts

    def _find_prompts_in_json(self, data: Any, depth: int = 0) -> list[dict]:
        """Recursively find prompts in JSON data."""
        if depth > 10:
            return []

        prompts = []

        if isinstance(data, dict):
            # Check if this looks like a prompt
            if any(k in data for k in ['prompt', 'content', 'text', 'body', 'description']):
                if any(k in data for k in ['title', 'name', 'id']):
                    prompts.append({
                        'title': data.get('title') or data.get('name'),
                        'content': data.get('prompt') or data.get('content') or data.get('text') or data.get('body'),
                        'id': data.get('id'),
                        'category': data.get('category'),
                        'tags': data.get('tags'),
                    })

            # Recurse into nested structures
            for key, value in data.items():
                if key.lower() in ['prompts', 'items', 'data', 'results', 'posts', 'list']:
                    prompts.extend(self._find_prompts_in_json(value, depth + 1))
                elif isinstance(value, (dict, list)):
                    prompts.extend(self._find_prompts_in_json(value, depth + 1))

        elif isinstance(data, list):
            for item in data:
                prompts.extend(self._find_prompts_in_json(item, depth + 1))

        return prompts

    def extract_selector(self, selector: str, limit: int = 100) -> list[dict]:
        """Extract elements matching a CSS selector."""
        results = []
        for el in self.soup.select(selector)[:limit]:
            results.append({
                'html': str(el)[:500],
                'text': el.get_text(strip=True)[:200]
            })
        return results

    def extract_all(self) -> dict:
        """Extract comprehensive data."""
        return {
            'title': self.soup.title.string if self.soup.title else None,
            'text': self.extract_text()[:10000],
            'links': self.extract_links(100),
            'images': [img.get('src') for img in self.soup.find_all('img', src=True)][:50],
            'meta': {
                meta.get('name', meta.get('property', 'unknown')): meta.get('content')
                for meta in self.soup.find_all('meta', content=True)
            },
            'json_data': self.extract_json(),
            'html_length': len(self.html)
        }

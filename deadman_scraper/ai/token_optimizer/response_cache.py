# [TRACEABILITY] REQ-301
import hashlib
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict

class ResponseCache:
    """
    Caches API responses to eliminate duplicate requests
    Target: 40-60% token savings on repeated queries
    """

    def __init__(self, cache_dir='data/cache', ttl_hours=24):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = timedelta(hours=ttl_hours)

        self.stats = {
            'hits': 0,
            'misses': 0,
            'savings_tokens': 0
        }

    def _get_cache_key(self, prompt: str, model: str = '') -> str:
        """Generate cache key from prompt"""
        content = f"{model}:{prompt}"
        return hashlib.md5(content.encode()).hexdigest()

    def get(self, prompt: str, model: str = '') -> Optional[Dict]:
        """Get cached response if available and fresh"""
        cache_key = self._get_cache_key(prompt, model)
        cache_file = self.cache_dir / f"{cache_key}.json"

        if not cache_file.exists():
            self.stats['misses'] += 1
            return None

        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached = json.load(f)

            cached_time = datetime.fromisoformat(cached['timestamp'])
            if datetime.now() - cached_time > self.ttl:
                self.stats['misses'] += 1
                return None

            self.stats['hits'] += 1
            self.stats['savings_tokens'] += cached.get('token_count', 0)

            return cached['response']

        except Exception:
            self.stats['misses'] += 1
            return None

    def set(self, prompt: str, response: any, model: str = '', token_count: int = 0):
        """Cache response"""
        cache_key = self._get_cache_key(prompt, model)
        cache_file = self.cache_dir / f"{cache_key}.json"

        cached = {
            'prompt': prompt,
            'response': response,
            'model': model,
            'token_count': token_count,
            'timestamp': datetime.now().isoformat()
        }

        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cached, f, indent=2)

    def get_stats(self) -> Dict:
        """Get cache statistics"""
        total = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total * 100) if total > 0 else 0

        return {
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'hit_rate': f"{hit_rate:.1f}%",
            'tokens_saved': self.stats['savings_tokens']
        }

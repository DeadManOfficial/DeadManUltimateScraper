# [TRACEABILITY] REQ-301
from typing import Dict, Optional, Any
from .prompt_optimizers import PromptOptimizer
from .response_cache import ResponseCache
from .output_controller import OutputController
from .context_manager import ContextManager
from .request_consolidator import RequestConsolidator

class TokenOptimizer:
    """
    Main token optimization orchestrator
    Combines all optimization techniques
    """

    def __init__(self, enable_caching: bool = True, cache_dir: str = 'data/cache'):
        self.prompt_optimizer = PromptOptimizer()
        self.cache = ResponseCache(cache_dir=cache_dir) if enable_caching else None
        self.output_controller = OutputController()
        self.context_manager = ContextManager()
        self.consolidator = RequestConsolidator()

        self.stats = {
            'prompts_optimized': 0,
            'tokens_saved': 0,
            'cache_hits': 0
        }

    def optimize_prompt(self, prompt: str,
                       compress: bool = True,
                       max_words: int = None,
                       use_bullets: bool = False) -> str:
        """
        Apply all prompt optimizations
        """
        optimized = prompt

        if compress:
            optimized = self.prompt_optimizer.compress_prompt(optimized)

        if max_words:
            optimized = self.output_controller.add_length_constraint(optimized, max_words=max_words)

        optimized = self.output_controller.request_concise_format(optimized)

        if use_bullets:
            optimized = self.output_controller.prefer_bullet_points(optimized)

        self.stats['prompts_optimized'] += 1

        return optimized

    def optimize_system_prompt(self, system_prompt: str) -> str:
        """Optimize system prompt"""
        return self.prompt_optimizer.optimize_system_prompt(system_prompt)

    def check_cache(self, prompt: str, model: str = '') -> Optional[Any]:
        """Check if response is cached"""
        if self.cache:
            result = self.cache.get(prompt, model)
            if result:
                self.stats['cache_hits'] += 1
            return result
        return None

    def cache_response(self, prompt: str, response: Any, model: str = '', tokens: int = 0):
        """Cache API response"""
        if self.cache:
            self.cache.set(prompt, response, model, tokens)

    def get_stats(self) -> Dict:
        """Get optimization statistics"""
        stats = {
            'prompts_optimized': self.stats['prompts_optimized'],
            'cache_hits': self.stats['cache_hits'],
        }

        if self.cache:
            cache_stats = self.cache.get_stats()
            stats.update(cache_stats)

        return stats

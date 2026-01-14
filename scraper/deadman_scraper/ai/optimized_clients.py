"""
Optimized LLM Clients for Mistral and Groq
==========================================
Drop-in replacements with automatic token optimization and caching.
Ensures "Free Forever" compliance by minimizing payload size.
"""

import asyncio
import logging

from token_optimizer.core import TokenOptimizer

from .llm_router import LLMResponse

logger = logging.getLogger("OptimizedLLM")

class OptimizedMistral:
    """
    Auto-optimizing wrapper for Mistral AI.
    Reduces token usage by ~40%.
    """
    def __init__(self, api_key: str, model: str = "mistral-small", cache_dir: str = "data/cache"):
        from mistralai import Mistral
        self.client = Mistral(api_key=api_key)
        self.model = model
        self.optimizer = TokenOptimizer(cache_dir=cache_dir)

    async def complete(self, prompt: str, **kwargs) -> LLMResponse:
        # 1. Optimize
        clean_prompt = self.optimizer.optimize_prompt(prompt)

        # 2. Check Cache
        cached = self.optimizer.check_cache(clean_prompt, model=self.model)
        if cached:
            return LLMResponse(success=True, content=cached, provider="mistral_cache")

        # 3. Call Mistral
        try:
            response = await asyncio.to_thread(
                self.client.chat.complete,
                model=self.model,
                messages=[{"role": "user", "content": clean_prompt}],
                **kwargs
            )
            content = response.choices[0].message.content
            tokens = response.usage.total_tokens

            # 4. Cache
            self.optimizer.cache_response(clean_prompt, content, model=self.model, tokens=tokens)

            return LLMResponse(
                success=True,
                content=content,
                provider="mistral",
                model=self.model,
                tokens_used=tokens
            )
        except Exception as e:
            return LLMResponse(success=False, error=str(e))

class OptimizedGroq:
    """
    Auto-optimizing wrapper for Groq.
    Essential for staying within the 14,400 req/day limit.
    """
    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile", cache_dir: str = "data/cache"):
        from groq import Groq
        self.client = Groq(api_key=api_key)
        self.model = model
        self.optimizer = TokenOptimizer(cache_dir=cache_dir)

    async def complete(self, prompt: str, **kwargs) -> LLMResponse:
        clean_prompt = self.optimizer.optimize_prompt(prompt)

        cached = self.optimizer.check_cache(clean_prompt, model=self.model)
        if cached:
            return LLMResponse(success=True, content=cached, provider="groq_cache")

        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model,
                messages=[{"role": "user", "content": clean_prompt}],
                **kwargs
            )
            content = response.choices[0].message.content
            tokens = response.usage.total_tokens if response.usage else 0

            self.optimizer.cache_response(clean_prompt, content, model=self.model, tokens=tokens)

            return LLMResponse(
                success=True,
                content=content,
                provider="groq",
                model=self.model,
                tokens_used=tokens
            )
        except Exception as e:
            return LLMResponse(success=False, error=str(e))

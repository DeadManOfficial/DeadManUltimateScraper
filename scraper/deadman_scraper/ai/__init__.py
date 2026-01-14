"""
AI Module
=========
FREE LLM routing for content analysis and filtering.

Providers (all FREE):
- Mistral: 1 BILLION tokens/month
- Groq: 14,400 requests/day
- Cerebras: 1M tokens/day
- Ollama: Unlimited (local)
"""

from deadman_scraper.ai.llm_router import FreeLLMRouter

__all__ = ["FreeLLMRouter"]

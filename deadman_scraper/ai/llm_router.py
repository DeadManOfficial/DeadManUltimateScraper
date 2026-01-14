"""
FREE LLM Router
===============
Intelligent routing to FREE LLM providers with quota management.

Providers:
- Mistral: 1 BILLION tokens/month (heavy filtering)
- Groq: 14,400 requests/day (fast inference)
- Cerebras: 1M tokens/day (fastest inference)
- Ollama: Unlimited (local, offline)

NO API COSTS - All providers have generous free tiers.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from deadman_scraper.core.config import LLMConfig

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Types of LLM tasks for routing decisions."""

    RELEVANCE_SCORING = auto()  # Quick, low tokens
    ENTITY_EXTRACTION = auto()  # Medium complexity
    SUMMARIZATION = auto()  # Higher tokens
    CONTENT_FILTERING = auto()  # Heavy, needs context
    CODE_GENERATION = auto()  # Specialized


@dataclass
class ProviderQuota:
    """Tracks usage quota for a provider."""

    name: str
    limit: int  # Per period
    period: str  # "day", "month", "hour"
    used: int = 0
    last_reset: datetime = field(default_factory=datetime.now)

    @property
    def remaining(self) -> int:
        return max(0, self.limit - self.used)

    @property
    def usage_percent(self) -> float:
        if self.limit == 0:
            return 0.0
        return self.used / self.limit

    def should_reset(self) -> bool:
        """Check if quota should reset based on period."""
        now = datetime.now()
        if self.period == "day":
            return now.date() > self.last_reset.date()
        elif self.period == "month":
            return now.month != self.last_reset.month or now.year != self.last_reset.year
        elif self.period == "hour":
            return now - self.last_reset > timedelta(hours=1)
        return False

    def reset(self) -> None:
        """Reset quota counter."""
        self.used = 0
        self.last_reset = datetime.now()

    def consume(self, amount: int) -> bool:
        """Consume quota. Returns False if insufficient."""
        if self.should_reset():
            self.reset()
        if self.used + amount > self.limit:
            return False
        self.used += amount
        return True


@dataclass
class LLMResponse:
    """Response from LLM provider."""

    success: bool
    content: str | None = None
    provider: str = ""
    model: str = ""
    tokens_used: int = 0
    latency_ms: float = 0.0
    error: str | None = None


class FreeLLMRouter:
    """
    Routes LLM requests to FREE providers with intelligent selection.

    Features:
    - Automatic provider selection based on task type
    - Quota tracking and automatic switching
    - Fallback chain when providers exhausted
    - Local Ollama support for offline operation

    Usage:
        router = FreeLLMRouter(config, api_keys)
        response = await router.complete("Extract entities from: ...")
        print(response.content)
    """

    # Provider configurations
    PROVIDERS = {
        "mistral": {
            "limit": 1_000_000_000,  # 1 billion tokens!
            "period": "month",
            "best_for": [TaskType.CONTENT_FILTERING, TaskType.SUMMARIZATION],
            "base_url": "https://api.mistral.ai/v1",
        },
        "groq": {
            "limit": 14_400,  # requests, not tokens
            "period": "day",
            "best_for": [TaskType.RELEVANCE_SCORING, TaskType.ENTITY_EXTRACTION],
            "base_url": "https://api.groq.com/openai/v1",
        },
        "cerebras": {
            "limit": 1_000_000,  # tokens
            "period": "day",
            "best_for": [TaskType.RELEVANCE_SCORING],  # Fastest
            "base_url": "https://api.cerebras.ai/v1",
        },
        "ollama": {
            "limit": float("inf"),  # Unlimited local
            "period": "day",
            "best_for": [TaskType.CODE_GENERATION],  # Offline/privacy
            "base_url": "http://localhost:11434/v1",
        },
    }

    def __init__(self, config: LLMConfig, api_keys: dict[str, str]):
        self.config = config
        self.api_keys = api_keys

        # Initialize quota trackers
        self._quotas: dict[str, ProviderQuota] = {}
        for name, info in self.PROVIDERS.items():
            limit = info["limit"]
            if limit == float("inf"):
                limit = 999_999_999
            self._quotas[name] = ProviderQuota(
                name=name,
                limit=int(limit),
                period=info["period"],
            )

    # =========================================================================
    # PUBLIC API
    # =========================================================================

    async def complete(
        self,
        prompt: str,
        *,
        task_type: TaskType | None = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        provider: str | None = None,
    ) -> LLMResponse:
        """
        Generate completion using optimal FREE provider.

        Args:
            prompt: The prompt to send
            task_type: Type of task (for routing)
            max_tokens: Maximum response tokens
            temperature: Sampling temperature
            provider: Force specific provider

        Returns:
            LLMResponse with content and metadata
        """
        start_time = datetime.now()

        # Select provider
        if provider:
            selected = provider
        else:
            selected = self._select_provider(task_type, len(prompt))

        # Try selected, then fallback chain
        fallback_chain = [selected] + [p for p in self.config.fallback_chain if p != selected]

        for provider_name in fallback_chain:
            # Check quota
            if not self._has_quota(provider_name, max_tokens):
                logger.debug(f"[LLM] {provider_name} quota exhausted, trying next...")
                continue

            # Try provider
            response = await self._call_provider(
                provider_name, prompt, max_tokens, temperature
            )

            if response.success:
                # Update local quota
                self._quotas[provider_name].consume(response.tokens_used)

                # Update master secrets file
                from deadman_scraper.utils.quota_tracker import QuotaTracker

                # Format remaining string based on provider type
                if provider_name == "groq":
                    remaining_str = f"~{self._quotas[provider_name].remaining} requests"
                else:
                    remaining_str = f"~{self._quotas[provider_name].remaining} tokens"

                # Increment is 1 request for Groq, tokens for others
                increment = 1 if provider_name == "groq" else response.tokens_used
                log_msg = f"{response.tokens_used} tokens ({response.model})"

                QuotaTracker.update_usage(provider_name, increment, remaining_str, log_msg)

                response.latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                return response

            logger.debug(f"[LLM] {provider_name} failed: {response.error}")

        # All providers failed
        return LLMResponse(
            success=False,
            error="All LLM providers exhausted or failed",
        )

    async def chat(
        self,
        messages: list[dict[str, str]],
        **kwargs,
    ) -> LLMResponse:
        """
        Chat completion with message history.

        Args:
            messages: List of {"role": "user|assistant|system", "content": "..."}
        """
        # Convert to single prompt for simple providers
        prompt = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
        return await self.complete(prompt, **kwargs)

    def get_quota_status(self) -> dict[str, dict[str, Any]]:
        """Get quota status for all providers."""
        status = {}
        for name, quota in self._quotas.items():
            if quota.should_reset():
                quota.reset()
            status[name] = {
                "used": quota.used,
                "remaining": quota.remaining,
                "limit": quota.limit,
                "period": quota.period,
                "percent_used": quota.usage_percent * 100,
            }
        return status

    # =========================================================================
    # PROVIDER SELECTION
    # =========================================================================

    def _select_provider(self, task_type: TaskType | None, prompt_length: int) -> str:
        """Select optimal provider based on task and quota."""
        # Check primary preference first
        primary = self.config.primary
        if self._has_quota(primary, prompt_length // 4):
            return primary

        # Route by task type
        if task_type:
            for provider, info in self.PROVIDERS.items():
                if task_type in info["best_for"]:
                    if self._has_quota(provider, prompt_length // 4):
                        return provider

        # Route by content length
        if prompt_length > 10000:
            # Large content - use Mistral (1B tokens)
            if self._has_quota("mistral", prompt_length // 4):
                return "mistral"

        # Default: fastest with quota
        for provider in ["cerebras", "groq", "mistral", "ollama"]:
            if self._has_quota(provider, prompt_length // 4):
                return provider

        return "ollama"  # Fallback to local

    def _has_quota(self, provider: str, estimated_tokens: int) -> bool:
        """Check if provider has sufficient quota."""
        if provider not in self._quotas:
            return False

        quota = self._quotas[provider]
        if quota.should_reset():
            quota.reset()

        # For Groq, quota is requests not tokens
        if provider == "groq":
            return quota.remaining > 0

        return quota.remaining >= estimated_tokens

    # =========================================================================
    # PROVIDER CALLS
    # =========================================================================

    async def _call_provider(
        self,
        provider: str,
        prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> LLMResponse:
        """Call specific LLM provider."""
        if provider == "mistral":
            return await self._call_mistral(prompt, max_tokens, temperature)
        elif provider == "groq":
            return await self._call_groq(prompt, max_tokens, temperature)
        elif provider == "cerebras":
            return await self._call_cerebras(prompt, max_tokens, temperature)
        elif provider == "ollama":
            return await self._call_ollama(prompt, max_tokens, temperature)
        else:
            return LLMResponse(success=False, error=f"Unknown provider: {provider}")

    async def _call_mistral(
        self, prompt: str, max_tokens: int, temperature: float
    ) -> LLMResponse:
        """Call Mistral AI API."""
        try:
            from mistralai import Mistral

            api_key = self.api_keys.get("mistral")
            if not api_key:
                return LLMResponse(success=False, error="Mistral API key not found")

            client = Mistral(api_key=api_key)
            model = self.config.mistral_model

            response = await asyncio.to_thread(
                client.chat.complete,
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
            )

            content = response.choices[0].message.content
            tokens = response.usage.total_tokens

            return LLMResponse(
                success=True,
                content=content,
                provider="mistral",
                model=model,
                tokens_used=tokens,
            )

        except ImportError:
            return LLMResponse(success=False, error="mistralai not installed")
        except Exception as e:
            return LLMResponse(success=False, error=str(e))

    async def _call_groq(
        self, prompt: str, max_tokens: int, temperature: float
    ) -> LLMResponse:
        """Call Groq API (fast inference)."""
        try:
            from groq import Groq

            api_key = self.api_keys.get("groq")
            if not api_key:
                return LLMResponse(success=False, error="Groq API key not found")

            client = Groq(api_key=api_key)
            model = self.config.groq_model

            response = await asyncio.to_thread(
                client.chat.completions.create,
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
            )

            content = response.choices[0].message.content
            tokens = response.usage.total_tokens if response.usage else 0

            return LLMResponse(
                success=True,
                content=content,
                provider="groq",
                model=model,
                tokens_used=tokens,
            )

        except ImportError:
            return LLMResponse(success=False, error="groq not installed")
        except Exception as e:
            return LLMResponse(success=False, error=str(e))

    async def _call_cerebras(
        self, prompt: str, max_tokens: int, temperature: float
    ) -> LLMResponse:
        """Call Cerebras API (fastest inference)."""
        try:
            import httpx

            api_key = self.api_keys.get("cerebras")
            if not api_key:
                return LLMResponse(success=False, error="Cerebras API key not found")

            model = self.config.cerebras_model

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.cerebras.ai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                    },
                    timeout=60,
                )

                if response.status_code != 200:
                    return LLMResponse(
                        success=False, error=f"Cerebras error: {response.status_code}"
                    )

                data = response.json()
                content = data["choices"][0]["message"]["content"]
                tokens = data.get("usage", {}).get("total_tokens", 0)

                return LLMResponse(
                    success=True,
                    content=content,
                    provider="cerebras",
                    model=model,
                    tokens_used=tokens,
                )

        except Exception as e:
            return LLMResponse(success=False, error=str(e))

    async def _call_ollama(
        self, prompt: str, max_tokens: int, temperature: float
    ) -> LLMResponse:
        """Call local Ollama (unlimited, offline)."""
        try:
            import httpx

            model = self.config.ollama_model

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "options": {
                            "num_predict": max_tokens,
                            "temperature": temperature,
                        },
                        "stream": False,
                    },
                    timeout=120,
                )

                if response.status_code != 200:
                    return LLMResponse(
                        success=False, error=f"Ollama error: {response.status_code}"
                    )

                data = response.json()
                content = data.get("response", "")

                return LLMResponse(
                    success=True,
                    content=content,
                    provider="ollama",
                    model=model,
                    tokens_used=0,  # Local, unlimited
                )

        except Exception as e:
            return LLMResponse(success=False, error=str(e))

"""
Relevance Scoring
=================
LLM-powered content relevance scoring for filtering search results.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from deadman_scraper.ai.llm_router import FreeLLMRouter

logger = logging.getLogger(__name__)


RELEVANCE_PROMPT = """Rate the relevance of this search result to the query.

Query: {query}

Result Title: {title}
Result URL: {url}
Result Snippet: {snippet}

Rate from 0.0 (completely irrelevant) to 1.0 (highly relevant).
Consider:
- Does the title/snippet directly address the query?
- Is the source likely to have quality information?
- Is this a primary source or aggregator?

Respond with ONLY a number between 0.0 and 1.0, nothing else."""


async def score_relevance(
    query: str,
    result: dict[str, Any],
    llm_router: FreeLLMRouter,
) -> float:
    """
    Score the relevance of a search result to a query.

    Args:
        query: The search query
        result: Dict with 'title', 'url', 'snippet' keys
        llm_router: LLM router for scoring

    Returns:
        Relevance score between 0.0 and 1.0
    """
    from deadman_scraper.ai.llm_router import TaskType

    prompt = RELEVANCE_PROMPT.format(
        query=query,
        title=result.get("title", ""),
        url=result.get("url", ""),
        snippet=result.get("snippet", ""),
    )

    response = await llm_router.complete(
        prompt,
        task_type=TaskType.RELEVANCE_SCORING,
        max_tokens=10,
        temperature=0.1,  # Low temp for consistent scoring
    )

    if not response.success:
        logger.debug(f"Relevance scoring failed: {response.error}")
        return 0.5  # Default middle score

    try:
        score = float(response.content.strip())
        return max(0.0, min(1.0, score))  # Clamp to [0, 1]
    except ValueError:
        logger.debug(f"Invalid relevance score: {response.content}")
        return 0.5


async def filter_relevant(
    query: str,
    results: list[dict[str, Any]],
    llm_router: FreeLLMRouter,
    threshold: float = 0.5,
    max_concurrent: int = 10,
) -> list[dict[str, Any]]:
    """
    Filter search results by relevance score.

    Args:
        query: The search query
        results: List of search result dicts
        llm_router: LLM router for scoring
        threshold: Minimum relevance score to keep
        max_concurrent: Max concurrent LLM calls

    Returns:
        Filtered list of results with 'relevance_score' added
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def score_with_limit(result: dict) -> tuple[dict, float]:
        async with semaphore:
            score = await score_relevance(query, result, llm_router)
            return result, score

    # Score all results concurrently
    tasks = [score_with_limit(r) for r in results]
    scored = await asyncio.gather(*tasks)

    # Filter and sort by relevance
    filtered = []
    for result, score in scored:
        if score >= threshold:
            result["relevance_score"] = score
            filtered.append(result)

    filtered.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

    logger.info(f"Filtered {len(results)} results to {len(filtered)} (threshold={threshold})")
    return filtered


SUMMARY_PROMPT = """Summarize the following content concisely.

Query context: {query}

Content:
{content}

Provide a 2-3 sentence summary focusing on information relevant to the query."""


async def summarize_content(
    content: str,
    query: str,
    llm_router: FreeLLMRouter,
    max_length: int = 500,
) -> str:
    """
    Summarize scraped content with query context.

    Args:
        content: The content to summarize
        query: Original query for context
        llm_router: LLM router

    Returns:
        Summary string
    """
    from deadman_scraper.ai.llm_router import TaskType

    # Truncate very long content
    if len(content) > 10000:
        content = content[:10000] + "..."

    prompt = SUMMARY_PROMPT.format(query=query, content=content)

    response = await llm_router.complete(
        prompt,
        task_type=TaskType.SUMMARIZATION,
        max_tokens=max_length,
        temperature=0.5,
    )

    if response.success:
        return response.content
    else:
        logger.warning(f"Summarization failed: {response.error}")
        return content[:max_length] + "..."  # Fallback to truncation


ENTITY_PROMPT = """Extract key entities from this text.

Text:
{text}

Extract and categorize:
- People (names)
- Organizations (companies, groups)
- Locations (places, countries)
- Technologies (tools, languages, frameworks)
- Dates/Times

Format as JSON:
{{"people": [], "organizations": [], "locations": [], "technologies": [], "dates": []}}"""


async def extract_entities(
    text: str,
    llm_router: FreeLLMRouter,
) -> dict[str, list[str]]:
    """
    Extract named entities from text.

    Args:
        text: Text to analyze
        llm_router: LLM router

    Returns:
        Dict of entity categories to lists of entities
    """
    import json

    from deadman_scraper.ai.llm_router import TaskType

    # Truncate
    if len(text) > 5000:
        text = text[:5000]

    prompt = ENTITY_PROMPT.format(text=text)

    response = await llm_router.complete(
        prompt,
        task_type=TaskType.ENTITY_EXTRACTION,
        max_tokens=500,
        temperature=0.3,
    )

    if not response.success:
        return {"people": [], "organizations": [], "locations": [], "technologies": [], "dates": []}

    try:
        # Try to parse JSON from response
        content = response.content.strip()
        # Handle markdown code blocks
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content)
    except (json.JSONDecodeError, IndexError):
        logger.debug(f"Failed to parse entities: {response.content}")
        return {"people": [], "organizations": [], "locations": [], "technologies": [], "dates": []}

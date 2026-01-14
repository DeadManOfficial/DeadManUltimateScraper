"""
NASA-Standard Unit Tests: CentralScraper
========================================
Tests for the "God" module high-level API.
"""

import pytest
from unittest.mock import AsyncMock, patch
from central_scraper import CentralScraper, ScrapeRequest
from deadman_scraper.core.engine import ScrapeResult

@pytest.mark.asyncio
async def test_single_scrape():
    """Verify single scrape orchestration."""
    with patch("central_scraper.Engine") as mock_engine_cls:
        mock_engine = mock_engine_cls.return_value
        mock_engine.start = AsyncMock()
        mock_engine.stop = AsyncMock()
        mock_engine.scrape = AsyncMock(return_value=ScrapeResult(
            url="https://example.com",
            success=True,
            status_code=200,
            content="<html></html>",
            fetch_layer=1
        ))
        
        async with CentralScraper() as god:
            req = ScrapeRequest(url="https://example.com")
            result = await god.scrape(req)
            
            assert result.success is True
            assert result.status_code == 200
            assert mock_engine.scrape.called

@pytest.mark.asyncio
async def test_batch_scrape():
    """Verify batch scrape yields results."""
    with patch("central_scraper.Engine") as mock_engine_cls:
        mock_engine = mock_engine_cls.return_value
        mock_engine.start = AsyncMock()
        mock_engine.stop = AsyncMock()
        
        # Mock async iterator
        async def mock_scrape_many(urls):
            for url in urls:
                yield ScrapeResult(url=url, success=True)
        
        mock_engine.scrape_many = mock_scrape_many
        
        async with CentralScraper() as god:
            requests = [
                ScrapeRequest(url="https://a.com"),
                ScrapeRequest(url="https://b.com")
            ]
            
            results = []
            async for res in god.scrape_batch(requests):
                results.append(res)
                
            assert len(results) == 2
            assert results[0].url == "https://a.com"

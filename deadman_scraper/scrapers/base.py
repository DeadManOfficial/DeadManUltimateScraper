"""
Base Site Scraper
=================
NASA Standard: Abstract base class for site-specific logic.
Ensures consistency and robustness across different targets.
"""

from abc import ABC, abstractmethod
from typing import Any

from central_scraper import CentralScraper, ScrapeRequest
from deadman_scraper.core.engine import ScrapeResult


class SiteScraper(ABC):
    """
    Abstract base class for all site-specific scrapers.
    """

    def __init__(self, scraper: CentralScraper):
        self.scraper = scraper

    @abstractmethod
    async def scrape(self, **kwargs) -> Any:
        """
        Execute the main scraping logic for the site.
        """
        pass

    async def _fetch(self, url: str, **kwargs) -> ScrapeResult:
        """
        Helper method to fetch content via CentralScraper.
        """
        request = ScrapeRequest(url=url, **kwargs)
        return await self.scraper.scrape(request)

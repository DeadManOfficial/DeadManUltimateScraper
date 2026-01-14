"""
Scraper Registry
================
Central access point for all site-specific scrapers.
"""

from deadman_scraper.scrapers.base import SiteScraper
from deadman_scraper.scrapers.costco import CostcoScraper
from deadman_scraper.scrapers.internet import InternetScraper
from deadman_scraper.scrapers.sentinel import SentinelScraper

__all__ = ["SiteScraper", "CostcoScraper", "SentinelScraper", "InternetScraper"]

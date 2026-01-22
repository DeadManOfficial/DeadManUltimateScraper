"""
DeadMan Ultimate Scraper - Dark Web Module
==========================================

Integrated dark web scraping capabilities from:
- TorCrawl.py (depth crawling, YARA rules)
- Darker (14-engine meta-search)
- Fresh Onions (multi-TOR, clone detection)
- DarkScrape (media extraction, face recognition)
- SpiderFoot (OSINT collection)

ALL FREE FOREVER - DeadManOfficial
"""

from .engine import DarkWebEngine
from .meta_search import DarkMetaSearch
from .crawler import OnionCrawler
from .media import MediaExtractor
from .validators import OnionValidator, CloneDetector
from .osint import OSINTCollector

__all__ = [
    "DarkWebEngine",
    "DarkMetaSearch",
    "OnionCrawler",
    "MediaExtractor",
    "OnionValidator",
    "CloneDetector",
    "OSINTCollector",
]

__version__ = "1.0.0"
__author__ = "DeadManOfficial"

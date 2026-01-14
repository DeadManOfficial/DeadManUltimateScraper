"""
Fetch Layer
===========
5-Layer Adaptive Downloader with automatic fallback.
"""

from deadman_scraper.fetch.downloader import AdaptiveDownloader, FetchResult
from deadman_scraper.fetch.tor_manager import TORManager

__all__ = ["AdaptiveDownloader", "FetchResult", "TORManager"]

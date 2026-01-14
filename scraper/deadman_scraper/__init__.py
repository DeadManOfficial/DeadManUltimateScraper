"""
DEADMAN ULTIMATE SCRAPER
========================
No Limits. No Cost. Scrape Anything.

A ground-up general purpose web scraping tool combining:
- 5-Layer Adaptive Downloader (curl_cffi → Camoufox → ChromeDriver → TOR → CAPTCHA)
- Multi-Engine Search Aggregation (15+ sources, clearnet + darknet)
- FREE LLM Router (Mistral 1B, Groq 14.4k/day, Cerebras 1M/day, Ollama unlimited)
- Strategy Pattern Extraction (CSS, XPath, Regex, LLM)
- Full Stealth Suite (JA3/JA4, Canvas, WebGL, Behavioral)
"""

__version__ = "1.0.0"
__author__ = "DeadMan"

from deadman_scraper.core.config import Config
from deadman_scraper.core.engine import Engine

__all__ = ["Engine", "Config", "__version__"]

"""
DEADMAN SCRAPER - Analytics Layer
==================================
Data analysis, sentiment scoring, and visualization support.

Modules:
- Sentiment: Weighted keyword sentiment analysis
- Keywords: Frequency tracking and trending
- Visualizations: Chart data generation
"""

from .sentiment import SentimentAnalyzer, DARK_WEB_KEYWORDS

__all__ = ["SentimentAnalyzer", "DARK_WEB_KEYWORDS"]

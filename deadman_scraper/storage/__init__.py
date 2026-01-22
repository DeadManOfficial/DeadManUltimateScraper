"""
DEADMAN SCRAPER - Storage Layer
================================
Unified storage backends for scraped data.

Backends:
- Elasticsearch: Full-text search and analytics
- MongoDB: User configuration and preferences
- SQLite: Local queue persistence (existing)
"""

from .elasticsearch import ElasticsearchStore
from .mongodb import MongoDBStore

__all__ = ["ElasticsearchStore", "MongoDBStore"]

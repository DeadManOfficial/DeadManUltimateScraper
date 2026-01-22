"""
DEADMAN SCRAPER - Elasticsearch Integration
============================================
Full-text search, indexing, and analytics for scraped data.

Features:
- Automatic index creation with mappings
- Bulk document indexing with MD5 deduplication
- Full-text wildcard search
- Paginated queries for infinite scroll
- Keyword frequency counting

Based on zilbers/dark-web-scraper patterns, enhanced for DeadMan.
"""

import hashlib
import logging
from datetime import datetime
from typing import Any

try:
    from elasticsearch import Elasticsearch, helpers
    HAS_ELASTICSEARCH = True
except ImportError:
    HAS_ELASTICSEARCH = False
    Elasticsearch = None

logger = logging.getLogger("DeadMan.Elasticsearch")


# Default index mappings for scraped content
DEFAULT_MAPPINGS = {
    "properties": {
        "url": {
            "type": "keyword"
        },
        "title": {
            "type": "text",
            "fields": {
                "keyword": {"type": "keyword", "ignore_above": 256}
            }
        },
        "content": {
            "type": "text",
            "fields": {
                "keyword": {"type": "keyword", "ignore_above": 256}
            }
        },
        "author": {
            "type": "text",
            "fields": {
                "keyword": {"type": "keyword", "ignore_above": 256}
            }
        },
        "source": {
            "type": "keyword"
        },
        "scraped_at": {
            "type": "date",
            "format": "yyyy-MM-dd HH:mm:ss||epoch_millis"
        },
        "domain": {
            "type": "keyword"
        },
        "is_onion": {
            "type": "boolean"
        },
        "fetch_layer": {
            "type": "keyword"
        },
        "status_code": {
            "type": "integer"
        },
        "sentiment_score": {
            "type": "float"
        },
        "sentiment_comparative": {
            "type": "float"
        },
        "keywords_found": {
            "type": "keyword"
        },
        "secrets_detected": {
            "type": "boolean"
        },
        "metadata": {
            "type": "object",
            "enabled": False
        }
    }
}


class ElasticsearchStore:
    """
    Elasticsearch storage backend for DeadMan Scraper.

    Provides:
    - Document indexing with deduplication
    - Full-text search with wildcards
    - Paginated results for infinite scroll
    - Keyword frequency analytics
    - Bulk operations for performance
    """

    def __init__(
        self,
        hosts: list[str] | str = "http://localhost:9200",
        index_name: str = "deadman_scrapes",
        max_retries: int = 5,
        request_timeout: int = 60,
        sniff_on_start: bool = True
    ):
        """
        Initialize Elasticsearch connection.

        Args:
            hosts: Elasticsearch host(s)
            index_name: Default index for scraped data
            max_retries: Max connection retries
            request_timeout: Request timeout in seconds
            sniff_on_start: Sniff cluster nodes on startup
        """
        if not HAS_ELASTICSEARCH:
            raise ImportError(
                "elasticsearch package required. Install with: pip install elasticsearch>=8.0.0"
            )

        if isinstance(hosts, str):
            hosts = [hosts]

        self.index_name = index_name
        self.client = Elasticsearch(
            hosts=hosts,
            max_retries=max_retries,
            request_timeout=request_timeout,
            sniff_on_start=sniff_on_start,
            retry_on_timeout=True
        )

        self._ensure_index()
        logger.info(f"Elasticsearch connected: {hosts}, index: {index_name}")

    def _ensure_index(self) -> None:
        """Create index if it doesn't exist."""
        if not self.client.indices.exists(index=self.index_name):
            self.client.indices.create(
                index=self.index_name,
                body={
                    "settings": {
                        "number_of_shards": 1,
                        "number_of_replicas": 0,
                        "analysis": {
                            "analyzer": {
                                "default": {
                                    "type": "standard"
                                }
                            }
                        }
                    },
                    "mappings": DEFAULT_MAPPINGS
                }
            )
            logger.info(f"Created index: {self.index_name}")

    @staticmethod
    def _generate_doc_id(doc: dict) -> str:
        """Generate MD5 hash for document deduplication."""
        key = f"{doc.get('url', '')}{doc.get('scraped_at', '')}{doc.get('title', '')}"
        return hashlib.md5(key.encode()).hexdigest()

    def index_document(self, doc: dict) -> dict:
        """
        Index a single document.

        Args:
            doc: Document to index (url, title, content, etc.)

        Returns:
            Elasticsearch response
        """
        doc_id = self._generate_doc_id(doc)

        # Add timestamp if not present
        if "scraped_at" not in doc:
            doc["scraped_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        response = self.client.index(
            index=self.index_name,
            id=doc_id,
            body=doc,
            refresh=True
        )

        logger.debug(f"Indexed document: {doc_id}")
        return response

    def bulk_index(self, documents: list[dict]) -> dict:
        """
        Bulk index multiple documents.

        Args:
            documents: List of documents to index

        Returns:
            Bulk operation response with success/error counts
        """
        if not documents:
            return {"indexed": 0, "errors": 0}

        actions = []
        for doc in documents:
            doc_id = self._generate_doc_id(doc)

            if "scraped_at" not in doc:
                doc["scraped_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            actions.append({
                "_index": self.index_name,
                "_id": doc_id,
                "_source": doc
            })

        success, errors = helpers.bulk(
            self.client,
            actions,
            refresh=True,
            raise_on_error=False
        )

        logger.info(f"Bulk indexed: {success} success, {len(errors) if errors else 0} errors")
        return {"indexed": success, "errors": len(errors) if errors else 0}

    def search(
        self,
        query: str = "",
        size: int = 1000,
        from_: int = 0,
        sort_field: str = "scraped_at",
        sort_order: str = "desc"
    ) -> list[dict]:
        """
        Search documents with optional wildcard query.

        Args:
            query: Search query (supports wildcards with *)
            size: Max results to return
            from_: Offset for pagination
            sort_field: Field to sort by
            sort_order: Sort direction (asc/desc)

        Returns:
            List of matching documents
        """
        if query:
            # Wildcard search across all text fields
            body = {
                "query": {
                    "query_string": {
                        "query": f"*{query}*",
                        "fields": ["title", "content", "author", "url"]
                    }
                },
                "sort": [{sort_field: {"order": sort_order}}]
            }
        else:
            body = {
                "query": {"match_all": {}},
                "sort": [{sort_field: {"order": sort_order}}]
            }

        response = self.client.search(
            index=self.index_name,
            body=body,
            size=size,
            from_=from_
        )

        results = []
        for hit in response["hits"]["hits"]:
            doc = hit["_source"]
            doc["id"] = hit["_id"]
            doc["_score"] = hit.get("_score")
            results.append(doc)

        return results

    def search_paginated(
        self,
        page: int = 0,
        page_size: int = 10,
        query: str = "",
        sort_field: str = "scraped_at"
    ) -> list[dict]:
        """
        Paginated search for infinite scroll.

        Args:
            page: Page number (0-indexed)
            page_size: Results per page
            query: Optional search query
            sort_field: Field to sort by

        Returns:
            List of documents for the page
        """
        return self.search(
            query=query,
            size=page_size,
            from_=page * page_size,
            sort_field=sort_field
        )

    def count_keyword(self, keyword: str) -> dict:
        """
        Count occurrences of a keyword.

        Args:
            keyword: Keyword to count

        Returns:
            Dict with label and count
        """
        response = self.client.count(
            index=self.index_name,
            body={
                "query": {
                    "query_string": {
                        "query": f"*{keyword}*",
                        "fields": ["title", "content"]
                    }
                }
            }
        )

        return {"label": keyword, "value": response["count"]}

    def get_keyword_frequencies(self, keywords: list[str]) -> list[dict]:
        """
        Get frequency counts for multiple keywords.

        Args:
            keywords: List of keywords to count

        Returns:
            List of {label, value} dicts
        """
        return [self.count_keyword(kw) for kw in keywords]

    def get_by_id(self, doc_id: str) -> dict | None:
        """Get a document by ID."""
        try:
            response = self.client.get(index=self.index_name, id=doc_id)
            doc = response["_source"]
            doc["id"] = response["_id"]
            return doc
        except Exception:
            return None

    def delete_by_id(self, doc_id: str) -> bool:
        """Delete a document by ID."""
        try:
            self.client.delete(index=self.index_name, id=doc_id, refresh=True)
            return True
        except Exception:
            return False

    def get_stats(self) -> dict:
        """Get index statistics."""
        count = self.client.count(index=self.index_name)
        stats = self.client.indices.stats(index=self.index_name)

        return {
            "document_count": count["count"],
            "size_bytes": stats["_all"]["primaries"]["store"]["size_in_bytes"],
            "index_name": self.index_name
        }

    def get_domain_distribution(self) -> list[dict]:
        """Get document count by domain."""
        response = self.client.search(
            index=self.index_name,
            body={
                "size": 0,
                "aggs": {
                    "domains": {
                        "terms": {
                            "field": "domain",
                            "size": 100
                        }
                    }
                }
            }
        )

        return [
            {"domain": bucket["key"], "count": bucket["doc_count"]}
            for bucket in response["aggregations"]["domains"]["buckets"]
        ]

    def get_onion_ratio(self) -> dict:
        """Get ratio of onion vs clearnet documents."""
        response = self.client.search(
            index=self.index_name,
            body={
                "size": 0,
                "aggs": {
                    "onion_ratio": {
                        "terms": {"field": "is_onion"}
                    }
                }
            }
        )

        result = {"onion": 0, "clearnet": 0}
        for bucket in response["aggregations"]["onion_ratio"]["buckets"]:
            if bucket["key"]:
                result["onion"] = bucket["doc_count"]
            else:
                result["clearnet"] = bucket["doc_count"]

        return result

    def close(self):
        """Close the Elasticsearch connection."""
        self.client.close()
        logger.info("Elasticsearch connection closed")

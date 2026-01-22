"""
DEADMAN SCRAPER - Worker Module
================================
Autonomous scraper worker for Docker deployment.

Based on zilbers/dark-web-scraper webscraper.py, enhanced with DeadMan features.

Features:
- Polls configuration from API server
- Executes scrapes using CentralScraper engine
- Posts results to Elasticsearch via API
- Updates status for real-time dashboard
- Cooldown management
"""

import asyncio
import logging
import os
import sys
import time
from datetime import datetime
from urllib.parse import urlparse

import requests

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from deadman_scraper.analytics.sentiment import SentimentAnalyzer
from deadman_scraper.storage.elasticsearch import ElasticsearchStore

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("DeadMan.Worker")


# Default keywords for dark web monitoring
DEFAULT_KEYWORDS = [
    "DDOS", "exploits", "credit cards", "attack", "bitcoin",
    "passwords", "hacked", "ransomware", "stolen", "leaked",
    "fullz", "malware", "vulnerability", "credentials", "breach"
]


class ScraperWorker:
    """
    Autonomous scraper worker that polls config and executes scrapes.
    """

    def __init__(self):
        """Initialize the worker with environment configuration."""
        self.api_server = os.environ.get('API_SERVER', 'http://localhost:8080')
        self.elasticsearch_host = os.environ.get('ELASTICSEARCH_HOST', 'http://localhost:9200')
        self.user_id = os.environ.get('USER_ID', 'default')

        # Initialize components
        self.sentiment = SentimentAnalyzer()
        self.es_store = None

        logger.info(f"Worker initialized - API: {self.api_server}")

    def connect_elasticsearch(self) -> bool:
        """Connect to Elasticsearch."""
        try:
            self.es_store = ElasticsearchStore(hosts=self.elasticsearch_host)
            logger.info("Connected to Elasticsearch")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Elasticsearch: {e}")
            return False

    def get_config(self) -> dict:
        """Fetch configuration from API server."""
        try:
            response = requests.get(
                f"{self.api_server}/api/user/_config",
                params={"id": self.user_id},
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get config: {e}")
            return {
                "keywords": DEFAULT_KEYWORDS,
                "cooldown_minutes": 5,
                "use_tor": True,
                "use_llm": False,
                "darkweb_enabled": True
            }

    def update_status(self, active: bool, message: str) -> None:
        """Update scraper status on API server."""
        try:
            requests.post(
                f"{self.api_server}/api/status",
                json={"active": active, "message": message},
                timeout=10
            )
        except Exception as e:
            logger.warning(f"Failed to update status: {e}")

    def post_results(self, documents: list[dict]) -> bool:
        """Post scraped results to API server."""
        if not documents:
            return True

        try:
            response = requests.post(
                f"{self.api_server}/api/data",
                json=documents,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"Posted {result.get('indexed', 0)} documents")
            return True
        except Exception as e:
            logger.error(f"Failed to post results: {e}")
            return False

    async def scrape_with_engine(self, config: dict) -> list[dict]:
        """Execute scrape using CentralScraper engine."""
        from central_scraper import CentralScraper, ScrapeRequest
        from deadman_scraper.core.scheduler import Priority

        documents = []
        keywords = config.get("keywords", DEFAULT_KEYWORDS)
        use_tor = config.get("use_tor", True)
        use_llm = config.get("use_llm", False)
        darkweb = config.get("darkweb_enabled", True)

        async with CentralScraper() as scraper:
            # Search and scrape for each keyword
            for keyword in keywords[:10]:  # Limit to 10 keywords per cycle
                logger.info(f"Searching for: {keyword}")

                try:
                    async for result in scraper.search_intelligence(keyword, darkweb=darkweb):
                        if result.success and result.content:
                            # Analyze sentiment
                            sentiment = self.sentiment.analyze(result.content)

                            # Build document
                            doc = {
                                "url": result.url,
                                "title": result.extracted.get("title", "") if result.extracted else "",
                                "content": result.content[:5000],  # Limit content size
                                "domain": urlparse(result.url).netloc,
                                "source": keyword,
                                "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "is_onion": ".onion" in result.url,
                                "fetch_layer": result.fetch_layer,
                                "status_code": result.status_code,
                                "sentiment_score": sentiment.score,
                                "sentiment_comparative": sentiment.comparative,
                                "keywords_found": sentiment.keyword_matches
                            }

                            documents.append(doc)

                            # Yield periodically to avoid blocking
                            if len(documents) >= 10:
                                break

                except Exception as e:
                    logger.error(f"Error scraping keyword '{keyword}': {e}")
                    continue

        return documents

    async def run_cycle(self) -> int:
        """Run a single scrape cycle."""
        # Get config
        config = self.get_config()
        cooldown = config.get("cooldown_minutes", 5)

        # Update status
        self.update_status(True, "Scraping!")
        logger.info("Starting scrape cycle")

        try:
            # Execute scrape
            documents = await self.scrape_with_engine(config)

            # Post results
            if documents:
                self.post_results(documents)
                logger.info(f"Cycle complete: {len(documents)} documents")
            else:
                logger.info("Cycle complete: no new documents")

            # Update status with cooldown
            self.update_status(False, f"On {cooldown} minutes cooldown!")

        except Exception as e:
            logger.exception("Error during scrape cycle")
            self.update_status(False, f"Error: {str(e)[:50]}")

        return cooldown

    async def run(self) -> None:
        """Main worker loop."""
        logger.info("Starting DeadMan Worker")

        # Connect to Elasticsearch
        if not self.connect_elasticsearch():
            logger.warning("Running without Elasticsearch")

        while True:
            try:
                # Run scrape cycle
                cooldown = await self.run_cycle()

                # Wait for cooldown
                logger.info(f"Waiting {cooldown} minutes before next cycle")
                await asyncio.sleep(cooldown * 60)

            except KeyboardInterrupt:
                logger.info("Worker stopped by user")
                break
            except Exception as e:
                logger.exception("Worker error")
                await asyncio.sleep(60)  # Wait 1 minute on error


def main():
    """Entry point for worker."""
    worker = ScraperWorker()
    asyncio.run(worker.run())


if __name__ == "__main__":
    main()

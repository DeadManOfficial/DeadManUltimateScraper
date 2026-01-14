"""Recursive Deep Scraper - Main orchestrator for recursive URL scraping."""

import asyncio
import json
from collections import defaultdict
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from ..core.config import Config
from ..core.deduplicator import DomainTracker
from ..core.engine import Engine
from ..core.persistent_queue import PersistentQueue
from ..extract.url_extractor import URLExtractor


@dataclass
class ScrapeStats:
    """Statistics for a recursive scrape session."""
    total_scraped: int = 0
    total_success: int = 0
    total_failed: int = 0
    total_urls_found: int = 0
    total_urls_added: int = 0
    by_domain: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    by_depth: dict[int, int] = field(default_factory=lambda: defaultdict(int))
    by_layer: dict[int, int] = field(default_factory=lambda: defaultdict(int))
    start_time: datetime = field(default_factory=datetime.now)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'total_scraped': self.total_scraped,
            'total_success': self.total_success,
            'total_failed': self.total_failed,
            'total_urls_found': self.total_urls_found,
            'total_urls_added': self.total_urls_added,
            'by_domain': dict(self.by_domain),
            'by_depth': dict(self.by_depth),
            'by_layer': dict(self.by_layer),
            'duration_seconds': (datetime.now() - self.start_time).total_seconds(),
            'errors_count': len(self.errors),
        }


class RecursiveScraper:
    """
    Main orchestrator for recursive deep scraping.

    Workflow:
    1. Initialize with seed URLs
    2. Scrape URLs in priority order
    3. Extract new URLs from content
    4. Add new URLs to queue (deduplicated)
    5. Repeat until queue empty or limits reached

    Features:
    - Persistent queue (survives restarts)
    - Priority-based scraping
    - Per-domain rate limiting
    - Depth limiting
    - Content-based deduplication
    - Progress tracking
    - Resume support
    """

    def __init__(
        self,
        config: Config,
        db_path: str = "data/queue.db",
        output_dir: str = "data/deep_results"
    ):
        """
        Initialize recursive scraper.

        Args:
            config: Scraper configuration
            db_path: Path to SQLite queue database
            output_dir: Directory for output files
        """
        self.config = config
        self.engine = Engine(config)
        self.queue = PersistentQueue(db_path)
        self.extractor = URLExtractor()
        self.domain_tracker = DomainTracker()
        self.stats = ScrapeStats()

        # Output setup
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "content").mkdir(exist_ok=True)
        (self.output_dir / "results").mkdir(exist_ok=True)

        # Domain filtering
        self.allowed_domains: set[str] | None = None
        self.blocked_domains: set[str] = set()

    async def run(
        self,
        seed_urls: list[str],
        max_depth: int = 5,
        max_pages: int = 1000,
        concurrency: int = 5,
        use_tor: bool = False,
        save_content: bool = True,
        progress_callback: callable = None
    ) -> ScrapeStats:
        """
        Run recursive deep scrape.

        Args:
            seed_urls: Initial URLs to start from
            max_depth: Maximum link depth to follow
            max_pages: Maximum total pages to scrape
            concurrency: Number of concurrent scrapers
            use_tor: Force TOR for all requests
            save_content: Save scraped content to files
            progress_callback: Optional callback for progress updates

        Returns:
            ScrapeStats with session statistics
        """
        self.stats = ScrapeStats()

        # Reset any stuck in_progress items
        self.queue.reset_in_progress()

        # Add seed URLs
        if seed_urls:
            added = self.queue.add_urls(seed_urls, depth=0)
            print(f"Added {added} seed URLs to queue")

        async with self.engine:
            while self.stats.total_scraped < max_pages:
                # Get next batch
                batch = self.queue.get_next_batch(
                    n=concurrency,
                    max_per_domain=3
                )

                if not batch:
                    print("Queue exhausted - scraping complete!")
                    break

                # Check depth limits
                batch = [
                    url for url in batch
                    if self.queue.get_depth(url) < max_depth
                ]

                if not batch:
                    continue

                # Scrape batch in parallel
                tasks = [
                    self._scrape_and_extract(
                        url,
                        max_depth=max_depth,
                        use_tor=use_tor,
                        save_content=save_content
                    )
                    for url in batch
                ]

                await asyncio.gather(*tasks, return_exceptions=True)

                # Progress report
                self._report_progress(progress_callback)

                # Small delay between batches
                await asyncio.sleep(0.5)

        # Save final stats
        self._save_stats()

        return self.stats

    async def run_stream(
        self,
        seed_urls: list[str],
        max_depth: int = 5,
        max_pages: int = 1000,
        concurrency: int = 5,
        use_tor: bool = False
    ) -> AsyncIterator[dict]:
        """
        Run recursive scrape with streaming results.

        Yields results as they complete.
        """
        self.stats = ScrapeStats()
        self.queue.reset_in_progress()

        if seed_urls:
            self.queue.add_urls(seed_urls, depth=0)

        async with self.engine:
            while self.stats.total_scraped < max_pages:
                batch = self.queue.get_next_batch(n=concurrency, max_per_domain=3)

                if not batch:
                    break

                batch = [
                    url for url in batch
                    if self.queue.get_depth(url) < max_depth
                ]

                if not batch:
                    continue

                for url in batch:
                    result = await self._scrape_and_extract(
                        url,
                        max_depth=max_depth,
                        use_tor=use_tor,
                        save_content=True
                    )
                    if result:
                        yield result

                await asyncio.sleep(0.5)

    async def _scrape_and_extract(
        self,
        url: str,
        max_depth: int,
        use_tor: bool,
        save_content: bool
    ) -> dict | None:
        """
        Scrape a URL and extract new URLs.

        Args:
            url: URL to scrape
            max_depth: Maximum depth limit
            use_tor: Force TOR routing
            save_content: Save content to file

        Returns:
            Result dict or None on error
        """
        depth = self.queue.get_depth(url)
        domain = urlparse(url).netloc

        try:
            # Check domain filters
            if self.allowed_domains and domain not in self.allowed_domains:
                self.queue.mark_failed(url, "Domain not in allowed list")
                return None

            if domain in self.blocked_domains:
                self.queue.mark_failed(url, "Domain blocked")
                return None

            # Check domain health
            if self.domain_tracker.should_skip(url, min_success_rate=0.1):
                self.queue.mark_failed(url, "Domain has too many failures")
                return None

            # Scrape
            result = await self.engine.scrape(url, use_tor=use_tor)

            # Update stats
            self.stats.total_scraped += 1
            self.stats.by_domain[domain] += 1
            self.stats.by_depth[depth] += 1

            if result.success:
                self.stats.total_success += 1
                self.stats.by_layer[result.fetch_layer] += 1

                # Track domain success
                self.domain_tracker.record(
                    url, True,
                    result.timing.get('total', 0)
                )

                new_urls_count = 0

                if result.content:
                    # Extract URLs from content
                    new_urls = self.extractor.extract_all(result.content, url)
                    self.stats.total_urls_found += len(new_urls)

                    # Filter and add to queue
                    if depth + 1 < max_depth:
                        filtered_urls = self._filter_urls(new_urls)
                        added = self.queue.add_urls(
                            filtered_urls,
                            parent_url=url,
                            depth=depth + 1
                        )
                        self.stats.total_urls_added += added
                        new_urls_count = added

                    # Save content
                    if save_content:
                        self._save_content(url, result, new_urls)

                # Mark complete
                self.queue.mark_complete(
                    url,
                    status_code=result.status_code,
                    content_type=result.content_type,
                    content_length=len(result.content) if result.content else 0,
                    fetch_layer=result.fetch_layer,
                    extracted_urls=new_urls_count
                )

                return {
                    'url': url,
                    'success': True,
                    'status_code': result.status_code,
                    'content_type': result.content_type,
                    'fetch_layer': result.fetch_layer,
                    'depth': depth,
                    'extracted_urls': new_urls_count,
                    'content_length': len(result.content) if result.content else 0
                }

            else:
                self.stats.total_failed += 1
                self.stats.errors.append(f"{url}: {result.error}")
                self.domain_tracker.record(url, False)
                self.queue.mark_failed(url, result.error)

                return {
                    'url': url,
                    'success': False,
                    'error': result.error,
                    'depth': depth
                }

        except Exception as e:
            self.stats.total_failed += 1
            error_msg = str(e)
            self.stats.errors.append(f"{url}: {error_msg}")
            self.queue.mark_failed(url, error_msg)

            return {
                'url': url,
                'success': False,
                'error': error_msg,
                'depth': depth
            }

    def _filter_urls(self, urls: list[str]) -> list[str]:
        """Filter URLs based on domain restrictions."""
        filtered = []

        for url in urls:
            try:
                parsed = urlparse(url)
                domain = parsed.netloc.lower()

                # Skip blocked domains
                if domain in self.blocked_domains:
                    continue

                # Check allowed domains
                if self.allowed_domains:
                    if not any(d in domain for d in self.allowed_domains):
                        continue

                filtered.append(url)

            except Exception:
                continue

        return filtered

    def _save_content(self, url: str, result, extracted_urls: list[str]):
        """Save scraped content to file."""
        from hashlib import md5

        try:
            # Create filename from URL hash
            url_hash = md5(url.encode(), usedforsecurity=False).hexdigest()[:16]  # nosec
            domain = urlparse(url).netloc.replace('.', '_')

            # Determine subdirectory based on domain type
            if '.onion' in url:
                subdir = "onion"
            elif 'github.com' in url:
                subdir = "github"
            elif 'reddit.com' in url:
                subdir = "reddit"
            else:
                subdir = "other"

            output_subdir = self.output_dir / "content" / subdir
            output_subdir.mkdir(exist_ok=True)

            # Save JSON with metadata
            output_file = output_subdir / f"{domain}_{url_hash}.json"
            data = {
                'url': url,
                'scraped_at': datetime.now().isoformat(),
                'status_code': result.status_code,
                'content_type': result.content_type,
                'fetch_layer': result.fetch_layer,
                'content': result.content,
                'extracted_urls': extracted_urls[:100],  # Limit stored URLs
                'extracted_count': len(extracted_urls),
            }

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to save content for {url}: {e}")

    def _save_stats(self):
        """Save session statistics."""
        stats_file = self.output_dir / "stats.json"
        queue_stats = self.queue.get_stats()

        combined_stats = {
            'session': self.stats.to_dict(),
            'queue': queue_stats,
            'saved_at': datetime.now().isoformat(),
        }

        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(combined_stats, f, indent=2)

    def _report_progress(self, callback: callable = None):
        """Report progress."""
        pending = self.queue.get_pending_count()

        progress = {
            'scraped': self.stats.total_scraped,
            'success': self.stats.total_success,
            'failed': self.stats.total_failed,
            'pending': pending,
            'urls_found': self.stats.total_urls_found,
            'urls_added': self.stats.total_urls_added,
        }

        print(
            f"[{self.stats.total_scraped}] "
            f"OK:{self.stats.total_success} "
            f"FAIL:{self.stats.total_failed} "
            f"PENDING:{pending} "
            f"FOUND:{self.stats.total_urls_found}"
        )

        if callback:
            callback(progress)

    def set_domain_filter(
        self,
        allowed: list[str] | None = None,
        blocked: list[str] | None = None
    ):
        """
        Set domain filtering.

        Args:
            allowed: Only scrape these domains (None = all)
            blocked: Never scrape these domains
        """
        if allowed:
            self.allowed_domains = set(d.lower() for d in allowed)
        else:
            self.allowed_domains = None

        if blocked:
            self.blocked_domains = set(d.lower() for d in blocked)

    def get_extracted_urls(self) -> list[str]:
        """Get all URLs extracted during the session."""
        urls = []
        content_dir = self.output_dir / "content"

        for json_file in content_dir.rglob("*.json"):
            try:
                with open(json_file, encoding='utf-8') as f:
                    data = json.load(f)
                    urls.extend(data.get('extracted_urls', []))
            except Exception:
                continue

        return list(set(urls))

    def export_results(self, format: str = 'json') -> str:
        """
        Export all results.

        Args:
            format: Output format ('json', 'urls', 'csv')

        Returns:
            Path to exported file
        """
        results = self.queue.get_all_results()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        if format == 'json':
            output_file = self.output_dir / f"results_{timestamp}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2)

        elif format == 'urls':
            output_file = self.output_dir / f"urls_{timestamp}.txt"
            urls = [r['url'] for r in results if r.get('status_code') == 200]
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(urls))

        elif format == 'csv':
            output_file = self.output_dir / f"results_{timestamp}.csv"
            import csv
            if results:
                with open(output_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=results[0].keys())
                    writer.writeheader()
                    writer.writerows(results)

        return str(output_file)


# Convenience function
async def deep_scrape(
    seed_urls: list[str],
    max_depth: int = 5,
    max_pages: int = 1000,
    use_tor: bool = False,
    output_dir: str = "data/deep_results"
) -> ScrapeStats:
    """
    Quick deep scrape function.

    Args:
        seed_urls: URLs to start from
        max_depth: Maximum depth
        max_pages: Maximum pages
        use_tor: Use TOR routing
        output_dir: Output directory

    Returns:
        Scraping statistics
    """
    from ..core.config import Config

    config = Config.from_env()
    config.load_api_keys()

    scraper = RecursiveScraper(config, output_dir=output_dir)
    return await scraper.run(
        seed_urls=seed_urls,
        max_depth=max_depth,
        max_pages=max_pages,
        use_tor=use_tor
    )

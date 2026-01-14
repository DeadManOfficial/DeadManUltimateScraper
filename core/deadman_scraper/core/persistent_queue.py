"""Persistent Priority Queue - SQLite-backed queue for recursive scraping."""

import json
import logging
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .deduplicator import URLDeduplicator

logger = logging.getLogger(__name__)

@dataclass
class QueueItem:
    """Represents an item in the scrape queue."""
    id: int
    url: str
    fingerprint: str
    priority: float
    depth: int
    parent_url: str | None
    domain: str
    status: str
    created_at: str
    scraped_at: str | None
    error: str | None = None
    metadata: dict | None = None


class PersistentQueue:
    """
    SQLite-backed priority queue for recursive scraping.

    Features:
    - Persistent storage (survives restarts)
    - Priority-based ordering
    - Per-domain rate limiting
    - Depth tracking
    - Resume support
    - Statistics tracking
    """

    # URL priority scoring
    DOMAIN_BONUSES = {
        'github.com': 25,
        'reddit.com': 15,
        'arxiv.org': 30,
        'docs.': 20,
        'api.': 20,
        'wiki': 15,
    }

    DOMAIN_PENALTIES = {
        'facebook.com': -50,
        'twitter.com': -30,
        'instagram.com': -50,
        'tiktok.com': -50,
        'ads.': -100,
        'tracking.': -100,
    }

    PATH_PENALTIES = {
        'login': -50,
        'signup': -50,
        'register': -50,
        'logout': -100,
        'password': -100,
        'checkout': -30,
        'cart': -30,
        'search': -20,
    }

    SKIP_EXTENSIONS = {
        '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.ico',
        '.mp3', '.mp4', '.wav', '.avi', '.mov', '.webm',
        '.css', '.woff', '.woff2', '.ttf', '.eot',
        '.zip', '.tar', '.gz', '.rar', '.exe', '.dmg',
        '.pdf',  # Optional: include or not based on needs
    }

    def __init__(
        self,
        db_path: str = "data/queue.db",
        deduplicator: URLDeduplicator | None = None
    ):
        """
        Initialize persistent queue.

        Args:
            db_path: Path to SQLite database
            deduplicator: Optional deduplicator instance (creates one if not provided)
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.deduper = deduplicator or URLDeduplicator()
        self._init_db()

    def _init_db(self):
        """Initialize database tables."""
        with self._get_conn() as conn:
            # Main queue table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE NOT NULL,
                    fingerprint TEXT NOT NULL,
                    priority REAL DEFAULT 100.0,
                    depth INTEGER DEFAULT 0,
                    parent_url TEXT,
                    domain TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    scraped_at TIMESTAMP,
                    error TEXT,
                    metadata TEXT
                )
            ''')

            # Results table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    status_code INTEGER,
                    content_type TEXT,
                    content_length INTEGER,
                    fetch_layer INTEGER,
                    extracted_urls INTEGER DEFAULT 0,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    error TEXT,
                    metadata TEXT
                )
            ''')

            # Statistics table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT NOT NULL,
                    total_attempts INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    total_time REAL DEFAULT 0.0,
                    last_attempt TIMESTAMP
                )
            ''')

            # Create indexes
            conn.execute('CREATE INDEX IF NOT EXISTS idx_queue_status ON queue(status)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_queue_priority ON queue(priority DESC)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_queue_domain ON queue(domain)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_queue_depth ON queue(depth)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_results_url ON results(url)')

            conn.commit()

    @contextmanager
    def _get_conn(self):
        """
        Get database connection with NASA-standard file locking.
        Prevents corruption during high-concurrency missions.
        """
        import portalocker
        lock_file = self.db_path.with_suffix(".lock")
        
        with portalocker.Lock(str(lock_file), timeout=10):
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()

    def add_urls(
        self,
        urls: list[str],
        parent_url: str | None = None,
        depth: int = 0,
        metadata: dict | None = None
    ) -> int:
        """
        Add URLs to the queue using atomic batch inserts.
        NASA Standard: ACID compliance for data integrity.
        """
        added = 0
        meta_json = json.dumps(metadata) if metadata else None

        with self._get_conn() as conn:
            # Explicitly start a transaction
            conn.execute("BEGIN TRANSACTION")
            try:
                for url in urls:
                    if self.deduper.check_and_mark(url):
                        continue

                    parsed = urlparse(url)
                    path_lower = parsed.path.lower()
                    if any(path_lower.endswith(ext) for ext in self.SKIP_EXTENSIONS):
                        continue

                    priority = self._calculate_priority(url, depth)
                    if priority <= 0:
                        continue

                    domain = parsed.netloc.lower()
                    if domain.startswith('www.'):
                        domain = domain[4:]

                    fingerprint = self.deduper.fingerprint(url)

                    conn.execute('''
                        INSERT OR IGNORE INTO queue
                        (url, fingerprint, priority, depth, parent_url, domain, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (url, fingerprint, priority, depth, parent_url, domain, meta_json))
                    added += 1

                conn.execute("COMMIT")
            except Exception as e:
                conn.execute("ROLLBACK")
                logger.error(f"Failed to add URLs: {e}")
                raise

        return added

    def _calculate_priority(self, url: str, depth: int) -> float:
        """
        Calculate URL priority score.

        Higher score = higher priority = scraped sooner.

        Args:
            url: URL to score
            depth: Current depth

        Returns:
            Priority score (0-200 typically)
        """
        score = 100.0

        # Depth penalty (deeper = lower priority)
        score -= depth * 15

        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        path = parsed.path.lower()

        # Domain bonuses
        for pattern, bonus in self.DOMAIN_BONUSES.items():
            if pattern in domain:
                score += bonus
                break

        # Domain penalties
        for pattern, penalty in self.DOMAIN_PENALTIES.items():
            if pattern in domain:
                score += penalty  # penalty is negative
                break

        # .onion bonus (high value)
        if '.onion' in domain:
            score += 40

        # Path penalties
        for pattern, penalty in self.PATH_PENALTIES.items():
            if pattern in path:
                score += penalty
                break

        # Path bonuses
        if '/docs/' in path or '/documentation/' in path:
            score += 25
        if '/api/' in path:
            score += 20
        if '/blob/' in path or '/tree/' in path:  # GitHub file paths
            score += 15

        return max(0, score)

    def get_next_batch(
        self,
        n: int = 10,
        max_per_domain: int = 3
    ) -> list[str]:
        """
        Get next batch of URLs to scrape.

        Implements per-domain limiting to avoid hammering single domains.

        Args:
            n: Maximum URLs to return
            max_per_domain: Maximum URLs per domain in batch

        Returns:
            List of URLs to scrape
        """
        urls = []
        domain_counts: dict[str, int] = {}

        with self._get_conn() as conn:
            # Get pending URLs ordered by priority
            cursor = conn.execute('''
                SELECT id, url, domain FROM queue
                WHERE status = 'pending'
                ORDER BY priority DESC
                LIMIT ?
            ''', (n * 5,))  # Fetch extra for domain filtering

            candidates = cursor.fetchall()

            for row in candidates:
                if len(urls) >= n:
                    break

                domain = row['domain']
                if domain_counts.get(domain, 0) >= max_per_domain:
                    continue

                urls.append(row['url'])
                domain_counts[domain] = domain_counts.get(domain, 0) + 1

                # Mark as in_progress
                conn.execute(
                    "UPDATE queue SET status = 'in_progress' WHERE id = ?",
                    (row['id'],)
                )

            conn.commit()

        return urls

    def mark_complete(
        self,
        url: str,
        status_code: int = 200,
        content_type: str = None,
        content_length: int = 0,
        fetch_layer: int = 1,
        extracted_urls: int = 0,
        error: str = None
    ):
        """Mark URL as completed and record result."""
        fingerprint = self.deduper.fingerprint(url)
        now = datetime.now().isoformat()

        with self._get_conn() as conn:
            # Update queue status
            conn.execute('''
                UPDATE queue
                SET status = ?, scraped_at = ?, error = ?
                WHERE url = ?
            ''', ('completed' if not error else 'failed', now, error, url))

            # Record result
            conn.execute('''
                INSERT INTO results
                (url, fingerprint, status_code, content_type, content_length,
                 fetch_layer, extracted_urls, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (url, fingerprint, status_code, content_type, content_length,
                  fetch_layer, extracted_urls, error))

            # Update domain stats
            domain = urlparse(url).netloc.lower()
            if domain.startswith('www.'):
                domain = domain[4:]

            success = 1 if not error else 0
            failure = 0 if not error else 1

            conn.execute('''
                INSERT INTO stats (domain, total_attempts, success_count, failure_count, last_attempt)
                VALUES (?, 1, ?, ?, ?)
                ON CONFLICT(domain) DO UPDATE SET
                    total_attempts = total_attempts + 1,
                    success_count = success_count + ?,
                    failure_count = failure_count + ?,
                    last_attempt = ?
            ''', (domain, success, failure, now, success, failure, now))

            conn.commit()

    def mark_failed(self, url: str, error: str):
        """Mark URL as failed."""
        self.mark_complete(url, status_code=0, error=error)

    def get_depth(self, url: str) -> int:
        """Get depth of a URL in the queue."""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT depth FROM queue WHERE url = ?",
                (url,)
            )
            row = cursor.fetchone()
            return row['depth'] if row else 0

    def get_stats(self) -> dict[str, Any]:
        """Get queue statistics."""
        with self._get_conn() as conn:
            # Queue stats
            cursor = conn.execute('''
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
                FROM queue
            ''')
            queue_stats = dict(cursor.fetchone())

            # Depth distribution
            cursor = conn.execute('''
                SELECT depth, COUNT(*) as count
                FROM queue
                GROUP BY depth
                ORDER BY depth
            ''')
            depth_dist = {row['depth']: row['count'] for row in cursor.fetchall()}

            # Domain distribution (top 10)
            cursor = conn.execute('''
                SELECT domain, COUNT(*) as count
                FROM queue
                GROUP BY domain
                ORDER BY count DESC
                LIMIT 10
            ''')
            domain_dist = {row['domain']: row['count'] for row in cursor.fetchall()}

            # Results stats
            cursor = conn.execute('''
                SELECT
                    COUNT(*) as total_scraped,
                    SUM(extracted_urls) as total_extracted,
                    AVG(content_length) as avg_content_length
                FROM results
            ''')
            results_stats = dict(cursor.fetchone())

        return {
            'queue': queue_stats,
            'depth_distribution': depth_dist,
            'top_domains': domain_dist,
            'results': results_stats,
            'deduplicator': self.deduper.get_stats(),
        }

    def reset_in_progress(self):
        """Reset all in_progress items to pending (for resume)."""
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE queue SET status = 'pending' WHERE status = 'in_progress'"
            )
            conn.commit()

    def get_pending_count(self) -> int:
        """Get count of pending URLs."""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) as count FROM queue WHERE status = 'pending'"
            )
            return cursor.fetchone()['count']

    def get_all_results(self, limit: int = None) -> list[dict]:
        """Get all scrape results."""
        with self._get_conn() as conn:
            query = "SELECT * FROM results ORDER BY scraped_at DESC"
            if limit:
                query += f" LIMIT {limit}"
            cursor = conn.execute(query)
            return [dict(row) for row in cursor.fetchall()]

    def export_urls(self, status: str = None) -> list[str]:
        """Export URLs from queue."""
        with self._get_conn() as conn:
            if status:
                cursor = conn.execute(
                    "SELECT url FROM queue WHERE status = ? ORDER BY priority DESC",
                    (status,)
                )
            else:
                cursor = conn.execute(
                    "SELECT url FROM queue ORDER BY priority DESC"
                )
            return [row['url'] for row in cursor.fetchall()]

    def clear(self, keep_results: bool = True):
        """Clear the queue."""
        with self._get_conn() as conn:
            conn.execute("DELETE FROM queue")
            if not keep_results:
                conn.execute("DELETE FROM results")
                conn.execute("DELETE FROM stats")
            conn.commit()
        self.deduper.clear()

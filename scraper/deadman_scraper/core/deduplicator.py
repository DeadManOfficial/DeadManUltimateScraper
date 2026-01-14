"""URL Deduplication - Fingerprinting and Bloom filter for efficient deduplication."""

import hashlib
import math
from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlencode, urlparse


class BloomFilter:
    """
    Memory-efficient probabilistic set for URL deduplication.

    Uses multiple hash functions to check membership with
    configurable false positive rate.
    """

    def __init__(self, expected_items: int = 100000, fp_rate: float = 0.01):
        """
        Initialize Bloom filter.

        Args:
            expected_items: Expected number of items to store
            fp_rate: Desired false positive rate (default 1%)
        """
        # Calculate optimal size and hash count
        self.size = self._optimal_size(expected_items, fp_rate)
        self.hash_count = self._optimal_hash_count(self.size, expected_items)
        self.bit_array = [False] * self.size
        self.count = 0

    def _optimal_size(self, n: int, p: float) -> int:
        """Calculate optimal bit array size."""
        m = -(n * math.log(p)) / (math.log(2) ** 2)
        return int(m)

    def _optimal_hash_count(self, m: int, n: int) -> int:
        """Calculate optimal number of hash functions."""
        k = (m / n) * math.log(2)
        return max(1, int(k))

    def _hash_positions(self, item: str) -> list[int]:
        """Generate hash positions for an item."""
        h1 = int(hashlib.md5(item.encode(), usedforsecurity=False).hexdigest(), 16)  # nosec
        h2 = int(hashlib.sha1(item.encode(), usedforsecurity=False).hexdigest(), 16) # nosec

        # Double hashing technique
        return [(h1 + i * h2) % self.size for i in range(self.hash_count)]

    def add(self, item: str) -> None:
        """Add an item to the filter."""
        for pos in self._hash_positions(item):
            self.bit_array[pos] = True
        self.count += 1

    def check(self, item: str) -> bool:
        """
        Check if item might be in the set.

        Returns:
            True if item might be present (could be false positive)
            False if item is definitely not present
        """
        return all(self.bit_array[pos] for pos in self._hash_positions(item))

    def __contains__(self, item: str) -> bool:
        """Support 'in' operator."""
        return self.check(item)

    def __len__(self) -> int:
        """Return approximate count of items added."""
        return self.count


@dataclass
class URLDeduplicator:
    """
    Comprehensive URL deduplication system.

    Uses multiple strategies:
    1. URL fingerprinting (canonical form)
    2. Bloom filter (fast probabilistic check)
    3. Exact hash set (guaranteed accuracy)
    4. Content hashing (detect duplicate content)
    """

    expected_urls: int = 100000
    fp_rate: float = 0.001

    # Internal state
    _seen: set[str] = field(default_factory=set)
    _bloom: BloomFilter = field(init=False)
    _content_hashes: dict[str, str] = field(default_factory=dict)

    # Tracking params to strip
    TRACKING_PARAMS: set[str] = field(default_factory=lambda: {
        'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
        'fbclid', 'gclid', 'msclkid', 'ref', 'ref_src', 'ref_url',
        'source', 'mc_cid', 'mc_eid', '_ga', 'yclid', 'click_id',
        'redirect', 'returnUrl', 'return_url', 'callback',
    })

    # Equivalent path patterns
    EQUIVALENT_PATHS: dict[str, str] = field(default_factory=lambda: {
        '/index.html': '/',
        '/index.htm': '/',
        '/index.php': '/',
        '/default.html': '/',
        '/default.htm': '/',
    })

    def __post_init__(self):
        """Initialize bloom filter after dataclass init."""
        self._bloom = BloomFilter(self.expected_urls, self.fp_rate)

    def fingerprint(self, url: str) -> str:
        """
        Generate canonical URL fingerprint.

        Normalizes URL by:
        - Lowercasing scheme and domain
        - Sorting query parameters
        - Removing tracking parameters
        - Normalizing equivalent paths
        - Removing fragments

        Args:
            url: URL to fingerprint

        Returns:
            MD5 hash of canonical URL
        """
        try:
            parsed = urlparse(url)

            # Normalize domain (lowercase, remove www.)
            domain = parsed.netloc.lower()
            if domain.startswith('www.'):
                domain = domain[4:]

            # Normalize path
            path = parsed.path or '/'
            path = self.EQUIVALENT_PATHS.get(path, path)

            # Remove trailing slashes (except root)
            if path != '/' and path.endswith('/'):
                path = path.rstrip('/')

            # Clean query parameters
            if parsed.query:
                params = parse_qs(parsed.query, keep_blank_values=False)
                # Remove tracking params
                cleaned = {
                    k.lower(): sorted(v)
                    for k, v in params.items()
                    if k.lower() not in self.TRACKING_PARAMS
                }
                # Sort parameters for consistency
                query = urlencode(cleaned, doseq=True) if cleaned else ''
            else:
                query = ''

            # Construct canonical form (no fragment)
            canonical = f"{domain}{path}"
            if query:
                canonical += f"?{query}"

            # Return hash
            return hashlib.md5(canonical.encode(), usedforsecurity=False).hexdigest()  # nosec

        except Exception:
            # Fallback: hash raw URL
            return hashlib.md5(url.encode(), usedforsecurity=False).hexdigest()  # nosec

    def fingerprint_content(self, content: str, max_length: int = 10000) -> str:
        """Create hash of content for duplication check."""
        normalized = content[:max_length].lower().strip()
        return hashlib.md5(normalized.encode(), usedforsecurity=False).hexdigest()  # nosec

    def is_duplicate(self, url: str, content: str | None = None) -> bool:
        """
        Check if URL (or its content) has been seen.

        Args:
            url: URL to check
            content: Optional content for duplicate content detection

        Returns:
            True if URL or content is a duplicate
        """
        fp = self.fingerprint(url)

        # Fast bloom filter check
        if fp in self._bloom:
            # Verify with exact set (bloom can have false positives)
            if fp in self._seen:
                return True

        # Check content hash if provided
        if content:
            ch = self.fingerprint_content(content)
            if ch in self._content_hashes:
                return True

        return False

    def mark_seen(self, url: str, content: str | None = None) -> str:
        """
        Mark URL as seen.

        Args:
            url: URL to mark
            content: Optional content for content-based dedup

        Returns:
            URL fingerprint
        """
        fp = self.fingerprint(url)

        # Add to both bloom and exact set
        self._bloom.add(fp)
        self._seen.add(fp)

        # Track content hash
        if content:
            ch = self.fingerprint_content(content)
            self._content_hashes[ch] = url

        return fp

    def check_and_mark(self, url: str, content: str | None = None) -> bool:
        """
        Check if duplicate, and mark as seen if not.

        Args:
            url: URL to check/mark
            content: Optional content

        Returns:
            True if was duplicate (not added)
            False if new (added to seen)
        """
        if self.is_duplicate(url, content):
            return True

        self.mark_seen(url, content)
        return False

    def get_stats(self) -> dict:
        """Get deduplication statistics."""
        return {
            'total_seen': len(self._seen),
            'bloom_count': len(self._bloom),
            'content_hashes': len(self._content_hashes),
            'bloom_size_bits': self._bloom.size,
            'bloom_hash_count': self._bloom.hash_count,
        }

    def clear(self) -> None:
        """Clear all seen URLs."""
        self._seen.clear()
        self._content_hashes.clear()
        self._bloom = BloomFilter(self.expected_urls, self.fp_rate)


class DomainTracker:
    """Track per-domain statistics for rate limiting and prioritization."""

    def __init__(self):
        self.domains: dict[str, dict] = {}

    def record(self, url: str, success: bool, response_time: float = 0.0):
        """Record a scrape attempt for a domain."""
        domain = urlparse(url).netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]

        if domain not in self.domains:
            self.domains[domain] = {
                'total': 0,
                'success': 0,
                'failed': 0,
                'total_time': 0.0,
                'avg_time': 0.0,
            }

        stats = self.domains[domain]
        stats['total'] += 1
        if success:
            stats['success'] += 1
        else:
            stats['failed'] += 1
        stats['total_time'] += response_time
        stats['avg_time'] = stats['total_time'] / stats['total']

    def get_success_rate(self, url: str) -> float:
        """Get success rate for a domain."""
        domain = urlparse(url).netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]

        if domain not in self.domains:
            return 1.0  # Unknown domain, assume success

        stats = self.domains[domain]
        if stats['total'] == 0:
            return 1.0
        return stats['success'] / stats['total']

    def should_skip(self, url: str, min_success_rate: float = 0.1) -> bool:
        """Check if domain should be skipped due to low success rate."""
        return self.get_success_rate(url) < min_success_rate

    def get_all_stats(self) -> dict[str, dict]:
        """Get stats for all domains."""
        return self.domains.copy()

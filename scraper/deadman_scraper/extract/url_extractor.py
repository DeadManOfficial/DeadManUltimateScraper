"""URL Extraction - Multi-pattern URL extraction from scraped content."""

import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlencode, urljoin, urlparse


@dataclass
class ExtractedURL:
    """Represents an extracted URL with metadata."""
    url: str
    source_pattern: str
    is_absolute: bool
    domain: str


class URLExtractor:
    """Extract ALL URLs from scraped content using multiple patterns."""

    PATTERNS = {
        # Standard HTML links
        'href': r'href=["\']([^"\']+)["\']',
        'src': r'src=["\']([^"\']+)["\']',
        'action': r'action=["\']([^"\']+)["\']',
        'data_url': r'data-(?:url|href|src)=["\']([^"\']+)["\']',

        # JavaScript URLs
        'js_url': r'["\'](?:https?:)?//[^"\'<>\s]+["\']',
        'js_path': r'["\']\/[a-zA-Z0-9_\-\/\.]+["\']',
        'window_location': r'window\.location\s*=\s*["\']([^"\']+)["\']',
        'fetch_url': r'fetch\s*\(\s*["\']([^"\']+)["\']',

        # Markdown links
        'md_link': r'\[.*?\]\(([^\)]+)\)',
        'md_reference': r'\[.*?\]:\s*(\S+)',

        # Plain text URLs
        'plain_https': r'https://[^\s<>"\')\]\}]+',
        'plain_http': r'http://[^\s<>"\')\]\}]+',

        # .onion addresses (v3 - 56 chars)
        'onion_v3': r'(?:https?://)?([a-z2-7]{56}\.onion)(?:/[^\s<>"\']*)?',
        # .onion addresses (v2 - 16 chars, legacy)
        'onion_v2': r'(?:https?://)?([a-z2-7]{16}\.onion)(?:/[^\s<>"\']*)?',

        # GitHub specific
        'github_repo': r'github\.com/([a-zA-Z0-9_\-]+/[a-zA-Z0-9_\-\.]+)',
        'github_file': r'github\.com/[^/]+/[^/]+/(?:blob|tree|raw)/[^/]+/[^\s<>"\']+',
        'github_gist': r'gist\.github\.com/[a-zA-Z0-9_\-]+/[a-f0-9]+',

        # Reddit specific
        'reddit_post': r'reddit\.com/r/[^/]+/comments/[a-z0-9]+(?:/[^\s<>"\']*)?',
        'reddit_user': r'reddit\.com/(?:u|user)/[a-zA-Z0-9_\-]+',
        'subreddit': r'/r/([a-zA-Z0-9_]+)',
        'reddit_short': r'redd\.it/[a-z0-9]+',

        # API endpoints
        'api_endpoint': r'["\']/?api/v?\d*/[^"\']+["\']',

        # Archive/Wayback
        'archive_org': r'web\.archive\.org/web/\d+/[^\s<>"\']+',

        # Common CDNs and resources
        'cdn_url': r'(?:cdn|static|assets)[a-z0-9\-]*\.[a-z]+\.[a-z]+/[^\s<>"\']+',
    }

    # URL parts to strip (tracking parameters)
    TRACKING_PARAMS = {
        'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
        'fbclid', 'gclid', 'msclkid', 'ref', 'ref_src', 'ref_url',
        'source', 'mc_cid', 'mc_eid', '_ga', 'yclid',
    }

    # File extensions to skip
    SKIP_EXTENSIONS = {
        '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.ico', '.bmp',
        '.mp3', '.mp4', '.wav', '.avi', '.mov', '.webm',
        '.css', '.woff', '.woff2', '.ttf', '.eot',
        '.zip', '.tar', '.gz', '.rar', '.7z',
    }

    def __init__(self, skip_media: bool = True, skip_tracking: bool = True):
        """
        Initialize URL extractor.

        Args:
            skip_media: Skip media file URLs (images, videos, fonts)
            skip_tracking: Remove tracking parameters from URLs
        """
        self.skip_media = skip_media
        self.skip_tracking = skip_tracking
        self._compiled_patterns = {
            name: re.compile(pattern, re.IGNORECASE)
            for name, pattern in self.PATTERNS.items()
        }

    def extract_all(self, content: str, base_url: str) -> list[str]:
        """
        Extract and normalize all URLs from content.

        Args:
            content: HTML/text content to extract URLs from
            base_url: Base URL for resolving relative URLs

        Returns:
            List of unique, normalized URLs
        """
        urls: set[str] = set()

        for pattern_name, pattern in self._compiled_patterns.items():
            try:
                matches = pattern.findall(content)
                for match in matches:
                    # Handle tuple results from groups
                    if isinstance(match, tuple):
                        match = match[0] if match[0] else match[-1]

                    # Clean the match
                    url = self._clean_match(match)
                    if not url:
                        continue

                    # Normalize and resolve
                    normalized = self._normalize(url, base_url)
                    if normalized and self._should_include(normalized):
                        urls.add(normalized)
            except Exception:
                continue

        return sorted(urls)

    def extract_with_metadata(self, content: str, base_url: str) -> list[ExtractedURL]:
        """
        Extract URLs with source pattern metadata.

        Args:
            content: Content to extract from
            base_url: Base URL for resolution

        Returns:
            List of ExtractedURL objects with metadata
        """
        results: list[ExtractedURL] = []
        seen: set[str] = set()

        for pattern_name, pattern in self._compiled_patterns.items():
            try:
                matches = pattern.findall(content)
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0] if match[0] else match[-1]

                    url = self._clean_match(match)
                    if not url:
                        continue

                    normalized = self._normalize(url, base_url)
                    if normalized and normalized not in seen and self._should_include(normalized):
                        seen.add(normalized)
                        parsed = urlparse(normalized)
                        results.append(ExtractedURL(
                            url=normalized,
                            source_pattern=pattern_name,
                            is_absolute=bool(parsed.scheme),
                            domain=parsed.netloc
                        ))
            except Exception:
                continue

        return results

    def extract_onions(self, content: str) -> list[str]:
        """Extract only .onion addresses from content."""
        onions: set[str] = set()

        # V3 onion (56 chars)
        v3_matches = re.findall(r'([a-z2-7]{56}\.onion)', content, re.IGNORECASE)
        onions.update(addr.lower() for addr in v3_matches)

        # V2 onion (16 chars) - legacy
        v2_matches = re.findall(r'([a-z2-7]{16}\.onion)', content, re.IGNORECASE)
        onions.update(addr.lower() for addr in v2_matches)

        return sorted(onions)

    def extract_github_repos(self, content: str) -> list[str]:
        """Extract GitHub repository URLs."""
        repos: set[str] = set()

        # Full repo URLs
        matches = re.findall(
            r'github\.com/([a-zA-Z0-9_\-]+/[a-zA-Z0-9_\-\.]+)',
            content,
            re.IGNORECASE
        )
        for match in matches:
            # Clean trailing punctuation
            clean = match.rstrip('.,;:!?')
            if '/' in clean:
                repos.add(f"https://github.com/{clean}")

        return sorted(repos)

    def extract_reddit_links(self, content: str) -> list[str]:
        """Extract Reddit post and subreddit URLs."""
        links: set[str] = set()

        # Posts
        post_matches = re.findall(
            r'reddit\.com/r/([^/]+)/comments/([a-z0-9]+)',
            content,
            re.IGNORECASE
        )
        for subreddit, post_id in post_matches:
            links.add(f"https://www.reddit.com/r/{subreddit}/comments/{post_id}")

        # Subreddits
        sub_matches = re.findall(r'/r/([a-zA-Z0-9_]+)', content)
        for sub in sub_matches:
            if len(sub) > 1:  # Skip single letters
                links.add(f"https://www.reddit.com/r/{sub}")

        return sorted(links)

    def _clean_match(self, match: str) -> str | None:
        """Clean a regex match for processing."""
        if not match:
            return None

        # Strip quotes and whitespace
        url = match.strip().strip('"\'<>')

        # Skip empty or too short
        if len(url) < 3:
            return None

        # Skip data URIs
        if url.startswith('data:'):
            return None

        # Skip javascript: links
        if url.lower().startswith('javascript:'):
            return None

        # Skip mailto: links
        if url.lower().startswith('mailto:'):
            return None

        # Skip anchors only
        if url.startswith('#'):
            return None

        return url

    def _normalize(self, url: str, base_url: str) -> str | None:
        """Normalize URL: resolve relative, clean params."""
        try:
            # Handle protocol-relative URLs
            if url.startswith('//'):
                url = 'https:' + url

            # Resolve relative URLs
            if not url.startswith(('http://', 'https://')):
                # Check if it's an .onion address
                if '.onion' in url and not url.startswith('/'):
                    url = 'http://' + url
                else:
                    url = urljoin(base_url, url)

            # Parse and reconstruct
            parsed = urlparse(url)

            # Skip invalid
            if not parsed.netloc:
                return None

            # Clean query parameters
            if self.skip_tracking and parsed.query:
                params = parse_qs(parsed.query, keep_blank_values=True)
                cleaned_params = {
                    k: v for k, v in params.items()
                    if k.lower() not in self.TRACKING_PARAMS
                }
                query = urlencode(cleaned_params, doseq=True) if cleaned_params else ''
            else:
                query = parsed.query

            # Reconstruct URL
            normalized = f"{parsed.scheme}://{parsed.netloc.lower()}{parsed.path}"
            if query:
                normalized += f"?{query}"

            # Remove trailing slash for consistency (except root)
            if normalized.endswith('/') and parsed.path != '/':
                normalized = normalized.rstrip('/')

            return normalized

        except Exception:
            return None

    def _should_include(self, url: str) -> bool:
        """Check if URL should be included in results."""
        if not url:
            return False

        # Check file extension
        if self.skip_media:
            parsed = urlparse(url)
            path_lower = parsed.path.lower()
            for ext in self.SKIP_EXTENSIONS:
                if path_lower.endswith(ext):
                    return False

        return True


# Convenience functions
def extract_urls(content: str, base_url: str) -> list[str]:
    """Quick URL extraction."""
    return URLExtractor().extract_all(content, base_url)


def extract_onions(content: str) -> list[str]:
    """Quick .onion extraction."""
    return URLExtractor().extract_onions(content)

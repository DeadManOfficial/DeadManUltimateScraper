"""
Dark Web Media Extractor
========================

Inspired by: github.com/itsmehacker/DarkScrape

Features:
- Image/video/document extraction from .onion sites
- Face detection in images (optional)
- Batch processing from URL lists
- Media deduplication via hashing

ALL FREE FOREVER - DeadManOfficial
"""

import asyncio
import hashlib
import mimetypes
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, Set
from urllib.parse import urljoin, urlparse
import logging

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class MediaItem:
    """Represents a media item found on dark web."""
    url: str
    media_type: str = ""  # image, video, audio, document
    filename: str = ""
    extension: str = ""
    source_page: str = ""
    file_hash: str = ""
    file_size: int = 0
    alt_text: str = ""
    downloaded: bool = False
    local_path: str = ""
    faces_detected: int = 0
    timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "media_type": self.media_type,
            "filename": self.filename,
            "extension": self.extension,
            "source_page": self.source_page,
            "file_hash": self.file_hash,
            "file_size": self.file_size,
            "alt_text": self.alt_text,
            "downloaded": self.downloaded,
            "local_path": self.local_path,
            "faces_detected": self.faces_detected,
            "timestamp": self.timestamp,
        }


@dataclass
class ExtractionConfig:
    """Configuration for media extraction."""
    extract_images: bool = True
    extract_videos: bool = True
    extract_audio: bool = True
    extract_documents: bool = True
    download_media: bool = False
    download_path: str = "./media"
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    detect_faces: bool = False
    deduplicate: bool = True
    allowed_extensions: list = field(default_factory=lambda: [
        # Images
        ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg",
        # Videos
        ".mp4", ".webm", ".avi", ".mov", ".mkv",
        # Audio
        ".mp3", ".wav", ".ogg", ".flac",
        # Documents
        ".pdf", ".doc", ".docx", ".txt", ".rtf",
    ])


class MediaExtractor:
    """
    Extract and optionally download media from dark web pages.
    """

    # Media URL patterns
    IMAGE_PATTERNS = [
        re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE),
        re.compile(r'background-image:\s*url\(["\']?([^"\']+)["\']?\)', re.IGNORECASE),
        re.compile(r'<source[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE),
    ]

    VIDEO_PATTERNS = [
        re.compile(r'<video[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE),
        re.compile(r'<source[^>]+src=["\']([^"\']+\.(?:mp4|webm|avi))["\']', re.IGNORECASE),
    ]

    AUDIO_PATTERNS = [
        re.compile(r'<audio[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE),
        re.compile(r'<source[^>]+src=["\']([^"\']+\.(?:mp3|wav|ogg))["\']', re.IGNORECASE),
    ]

    DOCUMENT_PATTERNS = [
        re.compile(r'href=["\']([^"\']+\.(?:pdf|doc|docx|txt))["\']', re.IGNORECASE),
    ]

    def __init__(
        self,
        tor_manager=None,
        fetch_func=None,
        config: ExtractionConfig = None,
    ):
        """
        Initialize MediaExtractor.

        Args:
            tor_manager: TOR manager for .onion requests
            fetch_func: Async function for HTTP requests
            config: Extraction configuration
        """
        self.tor_manager = tor_manager
        self.fetch_func = fetch_func
        self.config = config or ExtractionConfig()

        # Track seen media (for deduplication)
        self.seen_urls: Set[str] = set()
        self.seen_hashes: Set[str] = set()

        # Face detection (lazy load)
        self._face_detector = None

    async def extract_from_url(
        self,
        url: str,
        html: Optional[str] = None,
    ) -> list[MediaItem]:
        """
        Extract media items from a URL or HTML content.

        Args:
            url: Source URL
            html: Optional pre-fetched HTML content

        Returns:
            List of MediaItem objects
        """
        logger.info(f"[MediaExtractor] Extracting media from: {url}")

        if not html:
            html = await self._fetch(url)
            if not html:
                return []

        media_items = []

        # Extract images
        if self.config.extract_images:
            items = self._extract_media(html, url, self.IMAGE_PATTERNS, "image")
            media_items.extend(items)

        # Extract videos
        if self.config.extract_videos:
            items = self._extract_media(html, url, self.VIDEO_PATTERNS, "video")
            media_items.extend(items)

        # Extract audio
        if self.config.extract_audio:
            items = self._extract_media(html, url, self.AUDIO_PATTERNS, "audio")
            media_items.extend(items)

        # Extract documents
        if self.config.extract_documents:
            items = self._extract_media(html, url, self.DOCUMENT_PATTERNS, "document")
            media_items.extend(items)

        # Also parse with BeautifulSoup for better extraction
        soup_items = self._extract_with_soup(html, url)
        media_items.extend(soup_items)

        # Deduplicate
        if self.config.deduplicate:
            media_items = self._deduplicate(media_items)

        logger.info(f"[MediaExtractor] Found {len(media_items)} media items")

        # Download if configured
        if self.config.download_media:
            await self._download_media(media_items)

        return media_items

    async def extract_from_urls(
        self,
        urls: list[str],
        max_concurrent: int = 3,
    ) -> list[MediaItem]:
        """
        Extract media from multiple URLs.

        Args:
            urls: List of URLs to process
            max_concurrent: Maximum concurrent extractions

        Returns:
            List of all MediaItem objects
        """
        all_items = []
        semaphore = asyncio.Semaphore(max_concurrent)

        async def limited_extract(url):
            async with semaphore:
                return await self.extract_from_url(url)

        results = await asyncio.gather(
            *[limited_extract(url) for url in urls],
            return_exceptions=True
        )

        for result in results:
            if isinstance(result, list):
                all_items.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Extraction failed: {result}")

        return all_items

    async def extract_from_file(
        self,
        filepath: str,
    ) -> list[MediaItem]:
        """
        Extract media from URLs listed in a file.

        Args:
            filepath: Path to file containing URLs (one per line)

        Returns:
            List of MediaItem objects
        """
        path = Path(filepath)
        if not path.exists():
            logger.error(f"File not found: {filepath}")
            return []

        urls = [
            line.strip()
            for line in path.read_text().splitlines()
            if line.strip() and not line.startswith("#")
        ]

        return await self.extract_from_urls(urls)

    def _extract_media(
        self,
        html: str,
        base_url: str,
        patterns: list,
        media_type: str,
    ) -> list[MediaItem]:
        """Extract media URLs using regex patterns."""
        items = []

        for pattern in patterns:
            for match in pattern.finditer(html):
                url = match.group(1)
                if not url:
                    continue

                # Resolve relative URLs
                full_url = urljoin(base_url, url)

                # Check extension
                ext = self._get_extension(full_url)
                if ext and ext.lower() not in self.config.allowed_extensions:
                    continue

                item = MediaItem(
                    url=full_url,
                    media_type=media_type,
                    filename=self._get_filename(full_url),
                    extension=ext,
                    source_page=base_url,
                    timestamp=datetime.utcnow().isoformat(),
                )
                items.append(item)

        return items

    def _extract_with_soup(
        self,
        html: str,
        base_url: str,
    ) -> list[MediaItem]:
        """Extract media using BeautifulSoup."""
        items = []
        soup = BeautifulSoup(html, "lxml")

        # Images
        if self.config.extract_images:
            for img in soup.find_all("img", src=True):
                url = urljoin(base_url, img["src"])
                ext = self._get_extension(url)

                item = MediaItem(
                    url=url,
                    media_type="image",
                    filename=self._get_filename(url),
                    extension=ext,
                    source_page=base_url,
                    alt_text=img.get("alt", ""),
                    timestamp=datetime.utcnow().isoformat(),
                )
                items.append(item)

        # Videos
        if self.config.extract_videos:
            for video in soup.find_all("video"):
                src = video.get("src") or ""
                source = video.find("source")
                if source:
                    src = source.get("src", src)

                if src:
                    url = urljoin(base_url, src)
                    item = MediaItem(
                        url=url,
                        media_type="video",
                        filename=self._get_filename(url),
                        extension=self._get_extension(url),
                        source_page=base_url,
                        timestamp=datetime.utcnow().isoformat(),
                    )
                    items.append(item)

        # Links to documents
        if self.config.extract_documents:
            doc_extensions = {".pdf", ".doc", ".docx", ".txt", ".rtf", ".xls", ".xlsx"}
            for a in soup.find_all("a", href=True):
                href = a["href"]
                ext = self._get_extension(href)
                if ext and ext.lower() in doc_extensions:
                    url = urljoin(base_url, href)
                    item = MediaItem(
                        url=url,
                        media_type="document",
                        filename=self._get_filename(url),
                        extension=ext,
                        source_page=base_url,
                        alt_text=a.get_text(strip=True),
                        timestamp=datetime.utcnow().isoformat(),
                    )
                    items.append(item)

        return items

    def _deduplicate(self, items: list[MediaItem]) -> list[MediaItem]:
        """Remove duplicate media items."""
        unique = []
        for item in items:
            if item.url not in self.seen_urls:
                self.seen_urls.add(item.url)
                unique.append(item)
        return unique

    async def _download_media(self, items: list[MediaItem]):
        """Download media items."""
        download_path = Path(self.config.download_path)
        download_path.mkdir(parents=True, exist_ok=True)

        for item in items:
            try:
                content = await self._fetch_binary(item.url)
                if not content:
                    continue

                # Check size
                if len(content) > self.config.max_file_size:
                    logger.warning(f"Skipping large file: {item.url}")
                    continue

                # Calculate hash
                item.file_hash = hashlib.md5(content).hexdigest()
                item.file_size = len(content)

                # Skip if duplicate hash
                if self.config.deduplicate and item.file_hash in self.seen_hashes:
                    continue
                self.seen_hashes.add(item.file_hash)

                # Save file
                filename = f"{item.file_hash[:8]}_{item.filename}"
                filepath = download_path / item.media_type / filename
                filepath.parent.mkdir(parents=True, exist_ok=True)
                filepath.write_bytes(content)

                item.downloaded = True
                item.local_path = str(filepath)

                # Face detection
                if self.config.detect_faces and item.media_type == "image":
                    item.faces_detected = await self._detect_faces(filepath)

                logger.debug(f"Downloaded: {item.url} -> {filepath}")

            except Exception as e:
                logger.error(f"Failed to download {item.url}: {e}")

    async def _fetch(self, url: str) -> Optional[str]:
        """Fetch URL content as text."""
        try:
            if self.tor_manager:
                return await self._fetch_via_tor(url)
            elif self.fetch_func:
                return await self.fetch_func(url, timeout=60)
            return None
        except Exception as e:
            logger.error(f"Fetch failed for {url}: {e}")
            return None

    async def _fetch_via_tor(self, url: str) -> Optional[str]:
        """Fetch URL content via TOR proxy."""
        try:
            import httpx

            await self.tor_manager.ensure_running()
            proxy_url = self.tor_manager.proxy_url

            async with httpx.AsyncClient(
                timeout=httpx.Timeout(60),
                proxy=proxy_url,
            ) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    return response.text
                return None
        except Exception as e:
            logger.error(f"TOR fetch failed for {url}: {e}")
            return None

    async def _fetch_binary(self, url: str) -> Optional[bytes]:
        """Fetch URL content as binary."""
        try:
            if self.tor_manager:
                return await self._fetch_binary_via_tor(url)
            elif self.fetch_func:
                # Assume fetch_func can return binary
                return await self.fetch_func(url, timeout=60, binary=True)
            return None
        except Exception as e:
            logger.error(f"Binary fetch failed for {url}: {e}")
            return None

    async def _fetch_binary_via_tor(self, url: str) -> Optional[bytes]:
        """Fetch binary content via TOR proxy."""
        try:
            import httpx

            await self.tor_manager.ensure_running()
            proxy_url = self.tor_manager.proxy_url

            async with httpx.AsyncClient(
                timeout=httpx.Timeout(60),
                proxy=proxy_url,
            ) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    return response.content
                return None
        except Exception as e:
            logger.error(f"TOR binary fetch failed for {url}: {e}")
            return None

    async def _binary_fetch(self, url: str, **kwargs) -> Optional[bytes]:
        """Binary fetch wrapper."""
        import httpx
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(url)
            return response.content if response.status_code == 200 else None

    async def _detect_faces(self, image_path: Path) -> int:
        """Detect faces in image using OpenCV."""
        try:
            if self._face_detector is None:
                import cv2
                cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
                self._face_detector = cv2.CascadeClassifier(cascade_path)

            import cv2
            image = cv2.imread(str(image_path))
            if image is None:
                return 0

            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            faces = self._face_detector.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30),
            )
            return len(faces)

        except ImportError:
            logger.warning("OpenCV not installed. pip install opencv-python")
            return 0
        except Exception as e:
            logger.error(f"Face detection failed: {e}")
            return 0

    @staticmethod
    def _get_extension(url: str) -> str:
        """Get file extension from URL."""
        parsed = urlparse(url)
        path = parsed.path
        if "." in path:
            return "." + path.rsplit(".", 1)[-1].lower()[:10]
        return ""

    @staticmethod
    def _get_filename(url: str) -> str:
        """Get filename from URL."""
        parsed = urlparse(url)
        path = parsed.path
        if "/" in path:
            filename = path.rsplit("/", 1)[-1]
            return filename[:100] if filename else "unknown"
        return "unknown"


# Convenience function
async def extract_media(
    url: str,
    tor_manager=None,
    fetch_func=None,
    download: bool = False,
) -> list[MediaItem]:
    """Quick media extraction from URL."""
    config = ExtractionConfig(download_media=download)
    extractor = MediaExtractor(
        tor_manager=tor_manager,
        fetch_func=fetch_func,
        config=config,
    )
    return await extractor.extract_from_url(url)

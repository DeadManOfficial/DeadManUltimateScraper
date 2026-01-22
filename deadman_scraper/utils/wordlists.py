"""
DEADMAN SCRAPER - SecLists Integration
=======================================
Wordlist loading from danielmiessler/SecLists for fuzzing, discovery, and OSINT.

Categories:
- Discovery/Web-Content: Path fuzzing, directory enumeration
- Fuzzing: SQLi, XSS, command injection payloads
- Passwords: Common credential lists
- Usernames: Username wordlists
- Payloads: Attack payloads
- Ai: AI-specific wordlists
"""

import logging
import os
from pathlib import Path
from typing import Iterator, Optional

logger = logging.getLogger("DeadMan.Wordlists")

# Default wordlists directory (relative to project root)
WORDLISTS_DIR = Path(__file__).parent.parent.parent / "wordlists"

# High-value wordlists for common use cases
RECOMMENDED_LISTS = {
    "discovery": [
        "Discovery/Web-Content/common.txt",
        "Discovery/Web-Content/directory-list-2.3-medium.txt",
        "Discovery/Web-Content/raft-large-directories.txt",
        "Discovery/Web-Content/api-endpoints.txt",
    ],
    "fuzzing_sqli": [
        "Fuzzing/SQLi/quick-SQLi.txt",
        "Fuzzing/SQLi/Generic-SQLi.txt",
    ],
    "fuzzing_xss": [
        "Fuzzing/XSS/XSS-Bypass-Strings-BruteLogic.txt",
        "Fuzzing/XSS/xss-payload-list.txt",
    ],
    "fuzzing_lfi": [
        "Fuzzing/LFI/LFI-Jhaddix.txt",
    ],
    "passwords": [
        "Passwords/Common-Credentials/10k-most-common.txt",
        "Passwords/Common-Credentials/common-passwords-win.txt",
    ],
    "usernames": [
        "Usernames/Names/names.txt",
        "Usernames/top-usernames-shortlist.txt",
    ],
    "ai": [
        "Ai/ai-api-endpoints.txt",
        "Ai/ai-model-names.txt",
    ],
}


class WordlistLoader:
    """Load and iterate over SecLists wordlists."""

    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialize wordlist loader.

        Args:
            base_dir: Base directory for wordlists (defaults to project wordlists/)
        """
        self.base_dir = Path(base_dir) if base_dir else WORDLISTS_DIR

        if not self.base_dir.exists():
            logger.warning(f"Wordlists directory not found: {self.base_dir}")

    def get_path(self, relative_path: str) -> Path:
        """Get full path to a wordlist file."""
        return self.base_dir / relative_path

    def exists(self, relative_path: str) -> bool:
        """Check if a wordlist exists."""
        return self.get_path(relative_path).exists()

    def load(self, relative_path: str) -> list[str]:
        """
        Load entire wordlist into memory.

        Args:
            relative_path: Path relative to wordlists directory

        Returns:
            List of lines from the wordlist
        """
        path = self.get_path(relative_path)

        if not path.exists():
            logger.error(f"Wordlist not found: {path}")
            return []

        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return [line.strip() for line in f if line.strip() and not line.startswith("#")]
        except Exception as e:
            logger.error(f"Error loading wordlist {path}: {e}")
            return []

    def iterate(self, relative_path: str) -> Iterator[str]:
        """
        Iterate over wordlist lines without loading entire file.

        Args:
            relative_path: Path relative to wordlists directory

        Yields:
            Lines from the wordlist
        """
        path = self.get_path(relative_path)

        if not path.exists():
            logger.error(f"Wordlist not found: {path}")
            return

        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        yield line
        except Exception as e:
            logger.error(f"Error iterating wordlist {path}: {e}")

    def load_category(self, category: str) -> list[str]:
        """
        Load all wordlists for a category.

        Args:
            category: One of: discovery, fuzzing_sqli, fuzzing_xss, fuzzing_lfi,
                     passwords, usernames, ai

        Returns:
            Combined list of all words from category wordlists
        """
        if category not in RECOMMENDED_LISTS:
            logger.error(f"Unknown category: {category}")
            return []

        words = set()
        for wordlist in RECOMMENDED_LISTS[category]:
            words.update(self.load(wordlist))

        return list(words)

    def list_available(self, directory: str = "") -> list[str]:
        """
        List available wordlist files.

        Args:
            directory: Subdirectory to list (e.g., "Fuzzing/SQLi")

        Returns:
            List of relative paths to wordlist files
        """
        search_dir = self.base_dir / directory if directory else self.base_dir

        if not search_dir.exists():
            return []

        files = []
        for path in search_dir.rglob("*.txt"):
            rel_path = path.relative_to(self.base_dir)
            files.append(str(rel_path))

        return sorted(files)

    def count_lines(self, relative_path: str) -> int:
        """Count lines in a wordlist without loading it."""
        path = self.get_path(relative_path)

        if not path.exists():
            return 0

        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return sum(1 for line in f if line.strip() and not line.startswith("#"))
        except Exception:
            return 0

    def stats(self) -> dict:
        """Get statistics about available wordlists."""
        stats = {
            "base_dir": str(self.base_dir),
            "exists": self.base_dir.exists(),
            "categories": {},
            "total_files": 0,
            "total_lines": 0,
        }

        if not self.base_dir.exists():
            return stats

        for category in ["Discovery", "Fuzzing", "Passwords", "Usernames", "Payloads", "Ai"]:
            cat_dir = self.base_dir / category
            if cat_dir.exists():
                files = list(cat_dir.rglob("*.txt"))
                stats["categories"][category] = {
                    "files": len(files),
                    "subdirs": len([d for d in cat_dir.iterdir() if d.is_dir()]),
                }
                stats["total_files"] += len(files)

        return stats


# Singleton for convenience
_loader: Optional[WordlistLoader] = None


def get_loader() -> WordlistLoader:
    """Get the global wordlist loader instance."""
    global _loader
    if _loader is None:
        _loader = WordlistLoader()
    return _loader


def load_wordlist(path: str) -> list[str]:
    """Convenience function to load a wordlist."""
    return get_loader().load(path)


def iterate_wordlist(path: str) -> Iterator[str]:
    """Convenience function to iterate a wordlist."""
    return get_loader().iterate(path)


def load_category(category: str) -> list[str]:
    """Convenience function to load a category of wordlists."""
    return get_loader().load_category(category)

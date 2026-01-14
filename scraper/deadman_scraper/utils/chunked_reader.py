"""
Chunked File Reader - Handle large scraped content files.

Solves the 256KB read limit by:
1. Reading files in chunks
2. Extracting specific sections (JSON fields, text blocks)
3. Streaming content for processing
"""

import json
import os
from collections.abc import Generator
from pathlib import Path
from typing import Any


class ChunkedReader:
    """Read large files in manageable chunks."""

    DEFAULT_CHUNK_SIZE = 100_000  # 100KB chunks

    def __init__(self, chunk_size: int = DEFAULT_CHUNK_SIZE):
        self.chunk_size = chunk_size

    def read_chunks(self, file_path: str) -> Generator[str, None, None]:
        """Yield file content in chunks."""
        with open(file_path, encoding='utf-8', errors='ignore') as f:
            while True:
                chunk = f.read(self.chunk_size)
                if not chunk:
                    break
                yield chunk

    def read_json_field(self, file_path: str, field: str) -> Any | None:
        """
        Extract a specific field from a large JSON file.
        Uses streaming to avoid loading entire file.
        """
        try:
            # For smaller files, just load directly
            file_size = os.path.getsize(file_path)
            if file_size < 256_000:
                with open(file_path, encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get(field)

            # For large files, read and find field
            content = ""
            for chunk in self.read_chunks(file_path):
                content += chunk
                # Try to parse if we have enough content
                if len(content) > 10000:
                    try:
                        data = json.loads(content)
                        return data.get(field)
                    except json.JSONDecodeError:
                        continue

            # Final attempt
            data = json.loads(content)
            return data.get(field)

        except Exception:
            return None

    def extract_urls_from_large_file(self, file_path: str) -> list[str]:
        """Extract all URLs from a large file without loading it all."""
        import re
        urls = set()
        url_pattern = re.compile(r'https?://[^\s<>"\')\]]+')

        for chunk in self.read_chunks(file_path):
            matches = url_pattern.findall(chunk)
            urls.update(matches)

        return list(urls)

    def get_file_summary(self, file_path: str) -> dict[str, Any]:
        """Get summary of a large file without reading it all."""
        path = Path(file_path)
        size = path.stat().st_size

        # Read first and last chunks for context
        first_chunk = ""
        last_chunk = ""

        with open(file_path, encoding='utf-8', errors='ignore') as f:
            first_chunk = f.read(5000)

            # Seek to end for last chunk
            if size > 10000:
                f.seek(max(0, size - 5000))
                last_chunk = f.read()

        return {
            "file": str(path),
            "size_bytes": size,
            "size_kb": round(size / 1024, 2),
            "size_mb": round(size / (1024 * 1024), 2),
            "first_500_chars": first_chunk[:500],
            "last_500_chars": last_chunk[-500:] if last_chunk else "",
            "is_json": file_path.endswith('.json'),
            "is_large": size > 256_000
        }

    def stream_json_array(self, file_path: str) -> Generator[dict, None, None]:
        """
        Stream items from a JSON array file one at a time.
        Memory efficient for large arrays.
        """
        import ijson  # Optional: pip install ijson

        try:
            with open(file_path, 'rb') as f:
                parser = ijson.items(f, 'item')
                for item in parser:
                    yield item
        except ImportError:
            # Fallback: load entire file
            with open(file_path, encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        yield item


class ContentExtractor:
    """Extract useful content from scraped data files."""

    def __init__(self):
        self.reader = ChunkedReader()

    def extract_from_scrape_result(self, file_path: str) -> dict[str, Any]:
        """
        Extract key information from a scrape result JSON.
        Handles large files by only reading needed fields.
        """
        result = {
            "url": self.reader.read_json_field(file_path, "url"),
            "status_code": self.reader.read_json_field(file_path, "status_code"),
            "content_length": None,
            "extracted_urls_count": 0,
            "has_content": False
        }

        # Get content summary without loading all
        content = self.reader.read_json_field(file_path, "content")
        if content:
            result["content_length"] = len(content) if isinstance(content, str) else None
            result["has_content"] = True

        # Count extracted URLs
        urls = self.reader.read_json_field(file_path, "extracted_urls")
        if urls and isinstance(urls, list):
            result["extracted_urls_count"] = len(urls)

        return result

    def batch_analyze(self, directory: str, pattern: str = "*.json") -> list[dict]:
        """Analyze all JSON files in a directory."""
        from glob import glob

        results = []
        files = glob(os.path.join(directory, "**", pattern), recursive=True)

        for f in files:
            try:
                summary = self.reader.get_file_summary(f)
                if summary["is_json"]:
                    extracted = self.extract_from_scrape_result(f)
                    summary.update(extracted)
                results.append(summary)
            except Exception as e:
                results.append({"file": f, "error": str(e)})

        return results


# CLI usage
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        reader = ChunkedReader()

        print(f"Analyzing: {file_path}")
        summary = reader.get_file_summary(file_path)

        for k, v in summary.items():
            if k not in ["first_500_chars", "last_500_chars"]:
                print(f"  {k}: {v}")

        if summary["is_large"]:
            print("\n  [Large file - extracting URLs...]")
            urls = reader.extract_urls_from_large_file(file_path)
            print(f"  Found {len(urls)} URLs")

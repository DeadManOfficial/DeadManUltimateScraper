"""
Content Extractor
=================
Strategy pattern for flexible content extraction.

Strategies:
- CSS: CSS selector based extraction
- XPath: XPath expression extraction
- Regex: Regular expression extraction
- LLM: AI-powered intelligent extraction
- Auto: Automatic best-fit strategy
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from bs4 import BeautifulSoup
from lxml import html as lxml_html

if TYPE_CHECKING:
    from deadman_scraper.ai.llm_router import FreeLLMRouter
    from deadman_scraper.core.config import ExtractionConfig

logger = logging.getLogger(__name__)


class Extractor:
    """
    Strategy pattern content extractor.

    Usage:
        extractor = Extractor(config)
        data = await extractor.extract(html, strategy="css", selector="h1")
        data = await extractor.extract(html, strategy="llm", prompt="Extract prices")
    """

    def __init__(self, config: ExtractionConfig):
        self.config = config

    async def extract(
        self,
        content: str,
        *,
        strategy: Literal["css", "xpath", "regex", "llm", "auto"] | None = None,
        url: str | None = None,
        selector: str | None = None,
        pattern: str | None = None,
        prompt: str | None = None,
        llm_router: FreeLLMRouter | None = None,
    ) -> dict[str, Any]:
        """
        Extract data from content using specified strategy.

        Args:
            content: HTML/text content
            strategy: Extraction strategy
            url: Source URL (for context)
            selector: CSS selector or XPath expression
            pattern: Regex pattern
            prompt: LLM extraction prompt
            llm_router: LLM router for AI extraction

        Returns:
            Extracted data dict
        """
        strategy = strategy or self.config.default_strategy

        if strategy == "auto":
            strategy = self._auto_detect_strategy(selector, pattern, prompt)

        if strategy == "css":
            return self._extract_css(content, selector or "body")
        elif strategy == "xpath":
            return self._extract_xpath(content, selector or "//body")
        elif strategy == "regex":
            return self._extract_regex(content, pattern or r".*")
        elif strategy == "llm":
            return await self._extract_llm(content, prompt or "Extract key information", llm_router)
        else:
            return {"error": f"Unknown strategy: {strategy}"}

    def _auto_detect_strategy(
        self, selector: str | None, pattern: str | None, prompt: str | None
    ) -> str:
        """Auto-detect best extraction strategy based on parameters."""
        if prompt:
            return "llm"
        if pattern:
            return "regex"
        if selector:
            if selector.startswith("/"):
                return "xpath"
            return "css"
        return "css"  # Default

    def _extract_css(self, content: str, selector: str) -> dict[str, Any]:
        """Extract using CSS selectors."""
        try:
            soup = BeautifulSoup(content, "lxml")

            # Handle multiple selectors
            selectors = [s.strip() for s in selector.split(",")]

            results = {}
            for sel in selectors:
                elements = soup.select(sel)
                key = sel.replace(" ", "_").replace(".", "_").replace("#", "_")

                if len(elements) == 0:
                    results[key] = None
                elif len(elements) == 1:
                    results[key] = self._element_to_dict(elements[0])
                else:
                    results[key] = [self._element_to_dict(el) for el in elements]

            return {
                "strategy": "css",
                "selector": selector,
                "results": results,
            }

        except Exception as e:
            logger.error(f"CSS extraction failed: {e}")
            return {"error": str(e)}

    def _extract_xpath(self, content: str, expression: str) -> dict[str, Any]:
        """Extract using XPath expressions."""
        try:
            tree = lxml_html.fromstring(content)
            elements = tree.xpath(expression)

            results = []
            for el in elements:
                if isinstance(el, str):
                    results.append(el)
                else:
                    results.append({
                        "tag": el.tag,
                        "text": el.text_content().strip() if hasattr(el, "text_content") else str(el),
                        "attrib": dict(el.attrib) if hasattr(el, "attrib") else {},
                    })

            return {
                "strategy": "xpath",
                "expression": expression,
                "results": results if len(results) != 1 else results[0],
            }

        except Exception as e:
            logger.error(f"XPath extraction failed: {e}")
            return {"error": str(e)}

    def _extract_regex(self, content: str, pattern: str) -> dict[str, Any]:
        """Extract using regular expressions."""
        try:
            matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)

            return {
                "strategy": "regex",
                "pattern": pattern,
                "match_count": len(matches),
                "results": matches,
            }

        except Exception as e:
            logger.error(f"Regex extraction failed: {e}")
            return {"error": str(e)}

    async def _extract_llm(
        self, content: str, prompt: str, llm_router: FreeLLMRouter | None
    ) -> dict[str, Any]:
        """Extract using LLM intelligence."""
        if not llm_router:
            return {"error": "LLM router not provided"}

        try:
            # Clean content for LLM
            soup = BeautifulSoup(content, "lxml")

            # Remove scripts and styles
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()

            text = soup.get_text(separator="\n", strip=True)

            # Truncate if too long
            if len(text) > 8000:
                text = text[:8000] + "..."

            full_prompt = f"""{prompt}

Content:
{text}

Extract the requested information and return as JSON if possible."""

            from deadman_scraper.ai.llm_router import TaskType

            response = await llm_router.complete(
                full_prompt,
                task_type=TaskType.ENTITY_EXTRACTION,
                max_tokens=1000,
                temperature=0.3,
            )

            if response.success:
                # Try to parse as JSON
                import json

                result_content = response.content.strip()
                try:
                    if "```" in result_content:
                        # Extract JSON from code block
                        result_content = result_content.split("```")[1]
                        if result_content.startswith("json"):
                            result_content = result_content[4:]
                    parsed = json.loads(result_content)
                    return {
                        "strategy": "llm",
                        "prompt": prompt,
                        "provider": response.provider,
                        "results": parsed,
                    }
                except json.JSONDecodeError:
                    pass

                return {
                    "strategy": "llm",
                    "prompt": prompt,
                    "provider": response.provider,
                    "results": response.content,
                }
            else:
                return {"error": response.error}

        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return {"error": str(e)}

    def _element_to_dict(self, element) -> dict[str, Any]:
        """Convert BeautifulSoup element to dict."""
        return {
            "tag": element.name,
            "text": element.get_text(strip=True),
            "html": str(element),
            "attrs": dict(element.attrs),
        }

    def extract_links(self, content: str, base_url: str | None = None) -> list[dict[str, str]]:
        """Extract all links from content."""
        from urllib.parse import urljoin

        soup = BeautifulSoup(content, "lxml")
        links = []

        for a in soup.find_all("a", href=True):
            href = a["href"]
            if base_url:
                href = urljoin(base_url, href)

            links.append({
                "url": href,
                "text": a.get_text(strip=True),
                "title": a.get("title", ""),
            })

        return links

    def extract_metadata(self, content: str) -> dict[str, str]:
        """Extract page metadata (title, description, keywords, etc.)."""
        soup = BeautifulSoup(content, "lxml")

        metadata = {
            "title": "",
            "description": "",
            "keywords": "",
            "author": "",
            "og_title": "",
            "og_description": "",
            "og_image": "",
        }

        # Title
        if soup.title:
            metadata["title"] = soup.title.string or ""

        # Meta tags
        for meta in soup.find_all("meta"):
            name = meta.get("name", "").lower()
            prop = meta.get("property", "").lower()
            content = meta.get("content", "")

            if name == "description":
                metadata["description"] = content
            elif name == "keywords":
                metadata["keywords"] = content
            elif name == "author":
                metadata["author"] = content
            elif prop == "og:title":
                metadata["og_title"] = content
            elif prop == "og:description":
                metadata["og_description"] = content
            elif prop == "og:image":
                metadata["og_image"] = content

        return metadata

    def extract_assets(self, content: str, base_url: str | None = None) -> dict[str, list[dict[str, str]]]:
        """
        Extract media and document assets from content.
        NASA Standard: Exhaustive asset identification.
        """
        from urllib.parse import urljoin
        soup = BeautifulSoup(content, "lxml")

        assets = {
            "images": [],
            "documents": [],
            "scripts": [],
            "styles": []
        }

        # Images
        for img in soup.find_all("img", src=True):
            src = img["src"]
            if base_url:
                src = urljoin(base_url, src)
            assets["images"].append({
                "url": src,
                "alt": img.get("alt", ""),
                "title": img.get("title", "")
            })

        # Documents (PDF, Docx, etc.)
        doc_exts = (".pdf", ".docx", ".xlsx", ".csv", ".zip")
        for a in soup.find_all("a", href=True):
            href = a["href"].lower()
            if href.endswith(doc_exts):
                full_url = urljoin(base_url, href) if base_url else href
                assets["documents"].append({
                    "url": full_url,
                    "text": a.get_text(strip=True),
                    "ext": Path(href).suffix
                })

        return assets

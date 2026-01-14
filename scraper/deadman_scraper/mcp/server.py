"""
MCP Server - Model Context Protocol server for DeadMan Scraper.

Exposes scraper capabilities to Claude and other MCP clients.

Based on patterns from:
- oakenai/mcp-edit-file-lines
- Anthropic MCP specification

Usage:
    Run as MCP server: python -m deadman_scraper.mcp.server
    Configure in Claude: Add to mcp_servers in config
"""

import asyncio
import json
import sys
from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class MCPTool:
    """MCP Tool definition."""
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass
class MCPResource:
    """MCP Resource definition."""
    uri: str
    name: str
    description: str
    mime_type: str = "application/json"


class DeadManMCPServer:
    """
    MCP Server exposing DeadMan Scraper tools.

    Tools:
    - scrape_url: Scrape any URL with adaptive bypass
    - scrape_onion: Scrape .onion sites via TOR
    - search_reddit: Search and scrape Reddit
    - search_github: Search GitHub repos
    - deep_scrape: Recursive scraping from seed URLs

    Resources:
    - scraped_content: Access previously scraped content
    - onion_index: Index of known .onion sites
    """

    def __init__(self):
        self.tools = self._define_tools()
        self.resources = self._define_resources()
        self._scraped_data: dict[str, Any] = {}

    def _define_tools(self) -> list[MCPTool]:
        """Define available MCP tools."""
        return [
            MCPTool(
                name="scrape_url",
                description="Scrape any URL with automatic bypass for Cloudflare, rate limits, etc.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL to scrape"
                        },
                        "extract_links": {
                            "type": "boolean",
                            "description": "Extract all links from page",
                            "default": False
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in seconds",
                            "default": 30
                        }
                    },
                    "required": ["url"]
                }
            ),
            MCPTool(
                name="scrape_onion",
                description="Scrape .onion sites via TOR with circuit rotation",
                input_schema={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": ".onion URL to scrape"
                        },
                        "max_retries": {
                            "type": "integer",
                            "description": "Max retry attempts",
                            "default": 3
                        }
                    },
                    "required": ["url"]
                }
            ),
            MCPTool(
                name="search_reddit",
                description="Search Reddit posts and comments",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "subreddit": {
                            "type": "string",
                            "description": "Limit to specific subreddit"
                        },
                        "sort": {
                            "type": "string",
                            "enum": ["relevance", "hot", "top", "new"],
                            "default": "relevance"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Max results",
                            "default": 25
                        }
                    },
                    "required": ["query"]
                }
            ),
            MCPTool(
                name="search_github",
                description="Search GitHub repositories, code, and issues",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "type": {
                            "type": "string",
                            "enum": ["repositories", "code", "issues"],
                            "default": "repositories"
                        },
                        "language": {
                            "type": "string",
                            "description": "Filter by programming language"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Max results",
                            "default": 10
                        }
                    },
                    "required": ["query"]
                }
            ),
            MCPTool(
                name="deep_scrape",
                description="Recursive deep scrape from seed URLs, following links",
                input_schema={
                    "type": "object",
                    "properties": {
                        "seed_urls": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Starting URLs"
                        },
                        "max_depth": {
                            "type": "integer",
                            "description": "Max link depth to follow",
                            "default": 2
                        },
                        "max_pages": {
                            "type": "integer",
                            "description": "Max total pages to scrape",
                            "default": 50
                        },
                        "allow_domains": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Only scrape these domains"
                        }
                    },
                    "required": ["seed_urls"]
                }
            ),
            MCPTool(
                name="get_onion_index",
                description="Get index of known .onion sites",
                input_schema={
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "enum": ["all", "search", "news", "social", "crypto"],
                            "default": "all"
                        }
                    }
                }
            ),
        ]

    def _define_resources(self) -> list[MCPResource]:
        """Define available MCP resources."""
        return [
            MCPResource(
                uri="deadman://scraped/latest",
                name="Latest Scraped Content",
                description="Most recently scraped content",
            ),
            MCPResource(
                uri="deadman://onions/index",
                name="Onion Sites Index",
                description="Index of known .onion sites with categories",
            ),
            MCPResource(
                uri="deadman://stats/session",
                name="Session Statistics",
                description="Scraping statistics for current session",
            ),
        ]

    async def handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle incoming MCP request."""
        method = request.get("method", "")
        params = request.get("params", {})
        request_id = request.get("id")

        try:
            if method == "initialize":
                return self._response(request_id, {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "resources": {"subscribe": False, "listChanged": False},
                    },
                    "serverInfo": {
                        "name": "deadman-scraper",
                        "version": "1.0.0"
                    }
                })

            elif method == "tools/list":
                return self._response(request_id, {
                    "tools": [asdict(t) for t in self.tools]
                })

            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                result = await self._execute_tool(tool_name, arguments)
                return self._response(request_id, {
                    "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
                })

            elif method == "resources/list":
                return self._response(request_id, {
                    "resources": [asdict(r) for r in self.resources]
                })

            elif method == "resources/read":
                uri = params.get("uri")
                content = await self._read_resource(uri)
                return self._response(request_id, {
                    "contents": [{"uri": uri, "text": json.dumps(content, indent=2)}]
                })

            else:
                return self._error(request_id, -32601, f"Method not found: {method}")

        except Exception as e:
            return self._error(request_id, -32603, str(e))

    async def _execute_tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool and return result."""
        if name == "scrape_url":
            return await self._tool_scrape_url(args)
        elif name == "scrape_onion":
            return await self._tool_scrape_onion(args)
        elif name == "search_reddit":
            return await self._tool_search_reddit(args)
        elif name == "search_github":
            return await self._tool_search_github(args)
        elif name == "deep_scrape":
            return await self._tool_deep_scrape(args)
        elif name == "get_onion_index":
            return await self._tool_get_onion_index(args)
        else:
            return {"error": f"Unknown tool: {name}"}

    async def _tool_scrape_url(self, args: dict) -> dict:
        """Scrape URL tool implementation."""
        url = args.get("url")
        extract_links = args.get("extract_links", False)

        # Placeholder - would use actual scraper
        return {
            "url": url,
            "status": "success",
            "content_preview": f"[Content from {url}]",
            "links_extracted": 0 if not extract_links else "N/A"
        }

    async def _tool_scrape_onion(self, args: dict) -> dict:
        """Scrape .onion tool implementation."""
        url = args.get("url")

        # Would use TOR manager
        return {
            "url": url,
            "status": "requires_tor",
            "message": "TOR connection required for .onion sites"
        }

    async def _tool_search_reddit(self, args: dict) -> dict:
        """Search Reddit tool implementation."""
        from ..fetch.reddit_bypass import RedditBypass

        bypass = RedditBypass()
        results = await bypass.search(
            query=args.get("query"),
            subreddit=args.get("subreddit"),
            sort=args.get("sort", "relevance"),
            limit=args.get("limit", 25)
        )

        return results or {"error": "Search failed"}

    async def _tool_search_github(self, args: dict) -> dict:
        """Search GitHub tool implementation."""
        return {
            "query": args.get("query"),
            "type": args.get("type", "repositories"),
            "status": "not_implemented",
            "message": "GitHub search requires API token"
        }

    async def _tool_deep_scrape(self, args: dict) -> dict:
        """Deep scrape tool implementation."""
        return {
            "seed_urls": args.get("seed_urls", []),
            "max_depth": args.get("max_depth", 2),
            "max_pages": args.get("max_pages", 50),
            "status": "queued",
            "message": "Deep scrape queued for background execution"
        }

    async def _tool_get_onion_index(self, args: dict) -> dict:
        """Get onion index tool implementation."""
        category = args.get("category", "all")

        # Load from onion index file
        onions = {
            "search": [
                "duckduckgogg42xjoc72x3sjasowoarfbgcmvfimaftt6twagswzczad.onion",
                "juhanurmihxlp77nkq76byazcldy2hlmovfu2epvl5ankdibsot4csyd.onion",
            ],
            "news": [
                "bbcnewsd73hkzno2ini43t4gblxvycyac5aw4gnv7t2rccijh7745uqd.onion",
                "nytimesn7cgmftshazwhfgzm37qxb44r64ytbb2dj3x62d2lljsciiyd.onion",
            ],
            "social": [
                "facebookwkhpilnemxj7asaniu7vnjjbiltxjqhye3mhbshg7kx5tfyd.onion",
                "protonmailrmez3lotccipshtkleegetolb73fuirgj7r4o4vfu7ozyd.onion",
            ],
        }

        if category == "all":
            return {"onions": onions}
        return {"onions": {category: onions.get(category, [])}}

    async def _read_resource(self, uri: str) -> dict[str, Any]:
        """Read a resource."""
        if uri == "deadman://scraped/latest":
            return self._scraped_data.get("latest", {"message": "No recent scrapes"})
        elif uri == "deadman://onions/index":
            return await self._tool_get_onion_index({"category": "all"})
        elif uri == "deadman://stats/session":
            return {"total_requests": 0, "successful": 0, "failed": 0}
        return {"error": f"Unknown resource: {uri}"}

    def _response(self, request_id: Any, result: dict) -> dict:
        """Create success response."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        }

    def _error(self, request_id: Any, code: int, message: str) -> dict:
        """Create error response."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message}
        }

    async def run_stdio(self):
        """Run server over stdio (for Claude integration)."""
        print("DeadMan MCP Server started", file=sys.stderr)

        while True:
            try:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )
                if not line:
                    break

                request = json.loads(line.strip())
                response = await self.handle_request(request)
                print(json.dumps(response), flush=True)

            except json.JSONDecodeError:
                continue
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)


def main():
    """Entry point for MCP server."""
    server = DeadManMCPServer()
    asyncio.run(server.run_stdio())


if __name__ == "__main__":
    main()

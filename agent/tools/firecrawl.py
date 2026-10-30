import os
from typing import Any

import httpx
from dotenv import load_dotenv

from agent.schemas import ToolResult
from agent.tools.base import run_tool


load_dotenv()

FIRECRAWL_URL = "https://api.firecrawl.dev/v1"


def _headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def search_firecrawl(query: str, max_results: int = 5) -> ToolResult:
    def operation() -> list[dict[str, Any]]:
        api_key = os.getenv("FIRECRAWL_API_KEY")
        if not api_key:
            return []

        response = httpx.post(
            f"{FIRECRAWL_URL}/search",
            headers=_headers(api_key),
            json={"query": query, "limit": max_results},
            timeout=15.0,
        )
        response.raise_for_status()
        payload = response.json()

        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            raise ValueError("Firecrawl returned a malformed search response")

        results: list[dict[str, Any]] = []
        for result in payload["data"]:
            if not isinstance(result, dict):
                continue

            title = result.get("title")
            url = result.get("url")
            content = result.get("description") or result.get("markdown")
            if title and url and content:
                results.append(
                    {
                        "title": str(title),
                        "url": str(url),
                        "snippet": str(content),
                        "source_provider": "firecrawl",
                    }
                )

        return results

    return run_tool("firecrawl_search", operation)


def scrape_firecrawl(url: str) -> ToolResult:
    def operation() -> list[dict[str, Any]]:
        api_key = os.getenv("FIRECRAWL_API_KEY")
        if not api_key:
            return []

        response = httpx.post(
            f"{FIRECRAWL_URL}/scrape",
            headers=_headers(api_key),
            json={"url": url, "formats": ["markdown"]},
            timeout=20.0,
        )
        response.raise_for_status()
        payload = response.json()

        if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
            raise ValueError("Firecrawl returned a malformed scrape response")

        data = payload["data"]
        markdown = data.get("markdown")
        metadata = data.get("metadata") or {}
        title = metadata.get("title") if isinstance(metadata, dict) else None
        if not markdown:
            return []

        return [
            {
                "title": str(title or url),
                "url": url,
                "content": str(markdown),
                "source_provider": "firecrawl",
            }
        ]

    return run_tool("firecrawl_scrape", operation)

from typing import Any

import httpx
import trafilatura

from agent.schemas import ToolResult
from agent.tools.base import run_tool


def fetch_page(url: str) -> ToolResult:
    def operation() -> list[dict[str, Any]]:
        with httpx.Client(
            timeout=10.0,
            follow_redirects=True,
            headers={
                "User-Agent": "PredixionAI-Research-Agent/1.0"
            },
        ) as client:
            response = client.get(url)
            response.raise_for_status()

        content_type = response.headers.get("content-type", "").lower()

        if "text/html" not in content_type:
            return []

        if len(response.content) > 1_000_000:
            raise ValueError("Page is larger than the 1 MB safety limit")

        text = trafilatura.extract(response.text)

        if not text:
            return []

        return [
            {
                "title": url,
                "url": url,
                "content": text[:12_000],
            }
        ]

    return run_tool("fetch_page", operation)
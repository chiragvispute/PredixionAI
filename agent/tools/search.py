import os
from typing import Any

import httpx
from ddgs import DDGS
from dotenv import load_dotenv

from agent.schemas import ToolResult
from agent.tools.base import run_tool


load_dotenv()


def search_web(query: str, max_results: int = 5) -> ToolResult:
    def operation() -> list[dict[str, Any]]:
        tavily_key = os.getenv("TAVILY_API")

        if tavily_key:
            response = httpx.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": tavily_key,
                    "query": query,
                    "max_results": max_results,
                    "search_depth": "basic",
                    "include_answer": False,
                },
                timeout=10.0,
            )
            response.raise_for_status()
            payload = response.json()

            if not isinstance(payload, dict):
                raise ValueError("Tavily returned a malformed response")

            results: list[dict[str, Any]] = []

            for result in payload.get("results", []):
                if not isinstance(result, dict):
                    continue

                title = result.get("title")
                url = result.get("url")
                content = result.get("content")

                if title and url and content:
                    results.append(
                        {
                            "title": str(title),
                            "url": str(url),
                            "snippet": str(content),
                        }
                    )

            return results

        results: list[dict[str, Any]] = []

        with DDGS() as search_client:
            search_results = search_client.text(
                query,
                max_results=max_results,
            )

            for result in search_results:
                title = result.get("title")
                url = result.get("href") or result.get("url")
                snippet = result.get("body") or result.get("snippet")

                if title and url and snippet:
                    results.append(
                        {
                            "title": str(title),
                            "url": str(url),
                            "snippet": str(snippet),
                        }
                    )

        return results

    return run_tool("web_search", operation)
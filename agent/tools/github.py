import re
from typing import Any

import httpx
from dotenv import load_dotenv
from urllib.parse import quote_plus

from agent.schemas import ToolResult
from agent.tools.base import run_tool


load_dotenv()


def fetch_github_repo(repository: str) -> ToolResult:
    def operation() -> list[dict[str, Any]]:
        repository_query = repository.strip()
        if "/" in repository_query and " " not in repository_query:
            endpoint = (
                "https://api.github.com/repos/"
                f"{repository_query}"
            )
        else:
            search_query = " ".join(
                word
                for word in re.findall(r"[A-Za-z0-9+#.-]+", repository_query)
                if len(word) > 2
            )
            endpoint = (
                "https://api.github.com/search/repositories"
                f"?q={quote_plus(search_query)}+in:name,description,readme"
                "&sort=stars&order=desc&per_page=1"
            )

        response = httpx.get(
            endpoint,
            timeout=10.0,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "PredixionAI-Research-Agent",
            },
        )
        response.raise_for_status()

        data = response.json()

        if "/search/repositories" in endpoint:
            matches = data.get("items", [])
            if not matches:
                return []
            data = matches[0]

        if not isinstance(data, dict) or "html_url" not in data:
            raise ValueError("GitHub returned a malformed repository response")

        query_terms = {
            word.lower()
            for word in re.findall(r"[A-Za-z0-9+#.-]+", repository_query)
            if len(word) > 2
        }
        repository_text = " ".join(
            [
                str(data.get("full_name", "")),
                str(data.get("description", "")),
            ]
        ).lower()
        if (
            "/search/repositories" in endpoint
            and query_terms
            and not any(term in repository_text for term in query_terms)
        ):
            return []

        return [
            {
                "title": data.get("full_name", repository),
                "url": data["html_url"],
                "content": (
                    f"Description: {data.get('description') or 'Not provided'}\n"
                    f"Stars: {data.get('stargazers_count', 0)}\n"
                    f"Forks: {data.get('forks_count', 0)}\n"
                    f"Open issues: {data.get('open_issues_count', 0)}\n"
                    f"License: "
                    f"{(data.get('license') or {}).get('spdx_id', 'Not provided')}\n"
                    f"Last updated: {data.get('updated_at', 'Not provided')}"
                ),
            }
        ]

    return run_tool("github_repo", operation)
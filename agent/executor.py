import os

from agent.schemas import Plan, ToolResult
from agent.tools.fetch import fetch_page
from agent.tools.firecrawl import scrape_firecrawl, search_firecrawl
from agent.tools.github import fetch_github_repo
from agent.tools.search import search_web


def execute_plan(plan: Plan) -> tuple[list[dict], list[dict]]:
    collected_items: list[dict] = []
    tool_events: list[dict] = []

    for subtask in plan.subtasks:
        if subtask.tool == "web_search":
            result = search_web(subtask.query)
            tool_events.append(
                {
                    "subtask_id": subtask.id,
                    "tool": subtask.tool,
                    "status": result.status,
                    "latency_ms": result.latency_ms,
                    "error": result.error,
                    "items": len(result.data),
                }
            )

            if result.status == "ok":
                collected_items.extend(result.data)

                for search_result in result.data[:3]:
                    url = search_result.get("url")

                    if not url:
                        continue

                    if os.getenv("FIRECRAWL_API_KEY"):
                        page_tool_name = "firecrawl_scrape"
                        page_result = scrape_firecrawl(url)
                        if page_result.status != "ok":
                            page_tool_name = "fetch_page_fallback"
                            page_result = fetch_page(url)
                    else:
                        page_tool_name = "fetch_page"
                        page_result = fetch_page(url)

                    tool_events.append(
                        {
                            "subtask_id": subtask.id,
                            "tool": page_tool_name,
                            "status": page_result.status,
                            "latency_ms": page_result.latency_ms,
                            "error": page_result.error,
                            "items": len(page_result.data),
                        }
                    )

                    if page_result.status == "ok":
                        collected_items.extend(page_result.data)

        elif subtask.tool == "fetch_page":
            result = fetch_page(subtask.query)
            tool_events.append(
                {
                    "subtask_id": subtask.id,
                    "tool": subtask.tool,
                    "status": result.status,
                    "latency_ms": result.latency_ms,
                    "error": result.error,
                    "items": len(result.data),
                }
            )

            if result.status == "ok":
                collected_items.extend(result.data)

        elif subtask.tool == "firecrawl_search":
            result = search_firecrawl(subtask.query)
            tool_events.append(
                {
                    "subtask_id": subtask.id,
                    "tool": subtask.tool,
                    "status": result.status,
                    "latency_ms": result.latency_ms,
                    "error": result.error,
                    "items": len(result.data),
                }
            )
            if result.status == "ok":
                collected_items.extend(result.data)

        elif subtask.tool == "firecrawl_scrape":
            result = scrape_firecrawl(subtask.query)
            tool_events.append(
                {
                    "subtask_id": subtask.id,
                    "tool": subtask.tool,
                    "status": result.status,
                    "latency_ms": result.latency_ms,
                    "error": result.error,
                    "items": len(result.data),
                }
            )
            if result.status == "ok":
                collected_items.extend(result.data)

        elif subtask.tool == "github_repo":
            result = fetch_github_repo(subtask.query)
            tool_events.append(
                {
                    "subtask_id": subtask.id,
                    "tool": subtask.tool,
                    "status": result.status,
                    "latency_ms": result.latency_ms,
                    "error": result.error,
                    "items": len(result.data),
                }
            )

            if result.status == "ok":
                collected_items.extend(result.data)

        else:
            unsupported_result = ToolResult(
                status="error",
                error=f"Unsupported tool: {subtask.tool}",
            )

            tool_events.append(
                {
                    "subtask_id": subtask.id,
                    "tool": subtask.tool,
                    "status": unsupported_result.status,
                    "latency_ms": unsupported_result.latency_ms,
                    "error": unsupported_result.error,
                    "items": 0,
                }
            )

    return collected_items, tool_events
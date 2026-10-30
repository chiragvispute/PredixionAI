import time
from collections.abc import Callable
from typing import Any

from agent.schemas import ToolResult


def run_tool(
    tool_name: str,
    operation: Callable[[], list[dict[str, Any]]],
    retries: int = 2,
) -> ToolResult:
    last_error = "Unknown tool error"
    start_time = time.perf_counter()

    for attempt in range(retries + 1):
        try:
            data = operation()
            latency_ms = int((time.perf_counter() - start_time) * 1000)

            if not data:
                return ToolResult(
                    status="empty",
                    data=[],
                    error=f"{tool_name} returned no results",
                    latency_ms=latency_ms,
                )

            return ToolResult(
                status="ok",
                data=data,
                latency_ms=latency_ms,
            )

        except TimeoutError as error:
            last_error = str(error) or f"{tool_name} timed out"
            if attempt == retries:
                latency_ms = int((time.perf_counter() - start_time) * 1000)
                return ToolResult(
                    status="timeout",
                    data=[],
                    error=last_error,
                    latency_ms=latency_ms,
                )

        except Exception as error:
            last_error = str(error) or f"{tool_name} failed"
            if attempt == retries:
                latency_ms = int((time.perf_counter() - start_time) * 1000)
                return ToolResult(
                    status="error",
                    data=[],
                    error=last_error,
                    latency_ms=latency_ms,
                )

        time.sleep(2**attempt)

    latency_ms = int((time.perf_counter() - start_time) * 1000)
    return ToolResult(
        status="error",
        data=[],
        error=last_error,
        latency_ms=latency_ms,
    )
from typing import Literal

from pydantic import BaseModel, Field


class SubTask(BaseModel):
    id: str
    goal: str
    tool: Literal["web_search", "fetch_page", "firecrawl_search", "firecrawl_scrape", "github_repo"]
    query: str


class Plan(BaseModel):
    question: str
    assumptions: list[str] = Field(default_factory=list)
    subtasks: list[SubTask] = Field(min_length=1, max_length=6)


class ToolResult(BaseModel):
    status: Literal["ok", "empty", "error", "timeout"]
    data: list[dict] = Field(default_factory=list)
    error: str | None = None
    latency_ms: int = 0


class Evidence(BaseModel):
    id: str
    url: str
    title: str
    content: str
    score: float = 0.0
    flags: list[str] = Field(default_factory=list)


class Finding(BaseModel):
    claim: str
    evidence_ids: list[str] = Field(min_length=1)


class FinalAnswer(BaseModel):
    user_question: str
    short_answer: str
    key_findings: list[Finding]
    sources_used: list[str]
    confidence: Literal["high", "medium", "low"]
    limitations_or_assumptions: list[str]
    suggested_next_steps: list[str]
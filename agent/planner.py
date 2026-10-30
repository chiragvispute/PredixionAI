import json
import os

from dotenv import load_dotenv
from openai import APIError, OpenAI
from pydantic import ValidationError

from agent.schemas import Plan, SubTask


load_dotenv()

DEFAULT_LLM_BASE_URL = "https://api.mistral.ai/v1"
DEFAULT_LLM_MODEL = "ministral-3b-latest"


def fallback_plan(question: str) -> Plan:
    subtasks = [
        SubTask(
            id="search-question",
            goal="Find reliable information relevant to the research question.",
            tool="web_search",
            query=question,
        )
    ]

    if _is_software_question(question):
        subtasks.append(
            SubTask(
                id="github-repositories",
                goal="Find relevant public software repositories and metadata.",
                tool="github_repo",
                query=_github_query(question),
            )
        )

    return Plan(
        question=question,
        assumptions=["The answer will use publicly available web sources."],
        subtasks=subtasks,
    )


def _is_software_question(question: str) -> bool:
    software_terms = {
        "api",
        "database",
        "framework",
        "github",
        "library",
        "open-source",
        "package",
        "project",
        "repository",
        "software",
        "tool",
        "vector",
    }
    words = set(question.lower().replace("/", " ").split())
    return bool(words & software_terms)


def _github_query(question: str) -> str:
    stop_words = {
        "about",
        "and",
        "are",
        "building",
        "compare",
        "for",
        "from",
        "find",
        "how",
        "in",
        "into",
        "of",
        "on",
        "research",
        "the",
        "their",
        "these",
        "this",
        "using",
        "what",
        "which",
        "with",
    }
    words = [
        word
        for word in question.lower().replace("/", " ").split()
        if word.strip(".,?!:;()") not in stop_words
    ]
    return " ".join(words[:8]) or question


def _augment_plan(plan: Plan) -> Plan:
    if _is_software_question(plan.question) and not any(
        task.tool == "github_repo" for task in plan.subtasks
    ) and not _has_entity_verification_tasks(plan):
        return plan.model_copy(
            update={
                "subtasks": [
                    *plan.subtasks,
                    SubTask(
                        id="github-repositories",
                        goal="Find relevant public software repositories and metadata.",
                        tool="github_repo",
                        query=_github_query(plan.question),
                    ),
                ]
            }
        )
    return plan


def _has_entity_verification_tasks(plan: Plan) -> bool:
    verification_terms = ("verify", "official", "primary source", "features")
    return sum(
        any(term in task.goal.lower() for term in verification_terms)
        for task in plan.subtasks
    ) >= 2


def create_plan(question: str) -> Plan:
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL", DEFAULT_LLM_BASE_URL)
    model = os.getenv("LLM_MODEL", DEFAULT_LLM_MODEL)

    if not api_key:
        return fallback_plan(question)

    client = OpenAI(
        api_key=api_key,
        base_url=base_url or None,
    )

    prompt = f"""
Create a research plan for this question:

{question}

Available tools:
- web_search: discover relevant sources
- fetch_page: retrieve detailed content from a specific URL
- firecrawl_search: discover sources with robust web search
- firecrawl_scrape: retrieve readable content from a specific URL
- github_repo: retrieve repository facts when the question concerns software projects

For github_repo, query must be an exact "owner/repository" or concise
repository search keywords, never the full user question.
Every task must be executable independently from its query value. Never use
placeholders such as "URL from subtask 1" or refer to another task's output.
For list requests, create separate discovery and verification searches when
possible. For requests with multiple dimensions (for example pros and cons,
or company identity and positioning), create at least one subtask per
dimension. If the evidence may be insufficient, plan a search for authoritative
or official sources rather than assuming the requested facts exist.
For comparisons or list requests, name the entities you intend to compare in
separate subtasks whenever the evidence or question identifies them. Each
entity-specific task must verify the entity's requested attributes and gather
positioning or product evidence. Do not use a single broad search as the only
research task for a multi-entity request.

Return only valid JSON with this shape:
{{
  "question": "...",
  "assumptions": ["..."],
  "subtasks": [
    {{
      "id": "...",
      "goal": "...",
      "tool": "web_search",
      "query": "..."
    }}
  ]
}}

Use one to six subtasks. Do not invent URLs.
"""

    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                model=model,
                temperature=0,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You create concise, valid research plans. "
                            "Return JSON only."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            )

            content = response.choices[0].message.content

            if not content:
                raise ValueError("The planner returned an empty response")

            parsed = json.loads(content)
            return _augment_plan(Plan.model_validate(parsed))

        except (APIError, json.JSONDecodeError, ValidationError, ValueError):
            if attempt == 1:
                return fallback_plan(question)

    return fallback_plan(question)
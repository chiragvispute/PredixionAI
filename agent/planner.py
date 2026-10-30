import json
import os

from dotenv import load_dotenv
from openai import APIError, OpenAI
from pydantic import ValidationError

from agent.schemas import Plan, SubTask


load_dotenv()

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_GROQ_MODEL = "openai/gpt-oss-20b"


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
                query=question,
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


def _augment_plan(plan: Plan) -> Plan:
    if _is_software_question(plan.question) and not any(
        task.tool == "github_repo" for task in plan.subtasks
    ):
        return plan.model_copy(
            update={
                "subtasks": [
                    *plan.subtasks,
                    SubTask(
                        id="github-repositories",
                        goal="Find relevant public software repositories and metadata.",
                        tool="github_repo",
                        query=plan.question,
                    ),
                ]
            }
        )
    return plan


def create_plan(question: str) -> Plan:
    api_key = os.getenv("LLM_API_KEY")
    base_url = GROQ_BASE_URL
    model = DEFAULT_GROQ_MODEL

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
- github_repo: retrieve repository facts when the question concerns software projects

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
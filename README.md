# AI Research Agent

A small, production-oriented research agent that turns a research question
into a visible plan, selects information-gathering tools, filters retrieved
evidence, and produces a structured answer with citations, confidence, and
limitations.

The project is intentionally implemented as a simple planner-executor pipeline
instead of a large multi-agent framework. The goal is clarity, traceability,
and safe behavior when sources are incomplete or unreliable.

## What it does

<img width="1704" height="426" alt="Untitled - Visual 1" src="https://github.com/user-attachments/assets/087be06e-a835-4230-b973-1ac435b851fd" />


The final answer contains:

- User question
- Short answer
- Key findings
- Sources used
- Confidence level
- Limitations or assumptions
- Suggested next steps

## Why use an agentic approach?

A fixed search-and-summarize script would use the same tools for every question.
This project uses a planner because research questions have different needs:

- A software comparison may need GitHub repository facts.
- A broad topic may need several focused searches.
- A company list needs identity and positioning evidence.
- A question with pros and cons needs evidence for both sides.
- An inaccessible or nonexistent source must lower confidence rather than produce
  an invented answer.

The plan is printed before execution, so a user or evaluator can see which
subtasks and tools were selected.

## Technology choices

| Area | Choice | Reason |
| --- | --- | --- |
| Language | Python | Small, readable implementation and strong testing ecosystem |
| LLM | Configurable OpenAI-compatible provider (Mistral by default) | Structured planning and synthesis without coupling the application to one vendor |
| Orchestration | Custom planner-executor pipeline | Fewer abstractions and visible control flow |
| Validation | Pydantic | Runtime validation for plans, tool results, evidence, and answers |
| Search | Firecrawl when configured, then Tavily, then DuckDuckGo | Better extraction with practical fallbacks |
| Page extraction | Firecrawl, HTTPX, and Trafilatura | Handles normal pages and some difficult pages |
| Repository facts | GitHub REST API | Useful for software and open-source comparisons |
| Interface | Streamlit and CLI | Streamlit is judge-friendly; CLI remains useful for automation |
| Tests | Pytest | Focused tests for schemas, filtering, retries, and quality guardrails |
| Observability | JSONL run logs | Lightweight local tracing without a hosted service |

LangGraph, Langfuse, Helicone, and OpenTelemetry are not required for this
assignment. The custom implementation keeps the workflow easy to inspect and
run locally.

## Setup

### Requirements

- Python 3.11 or newer
- Internet access for the external research tools
- API keys for the LLM and at least one search provider

### Create the environment

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Configure environment variables

Copy [.env.example](./.env.example) to `.env` and set the values locally:

```env
LLM_API_KEY=your_mistral_key
LLM_BASE_URL=https://api.mistral.ai/v1
LLM_MODEL=ministral-3b-latest
TAVILY_API=your_tavily_key
FIRECRAWL_API_KEY=your_firecrawl_key
```

`FIRECRAWL_API_KEY` is optional. When it is absent, the project uses Tavily or
DuckDuckGo and the existing HTTP page extractor. Never commit `.env` or paste
real keys into documentation.

The current LLM endpoint and model are configured in the planner and
planner and synthesizer for the selected OpenAI-compatible provider. The default configuration uses Mistral; `LLM_BASE_URL` and `LLM_MODEL` can be changed for another compatible provider.

## Run the application

### Streamlit interface

```powershell
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

Open [http://localhost:8501](http://localhost:8501). Enter a question and click
**Research**. The interface displays the plan, tool events, evidence counts,
structured answer, citations, confidence, limitations, and raw JSON.

### CLI

```powershell
.\.venv\Scripts\python.exe -m agent.main "Compare the top 3 open-source vector databases for a startup building RAG products"
```

The CLI prints:

```text
PLANNING
EXECUTING TOOLS
FILTERING EVIDENCE
SYNTHESIZING ANSWER
FINAL ANSWER
```

## Reliability and safety design

### Timeouts and retries

Network tools use bounded HTTP timeouts. The shared tool wrapper retries
transient failures with exponential backoff and returns an explicit status:
`ok`, `empty`, `error`, or `timeout`. A tool failure does not crash the full
research run.

### Malformed and empty responses

Tool adapters validate response shapes before using them. Empty results are
preserved as an `empty` event, and malformed responses become an `error` event.
The final answer reports unavailable tools in its limitations.

### Evidence filtering

The filter:

- Normalizes URLs and removes tracking parameters.
- Removes duplicate URLs and duplicate content.
- Drops empty or very short content.
- Scores lexical relevance to the question.
- Down-ranks known low-quality domains.
- Detects prompt-injection phrases.
- Removes suspicious injection sentences before synthesis.

Retrieved pages are treated as untrusted data, not as instructions.

### Grounding and hallucination reduction

The synthesizer receives filtered evidence only. Findings must cite valid
evidence IDs. Invalid citations are removed, and `sources_used` is built in
code from the evidence cited by surviving findings rather than trusting URLs
returned by the LLM.

The quality layer also detects generic requirements such as:

- Requested item counts
- Comparison requests
- Pros and cons
- Positioning requests
- Broad questions
- Future-dated documents

Missing coverage lowers confidence and is reported as a limitation. The agent
does not invent missing companies, reports, findings, or citations merely to
match a requested count.

### Confidence guardrails

Confidence is calculated from evidence quantity, source diversity, failed tools,
and quality flags. Additional rules prevent:

- `high` confidence for broad questions
- Confident answers when pros and cons are not both supported
- Confident summaries of unverified future-dated documents
- Confident list answers when the requested count is not covered

## Repository layout

```text
agent/
  schemas.py              Pydantic models
  planner.py              LLM planning and fallback plan
  executor.py             Tool dispatch and event collection
  filters.py              Evidence quality and injection filtering
  quality.py              Generic requirement and confidence checks
  synthesizer.py          Grounded structured answer generation
  logging_utils.py        JSONL run logging
  main.py                 CLI entry point
  tools/
    base.py               Retry and result-status wrapper
    search.py             Tavily and DuckDuckGo search
    fetch.py              HTTPX and Trafilatura extraction
    firecrawl.py          Optional Firecrawl search and scraping
    github.py             GitHub repository lookup
streamlit_app.py          Streamlit interface
tests/                     Automated tests
evals/                     Evaluation queries and recorded results
logs/                      Local runtime traces; ignored by Git
```

## Testing

Run the automated test suite:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The tests cover:

- Pydantic schema validation
- URL normalization and deduplication
- Prompt-injection detection
- Empty tool responses
- Retry behavior
- Permanent tool failures
- Generic requirement extraction
- Confidence guardrails for vague and unbalanced questions

## Evaluation

The evaluation scenarios and expected behavior are documented in
[evals/queries.md](./evals/queries.md). Recorded observations are in
[evals/results.md](./evals/results.md).

Example evaluation:

```powershell
.\.venv\Scripts\python.exe -m agent.main "Tell me about AI"
```

The evaluations intentionally include incomplete and adversarial cases. A
research agent should not be graded only on whether it produces a long answer:
it should also identify when the evidence is insufficient and lower confidence
appropriately.

## Known limitations

- The planner can still create dependent tasks using placeholder text such as
  `URL from subtask 1`; a formal task dependency model is not implemented.
- Candidate-list questions are not yet guaranteed to perform a separate
  verification search for every candidate.
- Source quality is not always strong enough for high-confidence comparisons.
- The system uses lexical relevance rather than embedding-based retrieval.
- Search results and page availability vary over time, so live evaluations are
  not perfectly reproducible.
- Firecrawl and other providers have usage limits and variable latency.
- The prompt-injection detector is pattern-based and cannot identify every
  possible indirect injection.
- The current evaluator does not provide an independent second LLM judge.
- The project does not include authentication, multi-user persistence, or
  hosted deployment configuration.

## Future improvements

The next improvements would be:

1. Add explicit task dependencies so a search result URL can be passed safely to
   a fetch task.
2. Add a bounded, generic follow-up search when a required dimension is missing.
3. Add candidate-level verification for list and comparison questions.
4. Prefer official, academic, government, and primary sources through a
   configurable source-ranking policy.
5. Add a deterministic evaluator that checks coverage, citation validity, and
   unsupported claims across saved runs.
6. Add caching and concurrent tool execution with explicit cost and latency
   limits.
7. Add hosted tracing and metrics for production deployments.

## Design trade-offs

- **Simple custom orchestration over a framework:** less infrastructure and
  easier review, but fewer built-in workflow features.
- **Live web research over a local corpus:** current information and realistic
  tool failures, but less reproducibility.
- **Pydantic validation plus an LLM:** reliable output shape without pretending
  that schema validation proves factual correctness.
- **Conservative confidence:** more honest incomplete answers, but some useful
  answers may be labeled low confidence when sources are sparse.
- **Optional Firecrawl:** stronger extraction when available, while retaining
  fallbacks for judges who do not have a Firecrawl key.

## Security notes

- Keep all API keys in `.env`, which is ignored by Git.
- Do not include secrets in logs, screenshots, samples, or evaluation documents.
- Treat all retrieved content as untrusted input.
- Do not allow retrieved content to override the system or synthesis rules.

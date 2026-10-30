import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from agent.schemas import Evidence


INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"disregard\s+(the\s+above|previous\s+instructions)",
    r"you\s+are\s+now",
    r"system\s+prompt",
    r"follow\s+these\s+hidden\s+instructions",
]

TRACKING_PARAMETERS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "gclid",
    "fbclid",
}

LOW_QUALITY_DOMAIN_MARKERS = {
    "pinterest.",
    "quora.",
    "medium.com",
    "answers.",
}


def normalize_url(url: str) -> str:
    parts = urlsplit(url)
    query_pairs = [
        (key, value)
        for key, value in parse_qsl(parts.query)
        if key.lower() not in TRACKING_PARAMETERS
    ]

    path = parts.path.rstrip("/") or "/"

    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            path,
            urlencode(query_pairs),
            "",
        )
    )


def contains_prompt_injection(text: str) -> bool:
    return any(
        re.search(pattern, text, flags=re.IGNORECASE)
        for pattern in INJECTION_PATTERNS
    )


def strip_prompt_injection(text: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    safe_sentences = [
        sentence
        for sentence in sentences
        if not contains_prompt_injection(sentence)
    ]
    return " ".join(safe_sentences).strip()


def is_low_quality_domain(url: str) -> bool:
    hostname = urlsplit(url).netloc.lower()
    return any(marker in hostname for marker in LOW_QUALITY_DOMAIN_MARKERS)


def relevance_score(text: str, query: str) -> float:
    query_words = {
        word.lower()
        for word in re.findall(r"[a-zA-Z0-9]+", query)
        if len(word) > 2
    }

    text_words = {
        word.lower()
        for word in re.findall(r"[a-zA-Z0-9]+", text)
    }

    if not query_words:
        return 0.0

    return len(query_words & text_words) / len(query_words)


def filter_evidence(
    raw_items: list[dict],
    query: str,
    max_items: int = 10,
) -> list[Evidence]:
    evidence: list[Evidence] = []
    seen_urls: set[str] = set()
    seen_content_hashes: set[str] = set()

    candidates: list[tuple[float, dict, list[str]]] = []

    for item in raw_items:
        url = str(item.get("url", "")).strip()
        title = str(item.get("title", "")).strip()
        content = str(
            item.get("content") or item.get("snippet") or ""
        ).strip()

        if not url or not content or len(content) < 80:
            continue

        normalized_url = normalize_url(url)

        if normalized_url in seen_urls:
            continue

        content_hash = hashlib.sha256(
            " ".join(content.lower().split()).encode("utf-8")
        ).hexdigest()

        if content_hash in seen_content_hashes:
            continue

        seen_urls.add(normalized_url)
        seen_content_hashes.add(content_hash)

        flags: list[str] = []

        if contains_prompt_injection(content):
            flags.append("possible_injection")
            content = strip_prompt_injection(content)

        if not content or len(content) < 80:
            continue

        if is_low_quality_domain(normalized_url):
            flags.append("low_quality_domain")

        score = relevance_score(
            f"{title} {content}",
            query,
        )
        if "low_quality_domain" in flags:
            score *= 0.5

        candidates.append(
            (
                score,
                {
                    "url": normalized_url,
                    "title": title or normalized_url,
                    "content": content,
                },
                flags,
            )
        )

    candidates.sort(key=lambda candidate: candidate[0], reverse=True)

    for index, (score, item, flags) in enumerate(candidates[:max_items], start=1):
        evidence.append(
            Evidence(
                id=f"E{index}",
                url=item["url"],
                title=item["title"],
                content=item["content"],
                score=score,
                flags=flags,
            )
        )

    return evidence
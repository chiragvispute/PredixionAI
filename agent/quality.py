import re
from dataclasses import dataclass

from agent.schemas import Evidence, FinalAnswer


@dataclass(frozen=True)
class ResearchRequirements:
    requested_count: int | None = None
    requires_balance: bool = False
    requires_comparison: bool = False
    requires_positioning: bool = False
    is_vague: bool = False
    has_future_reference: bool = False


def extract_requirements(question: str) -> ResearchRequirements:
    normalized = question.lower()
    count_match = re.search(
        r"\b(?:find|identify|list|compare)\s+(\d+)\b",
        normalized,
    )
    return ResearchRequirements(
        requested_count=int(count_match.group(1)) if count_match else None,
        requires_balance=bool(
            re.search(
                r"\b(pros?\s+and\s+cons?|advantages?\s+and\s+disadvantages?)\b",
                normalized,
            )
        ),
        requires_comparison="compare" in normalized,
        requires_positioning="positioning" in normalized,
        is_vague=len(normalized.split()) <= 5
        or normalized.startswith("tell me about"),
        has_future_reference=bool(
            re.search(r"\b20(3[0-9]|[4-9][0-9])\b", normalized)
        ),
    )


def coverage_notes(
    question: str,
    evidence: list[Evidence],
    answer: FinalAnswer,
) -> list[str]:
    requirements = extract_requirements(question)
    notes: list[str] = []

    if requirements.requires_balance:
        claims = " ".join(
            finding.claim.lower() for finding in answer.key_findings
        )
        has_positive = bool(
            re.search(r"\b(pro|benefit|advantage|strength|improv)\w*", claims)
        )
        has_negative = bool(
            re.search(
                r"\b(con|risk|drawback|disadvantage|complex|limit)\w*",
                claims,
            )
        )
        if not (has_positive and has_negative):
            notes.append(
                "The answer does not contain clearly evidenced positive and "
                "negative findings."
            )

    if requirements.requested_count and len(answer.key_findings) < requirements.requested_count:
        notes.append(
            f"The request asked for {requirements.requested_count} items, "
            f"but only {len(answer.key_findings)} evidence-backed findings "
            "were produced."
        )

    if requirements.requires_positioning and not answer.key_findings:
        notes.append("No evidence-backed positioning findings were produced.")

    if requirements.is_vague:
        notes.append("The question is broad; the answer uses an assumed scope.")

    if requirements.has_future_reference:
        notes.append(
            "The requested future-dated document or event must be verified "
            "before it can be summarized."
        )

    if not evidence:
        notes.append("No usable evidence was retained after filtering.")
    elif max(item.score for item in evidence) < 0.15:
        notes.append("Retained evidence has weak relevance to the question.")

    return notes


def apply_confidence_guardrails(
    question: str,
    evidence: list[Evidence],
    answer: FinalAnswer,
    proposed: str,
) -> tuple[str, list[str]]:
    notes = coverage_notes(question, evidence, answer)
    requirements = extract_requirements(question)

    if notes:
        return "low", notes
    if requirements.is_vague:
        return "medium", notes
    return proposed, notes

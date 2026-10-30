import argparse
import json

from agent.executor import execute_plan
from agent.filters import filter_evidence
from agent.logging_utils import create_run_id, write_log
from agent.planner import create_plan
from agent.synthesizer import synthesize_answer


def main() -> None:
    parser = argparse.ArgumentParser(description="AI research agent")
    parser.add_argument("question", help="Research question")
    args = parser.parse_args()

    run_id = create_run_id()
    question = args.question

    write_log(
        run_id,
        "run_started",
        question=question,
    )

    print("\nPLANNING")
    plan = create_plan(question)

    print(json.dumps(plan.model_dump(), indent=2))

    write_log(
        run_id,
        "plan_created",
        subtasks=len(plan.subtasks),
    )

    print("\nEXECUTING TOOLS")
    raw_items, tool_events = execute_plan(plan)

    for event in tool_events:
        print(json.dumps(event, indent=2))
        write_log(run_id, "tool_executed", **event)

    print("\nFILTERING EVIDENCE")
    evidence = filter_evidence(raw_items, question)

    print(f"Collected items: {len(raw_items)}")
    print(f"Evidence kept: {len(evidence)}")

    write_log(
        run_id,
        "evidence_filtered",
        items_in=len(raw_items),
        items_out=len(evidence),
        injection_flags=sum(
            "possible_injection" in item.flags
            for item in evidence
        ),
    )

    print("\nSYNTHESIZING ANSWER")
    answer = synthesize_answer(question, evidence)

    write_log(
        run_id,
        "answer_created",
        confidence=answer.confidence,
        findings=len(answer.key_findings),
        sources=len(answer.sources_used),
    )

    print("\nFINAL ANSWER")
    print(json.dumps(answer.model_dump(), indent=2))

    write_log(run_id, "run_completed")


if __name__ == "__main__":
    main()
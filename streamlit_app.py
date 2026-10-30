import json

import streamlit as st

from agent.executor import execute_plan
from agent.filters import filter_evidence
from agent.logging_utils import create_run_id, write_log
from agent.planner import create_plan
from agent.synthesizer import synthesize_answer


st.set_page_config(
    page_title="AI Research Agent",
    page_icon="Research",
    layout="wide",
)

st.title("AI Research Agent")
st.caption("Planner -> tools -> evidence filtering -> grounded answer")

question = st.text_area(
    "Research question",
    placeholder="Compare the top 3 open-source vector databases for a startup building RAG products",
    height=100,
)

run_research = st.button("Research", type="primary", use_container_width=True)

if run_research:
    if not question.strip():
        st.warning("Enter a research question before starting.")
        st.stop()

    run_id = create_run_id()
    clean_question = question.strip()
    write_log(run_id, "run_started", question=clean_question)

    with st.status("Running research workflow...", expanded=True) as status:
        st.write("Planning the research...")
        plan = create_plan(clean_question)
        write_log(run_id, "plan_created", subtasks=len(plan.subtasks))

        st.write("Executing selected tools...")
        raw_items, tool_events = execute_plan(plan)
        for event in tool_events:
            write_log(run_id, "tool_executed", **event)

        st.write("Filtering evidence...")
        evidence = filter_evidence(raw_items, clean_question)
        write_log(
            run_id,
            "evidence_filtered",
            items_in=len(raw_items),
            items_out=len(evidence),
            injection_flags=sum(
                "possible_injection" in item.flags for item in evidence
            ),
            low_quality_flags=sum(
                "low_quality_domain" in item.flags for item in evidence
            ),
        )

        st.write("Synthesizing a source-grounded answer...")
        answer, synthesis_error = synthesize_answer(
            clean_question,
            evidence,
            tool_events,
        )
        write_log(
            run_id,
            "answer_created",
            confidence=answer.confidence,
            findings=len(answer.key_findings),
            sources=len(answer.sources_used),
            synthesis_status="fallback" if synthesis_error else "ok",
            synthesis_error=synthesis_error,
        )
        write_log(run_id, "run_completed")
        status.update(label="Research complete", state="complete")

    st.subheader("Research plan")
    st.json(plan.model_dump())

    st.subheader("Tool execution")
    st.dataframe(tool_events, use_container_width=True, hide_index=True)

    col1, col2 = st.columns(2)
    col1.metric("Collected items", len(raw_items))
    col2.metric("Evidence kept", len(evidence))

    st.subheader("Final answer")
    st.markdown("**User question**")
    st.write(answer.user_question)
    st.markdown("**Short answer**")
    st.write(answer.short_answer)

    st.markdown("**Key findings**")
    for finding in answer.key_findings:
        st.markdown(f"- {finding.claim}")
        st.caption("Evidence: " + ", ".join(finding.evidence_ids))

    st.markdown("**Sources used**")
    for source in answer.sources_used:
        st.markdown(f"- [{source}]({source})")

    st.markdown("**Confidence level**")
    st.info(answer.confidence.upper())

    st.markdown("**Limitations or assumptions**")
    for limitation in answer.limitations_or_assumptions:
        st.markdown(f"- {limitation}")

    st.markdown("**Suggested next steps**")
    for next_step in answer.suggested_next_steps:
        st.markdown(f"- {next_step}")

    with st.expander("Raw structured answer"):
        st.code(
            json.dumps(answer.model_dump(), indent=2),
            language="json",
        )

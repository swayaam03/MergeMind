"""LangGraph StateGraph workflow for MergeMind.

Orchestrates the autonomous retry loop:
1. Merge Agent proposes a resolution.
2. Deterministic Verifier runs (Docker sandbox tests + Semgrep security scanner).
3. If verification passes -> Complete.
4. If verification fails and retries < max_retries -> Pass specific failure feedback back to Merge Agent and retry.
5. If verification fails and retries exhausted -> Explanation Agent summarizes failure for human review.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from langgraph.graph import END, StateGraph

from app.context.models import RepositoryContext
from app.llm.merge_agent import MergeAgent
from app.pipeline.explanation_agent import ExplanationAgent
from app.pipeline.state import MergeAttemptRecord, MergeState, PipelineEvent
from app.pipeline.verifier import verify_merge_proposal
from app.schemas.verification import LanguageType

logger = logging.getLogger(__name__)


def extract_verification_feedback(verification_report: Dict[str, Any]) -> str:
    """Extract actionable, specific error messages from a failed verification report."""
    if not verification_report:
        return "Previous attempt failed verification with an unspecified error."

    feedback_parts: List[str] = []
    stages = verification_report.get("stages") or {}

    def get_stage(name: str) -> Dict[str, Any]:
        return verification_report.get(name) or stages.get(name) or {}

    def is_failed(st: Dict[str, Any]) -> bool:
        s = str(st.get("status", "")).lower()
        return s in ("failed", "fail", "error")

    # Stage 1: Syntax
    syntax_stage = get_stage("syntax")
    if is_failed(syntax_stage):
        msg = syntax_stage.get("details") or syntax_stage.get("error_message") or syntax_stage.get("output") or syntax_stage.get("summary", "")
        feedback_parts.append(f"SYNTAX ERROR: {msg.strip()}")

    # Stage 2: Compilation / Build
    build_stage = get_stage("build") or get_stage("compilation")
    if is_failed(build_stage):
        msg = build_stage.get("details") or build_stage.get("error_message") or build_stage.get("output") or build_stage.get("summary", "")
        feedback_parts.append(f"COMPILATION ERROR: {msg.strip()}")

    # Stage 3: Test Execution
    test_stage = get_stage("tests") or get_stage("test")
    if is_failed(test_stage):
        out = test_stage.get("details") or test_stage.get("output") or test_stage.get("error_message") or test_stage.get("summary", "")
        snippet = out[-1200:].strip() if len(out) > 1200 else out.strip()
        feedback_parts.append(f"UNIT TEST FAILURES:\n{snippet}")

    # Stage 4: Security Scan
    sec_stage = get_stage("security")
    if is_failed(sec_stage):
        findings = sec_stage.get("findings") or []
        finding_strs = []
        for f in findings:
            rule = f.get("rule_id", "rule")
            fmsg = f.get("message", "")
            line = f.get("line_number", "")
            finding_strs.append(f"- Line {line} [{rule}]: {fmsg}")
        joined_findings = "\n".join(finding_strs) if finding_strs else (sec_stage.get("summary") or "Security policy violations found.")
        feedback_parts.append(f"SECURITY SCAN FINDINGS:\n{joined_findings}")

    if not feedback_parts:
        summary = verification_report.get("summary") or "Automated verification did not pass."
        feedback_parts.append(summary)

    return "\n\n".join(feedback_parts)


def create_merge_graph(
    merge_agent: Optional[MergeAgent] = None,
    explanation_agent: Optional[ExplanationAgent] = None,
) -> Any:
    """
    Construct and compile the LangGraph StateGraph workflow for MergeMind.
    """
    m_agent = merge_agent or MergeAgent()
    e_agent = explanation_agent or ExplanationAgent()

    async def merge_node(state: MergeState) -> Dict[str, Any]:
        """Merge Agent node: Synthesizes or revises a merge proposal."""
        retry_count = state.get("retry_count", 0)
        history = state.get("history") or []
        events = list(state.get("events") or [])
        conflicted_file = state["conflicted_file"]

        # If retrying, extract specific failure feedback from the latest attempt
        feedback = None
        if retry_count > 0 and history:
            last_attempt = history[-1]
            last_verification = last_attempt.get("verification") or {}
            feedback = extract_verification_feedback(last_verification)
            logger.info("Injecting verification feedback into attempt #%d", retry_count + 1)

        repo_ctx = None
        if state.get("repository_context"):
            try:
                repo_ctx = RepositoryContext(**state["repository_context"])
            except Exception:
                repo_ctx = None

        logger.info("Executing Merge Agent node (attempt %d of max %d)", retry_count + 1, state.get("max_retries", 2))
        proposal = await m_agent.propose_merge(
            conflicted_file=conflicted_file,
            repository_context=repo_ctx,
            retry_feedback=feedback,
        )

        proposal_dict = proposal.model_dump()
        new_event: PipelineEvent = {
            "event_type": "proposal_generated",
            "message": f"Merge Agent generated proposal (status={proposal.status}, attempt={retry_count + 1})",
            "timestamp": time.time(),
            "data": {"status": proposal.status, "attempt": retry_count + 1},
        }
        events.append(new_event)

        return {
            "current_proposal": proposal_dict,
            "retry_count": retry_count + 1,
            "status": "verifying",
            "events": events,
        }

    def verify_node(state: MergeState) -> Dict[str, Any]:
        """Deterministic Verification node: Runs syntax, compile, tests, and security scans."""
        proposal = state.get("current_proposal") or {}
        merged_code = proposal.get("merged_code", "")
        file_path = state.get("file_path", "modified_file")
        language_raw = state.get("language", "python")
        source_dir = state.get("source_dir") or "."
        retry_count = state.get("retry_count", 1)
        history = list(state.get("history") or [])
        events = list(state.get("events") or [])

        # If LLM deemed the conflict unresolved, skip heavy verification
        if proposal.get("status") == "unresolved" or not merged_code.strip():
            logger.info("Proposal is unresolved; generating failed verification record directly.")
            mock_report = {
                "overall_status": "failed",
                "summary": "Proposal was marked unresolved by the merge agent.",
                "stages": {
                    "syntax": {"stage": "syntax", "status": "failed", "error_message": "Merged code is empty or unresolved."},
                    "compilation": {"stage": "compilation", "status": "skipped"},
                    "test": {"stage": "test", "status": "skipped"},
                    "security": {"stage": "security", "status": "skipped"},
                },
            }
            attempt_rec: MergeAttemptRecord = {
                "attempt_number": retry_count,
                "proposal": proposal,
                "verification": mock_report,
                "timestamp": time.time(),
            }
            history.append(attempt_rec)
            return {
                "current_verification": mock_report,
                "history": history,
                "status": "verification_failed",
            }

        # Normalize language type
        lang_str = str(language_raw).lower().strip()
        lang_enum: LanguageType = (
            lang_str if lang_str in ("python", "javascript", "typescript", "java") else "unknown"
        )

        logger.info("Executing deterministic verification for attempt #%d", retry_count)
        report = verify_merge_proposal(
            source_dir=Path(source_dir),
            target_file=file_path,
            merged_code=merged_code,
            language=lang_enum,
        )
        report_dict = report.model_dump()

        attempt_rec: MergeAttemptRecord = {
            "attempt_number": retry_count,
            "proposal": proposal,
            "verification": report_dict,
            "timestamp": time.time(),
        }
        history.append(attempt_rec)

        overall_status_str = (
            report.overall_status.value
            if hasattr(report.overall_status, "value")
            else str(report.overall_status)
        )

        new_event: PipelineEvent = {
            "event_type": "verification_completed",
            "message": f"Verification completed: overall_status={overall_status_str}",
            "timestamp": time.time(),
            "data": {"overall_status": overall_status_str, "attempt": retry_count},
        }
        events.append(new_event)

        new_status = "verified" if overall_status_str.upper() == "PASSED" else "verification_failed"

        return {
            "current_verification": report_dict,
            "history": history,
            "status": new_status,
            "events": events,
        }

    async def explanation_node(state: MergeState) -> Dict[str, Any]:
        """Explanation Agent node: Synthesizes plain-English failure briefing when retries are exhausted."""
        file_path = state.get("file_path", "")
        language = state.get("language", "")
        conflicted_file = state.get("conflicted_file") or {}
        history = state.get("history") or []
        ast_analysis = state.get("ast_analysis")
        events = list(state.get("events") or [])

        logger.info("Retries exhausted for '%s'; invoking Explanation Agent", file_path)
        report = await e_agent.explain_failure(
            file_path=file_path,
            language=language,
            conflicted_file=conflicted_file,
            history=history,
            ast_analysis=ast_analysis,
        )

        new_event: PipelineEvent = {
            "event_type": "escalated_to_human",
            "message": "Automated retries exhausted; Explanation report synthesized for human review",
            "timestamp": time.time(),
            "data": {"summary": report.summary},
        }
        events.append(new_event)

        return {
            "explanation": report.model_dump(),
            "status": "escalated",
            "events": events,
        }

    def route_after_verification(state: MergeState) -> str:
        """Route to success, retry, or human escalation."""
        verification = state.get("current_verification") or {}
        overall = verification.get("overall_status")
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 2)

        if str(overall).lower() in ("passed", "pass"):
            logger.info("Verification passed on attempt %d -> Workflow SUCCESS", retry_count)
            return "success"

        if retry_count < max_retries:
            logger.info("Verification failed on attempt %d < max %d -> RETRYING", retry_count, max_retries)
            return "retry"

        logger.info("Verification failed and retry limit reached (%d >= %d) -> ESCALATING", retry_count, max_retries)
        return "escalate"

    # Assemble StateGraph
    builder = StateGraph(MergeState)
    builder.add_node("merge", merge_node)
    builder.add_node("verify", verify_node)
    builder.add_node("explanation", explanation_node)

    builder.set_entry_point("merge")
    builder.add_edge("merge", "verify")

    builder.add_conditional_edges(
        "verify",
        route_after_verification,
        {
            "success": END,
            "retry": "merge",
            "escalate": "explanation",
        },
    )
    builder.add_edge("explanation", END)

    return builder.compile()


# Default compiled workflow instance
default_merge_workflow = create_merge_graph()


async def run_merge_workflow(
    conflicted_file: Dict[str, Any],
    repository_context: Optional[Dict[str, Any]] = None,
    source_dir: Optional[str] = None,
    max_retries: int = 2,
    merge_agent: Optional[MergeAgent] = None,
    explanation_agent: Optional[ExplanationAgent] = None,
) -> MergeState:
    """
    Convenience async entry point to execute the MergeMind LangGraph workflow.
    """
    workflow = (
        create_merge_graph(merge_agent=merge_agent, explanation_agent=explanation_agent)
        if (merge_agent or explanation_agent)
        else default_merge_workflow
    )

    initial_state: MergeState = {
        "file_path": conflicted_file.get("path", "file"),
        "language": conflicted_file.get("language", "python"),
        "conflicted_file": conflicted_file,
        "ast_analysis": conflicted_file.get("ast_analysis"),
        "repository_context": repository_context,
        "source_dir": source_dir,
        "retry_count": 0,
        "max_retries": max_retries,
        "current_proposal": None,
        "current_verification": None,
        "history": [],
        "explanation": None,
        "status": "initialized",
        "events": [
            {
                "event_type": "workflow_started",
                "message": f"Autonomous merge workflow started for {conflicted_file.get('path')}",
                "timestamp": time.time(),
                "data": {"max_retries": max_retries},
            }
        ],
        "error": None,
    }

    final_state = await workflow.ainvoke(initial_state)
    return final_state

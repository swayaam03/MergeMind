"""Unit and integration tests for Phase 6: LangGraph Retry & Explanation Workflow."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.llm.schemas import MergeProposal
from app.main import app
from app.pipeline.explanation_agent import ExplanationAgent, ExplanationReport
from app.pipeline.graph import create_merge_graph, extract_verification_feedback, run_merge_workflow
from app.pipeline.state import MergeState
from app.schemas.verification import StageResult, VerificationReport


@pytest.fixture
def client():
    return TestClient(app, follow_redirects=False)


@pytest.fixture
def sample_conflicted_file():
    return {
        "path": "calculator.py",
        "language": "python",
        "conflict_type": "textual",
        "base_sha": "base111",
        "local_sha": "local222",
        "remote_sha": "remote333",
        "base": "def calculate(x):\n    return x\n",
        "local": "def calculate(x):\n    return x * 10\n",
        "remote": "def calculate(x):\n    return x * 20\n",
        "conflict_markers": {
            "ours": "    return x * 10\n",
            "theirs": "    return x * 20\n",
        },
        "ast_analysis": {
            "classification": {
                "category": "MODIFY_MODIFY",
                "confidence": "deterministic",
                "reason": "Both branches modified the calculate function.",
            }
        },
    }


def make_stage(stage_name: str, status: str, summary: str = "", details: str = "") -> StageResult:
    return StageResult(
        stage=stage_name,
        status=status,
        duration_seconds=0.1,
        summary=summary or f"{stage_name} {status}",
        details=details or None,
    )


# ===========================================================================
# 1. Tests for Feedback Extraction
# ===========================================================================

def test_extract_verification_feedback_syntax_and_tests():
    report = {
        "overall_status": "FAILED",
        "syntax": {
            "status": "FAIL",
            "details": "SyntaxError: invalid syntax on line 12",
        },
        "build": {"status": "PASS"},
        "tests": {
            "status": "FAIL",
            "details": "FAILED test_calc.py::test_basic - AssertionError: expected 20 but got 10",
        },
        "security": {
            "status": "PASS",
            "findings": [],
        },
    }
    feedback = extract_verification_feedback(report)
    assert "SYNTAX ERROR" in feedback
    assert "SyntaxError: invalid syntax on line 12" in feedback
    assert "UNIT TEST FAILURES" in feedback
    assert "AssertionError: expected 20 but got 10" in feedback


def test_extract_verification_feedback_security():
    report = {
        "overall_status": "FAILED",
        "syntax": {"status": "PASS"},
        "build": {"status": "PASS"},
        "tests": {"status": "PASS"},
        "security": {
            "status": "FAIL",
            "findings": [
                {
                    "rule_id": "hardcoded-secret",
                    "message": "Potential hardcoded JWT secret found",
                    "line_number": 44,
                }
            ],
        },
    }
    feedback = extract_verification_feedback(report)
    assert "SECURITY SCAN FINDINGS" in feedback
    assert "hardcoded-secret" in feedback
    assert "Line 44" in feedback


# ===========================================================================
# 2. Tests for Workflow: Immediate Success on Attempt 1
# ===========================================================================

@pytest.mark.asyncio
async def test_workflow_immediate_success(sample_conflicted_file):
    mock_merge_agent = MagicMock()
    mock_merge_agent.propose_merge = AsyncMock(
        return_value=MergeProposal(
            status="resolved",
            merged_code="def calculate(x):\n    return x * 20\n",
            explanation="Adopted remote logic cleanly.",
            preserved_changes=["Remote multiplier"],
            risks=[],
        )
    )

    passing_report = VerificationReport(
        overall_status="PASSED",
        target_file="calculator.py",
        language="python",
        syntax=make_stage("syntax", "PASS"),
        build=make_stage("build", "PASS"),
        tests=make_stage("tests", "PASS"),
        security=make_stage("security", "PASS"),
        total_duration_seconds=0.4,
    )

    with patch("app.pipeline.graph.verify_merge_proposal", return_value=passing_report):
        final_state = await run_merge_workflow(
            conflicted_file=sample_conflicted_file,
            max_retries=2,
            merge_agent=mock_merge_agent,
        )

    assert final_state["status"] == "verified"
    assert final_state["retry_count"] == 1
    assert len(final_state["history"]) == 1
    assert final_state["current_proposal"]["status"] == "resolved"
    assert final_state["explanation"] is None
    assert mock_merge_agent.propose_merge.call_count == 1


# ===========================================================================
# 3. Tests for Workflow: Retry Loop (Fail Attempt 1 -> Pass Attempt 2)
# ===========================================================================

@pytest.mark.asyncio
async def test_workflow_retry_loop_success(sample_conflicted_file):
    mock_merge_agent = MagicMock()

    proposal_1 = MergeProposal(
        status="resolved",
        merged_code="def calculate(x): syntax error",
        explanation="Attempt 1 broken",
        preserved_changes=[],
        risks=[],
    )
    proposal_2 = MergeProposal(
        status="resolved",
        merged_code="def calculate(x):\n    return x * 20\n",
        explanation="Attempt 2 fixed",
        preserved_changes=["Fixed logic"],
        risks=[],
    )
    mock_merge_agent.propose_merge = AsyncMock(side_effect=[proposal_1, proposal_2])

    failing_report = VerificationReport(
        overall_status="FAILED",
        target_file="calculator.py",
        language="python",
        syntax=make_stage("syntax", "FAIL", details="SyntaxError on line 1"),
        build=make_stage("build", "PASS"),
        tests=make_stage("tests", "PASS"),
        security=make_stage("security", "PASS"),
        total_duration_seconds=0.4,
    )

    passing_report = VerificationReport(
        overall_status="PASSED",
        target_file="calculator.py",
        language="python",
        syntax=make_stage("syntax", "PASS"),
        build=make_stage("build", "PASS"),
        tests=make_stage("tests", "PASS"),
        security=make_stage("security", "PASS"),
        total_duration_seconds=0.4,
    )

    with patch("app.pipeline.graph.verify_merge_proposal", side_effect=[failing_report, passing_report]):
        final_state = await run_merge_workflow(
            conflicted_file=sample_conflicted_file,
            max_retries=2,
            merge_agent=mock_merge_agent,
        )

    assert final_state["status"] == "verified"
    assert final_state["retry_count"] == 2
    assert len(final_state["history"]) == 2
    assert mock_merge_agent.propose_merge.call_count == 2
    # Verify feedback was passed to second attempt
    second_call_kwargs = mock_merge_agent.propose_merge.call_args_list[1].kwargs
    assert "SyntaxError on line 1" in second_call_kwargs["retry_feedback"]


# ===========================================================================
# 4. Tests for Workflow: Retries Exhausted -> Escalates to Explanation Agent
# ===========================================================================

@pytest.mark.asyncio
async def test_workflow_retries_exhausted_escalation(sample_conflicted_file):
    mock_merge_agent = MagicMock()
    mock_merge_agent.propose_merge = AsyncMock(
        return_value=MergeProposal(
            status="resolved",
            merged_code="def calculate(x): fail",
            explanation="Still failing",
            preserved_changes=[],
            risks=[],
        )
    )

    mock_explanation_agent = MagicMock()
    mock_explanation_agent.explain_failure = AsyncMock(
        return_value=ExplanationReport(
            summary="Automated merge attempts exhausted. Logic divergence requires developer review.",
            conflict_overview="Local multiplied by 10 whereas remote multiplied by 20.",
            attempts_summary=["Attempt 1: Syntax failed", "Attempt 2: Syntax failed"],
            recommendations=["Choose multiplier 10 or 20 in diff editor."],
            model="mock-model",
        )
    )

    failing_report = VerificationReport(
        overall_status="FAILED",
        target_file="calculator.py",
        language="python",
        syntax=make_stage("syntax", "FAIL", details="Syntax error on line 1"),
        build=make_stage("build", "PASS"),
        tests=make_stage("tests", "PASS"),
        security=make_stage("security", "PASS"),
        total_duration_seconds=0.4,
    )

    with patch("app.pipeline.graph.verify_merge_proposal", return_value=failing_report):
        final_state = await run_merge_workflow(
            conflicted_file=sample_conflicted_file,
            max_retries=2,
            merge_agent=mock_merge_agent,
            explanation_agent=mock_explanation_agent,
        )

    assert final_state["status"] == "escalated"
    assert final_state["retry_count"] == 2
    assert len(final_state["history"]) == 2
    assert final_state["explanation"] is not None
    assert "divergence requires developer review" in final_state["explanation"]["summary"]
    assert mock_explanation_agent.explain_failure.call_count == 1


# ===========================================================================
# 5. Tests for POST /resolve-workflow API Endpoint
# ===========================================================================

@patch("app.api.routes.merges.get_installation_access_token")
@patch("app.api.routes.merges.get_installation_repositories")
@patch("app.api.routes.merges.get_pull_request_detail")
@patch("app.api.routes.merges.simulate_merge_and_extract_conflicts")
@patch("app.api.routes.merges.run_merge_workflow")
def test_resolve_workflow_endpoint_success(
    mock_run_wf,
    mock_simulate,
    mock_get_pr,
    mock_get_repos,
    mock_get_token,
    client,
):
    mock_get_token.return_value = "ghs_test_token"
    mock_get_repos.return_value = [{"full_name": "test-owner/test-repo"}]
    mock_get_pr.return_value = {
        "number": 1,
        "mergeable": False,
        "mergeable_state": "dirty",
        "base": {"ref": "main", "sha": "base123"},
        "head": {"ref": "feature", "sha": "head456"},
    }
    mock_simulate.return_value = {
        "conflicts": [
            {
                "path": "test.py",
                "language": "python",
                "base": "def f(): pass\n",
                "local": "def f(): return 1\n",
                "remote": "def f(): return 2\n",
            }
        ]
    }
    mock_run_wf.return_value = {
        "status": "verified",
        "file_path": "test.py",
        "retry_count": 1,
        "max_retries": 2,
        "current_proposal": {
            "status": "resolved",
            "merged_code": "def f(): return 2\n",
            "explanation": "Resolved",
        },
        "current_verification": {"overall_status": "passed"},
        "history": [],
        "explanation": None,
        "events": [],
    }

    client.cookies.set("installation_id", "123456")
    response = client.post("/api/github/repositories/test-owner/test-repo/pulls/1/resolve-workflow?max_retries=2")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "verified"
    assert data["file_path"] == "test.py"
    assert data["retry_count"] == 1
    assert data["current_proposal"]["status"] == "resolved"
    assert mock_run_wf.call_count == 1

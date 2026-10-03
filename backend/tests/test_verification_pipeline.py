"""Tests for deterministic verification pipeline (Phase 5 Task 6)."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.pipeline.verifier import verify_merge_proposal
from app.schemas.verification import VerificationReport


client = TestClient(app)


def test_verify_merge_proposal_success():
    """Verify that clean valid code passes all verification stages."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src = Path(tmpdir)
        (src / "calc.py").write_text("def add(a, b):\n    return a + b\n")

        valid_code = "def add(a: int, b: int) -> int:\n    \"\"\"Sum two numbers.\"\"\"\n    return a + b\n"
        report = verify_merge_proposal(
            source_dir=src,
            target_file="calc.py",
            merged_code=valid_code,
            language="python",
        )

        assert isinstance(report, VerificationReport)
        assert report.overall_status == "PASSED"
        assert report.syntax.status == "PASS"
        assert report.build.status == "PASS"
        assert report.security.status == "PASS"


def test_verify_merge_proposal_syntax_failure():
    """Verify that code with syntax error fails verification."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src = Path(tmpdir)
        (src / "bad.py").write_text("x = 1\n")

        bad_syntax = "def broken(:\n    return False\n"
        report = verify_merge_proposal(
            source_dir=src,
            target_file="bad.py",
            merged_code=bad_syntax,
            language="python",
        )

        assert report.overall_status == "FAILED"
        assert report.syntax.status == "FAIL"
        assert len(report.syntax.failing_items) > 0


def test_verify_merge_proposal_security_failure():
    """Verify that code containing dangerous sinks or secrets fails security stage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src = Path(tmpdir)
        (src / "vuln.py").write_text("x = 1\n")

        unsafe_code = "def run(cmd):\n    eval(cmd)\n"
        report = verify_merge_proposal(
            source_dir=src,
            target_file="vuln.py",
            merged_code=unsafe_code,
            language="python",
        )

        assert report.overall_status == "FAILED"
        assert report.security.status == "FAIL"
        assert any("eval" in item.lower() for item in report.security.failing_items)


@patch("app.api.routes.merges.resolve_installation_id", return_value=12345)
@patch("app.api.routes.merges.get_installation_access_token", return_value="fake_tok")
@patch("app.api.routes.merges.get_pull_request_detail")
@patch("app.api.routes.merges.checkout_pr_baseline")
def test_verify_proposal_api_endpoint(mock_checkout, mock_pr, mock_token, mock_install):
    """Test POST /verify-proposal API endpoint integration."""
    mock_pr.return_value = {
        "number": 1,
        "base_ref": "main",
        "base_sha": "abc1234",
    }

    payload = {
        "target_file": "app/service.py",
        "merged_code": "def process():\n    return 'clean'\n",
        "language": "python",
    }

    res = client.post(
        "/api/github/repositories/testowner/testrepo/pulls/1/verify-proposal",
        json=payload,
        cookies={"installation_id": "12345"},
    )

    assert res.status_code == 200
    data = res.json()
    assert data["overall_status"] == "PASSED"
    assert data["syntax"]["status"] == "PASS"
    assert data["security"]["status"] == "PASS"
    assert "docker_used" in data

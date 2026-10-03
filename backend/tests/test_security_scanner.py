"""Unit tests for Phase 5 Task 5: Semgrep & Deterministic Security Scanning."""

from unittest.mock import MagicMock, patch
import pytest

from app.pipeline.security_scanner import (
    SemgrepSecurityScanner,
    parse_semgrep_json_output,
    scan_code_with_ast_and_patterns,
)
from app.sandbox.merge_workspace import prepare_proposed_workspace
from app.schemas.verification import ContainerExecutionResult, StageResult


# ============================================================================
# Secret & Token Pattern Leak Tests
# ============================================================================


def test_detect_github_token_leak():
    """Detect exposed GitHub personal access tokens."""
    code = """
API_TOKEN = "ghp_111122223333444455556666777788889999"
def fetch_data():
    pass
"""
    findings = scan_code_with_ast_and_patterns(code, "config.py", "python")
    assert len(findings) > 0
    token_findings = [f for f in findings if "github_token" in f.rule_id]
    assert len(token_findings) == 1
    assert token_findings[0].severity == "ERROR"
    assert token_findings[0].line_number == 2


def test_detect_openrouter_key_leak():
    """Detect exposed OpenRouter API keys."""
    code = """
KEY = "sk-or-v1-0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
"""
    findings = scan_code_with_ast_and_patterns(code, "llm.py", "python")
    assert any("openrouter_key" in f.rule_id for f in findings)


def test_detect_private_key_leak():
    """Detect exposed private key certificates."""
    code = """
PEM = \"\"\"-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEA0Y...
-----END RSA PRIVATE KEY-----\"\"\"
"""
    findings = scan_code_with_ast_and_patterns(code, "auth.py", "python")
    assert any("private_key" in f.rule_id for f in findings)


# ============================================================================
# AST Code Injection & Deserialization Tests
# ============================================================================


def test_detect_eval_and_exec():
    """Detect dangerous dynamic code evaluation with eval/exec."""
    code = """
def run_user_input(code_str):
    return eval(code_str)

def run_exec(cmd):
    exec(cmd)
"""
    findings = scan_code_with_ast_and_patterns(code, "calc.py", "python")
    eval_findings = [f for f in findings if "eval_exec" in f.rule_id]
    assert len(eval_findings) == 2
    assert all(f.severity == "ERROR" for f in eval_findings)


def test_detect_pickle_deserialization():
    """Detect insecure deserialization via pickle.loads."""
    code = """
import pickle

def load_payload(raw_bytes):
    return pickle.loads(raw_bytes)
"""
    findings = scan_code_with_ast_and_patterns(code, "loader.py", "python")
    pickle_findings = [f for f in findings if "pickle" in f.rule_id]
    assert len(pickle_findings) == 1
    assert pickle_findings[0].severity == "ERROR"
    assert pickle_findings[0].line_number == 5


def test_detect_subprocess_shell_true():
    """Detect dangerous command injection via subprocess with shell=True."""
    code = """
import subprocess

def run_command(user_param):
    subprocess.run(f"echo {user_param}", shell=True)
"""
    findings = scan_code_with_ast_and_patterns(code, "system.py", "python")
    shell_findings = [f for f in findings if "subprocess_shell_true" in f.rule_id]
    assert len(shell_findings) == 1
    assert shell_findings[0].severity == "ERROR"


def test_detect_os_system():
    """Detect os.system command execution."""
    code = """
import os

def ping(host):
    os.system("ping " + host)
"""
    findings = scan_code_with_ast_and_patterns(code, "net.py", "python")
    os_findings = [f for f in findings if "os_system" in f.rule_id]
    assert len(os_findings) == 1
    assert os_findings[0].severity == "ERROR"


def test_clean_python_code_has_no_findings():
    """Verify that safe code produces zero false positives."""
    code = """
import json

def process_data(items: list[int]) -> int:
    serialized = json.dumps({"count": len(items)})
    parsed = json.loads(serialized)
    return parsed["count"]
"""
    findings = scan_code_with_ast_and_patterns(code, "safe.py", "python")
    assert len(findings) == 0


# ============================================================================
# JavaScript Security Scan Tests
# ============================================================================


def test_detect_javascript_eval():
    """Detect eval() in JavaScript code."""
    code = """
function calculate(expr) {
    return eval(expr);
}
"""
    findings = scan_code_with_ast_and_patterns(code, "calc.js", "javascript")
    assert any("eval" in f.rule_id for f in findings)


# ============================================================================
# Semgrep Output Parsing Tests
# ============================================================================


def test_parse_semgrep_json_output():
    """Parse real Semgrep JSON findings format into SecurityFinding models."""
    sample_json = """
{
  "results": [
    {
      "check_id": "python.lang.security.deserialization.pickle.avoid-pickle",
      "path": "app/service.py",
      "start": {"line": 15, "col": 12},
      "extra": {
        "message": "Avoid using pickle.loads() on untrusted input",
        "severity": "ERROR",
        "lines": "pickle.loads(payload)"
      }
    },
    {
      "check_id": "python.lang.best-practice.open-without-context",
      "path": "app/service.py",
      "start": {"line": 25, "col": 5},
      "extra": {
        "message": "Use context manager with open()",
        "severity": "WARNING",
        "lines": "f = open('data.txt')"
      }
    }
  ]
}
"""
    findings = parse_semgrep_json_output(sample_json, "app/service.py")
    assert len(findings) == 2

    assert findings[0].rule_id == "python.lang.security.deserialization.pickle.avoid-pickle"
    assert findings[0].severity == "ERROR"
    assert findings[0].line_number == 15

    assert findings[1].severity == "WARNING"
    assert findings[1].line_number == 25


# ============================================================================
# SemgrepSecurityScanner End-to-End Tests
# ============================================================================


def test_scanner_clean_workspace():
    """Scan on safe workspace returns PASS and 0 error findings."""
    safe_code = "def add(a, b):\n    return a + b\n"
    with prepare_proposed_workspace("math.py", safe_code) as ws:
        scanner = SemgrepSecurityScanner()
        stage_res, report = scanner.scan_workspace(ws)

        assert stage_res.stage == "security"
        assert stage_res.status == "PASS"
        assert stage_res.exit_code == 0
        assert report.error_count == 0
        assert len(stage_res.failing_items) == 0


def test_scanner_vulnerable_workspace():
    """Scan on vulnerable workspace returns FAIL with structured failing items."""
    vulnerable_code = """
import os

def ping_host(host):
    os.system("ping " + host)
"""
    with prepare_proposed_workspace("network.py", vulnerable_code) as ws:
        scanner = SemgrepSecurityScanner()
        stage_res, report = scanner.scan_workspace(ws)

        assert stage_res.stage == "security"
        assert stage_res.status == "FAIL"
        assert stage_res.exit_code == 1
        assert report.error_count > 0
        assert len(stage_res.failing_items) > 0
        assert any("os_system" in item for item in stage_res.failing_items)


def test_scanner_docker_execution_mocked():
    """Mock Docker container Semgrep execution and check structured results."""
    mock_runner = MagicMock()
    mock_runner.is_available.return_value = True
    mock_runner.run_in_sandbox.return_value = ContainerExecutionResult(
        exit_code=0,
        stdout="""
{
  "results": [
    {
      "check_id": "security.auth.bypass",
      "path": "auth.py",
      "start": {"line": 10, "col": 1},
      "extra": {
        "message": "Authentication check was removed",
        "severity": "ERROR",
        "lines": "def admin_panel(): pass"
      }
    }
  ]
}
""",
        stderr="",
        duration_seconds=0.75,
        timed_out=False,
    )

    with prepare_proposed_workspace("auth.py", "def admin_panel(): pass\n") as ws:
        scanner = SemgrepSecurityScanner(runner=mock_runner)
        stage_res, report = scanner.scan_workspace(ws)

        assert mock_runner.run_in_sandbox.called
        assert stage_res.status == "FAIL"
        assert report.error_count == 1
        assert "security.auth.bypass" in stage_res.failing_items[0]

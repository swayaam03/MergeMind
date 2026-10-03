"""Unit tests for Phase 5 Task 4: Test Suite Discovery & Sandbox Execution."""

from unittest.mock import MagicMock, patch
import pytest

from app.sandbox.merge_workspace import prepare_proposed_workspace
from app.sandbox.test_runner import (
    SandboxTestRunner,
    discover_test_files,
    parse_npm_test_output,
    parse_pytest_output,
)
from app.schemas.verification import ContainerExecutionResult, StageResult


# ============================================================================
# Output Parsing Tests
# ============================================================================


def test_parse_pytest_output_all_passing():
    """Parse output from fully passing pytest suite."""
    output = """
============================= test session starts =============================
collected 4 items

tests/test_calc.py ....                                                  [100%]

============================== 4 passed in 0.12s ==============================
"""
    passed, failed, skipped, failing_tests = parse_pytest_output(output)
    assert passed == 4
    assert failed == 0
    assert skipped == 0
    assert len(failing_tests) == 0


def test_parse_pytest_output_with_failures():
    """Parse output from pytest with failures and extract failed test names."""
    output = """
============================= test session starts =============================
collected 3 items

tests/test_calc.py .F.                                                   [100%]

================================== FAILURES ===================================
________________________________ test_subtract ________________________________
    def test_subtract():
>       assert subtract(5, 3) == 1
E       AssertionError: assert 2 == 1
=========================== short test summary info ===========================
FAILED tests/test_calc.py::test_subtract - AssertionError: assert 2 == 1
========================= 1 failed, 2 passed in 0.24s =========================
"""
    passed, failed, skipped, failing_tests = parse_pytest_output(output)
    assert passed == 2
    assert failed == 1
    assert skipped == 0
    assert len(failing_tests) == 1
    assert failing_tests[0] == "tests/test_calc.py::test_subtract"


def test_parse_npm_test_output_jest():
    """Parse output from Jest test runner."""
    output = """
 PASS  src/__tests__/sum.test.js
 FAIL  src/__tests__/mult.test.js
  ● Multiplication › multiplies numbers correctly

    expect(received).toBe(expected) // Object.is equality

    Expected: 6
    Received: 5

Tests:       1 failed, 1 passed, 2 total
Snapshots:   0 total
Time:        1.234 s
"""
    passed, failed, skipped, failing_tests = parse_npm_test_output(output)
    assert passed == 1
    assert failed == 1
    assert len(failing_tests) == 1
    assert "Multiplication › multiplies numbers correctly" in failing_tests[0]


# ============================================================================
# Test Discovery Tests
# ============================================================================


def test_discover_test_files():
    """Verify discovery of language-specific test files in workspace."""
    source_files = {
        "src/calc.py": "def add(a, b): return a + b\n",
        "tests/test_calc.py": "def test_add(): pass\n",
        "tests/sub/another_test.py": "def test_another(): pass\n",
        "docs/test_doc.md": "# Docs\n",
    }

    with prepare_proposed_workspace("src/calc.py", "def add(a, b): return a + b\n", source_files=source_files) as ws:
        py_tests = discover_test_files(ws.path, "python")
        assert "tests/test_calc.py" in py_tests
        assert "tests/sub/another_test.py" in py_tests
        assert "docs/test_doc.md" not in py_tests


# ============================================================================
# SandboxTestRunner End-to-End & Mocked Tests
# ============================================================================


def test_runner_skips_when_no_tests_exist():
    """When a workspace has no test files, tests stage is SKIPPED."""
    source_files = {
        "src/util.py": "def do_stuff(): pass\n",
        "README.md": "# Readme\n",
    }
    with prepare_proposed_workspace("src/util.py", "def do_stuff(): pass\n", source_files=source_files) as ws:
        test_runner = SandboxTestRunner()
        result = test_runner.run_tests(ws)

        assert isinstance(result, StageResult)
        assert result.stage == "tests"
        assert result.status == "SKIPPED"
        assert "No test suite detected" in result.summary


def test_runner_docker_execution_pass():
    """When Docker container tests pass, return StageResult with PASS."""
    mock_runner = MagicMock()
    mock_runner.is_available.return_value = True
    mock_runner.run_in_sandbox.return_value = ContainerExecutionResult(
        exit_code=0,
        stdout="============================== 2 passed in 0.10s ==============================\n",
        stderr="",
        duration_seconds=1.2,
        timed_out=False,
    )

    source_files = {
        "calc.py": "def add(a, b): return a + b\n",
        "test_calc.py": "def test_add(): pass\n",
    }
    with prepare_proposed_workspace("calc.py", "def add(a, b): return a + b\n", source_files=source_files) as ws:
        test_runner = SandboxTestRunner(runner=mock_runner)
        result = test_runner.run_tests(ws)

        assert result.stage == "tests"
        assert result.status == "PASS"
        assert result.exit_code == 0
        assert "2 passed" in result.summary


def test_runner_docker_execution_fail():
    """When Docker container tests fail, return StageResult with FAIL and failing items."""
    mock_runner = MagicMock()
    mock_runner.is_available.return_value = True
    mock_runner.run_in_sandbox.return_value = ContainerExecutionResult(
        exit_code=1,
        stdout="""
FAILED test_calc.py::test_fail - AssertionError
========================= 1 failed, 1 passed in 0.10s =========================
""",
        stderr="",
        duration_seconds=1.5,
        timed_out=False,
    )

    source_files = {
        "calc.py": "def add(a, b): return a - b\n",
        "test_calc.py": "def test_fail(): assert False\n",
    }
    with prepare_proposed_workspace("calc.py", "def add(a, b): return a - b\n", source_files=source_files) as ws:
        test_runner = SandboxTestRunner(runner=mock_runner)
        result = test_runner.run_tests(ws)

        assert result.stage == "tests"
        assert result.status == "FAIL"
        assert result.exit_code == 1
        assert "1 failed" in result.summary
        assert "test_calc.py::test_fail" in result.failing_items


def test_runner_docker_timeout():
    """When Docker container times out, return StageResult with FAIL and timeout message."""
    mock_runner = MagicMock()
    mock_runner.is_available.return_value = True
    mock_runner.run_in_sandbox.return_value = ContainerExecutionResult(
        exit_code=124,
        stdout="Test suite running...",
        stderr="Container killed after timeout",
        duration_seconds=45.0,
        timed_out=True,
    )

    source_files = {
        "loop.py": "while True: pass\n",
        "test_loop.py": "import loop\ndef test_loop(): pass\n",
    }
    with prepare_proposed_workspace("loop.py", "while True: pass\n", source_files=source_files) as ws:
        test_runner = SandboxTestRunner(runner=mock_runner, timeout_seconds=45)
        result = test_runner.run_tests(ws)

        assert result.status == "FAIL"
        assert result.exit_code == 124
        assert "timed out" in result.summary.lower()
        assert any("TIMEOUT" in item for item in result.failing_items)


def test_runner_local_execution_passing_test():
    """Test actual local pytest execution on a passing test case."""
    source_files = {
        "solution.py": "def multiply(a, b): return a * b\n",
        "test_solution.py": "from solution import multiply\ndef test_mult(): assert multiply(3, 4) == 12\n",
    }
    with prepare_proposed_workspace("solution.py", "def multiply(a, b): return a * b\n", source_files=source_files) as ws:
        # Force local fallback
        mock_runner = MagicMock()
        mock_runner.is_available.return_value = False

        test_runner = SandboxTestRunner(runner=mock_runner)
        result = test_runner.run_tests(ws)

        # Local pytest is installed in Python environment, should pass
        assert result.stage == "tests"
        assert result.status == "PASS"
        assert result.exit_code == 0
        assert "passed" in result.summary.lower()


def test_runner_local_execution_failing_test():
    """Test actual local pytest execution on a failing test case."""
    source_files = {
        "solution.py": "def multiply(a, b): return a + b  # bug\n",
        "test_solution.py": "from solution import multiply\ndef test_mult(): assert multiply(3, 4) == 12\n",
    }
    with prepare_proposed_workspace("solution.py", "def multiply(a, b): return a + b\n", source_files=source_files) as ws:
        # Force local fallback
        mock_runner = MagicMock()
        mock_runner.is_available.return_value = False

        test_runner = SandboxTestRunner(runner=mock_runner)
        result = test_runner.run_tests(ws)

        assert result.stage == "tests"
        assert result.status == "FAIL"
        assert result.exit_code != 0
        assert any("test_solution.py::test_mult" in item for item in result.failing_items)

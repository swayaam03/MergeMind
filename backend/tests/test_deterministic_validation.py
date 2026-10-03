"""Unit tests for Phase 5 Task 3: Deterministic Validation (Syntax & Build checks)."""

from unittest.mock import MagicMock, patch
import pytest

from app.sandbox.merge_workspace import prepare_proposed_workspace
from app.sandbox.syntax_validator import (
    DeterministicValidator,
    validate_java_syntax_with_treesitter,
    validate_javascript_syntax_with_treesitter,
    validate_python_syntax_in_process,
)
from app.schemas.verification import ContainerExecutionResult, StageResult


# ============================================================================
# Python Syntax Validation Tests
# ============================================================================


def test_validate_python_syntax_valid():
    """Valid Python code passes in-process syntax check."""
    code = """
def calculate_total(items: list[int]) -> int:
    return sum(items)

class Calculator:
    def __init__(self, value: int = 0):
        self.value = value
"""
    is_valid, summary, failing = validate_python_syntax_in_process(code, "calc.py")
    assert is_valid is True
    assert "successfully" in summary
    assert len(failing) == 0


def test_validate_python_syntax_invalid():
    """Syntax error in Python code returns line and column."""
    code = """
def broken_func(a, b):
    return a + * b
"""
    is_valid, summary, failing = validate_python_syntax_in_process(code, "broken.py")
    assert is_valid is False
    assert "SyntaxError" in summary
    assert len(failing) > 0
    assert "line 3" in failing[0]


def test_validate_python_syntax_indentation_error():
    """Indentation error in Python is properly caught."""
    code = """
def foo():
print("bad indent")
"""
    is_valid, summary, failing = validate_python_syntax_in_process(code, "indent.py")
    assert is_valid is False
    assert len(failing) > 0
    assert "line 3" in failing[0]


# ============================================================================
# JavaScript Syntax Validation Tests
# ============================================================================


def test_validate_javascript_syntax_valid():
    """Valid JavaScript code passes Tree-sitter check."""
    code = """
const calculate = (a, b) => {
    return a + b;
};

class Greeter {
    constructor(name) {
        this.name = name;
    }
}
"""
    is_valid, summary, failing = validate_javascript_syntax_with_treesitter(code, "app.js")
    assert is_valid is True
    assert len(failing) == 0


def test_validate_javascript_syntax_invalid():
    """Malformed JavaScript code returns error node positions."""
    code = """
const broken = (a, b => {
    return a + b;
};
"""
    is_valid, summary, failing = validate_javascript_syntax_with_treesitter(code, "broken.js")
    assert is_valid is False
    assert "syntax error" in summary.lower()
    assert len(failing) > 0


# ============================================================================
# Java Syntax Validation Tests
# ============================================================================


def test_validate_java_syntax_valid():
    """Valid Java code passes Tree-sitter check."""
    code = """
package com.example;

public class MathUtils {
    public static int add(int a, int b) {
        return a + b;
    }
}
"""
    is_valid, summary, failing = validate_java_syntax_with_treesitter(code, "MathUtils.java")
    assert is_valid is True
    assert len(failing) == 0


def test_validate_java_syntax_invalid():
    """Malformed Java code returns error node positions."""
    code = """
public class MathUtils {
    public static int add(int a int b) {  // missing comma
        return a + b;
    }
"""
    is_valid, summary, failing = validate_java_syntax_with_treesitter(code, "MathUtils.java")
    assert is_valid is False
    assert len(failing) > 0


# ============================================================================
# DeterministicValidator End-to-End Tests
# ============================================================================


def test_validator_python_stage_result_pass():
    """Validator produces StageResult with status PASS on valid Python workspace."""
    code = "def add(x, y):\n    return x + y\n"
    with prepare_proposed_workspace("src/calc.py", code) as ws:
        validator = DeterministicValidator()
        result = validator.validate_syntax(ws)

        assert isinstance(result, StageResult)
        assert result.stage == "syntax"
        assert result.status == "PASS"
        assert "Python" in result.summary


def test_validator_python_stage_result_fail():
    """Validator produces StageResult with status FAIL on invalid Python workspace."""
    broken_code = "def add(x, y)\n    return x + y\n"  # missing colon
    with prepare_proposed_workspace("src/calc.py", broken_code) as ws:
        validator = DeterministicValidator()
        result = validator.validate_syntax(ws)

        assert isinstance(result, StageResult)
        assert result.stage == "syntax"
        assert result.status == "FAIL"
        assert len(result.failing_items) > 0
        assert "line 1" in result.failing_items[0]


def test_validator_javascript_stage_result():
    """Validator checks JavaScript files with Tree-sitter or host node."""
    code = "function greet(name) { return `Hello ${name}`; }\n"
    with prepare_proposed_workspace("src/greet.js", code) as ws:
        validator = DeterministicValidator()
        result = validator.validate_syntax(ws)

        assert result.stage == "syntax"
        assert result.status == "PASS"


def test_validator_build_interpreted_language():
    """Python and JavaScript skip build stage and return PASS."""
    with prepare_proposed_workspace("main.py", "x = 1\n") as ws:
        validator = DeterministicValidator()
        build_result = validator.validate_build(ws)

        assert build_result.stage == "build"
        assert build_result.status == "PASS"
        assert "interpreted" in build_result.summary.lower()


def test_validator_docker_syntax_execution_mocked():
    """Validator uses Docker container execution when Docker is available."""
    mock_runner = MagicMock()
    mock_runner.is_available.return_value = True
    mock_runner.run_in_sandbox.return_value = ContainerExecutionResult(
        exit_code=0,
        stdout="py_compile successful\n",
        stderr="",
        duration_seconds=0.15,
        timed_out=False,
    )

    validator = DeterministicValidator(runner=mock_runner)
    code = "def valid(): pass\n"
    with prepare_proposed_workspace("utils.py", code) as ws:
        result = validator.validate_syntax(ws)

        assert mock_runner.run_in_sandbox.called
        assert result.status == "PASS"
        assert result.exit_code == 0
        assert result.duration_seconds == 0.15


def test_validator_docker_syntax_failure_mocked():
    """Validator extracts failing items from Docker container syntax error output."""
    mock_runner = MagicMock()
    mock_runner.is_available.return_value = True
    mock_runner.run_in_sandbox.return_value = ContainerExecutionResult(
        exit_code=1,
        stdout="",
        stderr='  File "/workspace/broken.py", line 4\n    return *\n           ^\nSyntaxError: invalid syntax\n',
        duration_seconds=0.20,
        timed_out=False,
    )

    validator = DeterministicValidator(runner=mock_runner)
    with prepare_proposed_workspace("broken.py", "def broken(): pass\n") as ws:
        result = validator.validate_syntax(ws)

        assert result.status == "FAIL"
        assert result.exit_code == 1
        assert len(result.failing_items) > 0
        assert any("line 4" in item or "SyntaxError" in item for item in result.failing_items)

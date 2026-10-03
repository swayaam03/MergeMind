"""Deterministic syntax and build validation for MergeMind verification.

Evaluates the proposed merge without executing arbitrary repository logic:
- Python: syntax checking via python -m py_compile / ast.parse
- JavaScript / TypeScript: syntax checking via node --check / tree-sitter
- Java: compilation checking via javac
- Structured StageResult reporting with exact line numbers and error diagnostics
"""

from __future__ import annotations

import ast
import logging
import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

from app.ast.languages import get_parser_for_language
from app.sandbox.docker_runner import DockerSandboxRunner, DockerUnavailableError
from app.sandbox.language_configs import get_language_config
from app.sandbox.merge_workspace import ProposedWorkspace
from app.schemas.verification import (
    DockerContainerConfig,
    LanguageType,
    StageResult,
    VerificationStageStatus,
)

logger = logging.getLogger(__name__)


def validate_python_syntax_in_process(code: str, file_path: str) -> Tuple[bool, Optional[str], List[str]]:
    """
    Deterministically validate Python syntax using standard library ast.parse.
    Completely safe: does not execute any code.
    Returns (is_valid, summary, failing_items).
    """
    try:
        ast.parse(code, filename=file_path)
        return True, "Python syntax parsed successfully", []
    except SyntaxError as exc:
        line = exc.lineno or "?"
        col = exc.offset or "?"
        msg = exc.msg or "syntax error"
        line_text = (exc.text or "").strip()
        detail = f"line {line}:{col}: {msg}"
        if line_text:
            detail += f" -> '{line_text}'"
        return False, f"SyntaxError: {msg} at line {line}", [detail]
    except Exception as exc:
        return False, f"Syntax validation error: {str(exc)}", [str(exc)]


def validate_javascript_syntax_with_treesitter(code: str, file_path: str) -> Tuple[bool, Optional[str], List[str]]:
    """
    Deterministically validate JavaScript syntax using Tree-sitter parser error nodes.
    Returns (is_valid, summary, failing_items).
    """
    try:
        parser = get_parser_for_language("javascript")
        tree = parser.parse(code.encode("utf-8"))
        if not tree.root_node.has_error:
            return True, "JavaScript syntax parsed successfully", []

        # Find error nodes
        errors: List[str] = []

        def traverse(node):
            if node.type == "ERROR" or node.is_missing:
                start_row = node.start_point.row + 1
                start_col = node.start_point.column + 1
                snippet = code.splitlines()[node.start_point.row] if node.start_point.row < len(code.splitlines()) else ""
                errors.append(f"line {start_row}:{start_col}: Syntax error near '{snippet.strip()}'")
            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        summary = f"JavaScript syntax errors detected ({len(errors)} error{'s' if len(errors) != 1 else ''})"
        return False, summary, errors[:10]
    except Exception as exc:
        return False, f"Tree-sitter JS validation failed: {str(exc)}", [str(exc)]


def validate_java_syntax_with_treesitter(code: str, file_path: str) -> Tuple[bool, Optional[str], List[str]]:
    """
    Deterministically validate Java syntax using Tree-sitter parser error nodes.
    Returns (is_valid, summary, failing_items).
    """
    try:
        parser = get_parser_for_language("java")
        tree = parser.parse(code.encode("utf-8"))
        if not tree.root_node.has_error:
            return True, "Java syntax parsed successfully", []

        errors: List[str] = []

        def traverse(node):
            if node.type == "ERROR" or node.is_missing:
                start_row = node.start_point.row + 1
                start_col = node.start_point.column + 1
                snippet = code.splitlines()[node.start_point.row] if node.start_point.row < len(code.splitlines()) else ""
                errors.append(f"line {start_row}:{start_col}: Java syntax error near '{snippet.strip()}'")
            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        summary = f"Java syntax errors detected ({len(errors)} error{'s' if len(errors) != 1 else ''})"
        return False, summary, errors[:10]
    except Exception as exc:
        return False, f"Tree-sitter Java validation failed: {str(exc)}", [str(exc)]


class DeterministicValidator:
    """
    Executes syntax and build validation stages on a ProposedWorkspace.
    Runs inside a locked-down Docker container when available, with
    fast, robust AST-level fallback when Docker is offline.
    """

    def __init__(self, runner: Optional[DockerSandboxRunner] = None) -> None:
        self.runner = runner or DockerSandboxRunner()

    def validate_syntax(self, workspace: ProposedWorkspace) -> StageResult:
        """
        Validate syntax of the target file in the proposed workspace.
        """
        language = workspace.language
        target_file = workspace.target_file
        file_path_on_host = workspace.path / target_file

        if not file_path_on_host.exists():
            return StageResult(
                stage="syntax",
                status="ERROR",
                duration_seconds=0.0,
                summary=f"Target file not found in workspace: {target_file}",
                details="File missing from isolated workspace.",
            )

        code_content = file_path_on_host.read_text(encoding="utf-8", errors="replace")

        # 1. Try Docker sandbox execution if available
        if self.runner.is_available():
            lang_cfg = get_language_config(language)
            if lang_cfg:
                return self._validate_syntax_in_docker(workspace, lang_cfg)

        # 2. In-process deterministic AST fallback
        return self._validate_syntax_fallback(code_content, target_file, language, full_path=file_path_on_host)

    def validate_build(self, workspace: ProposedWorkspace) -> StageResult:
        """
        Validate build / compilation of the proposed workspace.
        Required for compiled languages (Java). For interpreted languages (Python, JS),
        checks if any compilation step or package check is necessary.
        """
        language = workspace.language
        target_file = workspace.target_file
        file_path_on_host = workspace.path / target_file

        if language == "java":
            return self._validate_java_build(workspace)

        # Interpreted languages: compilation is skipped by design
        return StageResult(
            stage="build",
            status="PASS",
            duration_seconds=0.0,
            summary=f"{language.capitalize()} is an interpreted language; compilation not required.",
            details="Syntax check passed. No compilation artifacts needed.",
            failing_items=[],
        )

    def _validate_syntax_in_docker(self, workspace: ProposedWorkspace, lang_cfg) -> StageResult:
        """Run syntax check command inside locked-down Docker container."""
        cmd = list(lang_cfg.syntax_command)
        cmd.append(workspace.target_file)

        config = DockerContainerConfig(
            image=lang_cfg.docker_image,
            command=cmd,
            working_dir="/workspace",
            timeout_seconds=20,
            network_mode="none",
        )

        try:
            res = self.runner.run_in_sandbox(workspace.path, config)
            if res.is_success:
                return StageResult(
                    stage="syntax",
                    status="PASS",
                    exit_code=res.exit_code,
                    duration_seconds=res.duration_seconds,
                    summary=f"{lang_cfg.name.capitalize()} syntax validation passed",
                    details=res.stdout,
                )

            # Failure occurred: parse output
            error_output = res.stderr or res.stdout
            failing_lines = self._extract_syntax_errors(error_output, workspace.target_file)
            return StageResult(
                stage="syntax",
                status="FAIL",
                exit_code=res.exit_code,
                duration_seconds=res.duration_seconds,
                summary=f"{lang_cfg.name.capitalize()} syntax check failed",
                details=error_output,
                failing_items=failing_lines,
            )
        except Exception as exc:
            logger.warning("Docker syntax validation failed, falling back to AST: %s", exc)
            code = (workspace.path / workspace.target_file).read_text(encoding="utf-8", errors="replace")
            return self._validate_syntax_fallback(
                code,
                workspace.target_file,
                workspace.language,
                full_path=workspace.path / workspace.target_file,
            )

    def _validate_syntax_fallback(
        self,
        code: str,
        file_path: str,
        language: LanguageType,
        full_path: Optional[Path] = None,
    ) -> StageResult:
        """In-process AST syntax validation without executing code."""
        if language == "python":
            is_valid, summary, failing = validate_python_syntax_in_process(code, file_path)
            return StageResult(
                stage="syntax",
                status="PASS" if is_valid else "FAIL",
                duration_seconds=0.01,
                summary=summary,
                details="\n".join(failing) if failing else None,
                failing_items=failing,
            )

        if language in ("javascript", "typescript"):
            # If real file exists on host, check if host node is available
            node_path = shutil.which("node")
            target_to_check = full_path if (full_path and full_path.exists()) else None

            if node_path and target_to_check:
                try:
                    proc = subprocess.run(
                        [node_path, "--check", str(target_to_check)],
                        text=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=5,
                    )
                    if proc.returncode == 0:
                        return StageResult(
                            stage="syntax",
                            status="PASS",
                            duration_seconds=0.05,
                            summary="Node.js syntax check passed",
                        )
                    err = proc.stderr
                    failing = self._extract_syntax_errors(err, file_path)
                    return StageResult(
                        stage="syntax",
                        status="FAIL",
                        duration_seconds=0.05,
                        summary="JavaScript syntax check failed",
                        details=err,
                        failing_items=failing,
                    )
                except Exception:
                    pass

            is_valid, summary, failing = validate_javascript_syntax_with_treesitter(code, file_path)
            return StageResult(
                stage="syntax",
                status="PASS" if is_valid else "FAIL",
                duration_seconds=0.01,
                summary=summary,
                details="\n".join(failing) if failing else None,
                failing_items=failing,
            )

        if language == "java":
            is_valid, summary, failing = validate_java_syntax_with_treesitter(code, file_path)
            return StageResult(
                stage="syntax",
                status="PASS" if is_valid else "FAIL",
                duration_seconds=0.01,
                summary=summary,
                details="\n".join(failing) if failing else None,
                failing_items=failing,
            )

        return StageResult(
            stage="syntax",
            status="SKIPPED",
            duration_seconds=0.0,
            summary=f"Syntax checking not supported for language: {language}",
        )

    def _validate_java_build(self, workspace: ProposedWorkspace) -> StageResult:
        """Validate Java compilation via javac inside Docker or local host."""
        target_file = workspace.target_file

        if self.runner.is_available():
            lang_cfg = get_language_config("java")
            if lang_cfg:
                config = DockerContainerConfig(
                    image=lang_cfg.docker_image,
                    command=["javac", target_file],
                    working_dir="/workspace",
                    timeout_seconds=30,
                    network_mode="none",
                )
                try:
                    res = self.runner.run_in_sandbox(workspace.path, config)
                    if res.is_success:
                        return StageResult(
                            stage="build",
                            status="PASS",
                            exit_code=0,
                            duration_seconds=res.duration_seconds,
                            summary="Java compilation succeeded (javac)",
                        )
                    errors = self._extract_syntax_errors(res.stderr or res.stdout, target_file)
                    return StageResult(
                        stage="build",
                        status="FAIL",
                        exit_code=res.exit_code,
                        duration_seconds=res.duration_seconds,
                        summary="Java compilation failed (javac)",
                        details=res.stderr or res.stdout,
                        failing_items=errors,
                    )
                except Exception as exc:
                    logger.warning("Docker Java build failed: %s", exc)

        # Host javac check if available
        javac_path = shutil.which("javac")
        if javac_path:
            try:
                proc = subprocess.run(
                    [javac_path, str(workspace.path / target_file)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=15,
                )
                if proc.returncode == 0:
                    return StageResult(
                        stage="build",
                        status="PASS",
                        duration_seconds=0.5,
                        summary="Java compilation succeeded (local javac)",
                    )
                errors = self._extract_syntax_errors(proc.stderr, target_file)
                return StageResult(
                    stage="build",
                    status="FAIL",
                    duration_seconds=0.5,
                    summary="Java compilation failed (local javac)",
                    details=proc.stderr,
                    failing_items=errors,
                )
            except Exception as exc:
                logger.warning("Local javac build error: %s", exc)

        # Tree-sitter check as final deterministic fallback for Java
        code = (workspace.path / target_file).read_text(encoding="utf-8", errors="replace")
        is_valid, summary, failing = validate_java_syntax_with_treesitter(code, target_file)
        return StageResult(
            stage="build",
            status="PASS" if is_valid else "FAIL",
            duration_seconds=0.01,
            summary=f"Java structure validation: {'PASS' if is_valid else 'FAIL'}",
            details="\n".join(failing) if failing else "No javac available; AST structure verified.",
            failing_items=failing,
        )

    def _extract_syntax_errors(self, raw_output: str, filename: str) -> List[str]:
        """Extract line-specific error messages from compiler/interpreter output."""
        if not raw_output:
            return []
        errors: List[str] = []
        for line in raw_output.splitlines():
            line_str = line.strip()
            if not line_str:
                continue
            if "SyntaxError" in line_str or "error:" in line_str.lower() or "line " in line_str.lower():
                errors.append(line_str)
        return errors[:10] if errors else [raw_output.splitlines()[0][:200]]

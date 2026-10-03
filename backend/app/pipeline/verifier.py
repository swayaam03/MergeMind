"""Deterministic verification pipeline orchestrator for MergeMind.

Orchestrates the 4 verification stages for a proposed merge:
1. Syntax Validation: python -m py_compile / ast.parse / node --check / tree-sitter
2. Build / Compilation: javac / typescript build check (or skipped for interpreted)
3. Test Execution: pytest / npm test / mvn test within network-restricted sandbox
4. Security Audit: Semgrep rules and AST static security scans for sinks & secrets

Strict zero-LLM policy in verification stages. Backend stays completely swappable.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

from app.pipeline.security_scanner import SemgrepSecurityScanner
from app.sandbox.docker_runner import DockerSandboxRunner
from app.sandbox.merge_workspace import prepare_proposed_workspace
from app.sandbox.syntax_validator import DeterministicValidator
from app.sandbox.test_runner import SandboxTestRunner
from app.schemas.verification import (
    LanguageType,
    OverallVerificationStatus,
    StageResult,
    VerificationReport,
)

logger = logging.getLogger(__name__)


def verify_merge_proposal(
    source_dir: Path | str,
    target_file: str,
    merged_code: str,
    language: Optional[LanguageType] = None,
    runner: Optional[DockerSandboxRunner] = None,
) -> VerificationReport:
    """
    Execute end-to-end deterministic verification on a proposed merge resolution.

    Args:
        source_dir: Root directory of repository containing baseline files.
        target_file: Relative path of the modified/conflicted file.
        merged_code: Proposed resolved code to verify.
        language: Optional language hint; auto-detected if None.
        runner: Optional DockerSandboxRunner instance.

    Returns:
        VerificationReport containing structured results from all 4 stages.
    """
    start_time = time.monotonic()
    sandbox_runner = runner or DockerSandboxRunner()
    syntax_validator = DeterministicValidator(runner=sandbox_runner)
    test_runner = SandboxTestRunner(runner=sandbox_runner)
    security_scanner = SemgrepSecurityScanner(runner=sandbox_runner)

    with prepare_proposed_workspace(
        target_file=target_file,
        merged_code=merged_code,
        source_repo_path=source_dir,
    ) as workspace:
        if language and language != "unknown":
            workspace.language = language

        logger.info(
            "Verifying proposed merge in workspace %s (lang=%s, target=%s)",
            workspace.workspace_id,
            workspace.language,
            workspace.target_file,
        )

        # Stage 1: Syntax Validation
        try:
            syntax_result = syntax_validator.validate_syntax(workspace)
        except Exception as exc:
            logger.exception("Error during syntax validation stage")
            syntax_result = StageResult(
                stage="syntax",
                status="ERROR",
                summary=f"Syntax stage exception: {str(exc)}",
                details=str(exc),
            )

        # Stage 2: Compilation / Build Validation
        try:
            build_result = syntax_validator.validate_build(workspace)
        except Exception as exc:
            logger.exception("Error during build validation stage")
            build_result = StageResult(
                stage="build",
                status="ERROR",
                summary=f"Build stage exception: {str(exc)}",
                details=str(exc),
            )

        # Stage 3: Test Execution
        try:
            tests_result = test_runner.run_tests(workspace)
        except Exception as exc:
            logger.exception("Error during test execution stage")
            tests_result = StageResult(
                stage="tests",
                status="ERROR",
                summary=f"Tests stage exception: {str(exc)}",
                details=str(exc),
            )

        # Stage 4: Security Scan (Semgrep + AST Auditor)
        try:
            security_result, _ = security_scanner.scan_workspace(workspace)
        except Exception as exc:
            logger.exception("Error during security scanning stage")
            security_result = StageResult(
                stage="security",
                status="ERROR",
                summary=f"Security stage exception: {str(exc)}",
                details=str(exc),
            )

        # Overall Status Resolution
        statuses = [
            syntax_result.status,
            build_result.status,
            tests_result.status,
            security_result.status,
        ]

        if any(s == "FAIL" for s in statuses):
            overall_status: OverallVerificationStatus = "FAILED"
        elif any(s == "ERROR" for s in statuses):
            overall_status = "ERROR"
        else:
            overall_status = "PASSED"

        total_duration = round(time.monotonic() - start_time, 3)
        docker_available = sandbox_runner.is_available()

        return VerificationReport(
            overall_status=overall_status,
            language=workspace.language,
            target_file=workspace.target_file,
            syntax=syntax_result,
            build=build_result,
            tests=tests_result,
            security=security_result,
            total_duration_seconds=total_duration,
            docker_used=docker_available,
            sandbox_details={
                "workspace_id": workspace.workspace_id,
                "docker_available": docker_available,
                "file_count": workspace.file_count,
            },
        )

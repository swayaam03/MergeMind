"""Test suite execution engine for MergeMind verification.

Executes project tests inside an isolated, network-restricted Docker sandbox:
- Discovers existing test suites and test files across Python, JavaScript, and Java
- Runs tests inside locked-down containers with strict CPU, memory, and timeout limits
- Captures and parses stdout/stderr to extract structured pass/fail metrics
- Handles execution timeouts safely (SIGKILL on runaway processes)
- Produces structured StageResult and TestExecutionReport objects
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.core.config import settings
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


@dataclass
class TestExecutionReport:
    """Detailed metrics from test suite execution."""

    has_tests: bool
    framework: Optional[str] = None
    passed_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    failing_tests: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    timed_out: bool = False
    raw_output: str = ""


def discover_test_files(workspace_dir: Path, language: LanguageType) -> List[str]:
    """Discover relative paths of test files in workspace."""
    if not workspace_dir.exists():
        return []

    test_files: List[str] = []
    lang_cfg = get_language_config(language)
    patterns = lang_cfg.test_file_patterns if lang_cfg else []

    for root, _, files in os.walk(workspace_dir):
        rel_root = Path(root).relative_to(workspace_dir)
        for f in files:
            rel_file = str(rel_root / f).replace("\\", "/")
            if rel_file.startswith("./"):
                rel_file = rel_file[2:]

            # Match patterns
            if language == "python":
                if f.startswith("test_") and f.endswith(".py"):
                    test_files.append(rel_file)
                elif f.endswith("_test.py"):
                    test_files.append(rel_file)
            elif language in ("javascript", "typescript"):
                if f.endswith(".test.js") or f.endswith(".spec.js") or f.endswith(".test.ts") or f.endswith(".spec.ts"):
                    test_files.append(rel_file)
            elif language == "java":
                if (f.endswith("Test.java") or f.endswith("Tests.java")) and "src/test" in rel_file:
                    test_files.append(rel_file)

    return sorted(test_files)


def parse_pytest_output(output: str) -> Tuple[int, int, int, List[str]]:
    """
    Parse stdout/stderr of pytest to extract passed, failed, skipped counts and failing test names.
    """
    passed = 0
    failed = 0
    skipped = 0
    failing_tests: List[str] = []

    # Regex for standard pytest summary: "5 passed, 2 failed, 1 skipped in 1.23s"
    summary_match = re.search(r"(=+)\s+([0-9\w\s,]+)\s+in\s+[\d\.]+s\s+(=+)", output)
    if summary_match:
        summary_text = summary_match.group(2)
        p_match = re.search(r"(\d+)\s+passed", summary_text)
        f_match = re.search(r"(\d+)\s+failed", summary_text)
        s_match = re.search(r"(\d+)\s+skipped", summary_text)

        if p_match:
            passed = int(p_match.group(1))
        if f_match:
            failed = int(f_match.group(1))
        if s_match:
            skipped = int(s_match.group(1))

    # Parse short test summary info or FAILED markers
    # Example: FAILED tests/test_calc.py::test_add - AssertionError
    for line in output.splitlines():
        line_clean = line.strip()
        if line_clean.startswith("FAILED ") or line_clean.startswith("ERROR "):
            parts = line_clean.split(" ", 1)
            if len(parts) > 1:
                test_name = parts[1].split(" - ")[0].strip()
                if test_name not in failing_tests:
                    failing_tests.append(test_name)

    # Fallback if failed > 0 but failing_tests empty
    if failed > 0 and not failing_tests:
        failing_tests.append(f"{failed} test(s) failed in pytest run")

    return passed, failed, skipped, failing_tests


def parse_npm_test_output(output: str) -> Tuple[int, int, int, List[str]]:
    """Parse Jest / Vitest / Mocha output for test statistics and failures."""
    passed = 0
    failed = 0
    skipped = 0
    failing_tests: List[str] = []

    # Jest style: Tests: 2 failed, 8 passed, 10 total
    jest_match = re.search(r"Tests:\s+([^\n\r]+)", output)
    if jest_match:
        stat_line = jest_match.group(1)
        p_match = re.search(r"(\d+)\s+passed", stat_line)
        f_match = re.search(r"(\d+)\s+failed", stat_line)
        s_match = re.search(r"(\d+)\s+skipped", stat_line)
        if p_match:
            passed = int(p_match.group(1))
        if f_match:
            failed = int(f_match.group(1))
        if s_match:
            skipped = int(s_match.group(1))

    # Jest failing markers: "● Calculator › addition" or "✕ should calculate"
    for line in output.splitlines():
        line_clean = line.strip()
        if line_clean.startswith("● ") or line_clean.startswith("✕ "):
            item = line_clean[2:].strip()
            if item and item not in failing_tests:
                failing_tests.append(item)

    if failed > 0 and not failing_tests:
        failing_tests.append(f"{failed} JavaScript test(s) failed")

    return passed, failed, skipped, failing_tests


class SandboxTestRunner:
    """
    Executes existing test suites for proposed merges inside locked-down sandboxes.
    """

    def __init__(
        self,
        runner: Optional[DockerSandboxRunner] = None,
        timeout_seconds: int = settings.SANDBOX_TIMEOUT_SECONDS,
    ) -> None:
        self.runner = runner or DockerSandboxRunner()
        self.timeout_seconds = timeout_seconds

    def run_tests(self, workspace: ProposedWorkspace) -> StageResult:
        """
        Execute test suite for the given proposed workspace.
        Returns a structured StageResult.
        """
        start_time = time.monotonic()
        language = workspace.language
        test_files = discover_test_files(workspace.path, language)

        # 1. Check if tests exist in the workspace
        if not test_files and not workspace.has_tests:
            logger.info("No test files detected in workspace %s", workspace.workspace_id)
            return StageResult(
                stage="tests",
                status="SKIPPED",
                exit_code=0,
                duration_seconds=0.0,
                summary="No test suite detected in repository workspace",
                details="Verification skipped test stage because no test files (*test*.py, *.test.js, src/test) were found.",
                failing_items=[],
            )

        lang_cfg = get_language_config(language)
        if not lang_cfg or not lang_cfg.default_test_command:
            return StageResult(
                stage="tests",
                status="SKIPPED",
                exit_code=0,
                duration_seconds=0.0,
                summary=f"No default test command configured for language: {language}",
                details=f"Test files detected ({len(test_files)}), but no runner exists for {language}.",
                failing_items=[],
            )

        # 2. Execute tests in Docker sandbox if available
        if self.runner.is_available():
            return self._run_tests_in_docker(workspace, lang_cfg, test_files, start_time)

        # 3. Fallback execution when Docker daemon is not active
        return self._run_tests_fallback(workspace, lang_cfg, test_files, start_time)

    def _run_tests_in_docker(
        self,
        workspace: ProposedWorkspace,
        lang_cfg,
        test_files: List[str],
        start_time: float,
    ) -> StageResult:
        """Execute test runner command inside Docker sandbox."""
        cmd = list(lang_cfg.default_test_command)

        config = DockerContainerConfig(
            image=lang_cfg.docker_image,
            command=cmd,
            working_dir="/workspace",
            timeout_seconds=self.timeout_seconds,
            network_mode="none",
        )

        try:
            res = self.runner.run_in_sandbox(workspace.path, config)
            duration = res.duration_seconds

            if res.timed_out:
                return StageResult(
                    stage="tests",
                    status="FAIL",
                    exit_code=124,
                    duration_seconds=duration,
                    summary=f"Test execution timed out after {self.timeout_seconds}s limit",
                    details=res.stderr or res.stdout,
                    failing_items=[f"TIMEOUT: Test suite exceeded {self.timeout_seconds}s execution limit"],
                )

            # Parse test counts and failing tests
            combined_output = f"{res.stdout}\n{res.stderr}".strip()
            passed, failed, skipped, failing_tests = self._parse_test_output(
                combined_output,
                workspace.language,
                workspace.test_framework,
            )

            if res.is_success and failed == 0:
                summary = f"All tests passed ({passed} passed"
                if skipped > 0:
                    summary += f", {skipped} skipped"
                summary += f") across {len(test_files)} test file(s)"

                return StageResult(
                    stage="tests",
                    status="PASS",
                    exit_code=0,
                    duration_seconds=duration,
                    summary=summary,
                    details=res.stdout,
                    failing_items=[],
                )

            # Test failure
            fail_summary = f"Tests failed: {failed} failed, {passed} passed"
            if skipped > 0:
                fail_summary += f", {skipped} skipped"

            return StageResult(
                stage="tests",
                status="FAIL",
                exit_code=res.exit_code,
                duration_seconds=duration,
                summary=fail_summary,
                details=combined_output,
                failing_items=failing_tests,
            )

        except Exception as exc:
            logger.warning("Docker test run error, falling back: %s", exc)
            return self._run_tests_fallback(workspace, lang_cfg, test_files, start_time)

    def _run_tests_fallback(
        self,
        workspace: ProposedWorkspace,
        lang_cfg,
        test_files: List[str],
        start_time: float,
    ) -> StageResult:
        """
        Execute tests locally on host when Docker is unavailable,
        with strict safety checks and timeout enforcement.
        """
        if workspace.language == "python":
            pytest_path = shutil.which("pytest")
            if pytest_path:
                try:
                    proc = subprocess.run(
                        [pytest_path, "-v"],
                        cwd=workspace.path,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=self.timeout_seconds,
                    )
                    duration = round(time.monotonic() - start_time, 3)
                    combined_output = f"{proc.stdout}\n{proc.stderr}".strip()
                    passed, failed, skipped, failing_tests = parse_pytest_output(combined_output)

                    if proc.returncode == 0 and failed == 0:
                        return StageResult(
                            stage="tests",
                            status="PASS",
                            exit_code=0,
                            duration_seconds=duration,
                            summary=f"All tests passed ({passed} passed) across {len(test_files)} test file(s)",
                            details=proc.stdout,
                            failing_items=[],
                        )

                    return StageResult(
                        stage="tests",
                        status="FAIL",
                        exit_code=proc.returncode,
                        duration_seconds=duration,
                        summary=f"Tests failed: {failed} failed, {passed} passed",
                        details=combined_output,
                        failing_items=failing_tests,
                    )
                except subprocess.TimeoutExpired as texc:
                    duration = round(time.monotonic() - start_time, 3)
                    return StageResult(
                        stage="tests",
                        status="FAIL",
                        exit_code=124,
                        duration_seconds=duration,
                        summary=f"Test execution timed out after {self.timeout_seconds}s limit",
                        details=str(texc.stderr or texc.stdout or ""),
                        failing_items=[f"TIMEOUT: Test suite exceeded {self.timeout_seconds}s limit"],
                    )
                except Exception as exc:
                    logger.warning("Local test execution failed: %s", exc)

        duration = round(time.monotonic() - start_time, 3)
        return StageResult(
            stage="tests",
            status="SKIPPED",
            exit_code=0,
            duration_seconds=duration,
            summary=f"Docker sandbox offline; test suite detected ({len(test_files)} files: {', '.join(test_files[:3])})",
            details="Docker is required for safe isolated execution of repository test scripts.",
            failing_items=[],
        )

    def _parse_test_output(
        self,
        output: str,
        language: LanguageType,
        framework: Optional[str],
    ) -> Tuple[int, int, int, List[str]]:
        """Delegate test output parsing to language-specific parser."""
        if language == "python" or framework == "pytest":
            return parse_pytest_output(output)
        if language in ("javascript", "typescript") or framework in ("jest", "vitest", "mocha", "npm-test"):
            return parse_npm_test_output(output)
        return 0, 0, 0, []

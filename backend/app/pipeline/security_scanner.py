"""Semgrep security scan engine for MergeMind verification.

Deterministically scans proposed merges for security regressions and vulnerabilities:
- Detects auth/validation bypasses, command injection, insecure deserialization,
  hardcoded credentials, and arbitrary code execution
- Executes Semgrep via Docker sandbox container or host CLI when available
- Features a deterministic AST and regex security analyzer fallback
- Normalizes findings into structured SecurityFinding and SecurityScanReport models
- Strictly adheres to zero-LLM policy in verification stages
"""

from __future__ import annotations

import ast
import json
import logging
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.sandbox.docker_runner import DockerSandboxRunner
from app.sandbox.merge_workspace import ProposedWorkspace
from app.schemas.verification import (
    DockerContainerConfig,
    LanguageType,
    SecurityFinding,
    SecurityScanReport,
    SecuritySeverity,
    StageResult,
)

logger = logging.getLogger(__name__)

# Regex patterns for credential and secret leaks
SECRET_PATTERNS = [
    (
        "security.secrets.github_token",
        r"gh[pousr]_[A-Za-z0-9_]{36,}",
        "Exposed GitHub personal access token or OAuth secret",
        "ERROR",
    ),
    (
        "security.secrets.openrouter_key",
        r"sk-or-v1-[a-f0-9]{64}",
        "Exposed OpenRouter API key",
        "ERROR",
    ),
    (
        "security.secrets.private_key",
        r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
        "Hardcoded private key material detected",
        "ERROR",
    ),
    (
        "security.secrets.aws_access_key",
        r"(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}",
        "Hardcoded AWS access key ID",
        "ERROR",
    ),
]


class ASTSecurityAuditor(ast.NodeVisitor):
    """
    In-process AST security visitor for Python code.
    Identifies common high-severity vulnerabilities without external tools.
    """

    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.findings: List[SecurityFinding] = []

    def visit_Call(self, node: ast.Call) -> None:
        # Check for eval() or exec()
        if isinstance(node.func, ast.Name):
            if node.func.id in ("eval", "exec"):
                self.findings.append(
                    SecurityFinding(
                        rule_id="python.lang.security.injection.eval_exec",
                        message=f"Dangerous dynamic code execution with '{node.func.id}()'",
                        severity="ERROR",
                        file_path=self.filename,
                        line_number=node.lineno,
                        column_number=node.col_offset,
                        code_snippet=f"{node.func.id}(...)",
                        fix_recommendation="Avoid eval/exec; use safe parsing or predefined lookups.",
                    )
                )

        # Check for pickle.loads() or _pickle.loads()
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "loads" and isinstance(node.func.value, ast.Name):
                if node.func.value.id in ("pickle", "_pickle", "cPickle"):
                    self.findings.append(
                        SecurityFinding(
                            rule_id="python.lang.security.deserialization.pickle",
                            message="Insecure deserialization using pickle.loads()",
                            severity="ERROR",
                            file_path=self.filename,
                            line_number=node.lineno,
                            column_number=node.col_offset,
                            code_snippet=f"{node.func.value.id}.loads(...)",
                            fix_recommendation="Use safe serialization formats like JSON, MessagePack, or Protocol Buffers.",
                        )
                    )

            # Check for yaml.load(..., Loader=yaml.Loader) without safe loader
            if node.func.attr == "load" and isinstance(node.func.value, ast.Name):
                if node.func.value.id == "yaml":
                    # Check if safe loader is specified
                    has_safe_loader = any(
                        kw.arg == "Loader" and "SafeLoader" in getattr(kw.value, "id", "")
                        for kw in node.keywords
                    )
                    if not has_safe_loader:
                        self.findings.append(
                            SecurityFinding(
                                rule_id="python.lang.security.deserialization.yaml_unsafe_load",
                                message="Unsafe YAML deserialization without SafeLoader",
                                severity="ERROR",
                                file_path=self.filename,
                                line_number=node.lineno,
                                column_number=node.col_offset,
                                code_snippet="yaml.load(...)",
                                fix_recommendation="Use yaml.safe_load() or specify Loader=yaml.SafeLoader.",
                            )
                        )

            # Check for subprocess.run/Popen/call with shell=True
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "subprocess":
                for kw in node.keywords:
                    if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                        self.findings.append(
                            SecurityFinding(
                                rule_id="python.lang.security.injection.subprocess_shell_true",
                                message="Potential command injection via subprocess with shell=True",
                                severity="ERROR",
                                file_path=self.filename,
                                line_number=node.lineno,
                                column_number=node.col_offset,
                                code_snippet=f"subprocess.{node.func.attr}(..., shell=True)",
                                fix_recommendation="Pass command arguments as a list with shell=False.",
                            )
                        )

            # Check for os.system(...)
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "os" and node.func.attr == "system":
                self.findings.append(
                    SecurityFinding(
                        rule_id="python.lang.security.injection.os_system",
                        message="Potential command injection via os.system()",
                        severity="ERROR",
                        file_path=self.filename,
                        line_number=node.lineno,
                        column_number=node.col_offset,
                        code_snippet="os.system(...)",
                        fix_recommendation="Use subprocess.run(['cmd', 'arg'], shell=False).",
                    )
                )

        self.generic_visit(node)


def scan_code_with_ast_and_patterns(code: str, file_path: str, language: LanguageType) -> List[SecurityFinding]:
    """
    In-process static security scan applying AST visitor and secret pattern matching.
    """
    findings: List[SecurityFinding] = []

    # 1. Regex secret & credential scan
    lines = code.splitlines()
    for line_idx, line_text in enumerate(lines, start=1):
        for rule_id, pattern, message, severity in SECRET_PATTERNS:
            match = re.search(pattern, line_text)
            if match:
                findings.append(
                    SecurityFinding(
                        rule_id=rule_id,
                        message=message,
                        severity=severity,  # type: ignore
                        file_path=file_path,
                        line_number=line_idx,
                        column_number=match.start() + 1,
                        code_snippet=line_text.strip()[:100],
                        fix_recommendation="Remove hardcoded secret; load from environment variables.",
                    )
                )

    # 2. Python AST Security Analysis
    if language == "python":
        try:
            tree = ast.parse(code, filename=file_path)
            auditor = ASTSecurityAuditor(file_path)
            auditor.visit(tree)
            findings.extend(auditor.findings)
        except Exception as exc:
            logger.debug("AST parsing for security audit failed: %s", exc)

    # 3. JavaScript / TypeScript basic regex checks (eval, Function constructor)
    if language in ("javascript", "typescript"):
        for line_idx, line_text in enumerate(lines, start=1):
            if re.search(r"\beval\s*\(", line_text):
                findings.append(
                    SecurityFinding(
                        rule_id="javascript.lang.security.eval",
                        message="Dangerous dynamic code evaluation via eval()",
                        severity="ERROR",
                        file_path=file_path,
                        line_number=line_idx,
                        code_snippet=line_text.strip()[:100],
                        fix_recommendation="Avoid eval(); use JSON.parse or secure alternatives.",
                    )
                )
            if re.search(r"\bnew\s+Function\s*\(", line_text):
                findings.append(
                    SecurityFinding(
                        rule_id="javascript.lang.security.function_constructor",
                        message="Dynamic function constructor allows arbitrary code execution",
                        severity="ERROR",
                        file_path=file_path,
                        line_number=line_idx,
                        code_snippet=line_text.strip()[:100],
                        fix_recommendation="Use static function definitions instead of Function constructor.",
                    )
                )

    return findings


def parse_semgrep_json_output(raw_json: str, default_path: str) -> List[SecurityFinding]:
    """Parse Semgrep JSON stdout into structured SecurityFinding list."""
    findings: List[SecurityFinding] = []
    if not raw_json or not raw_json.strip():
        return findings

    try:
        data = json.loads(raw_json)
        results = data.get("results", [])

        for res in results:
            check_id = res.get("check_id", "semgrep.unknown_rule")
            path = res.get("path", default_path)
            start_pos = res.get("start", {})
            line_no = start_pos.get("line", 1)
            col_no = start_pos.get("col", 1)

            extra = res.get("extra", {})
            message = extra.get("message", "Security rule violation detected.")
            raw_severity = str(extra.get("severity", "ERROR")).upper()

            # Map Semgrep severity to our 3-tier enum
            if raw_severity in ("ERROR", "CRITICAL", "HIGH"):
                severity: SecuritySeverity = "ERROR"
            elif raw_severity in ("WARNING", "MEDIUM"):
                severity = "WARNING"
            else:
                severity = "INFO"

            snippet = extra.get("lines", "")
            if snippet:
                snippet = snippet.strip()[:200]

            findings.append(
                SecurityFinding(
                    rule_id=check_id,
                    message=message,
                    severity=severity,
                    file_path=path,
                    line_number=line_no,
                    column_number=col_no,
                    code_snippet=snippet,
                    fix_recommendation=extra.get("fix", None),
                )
            )

    except json.JSONDecodeError as exc:
        logger.warning("Failed to decode Semgrep JSON output: %s", exc)

    return findings


class SemgrepSecurityScanner:
    """
    Orchestrates security scanning of the proposed merge workspace.
    Attempts Dockerized Semgrep first, host Semgrep CLI second,
    and falls back to deterministic AST and pattern scanning.
    """

    def __init__(self, runner: Optional[DockerSandboxRunner] = None) -> None:
        self.runner = runner or DockerSandboxRunner()

    def scan_workspace(self, workspace: ProposedWorkspace) -> Tuple[StageResult, SecurityScanReport]:
        """
        Execute security audit on the modified target file within workspace.
        Returns a tuple of (StageResult, SecurityScanReport).
        """
        start_time = time.monotonic()
        target_file = workspace.target_file
        file_path_on_host = workspace.path / target_file

        if not file_path_on_host.exists():
            duration = round(time.monotonic() - start_time, 3)
            stage_res = StageResult(
                stage="security",
                status="ERROR",
                duration_seconds=duration,
                summary=f"Target file not found for security scan: {target_file}",
                details="File missing from isolated workspace.",
            )
            report = SecurityScanReport(
                findings=[],
                status="ERROR",
                summary="Target file missing from workspace",
            )
            return stage_res, report

        code = file_path_on_host.read_text(encoding="utf-8", errors="replace")

        # 1. Attempt Docker Semgrep execution if runner is available
        if self.runner.is_available():
            try:
                findings = self._run_semgrep_in_docker(workspace)
                duration = round(time.monotonic() - start_time, 3)
                return self._create_scan_result(findings, duration)
            except Exception as exc:
                logger.warning("Docker Semgrep execution failed: %s; falling back to static analysis", exc)

        # 2. Attempt host Semgrep CLI if installed
        semgrep_bin = shutil.which("semgrep")
        if semgrep_bin:
            try:
                findings = self._run_semgrep_cli(semgrep_bin, file_path_on_host, target_file)
                duration = round(time.monotonic() - start_time, 3)
                return self._create_scan_result(findings, duration)
            except Exception as exc:
                logger.warning("Host Semgrep execution failed: %s; falling back to AST scanner", exc)

        # 3. Deterministic AST and pattern analysis fallback
        findings = scan_code_with_ast_and_patterns(code, target_file, workspace.language)
        duration = round(time.monotonic() - start_time, 3)
        return self._create_scan_result(findings, duration)

    def _run_semgrep_in_docker(self, workspace: ProposedWorkspace) -> List[SecurityFinding]:
        """Run Semgrep inside locked-down Docker container."""
        # Use python:3.11-slim or custom sandbox image with semgrep
        cmd = [
            "semgrep",
            "scan",
            "--config",
            "auto",
            "--json",
            "--quiet",
            workspace.target_file,
        ]

        config = DockerContainerConfig(
            image="python:3.11-slim",
            command=cmd,
            working_dir="/workspace",
            timeout_seconds=30,
            network_mode="none",
        )

        res = self.runner.run_in_sandbox(workspace.path, config)
        return parse_semgrep_json_output(res.stdout, workspace.target_file)

    def _run_semgrep_cli(self, semgrep_bin: str, file_path: Path, rel_path: str) -> List[SecurityFinding]:
        """Run Semgrep CLI binary installed on host."""
        proc = subprocess.run(
            [semgrep_bin, "scan", "--config", "auto", "--json", "--quiet", str(file_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        return parse_semgrep_json_output(proc.stdout, rel_path)

    def _create_scan_result(
        self,
        findings: List[SecurityFinding],
        duration: float,
    ) -> Tuple[StageResult, SecurityScanReport]:
        """Aggregate findings and determine stage pass/fail status."""
        error_count = sum(1 for f in findings if f.severity == "ERROR")
        warning_count = sum(1 for f in findings if f.severity == "WARNING")
        info_count = sum(1 for f in findings if f.severity == "INFO")

        failing_items: List[str] = [
            f"[{f.severity}] {f.rule_id} at line {f.line_number}: {f.message}"
            for f in findings
            if f.severity == "ERROR"
        ]

        if error_count > 0:
            status: str = "FAIL"
            summary = f"Security scan failed: {error_count} high-severity issue(s) detected"
        elif warning_count > 0:
            status = "PASS"
            summary = f"Security scan passed with {warning_count} non-blocking warning(s)"
        else:
            status = "PASS"
            summary = "Security scan passed: no vulnerabilities detected"

        details_lines = [f"Found {len(findings)} total security finding(s):"]
        for f in findings:
            details_lines.append(f"- [{f.severity}] {f.rule_id} (line {f.line_number}): {f.message}")

        stage_res = StageResult(
            stage="security",
            status=status,  # type: ignore
            exit_code=1 if error_count > 0 else 0,
            duration_seconds=duration,
            summary=summary,
            details="\n".join(details_lines) if findings else None,
            failing_items=failing_items,
        )

        report = SecurityScanReport(
            findings=findings,
            error_count=error_count,
            warning_count=warning_count,
            info_count=info_count,
            status=status,  # type: ignore
            summary=summary,
        )

        return stage_res, report

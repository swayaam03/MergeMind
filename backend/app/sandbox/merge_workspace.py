"""Merge proposal application engine for MergeMind verification.

Prepares an isolated workspace containing the proposed merge:
- Reconstructs or copies repository structure without secrets or VCS bloat
- Replaces strictly the single affected file with the LLM's merged_code
- Normalizes file line endings and verifies path traversal security
- Detects workspace language and test suites for subsequent verification stages
"""

from __future__ import annotations

import logging
import os
import shutil
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Set, Union

from app.sandbox.language_configs import detect_file_language, detect_workspace_test_framework
from app.sandbox.workspace import (
    FORBIDDEN_FILE_PATTERNS,
    IsolatedWorkspace,
    WorkspaceSecurityError,
    _on_rm_error,
    is_forbidden_file,
    is_path_safe,
)
from app.schemas.verification import LanguageType, ProposedWorkspaceInfo

logger = logging.getLogger(__name__)

# Directories that should be skipped when copying from a source repository
IGNORED_DIR_NAMES: Set[str] = {
    ".git",
    ".github",
    ".idea",
    ".vscode",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "node_modules",
    ".next",
    ".dist",
    "dist",
    "build",
    "target",
    ".gradle",
    "venv",
    ".venv",
    "env",
    ".env",
}


class ProposedWorkspace:
    """
    An isolated verification workspace containing the full repository structure
    with the LLM merge proposal applied to the target conflicted file.
    """

    def __init__(
        self,
        workspace_id: str,
        workspace: IsolatedWorkspace,
        target_file: str,
        language: LanguageType,
        has_tests: bool,
        test_framework: Optional[str],
        replaced_file_size: int,
    ) -> None:
        self.workspace_id = workspace_id
        self.workspace = workspace
        self.target_file = target_file
        self.language = language
        self.has_tests = has_tests
        self.test_framework = test_framework
        self.replaced_file_size = replaced_file_size

    @property
    def path(self) -> Path:
        """Absolute directory path to the workspace."""
        if self.workspace.path is None:
            raise RuntimeError("Workspace has not been initialized.")
        return self.workspace.path

    @property
    def file_count(self) -> int:
        """Total number of files in the isolated workspace."""
        return len(self.workspace.list_files())

    def info(self) -> ProposedWorkspaceInfo:
        """Produce a structured Pydantic info object for reporting."""
        return ProposedWorkspaceInfo(
            workspace_id=self.workspace_id,
            workspace_path=str(self.path),
            target_file=self.target_file,
            language=self.language,
            file_count=len(self.workspace.list_files()),
            has_test_suite=self.has_tests,
            test_framework=self.test_framework,
            replaced_file_size=self.replaced_file_size,
        )

    def cleanup(self) -> None:
        """Clean up the underlying isolated workspace."""
        self.workspace.cleanup()

    def __enter__(self) -> ProposedWorkspace:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.cleanup()


def normalize_code_content(content: str) -> str:
    """Normalize line endings to UNIX LF and ensure trailing newline."""
    if not content:
        return ""
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.endswith("\n"):
        normalized += "\n"
    return normalized


def copy_source_repo_sanitized(src_dir: Path, dest_dir: Path) -> int:
    """
    Safely copy repository structure from src_dir to dest_dir.
    Skips secret files, forbidden credentials, and heavy cache/vcs folders.
    Returns the count of copied files.
    """
    copied_count = 0
    resolved_src = src_dir.resolve()

    for root, dirs, files in os.walk(resolved_src):
        # Prune ignored directories in-place
        dirs[:] = [d for d in dirs if d not in IGNORED_DIR_NAMES and not is_forbidden_file(d)]

        rel_root = Path(root).relative_to(resolved_src)
        target_root = dest_dir / rel_root

        for f in files:
            if is_forbidden_file(f):
                continue

            src_file = Path(root) / f
            dest_file = target_root / f

            # Security check: ensure target does not escape destination
            if not is_path_safe(dest_dir, dest_file):
                continue

            dest_file.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(src_file, dest_file)
                copied_count += 1
            except Exception as exc:
                logger.warning("Failed to copy file %s to workspace: %s", src_file, exc)

    return copied_count


def apply_merge_to_workspace(
    target_file: str,
    merged_code: str,
    source_repo_path: Optional[str | Path] = None,
    source_files: Optional[Dict[str, str]] = None,
    workspace_prefix: str = "mergemind_verify_",
) -> ProposedWorkspace:
    """
    Create an isolated workspace, apply the repository files, and replace the
    target conflicted file with the LLM's merged_code.

    Parameters:
    - target_file: Relative path of the file to replace (e.g. 'src/math_utils.py')
    - merged_code: The resolved code proposed by the LLM
    - source_repo_path: Optional path to host repository to clone structure from
    - source_files: Optional dict of {relative_path: content} for memory/PR based structures
    - workspace_prefix: Temp directory prefix

    Returns:
    - Initialized ProposedWorkspace ready for verification
    """
    # Normalize target file path (strip leading slashes or Windows drive indicators)
    cleaned_target = target_file.strip().replace("\\", "/")
    if cleaned_target.startswith("/"):
        cleaned_target = cleaned_target.lstrip("/")

    if ".." in cleaned_target.split("/"):
        raise WorkspaceSecurityError(f"Target file path '{target_file}' cannot contain parent directory traversals ('..')")

    workspace_id = f"ws_{uuid.uuid4().hex[:12]}"
    workspace = IsolatedWorkspace(prefix=f"{workspace_prefix}{workspace_id}_")
    workspace_path = workspace.create()

    # 1. Populate workspace from source directory if provided
    if source_repo_path:
        src = Path(source_repo_path)
        if src.exists() and src.is_dir():
            copy_source_repo_sanitized(src, workspace_path)

    # 2. Populate workspace from in-memory file dictionary if provided
    if source_files:
        for rel_path, content in source_files.items():
            norm_rel = rel_path.strip().replace("\\", "/").lstrip("/")
            if is_forbidden_file(norm_rel):
                continue
            if ".." in norm_rel.split("/"):
                continue
            workspace.write_file(norm_rel, content)

    # 3. Apply merged_code to the target file
    normalized_merged_code = normalize_code_content(merged_code)
    applied_path = workspace.write_file(cleaned_target, normalized_merged_code)

    # 4. Verify that target file exists and content matches
    if not applied_path.exists():
        workspace.cleanup()
        raise RuntimeError(f"Failed to apply merged code to target file: {cleaned_target}")

    replaced_file_size = applied_path.stat().st_size

    # 5. Detect language and test framework
    language = detect_file_language(cleaned_target)
    test_framework = detect_workspace_test_framework(workspace_path, language)
    has_tests = test_framework is not None

    logger.info(
        "Prepared proposed workspace %s for '%s' (lang=%s, has_tests=%s, test_framework=%s)",
        workspace_id,
        cleaned_target,
        language,
        has_tests,
        test_framework,
    )

    return ProposedWorkspace(
        workspace_id=workspace_id,
        workspace=workspace,
        target_file=cleaned_target,
        language=language,
        has_tests=has_tests,
        test_framework=test_framework,
        replaced_file_size=replaced_file_size,
    )


@contextmanager
def prepare_proposed_workspace(
    target_file: str,
    merged_code: str,
    source_repo_path: Optional[str | Path] = None,
    source_files: Optional[Dict[str, str]] = None,
) -> Generator[ProposedWorkspace, None, None]:
    """Context manager for preparing a proposed workspace with guaranteed cleanup."""
    pw = apply_merge_to_workspace(
        target_file=target_file,
        merged_code=merged_code,
        source_repo_path=source_repo_path,
        source_files=source_files,
    )
    try:
        yield pw
    finally:
        pw.cleanup()

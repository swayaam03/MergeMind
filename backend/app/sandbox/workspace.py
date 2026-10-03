"""Isolated workspace management for sandbox verification.

Provides temporary, secure filesystem environments where merged code can be applied
and tested without risk to the host repository, operating system, or environment.
"""

from __future__ import annotations

import logging
import os
import shutil
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, List, Optional, Set

logger = logging.getLogger(__name__)

# Files and patterns that should never be copied into the sandbox workspace
FORBIDDEN_FILE_PATTERNS: Set[str] = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    ".git",
    "id_rsa",
    "id_ed25519",
    "*.pem",
    "*.key",
    "credentials",
    "secrets",
    ".aws",
    ".ssh",
    ".netrc",
}


class WorkspaceSecurityError(Exception):
    """Raised when a file path violates sandbox workspace boundary safety."""
    pass


def _on_rm_error(func, path, exc_info):
    """Handle read-only files on Windows during directory cleanup."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


def is_path_safe(base_dir: Path, target_path: Path) -> bool:
    """
    Verify that target_path resolves strictly within base_dir.
    Prevents directory traversal attacks (e.g. ../../etc/passwd).
    """
    try:
        resolved_base = base_dir.resolve()
        resolved_target = target_path.resolve()
        return resolved_target == resolved_base or resolved_base in resolved_target.parents
    except Exception:
        return False


def is_forbidden_file(filename: str) -> bool:
    """Check if a filename or path matches known secret or sensitive file patterns."""
    basename = Path(filename).name.lower()
    for pattern in FORBIDDEN_FILE_PATTERNS:
        if pattern.startswith("*."):
            ext = pattern[1:]
            if basename.endswith(ext):
                return True
        elif basename == pattern or pattern in basename:
            return True
    return False


class IsolatedWorkspace:
    """
    Manages the lifecycle of a secure, isolated temporary directory on the host.
    Ensures safe creation, isolated permissioning, and guaranteed cleanup.
    """

    def __init__(self, prefix: str = "mergemind_sandbox_") -> None:
        self.prefix = prefix
        self.path: Optional[Path] = None
        self._is_cleaned_up = False

    def create(self) -> Path:
        """Create the temporary isolated directory."""
        if self.path is not None and self.path.exists():
            return self.path

        raw_dir = tempfile.mkdtemp(prefix=self.prefix)
        self.path = Path(raw_dir).resolve()
        self._is_cleaned_up = False
        logger.debug("Created isolated workspace at: %s", self.path)
        return self.path

    def cleanup(self) -> None:
        """Completely remove the temporary directory and all its contents."""
        if self.path and self.path.exists() and not self._is_cleaned_up:
            try:
                shutil.rmtree(self.path, onerror=_on_rm_error)
                self._is_cleaned_up = True
                logger.debug("Cleaned up isolated workspace at: %s", self.path)
            except Exception as exc:
                logger.warning("Error during workspace cleanup for %s: %s", self.path, exc)

    def write_file(self, relative_path: str | Path, content: str | bytes) -> Path:
        """
        Safely write content to a file inside the isolated workspace.
        Ensures the path does not escape the workspace boundary.
        """
        if self.path is None:
            raise RuntimeError("Workspace has not been created yet.")

        target = (self.path / relative_path).resolve()
        if not is_path_safe(self.path, target):
            raise WorkspaceSecurityError(
                f"Path traversal detected: '{relative_path}' resolves outside workspace boundary"
            )

        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, str):
            target.write_text(content, encoding="utf-8", errors="replace")
        else:
            target.write_bytes(content)
        return target

    def read_file(self, relative_path: str | Path) -> str:
        """Safely read content from a file inside the workspace."""
        if self.path is None:
            raise RuntimeError("Workspace has not been created yet.")

        target = (self.path / relative_path).resolve()
        if not is_path_safe(self.path, target):
            raise WorkspaceSecurityError(
                f"Path traversal detected: '{relative_path}' resolves outside workspace boundary"
            )
        if not target.exists():
            raise FileNotFoundError(f"File not found in workspace: {relative_path}")

        return target.read_text(encoding="utf-8", errors="replace")

    def list_files(self) -> List[str]:
        """List all files in the workspace relative to its root."""
        if self.path is None or not self.path.exists():
            return []

        rel_paths: List[str] = []
        for root, _, files in os.walk(self.path):
            root_path = Path(root)
            for f in files:
                full_path = root_path / f
                try:
                    rel_paths.append(str(full_path.relative_to(self.path)).replace("\\", "/"))
                except ValueError:
                    continue
        return rel_paths

    def __enter__(self) -> IsolatedWorkspace:
        self.create()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.cleanup()


@contextmanager
def temporary_workspace(prefix: str = "mergemind_sandbox_") -> Generator[IsolatedWorkspace, None, None]:
    """Context manager yielding an IsolatedWorkspace with guaranteed cleanup."""
    workspace = IsolatedWorkspace(prefix=prefix)
    try:
        workspace.create()
        yield workspace
    finally:
        workspace.cleanup()

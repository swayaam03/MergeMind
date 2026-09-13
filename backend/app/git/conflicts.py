"""Git conflict extraction and simulation engine for MergeMind.

Deterministically extracts merge conflicts for a given pull request by simulating
a 3-way Git merge in an isolated temporary directory. Identifies conflicting files,
extracts Base (common ancestor), Local (target/base branch), and Remote (source/head branch)
versions along with blob SHAs and conflict markers.

ZERO arbitrary repository code or build scripts are executed.
All operations are read-only Git metadata simulations.
"""

import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Map file extensions to standard language identifiers
LANGUAGE_MAP: dict[str, str] = {
    ".py": "python",
    ".pyw": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "scss",
    ".json": "json",
    ".xml": "xml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".md": "markdown",
    ".sql": "sql",
    ".sh": "shell",
    ".bash": "shell",
}


class GitConflictError(Exception):
    """Raised when a Git simulation or extraction operation fails."""

    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


def detect_language(file_path: str) -> str:
    """Detect the programming language from the file extension."""
    ext = Path(file_path).suffix.lower()
    return LANGUAGE_MAP.get(ext, "unknown")


def sanitize_text(text: str, secret_tokens: list[str] | None = None) -> str:
    """
    Scrub sensitive access tokens, JWTs, and URLs with credentials from error logs and strings.
    """
    if not text:
        return ""
    cleaned = text
    # Mask URL credentials e.g. https://x-access-token:...@github.com
    cleaned = re.sub(
        r"(https?://)([^@/\s]+)@",
        r"\1[REDACTED_CREDENTIALS]@",
        cleaned,
    )
    # Mask common GitHub tokens
    cleaned = re.sub(r"gh[sptr]_[A-Za-z0-9_]{10,}", "[REDACTED_TOKEN]", cleaned)
    if secret_tokens:
        for token in secret_tokens:
            if token and token in cleaned:
                cleaned = cleaned.replace(token, "[REDACTED_TOKEN]")
    return cleaned


def run_git_command(
    args: list[str],
    cwd: str | Path,
    secret_tokens: list[str] | None = None,
    timeout: float = 30.0,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """
    Safely execute a Git CLI command in a sandboxed working directory.
    Enforces GIT_TERMINAL_PROMPT=0 so Git never hangs on credential prompts.
    Never executes repository code.
    """
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_ASKPASS"] = "echo"

    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise GitConflictError("Git operation timed out.", status_code=504) from exc
    except FileNotFoundError as exc:
        raise GitConflictError("Git binary not found on the system.", status_code=500) from exc
    except Exception as exc:
        safe_msg = sanitize_text(str(exc), secret_tokens)
        raise GitConflictError(f"Failed to execute git command: {safe_msg}", status_code=500) from exc

    if check and result.returncode != 0:
        safe_err = sanitize_text(result.stderr.strip() or result.stdout.strip(), secret_tokens)
        raise GitConflictError(f"Git command failed: {safe_err}", status_code=500)

    return result


def parse_conflict_markers(content: str) -> dict[str, str]:
    """
    Extract 'ours' (local branch) and 'theirs' (remote branch) conflict blocks from a file.
    If multiple conflict hunks exist, concatenates them cleanly.
    """
    ours_chunks: list[str] = []
    theirs_chunks: list[str] = []

    lines = content.splitlines(keepends=True)
    in_ours = False
    in_theirs = False
    curr_ours: list[str] = []
    curr_theirs: list[str] = []

    for line in lines:
        if line.startswith("<<<<<<<"):
            in_ours = True
            in_theirs = False
            curr_ours = []
            curr_theirs = []
        elif line.startswith("=======") and in_ours:
            in_ours = False
            in_theirs = True
        elif line.startswith(">>>>>>>") and in_theirs:
            in_theirs = False
            if curr_ours:
                ours_chunks.append("".join(curr_ours))
            if curr_theirs:
                theirs_chunks.append("".join(curr_theirs))
        else:
            if in_ours:
                curr_ours.append(line)
            elif in_theirs:
                curr_theirs.append(line)

    return {
        "ours": "\n---\n".join(ours_chunks) if ours_chunks else "",
        "theirs": "\n---\n".join(theirs_chunks) if theirs_chunks else "",
    }


def simulate_merge_and_extract_conflicts(
    owner: str,
    repo: str,
    pull_number: int,
    base_branch: str,
    head_branch: str,
    base_sha: str,
    head_sha: str,
    installation_token: str,
) -> dict[str, Any]:
    """
    Simulate Git merge in an isolated temporary directory to extract conflict information.

    Steps:
    1. Create temporary directory.
    2. Initialize bare-like minimal git environment with safe dummy user identity.
    3. Add authenticated remote using installation token.
    4. Fetch base branch and pull request head commit.
    5. Resolve deterministic merge-base commit SHA.
    6. Identify all changed files between base and head.
    7. Checkout base commit and simulate `git merge --no-commit --no-ff <head_sha>`.
    8. Extract unmerged files via `git ls-files -u` with Base (:1:), Local (:2:), and Remote (:3:) stages.
    9. Read content for each version and parse conflict markers from the working tree.
    10. Ensure the temporary directory is cleaned up upon completion.
    """
    secrets = [installation_token]
    remote_url = f"https://x-access-token:{installation_token}@github.com/{owner}/{repo}.git"

    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir)

        # 1. Initialize temporary Git repo
        run_git_command(["init"], cwd=temp_path, secret_tokens=secrets)
        run_git_command(["config", "user.name", "MergeMind"], cwd=temp_path, secret_tokens=secrets)
        run_git_command(["config", "user.email", "mergemind@local"], cwd=temp_path, secret_tokens=secrets)
        run_git_command(["remote", "add", "origin", remote_url], cwd=temp_path, secret_tokens=secrets)

        # 2. Fetch base ref and pull request head ref
        # Fetching refs/heads/<base_branch> and refs/pull/<pull_number>/head
        logger.info(
            "Fetching Git references for %s/%s PR #%d (base=%s, head=%s)",
            owner,
            repo,
            pull_number,
            base_branch,
            head_branch,
        )
        fetch_args = [
            "fetch",
            "--depth=100",
            "origin",
            f"refs/heads/{base_branch}",
            f"refs/pull/{pull_number}/head",
        ]
        try:
            run_git_command(fetch_args, cwd=temp_path, secret_tokens=secrets)
        except GitConflictError:
            # Fallback: attempt fetching by commit SHAs directly if ref lookup fails
            logger.info("Ref fetch fallback: fetching commit SHAs %s and %s", base_sha, head_sha)
            run_git_command(["fetch", "--depth=100", "origin", base_sha, head_sha], cwd=temp_path, secret_tokens=secrets)

        # 3. Determine common merge-base
        mb_proc = run_git_command(["merge-base", base_sha, head_sha], cwd=temp_path, secret_tokens=secrets, check=False)
        merge_base_sha = mb_proc.stdout.strip()

        # If merge-base wasn't found due to shallow history, deepen fetch
        if mb_proc.returncode != 0 or not merge_base_sha:
            logger.info("Merge base not found with depth=100; deepening fetch for full history.")
            run_git_command(["fetch", "--unshallow", "origin"], cwd=temp_path, secret_tokens=secrets, check=False)
            mb_proc = run_git_command(["merge-base", base_sha, head_sha], cwd=temp_path, secret_tokens=secrets, check=False)
            merge_base_sha = mb_proc.stdout.strip()

        # 4. Determine list of changed files in PR (diff between base and head)
        changed_proc = run_git_command(
            ["diff", "--name-only", f"{base_sha}...{head_sha}"],
            cwd=temp_path,
            secret_tokens=secrets,
            check=False,
        )
        changed_files: list[str] = [
            f.strip() for f in changed_proc.stdout.splitlines() if f.strip()
        ]
        if not changed_files:
            # If triple-dot diff is empty, fallback to double-dot diff
            fallback_proc = run_git_command(
                ["diff", "--name-only", base_sha, head_sha],
                cwd=temp_path,
                secret_tokens=secrets,
                check=False,
            )
            changed_files = [f.strip() for f in fallback_proc.stdout.splitlines() if f.strip()]

        # 5. Checkout base commit (detached HEAD)
        run_git_command(["checkout", base_sha], cwd=temp_path, secret_tokens=secrets)

        # 6. Simulate merge with source commit (head_sha)
        # We expect exit code != 0 when there are conflicts
        merge_proc = run_git_command(
            ["merge", "--no-commit", "--no-ff", head_sha],
            cwd=temp_path,
            secret_tokens=secrets,
            check=False,
        )
        logger.info(
            "Git merge simulation for %s/%s PR #%d exited with code %d",
            owner,
            repo,
            pull_number,
            merge_proc.returncode,
        )

        # 7. Identify unmerged (conflicting) files using `git ls-files -u`
        ls_proc = run_git_command(["ls-files", "-u"], cwd=temp_path, secret_tokens=secrets, check=False)
        unmerged_lines = ls_proc.stdout.strip().splitlines()

        # Map file paths to their stage blob SHAs: {path: {1: sha, 2: sha, 3: sha}}
        stage_map: dict[str, dict[int, str]] = {}
        for line in unmerged_lines:
            parts = line.split()
            if len(parts) >= 4:
                sha = parts[1]
                stage_str = parts[2]
                path_name = " ".join(parts[3:])  # in case path has spaces
                try:
                    stage_num = int(stage_str)
                except ValueError:
                    continue
                if path_name not in stage_map:
                    stage_map[path_name] = {}
                stage_map[path_name][stage_num] = sha

        conflicts: list[dict[str, Any]] = []
        conflicting_files: list[str] = list(stage_map.keys())

        for file_path in conflicting_files:
            stages = stage_map.get(file_path, {})
            b_sha = stages.get(1, "")
            l_sha = stages.get(2, "")
            r_sha = stages.get(3, "")

            # Retrieve Base (:1:), Local (:2:), and Remote (:3:) content
            base_content_proc = run_git_command(["show", f":1:{file_path}"], cwd=temp_path, secret_tokens=secrets, check=False)
            local_content_proc = run_git_command(["show", f":2:{file_path}"], cwd=temp_path, secret_tokens=secrets, check=False)
            remote_content_proc = run_git_command(["show", f":3:{file_path}"], cwd=temp_path, secret_tokens=secrets, check=False)

            base_content = base_content_proc.stdout if base_content_proc.returncode == 0 else ""
            local_content = local_content_proc.stdout if local_content_proc.returncode == 0 else ""
            remote_content = remote_content_proc.stdout if remote_content_proc.returncode == 0 else ""

            # Read working tree file with conflict markers
            working_file = temp_path / file_path
            conflict_markers = {"ours": "", "theirs": ""}
            if working_file.is_file():
                try:
                    working_content = working_file.read_text(encoding="utf-8", errors="replace")
                    conflict_markers = parse_conflict_markers(working_content)
                except Exception as exc:
                    logger.warning("Could not read working tree conflict markers for %s: %s", file_path, exc)

            language = detect_language(file_path)

            conflicts.append({
                "path": file_path,
                "language": language,
                "base_sha": b_sha,
                "local_sha": l_sha,
                "remote_sha": r_sha,
                "base": base_content,
                "local": local_content,
                "remote": remote_content,
                "conflict_markers": conflict_markers,
                "conflict_type": "textual",
            })

        logger.info(
            "Conflict extraction complete for %s/%s PR #%d: total_changed=%d, total_conflicting=%d",
            owner,
            repo,
            pull_number,
            len(changed_files),
            len(conflicting_files),
        )

        return {
            "merge_base_sha": merge_base_sha,
            "changed_files": changed_files,
            "conflicting_files": conflicting_files,
            "conflicts": conflicts,
        }

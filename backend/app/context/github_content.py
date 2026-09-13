"""GitHub content and tree fetching utilities for repository context extraction.

Provides deterministic, read-only helpers to query GitHub REST endpoints for:
- Repository README
- Recursive Git directory trees
- Repository language breakdowns
- Individual file content previews with strict size capping

Never leaks secrets, tokens, or credentials in error messages or logs.
"""

import base64
import logging
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.git.github import (
    GITHUB_API_BASE,
    GITHUB_API_VERSION,
    GitHubAPIError,
    GitHubAuthError,
)

logger = logging.getLogger(__name__)

# Defaults and safety caps
DEFAULT_README_MAX_BYTES = 10_000      # 10 KB
DEFAULT_FILE_MAX_BYTES = 5_000         # 5 KB
DEFAULT_TREE_MAX_ENTRIES = 500         # 500 paths


def _build_headers(token: str) -> Dict[str, str]:
    """Create standard GitHub REST API request headers."""
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
    }


def fetch_readme(
    owner: str,
    repo: str,
    token: str,
    ref: Optional[str] = None,
    max_bytes: int = DEFAULT_README_MAX_BYTES,
    client: Optional[httpx.Client] = None,
) -> Optional[str]:
    """
    Fetch and decode repository README from GitHub API.

    GET /repos/{owner}/{repo}/readme
    Returns truncated UTF-8 string or None if README does not exist (404).
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/readme"
    params = {}
    if ref:
        params["ref"] = ref

    owns_client = False
    if client is None:
        client = httpx.Client(timeout=10.0)
        owns_client = True

    try:
        response = client.get(url, headers=_build_headers(token), params=params)
    except httpx.RequestError as exc:
        logger.warning("Network error fetching README for %s/%s: %s", owner, repo, exc)
        return None
    finally:
        if owns_client:
            client.close()

    if response.status_code == 404:
        return None

    if response.status_code in (401, 403):
        raise GitHubAuthError(
            "GitHub authentication failed while fetching README.",
            status_code=response.status_code,
        )

    if response.status_code != 200:
        logger.warning(
            "Non-200 status %d fetching README for %s/%s", response.status_code, owner, repo
        )
        return None

    data = response.json()
    raw_b64 = data.get("content", "")
    encoding = data.get("encoding", "")

    if not raw_b64:
        return None

    try:
        if encoding == "base64":
            raw_bytes = base64.b64decode(raw_b64.encode("ascii"))
        else:
            raw_bytes = raw_b64.encode("utf-8")
    except Exception as exc:
        logger.warning("Failed to decode base64 README for %s/%s: %s", owner, repo, exc)
        return None

    # Cap byte length and decode
    capped_bytes = raw_bytes[:max_bytes]
    return capped_bytes.decode("utf-8", errors="replace")


def fetch_directory_tree(
    owner: str,
    repo: str,
    commit_sha_or_branch: str,
    token: str,
    max_entries: int = DEFAULT_TREE_MAX_ENTRIES,
    client: Optional[httpx.Client] = None,
) -> Tuple[List[str], bool]:
    """
    Fetch repository Git tree recursively.

    GET /repos/{owner}/{repo}/git/trees/{tree_sha}?recursive=1
    Returns (paths, is_truncated).
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/git/trees/{commit_sha_or_branch}"
    params = {"recursive": "1"}

    owns_client = False
    if client is None:
        client = httpx.Client(timeout=15.0)
        owns_client = True

    try:
        response = client.get(url, headers=_build_headers(token), params=params)
    except httpx.RequestError as exc:
        raise GitHubAPIError(f"Network error fetching tree for {owner}/{repo}.", status_code=502) from exc
    finally:
        if owns_client:
            client.close()

    if response.status_code == 404:
        logger.warning("Tree ref '%s' not found for %s/%s", commit_sha_or_branch, owner, repo)
        return ([], False)

    if response.status_code in (401, 403):
        raise GitHubAuthError(
            "GitHub authentication failed while fetching directory tree.",
            status_code=response.status_code,
        )

    if response.status_code != 200:
        raise GitHubAPIError(
            f"GitHub API error fetching tree for {owner}/{repo}: {response.status_code}",
            status_code=response.status_code,
        )

    data = response.json()
    github_truncated = bool(data.get("truncated", False))
    raw_tree = data.get("tree", [])

    # Filter for file blob paths (or directory items) - paths are repository-relative
    file_paths: List[str] = [
        item["path"]
        for item in raw_tree
        if isinstance(item, dict) and "path" in item
    ]

    total_paths = len(file_paths)
    is_truncated = github_truncated or (total_paths > max_entries)
    capped_paths = file_paths[:max_entries]

    return (capped_paths, is_truncated)


def fetch_languages(
    owner: str,
    repo: str,
    token: str,
    client: Optional[httpx.Client] = None,
) -> Dict[str, int]:
    """
    Fetch language byte statistics for repository.

    GET /repos/{owner}/{repo}/languages
    Returns dict mapping language names to byte count.
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/languages"

    owns_client = False
    if client is None:
        client = httpx.Client(timeout=10.0)
        owns_client = True

    try:
        response = client.get(url, headers=_build_headers(token))
    except httpx.RequestError as exc:
        logger.warning("Network error fetching languages for %s/%s: %s", owner, repo, exc)
        return {}
    finally:
        if owns_client:
            client.close()

    if response.status_code == 200:
        res = response.json()
        if isinstance(res, dict):
            return {k: int(v) for k, v in res.items() if isinstance(v, (int, float))}
        return {}

    logger.warning("Non-200 status %d fetching languages for %s/%s", response.status_code, owner, repo)
    return {}


def fetch_file_content(
    owner: str,
    repo: str,
    path: str,
    token: str,
    ref: Optional[str] = None,
    max_bytes: int = DEFAULT_FILE_MAX_BYTES,
    client: Optional[httpx.Client] = None,
) -> Tuple[Optional[str], int, bool]:
    """
    Fetch an individual file's content from GitHub contents API.

    GET /repos/{owner}/{repo}/contents/{path}
    Returns (content_str, original_size, is_truncated).
    If file not found or binary, returns (None, 0, False).
    """
    # Clean leading slashes
    clean_path = path.lstrip("/")
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{clean_path}"
    params = {}
    if ref:
        params["ref"] = ref

    owns_client = False
    if client is None:
        client = httpx.Client(timeout=10.0)
        owns_client = True

    try:
        response = client.get(url, headers=_build_headers(token), params=params)
    except httpx.RequestError as exc:
        logger.warning("Network error fetching file %s for %s/%s: %s", path, owner, repo, exc)
        return (None, 0, False)
    finally:
        if owns_client:
            client.close()

    if response.status_code == 404:
        return (None, 0, False)

    if response.status_code in (401, 403):
        raise GitHubAuthError(
            f"GitHub authentication failed while fetching file '{path}'.",
            status_code=response.status_code,
        )

    if response.status_code != 200:
        logger.warning("Status %d fetching file %s for %s/%s", response.status_code, path, owner, repo)
        return (None, 0, False)

    data = response.json()
    if not isinstance(data, dict):
        return (None, 0, False)

    # If it's a directory, return None
    if data.get("type") != "file":
        return (None, 0, False)

    raw_b64 = data.get("content", "")
    original_size = data.get("size", 0)
    encoding = data.get("encoding", "")

    if not raw_b64:
        return ("", original_size, False)

    try:
        if encoding == "base64":
            raw_bytes = base64.b64decode(raw_b64.encode("ascii"))
        else:
            raw_bytes = raw_b64.encode("utf-8")
    except Exception as exc:
        logger.warning("Failed to decode base64 file %s for %s/%s: %s", path, owner, repo, exc)
        return (None, original_size, False)

    truncated = len(raw_bytes) > max_bytes
    capped_bytes = raw_bytes[:max_bytes]

    try:
        content_str = capped_bytes.decode("utf-8", errors="replace")
    except Exception:
        return (None, original_size, False)

    return (content_str, original_size, truncated)

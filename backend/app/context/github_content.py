"""GitHub content, directory tree, and documentation fetching utilities.

Provides deterministic, read-only helpers to query GitHub REST endpoints for:
- Repository documentation (README.md, ProjectInfo.md, CONTRIBUTING.md, docs/)
- Clean filtered recursive directory trees
- Formatted visual compact directory trees
- Language breakdowns
- Individual file content previews with strict size capping
- Deterministic project description extraction

Security guarantees:
- Rejects secret files (.env, private keys, *.pem, *.key, secrets/)
- Rejects vendor/generated directories (.git, node_modules, venv, dist, etc.)
- Treats all documentation strictly as untrusted data without execution
- Never leaks credentials, tokens, or JWTs
"""

import base64
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.context.models import DocumentationFile
from app.core.config import settings
from app.git.github import (
    GITHUB_API_BASE,
    GITHUB_API_VERSION,
    GitHubAPIError,
    GitHubAuthError,
)

logger = logging.getLogger(__name__)

# Defaults and safety caps
DEFAULT_README_MAX_BYTES = getattr(settings, "MERGEMIND_MAX_DOCUMENTATION_CHARS", 10_000)
DEFAULT_FILE_MAX_BYTES = 5_000
DEFAULT_TREE_MAX_ENTRIES = getattr(settings, "MERGEMIND_MAX_TREE_ENTRIES", 500)

# Generated, build, or vendor directory names to ignore completely
IGNORED_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "dist",
    "build",
    "target",
    ".next",
    ".cache",
    ".pytest_cache",
    ".idea",
    ".vscode",
    ".tox",
    ".eggs",
    "coverage",
    ".nyc_output",
}

# Secret file patterns that must never be traversed, read, or exposed
SECRET_PATTERNS = [
    re.compile(r"^\.env(\..+)?$", re.IGNORECASE),
    re.compile(r"^.*\.(pem|key|pfx|p12|pkcs12|kdbx|crt|secret|token)$", re.IGNORECASE),
    re.compile(r"^(id_rsa|id_dsa|id_ed25519|id_ecdsa)$", re.IGNORECASE),
    re.compile(r"^(credentials|secrets?)(\..+)?$", re.IGNORECASE),
    re.compile(r"^service-account.*\.json$", re.IGNORECASE),
    re.compile(r"^client_secret.*\.json$", re.IGNORECASE),
]

SECRET_DIR_NAMES = {"secrets", ".secrets", "credentials", ".credentials"}

# Binary extensions to skip from source/tree analysis
BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp",
    ".pdf", ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar",
    ".exe", ".dll", ".so", ".dylib", ".pyc", ".class", ".jar",
    ".war", ".wasm", ".bin", ".woff", ".woff2", ".ttf", ".eot",
}

# Priority documentation candidates
PRIMARY_DOC_NAMES = [
    "readme.md",
    "readme",
    "readme.rst",
    "readme.txt",
]

SECONDARY_DOC_NAMES = [
    "projectinfo.md",
    "project.md",
    "contributing.md",
]


def _build_headers(token: str) -> Dict[str, str]:
    """Create standard GitHub REST API request headers."""
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
    }


def is_safe_repo_path(path: str) -> bool:
    """
    Deterministically check if a repository-relative path should be included.
    Excludes generated/vendor directories, secret files/directories, and binary files.
    """
    if not path or not path.strip():
        return False

    clean = path.strip("/")
    parts = [p for p in clean.split("/") if p]
    if not parts:
        return False

    # Check all parent directories
    for part in parts[:-1]:
        part_lower = part.lower()
        if part_lower in IGNORED_DIRS or part_lower in SECRET_DIR_NAMES:
            return False

    filename = parts[-1]
    filename_lower = filename.lower()

    if filename_lower in IGNORED_DIRS or filename_lower in SECRET_DIR_NAMES:
        return False

    for pat in SECRET_PATTERNS:
        if pat.match(filename):
            return False

    for ext in BINARY_EXTENSIONS:
        if filename_lower.endswith(ext):
            return False

    return True


def generate_compact_tree(file_paths: List[str]) -> str:
    """
    Build a clean, deterministic, compact ASCII/Unicode directory tree.
    Guarantees deterministic sorting.
    """
    if not file_paths:
        return ""

    safe_paths = [p for p in file_paths if is_safe_repo_path(p)]
    if not safe_paths:
        return ""

    tree_dict: dict[str, Any] = {}
    for p in sorted(safe_paths):
        parts = [part for part in p.strip("/").split("/") if part]
        curr = tree_dict
        for part in parts:
            curr = curr.setdefault(part, {})

    lines: List[str] = []

    def _walk(node: dict[str, Any], prefix: str = "") -> None:
        entries = sorted(node.keys(), key=lambda k: (len(node[k]) == 0, k.lower()))
        for i, name in enumerate(entries):
            is_last = (i == len(entries) - 1)
            branch = "└── " if is_last else "├── "
            sub_prefix = "    " if is_last else "│   "
            is_dir = len(node[name]) > 0
            lines.append(f"{prefix}{branch}{name}{'/' if is_dir else ''}")
            if is_dir:
                _walk(node[name], prefix + sub_prefix)

    _walk(tree_dict)
    return "\n".join(lines)


def extract_project_description(markdown_text: str) -> Optional[str]:
    """
    Deterministically extract a concise project description from README or ProjectInfo.
    Scans for the first descriptive sentence/paragraph following the main title.
    Returns None if no clear description is present.
    Never uses an LLM.
    """
    if not markdown_text or not markdown_text.strip():
        return None

    lines = markdown_text.splitlines()
    desc_lines: List[str] = []
    past_title = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if desc_lines:
                break
            continue

        # Skip badge lines like [![Build Status]...] or image tags
        if stripped.startswith("[![") or stripped.startswith("<") or stripped.startswith("!["):
            continue

        # Check title header
        if stripped.startswith("# ") or stripped.startswith("=="):
            past_title = True
            continue

        # Stop if a secondary section header is encountered
        if past_title and (stripped.startswith("## ") or stripped.startswith("--")):
            if desc_lines:
                break
            continue

        # Stop on code blocks or prompt injections
        if stripped.startswith("```"):
            if desc_lines:
                break
            continue

        # Clean inline markdown links: [text](url) -> text
        cleaned = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", stripped)
        # Clean bold/italics
        cleaned = re.sub(r"[*_`]", "", cleaned)
        desc_lines.append(cleaned)

        if cleaned.endswith((".", "!", "?")) and len(" ".join(desc_lines)) >= 20:
            break

    full_desc = " ".join(desc_lines).strip()
    if full_desc and 15 <= len(full_desc) <= 400:
        return full_desc

    return None


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

    capped_bytes = raw_bytes[:max_bytes]
    return capped_bytes.decode("utf-8", errors="replace")


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
    If file not found, secret, or binary, returns (None, 0, False).
    """
    clean_path = path.lstrip("/")

    # Security check: never fetch secret files
    if not is_safe_repo_path(clean_path):
        logger.warning("Blocked attempt to fetch unsafe/secret path: %s", clean_path)
        return (None, 0, False)

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


def fetch_documentation_files(
    owner: str,
    repo: str,
    token: str,
    tree_paths: List[str],
    ref: Optional[str] = None,
    max_total_chars: int = DEFAULT_README_MAX_BYTES,
    client: Optional[httpx.Client] = None,
) -> Tuple[List[DocumentationFile], Optional[str]]:
    """
    Deterministically retrieve prioritized documentation files:
    1. README.md (or README, README.rst, README.txt)
    2. ProjectInfo.md, PROJECT.md
    3. CONTRIBUTING.md
    4. Relevant docs/ files (e.g. docs/index.md, docs/architecture.md, docs/README.md)

    Returns:
        (documentation_files, extracted_project_description)
    """
    doc_files: List[DocumentationFile] = []
    seen_paths: set[str] = set()
    total_chars_consumed = 0
    extracted_description: Optional[str] = None

    # Identify matching candidate paths from tree
    path_map = {p.lower(): p for p in tree_paths}

    candidates_to_fetch: List[str] = []

    # 1. Primary README
    for name in PRIMARY_DOC_NAMES:
        if name in path_map and path_map[name] not in seen_paths:
            candidates_to_fetch.append(path_map[name])
            seen_paths.add(path_map[name])
            break

    # 2. Secondary docs
    for name in SECONDARY_DOC_NAMES:
        if name in path_map and path_map[name] not in seen_paths:
            candidates_to_fetch.append(path_map[name])
            seen_paths.add(path_map[name])

    # 3. docs/ directory files (up to 2 files)
    docs_dir_files = [
        p for p in tree_paths
        if p.lower().startswith("docs/") and p.lower().endswith((".md", ".rst", ".txt"))
    ]
    for dpath in sorted(docs_dir_files)[:2]:
        if dpath not in seen_paths:
            candidates_to_fetch.append(dpath)
            seen_paths.add(dpath)

    # If no tree candidates matched, attempt GitHub default README endpoint as fallback
    if not candidates_to_fetch:
        default_readme = fetch_readme(owner, repo, token, ref=ref, max_bytes=max_total_chars, client=client)
        if default_readme is not None:
            trunc = len(default_readme) >= max_total_chars
            doc_files.append(
                DocumentationFile(
                    path="README.md",
                    content=default_readme,
                    truncated=trunc,
                )
            )
            extracted_description = extract_project_description(default_readme)
        return (doc_files, extracted_description)

    for doc_path in candidates_to_fetch:
        remaining_budget = max(0, max_total_chars - total_chars_consumed)
        if remaining_budget <= 0:
            break

        content, size, truncated = fetch_file_content(
            owner=owner,
            repo=repo,
            path=doc_path,
            token=token,
            ref=ref,
            max_bytes=remaining_budget,
            client=client,
        )

        if content is None:
            continue

        is_trunc = truncated or (len(content) > remaining_budget)
        final_content = content[:remaining_budget]
        if is_trunc:
            final_content += "\n\n[TRUNCATED: Exceeded character limit]"

        doc_files.append(
            DocumentationFile(
                path=doc_path,
                content=final_content,
                truncated=is_trunc,
            )
        )
        total_chars_consumed += len(final_content)

        if extracted_description is None:
            extracted_description = extract_project_description(final_content)

    return (doc_files, extracted_description)


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
    Filters out ignored directories and secrets.
    Returns (filtered_paths, is_truncated).
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

    # Filter out generated/vendor directories, secrets, and binary files
    filtered_paths: List[str] = [
        item["path"]
        for item in raw_tree
        if isinstance(item, dict) and "path" in item and is_safe_repo_path(item["path"])
    ]

    # Sort deterministically
    sorted_paths = sorted(filtered_paths)

    total_paths = len(sorted_paths)
    is_truncated = github_truncated or (total_paths > max_entries)
    capped_paths = sorted_paths[:max_entries]

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

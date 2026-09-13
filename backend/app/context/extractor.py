"""Context extractor orchestrator for MergeMind.

Deterministically coordinates the retrieval of repository README, directory structure,
language statistics, technology detection, and relevant neighbor files.
Safe for downstream consumption by the LLM Merge Agent.
"""

import logging
from typing import List, Optional

import httpx

from app.context.github_content import (
    DEFAULT_FILE_MAX_BYTES,
    DEFAULT_README_MAX_BYTES,
    DEFAULT_TREE_MAX_ENTRIES,
    fetch_directory_tree,
    fetch_file_content,
    fetch_languages,
    fetch_readme,
)
from app.context.models import FilePreview, RepositoryContext
from app.context.relevance import find_relevant_paths
from app.context.technology import detect_technologies

logger = logging.getLogger(__name__)

# Key manifest file paths to fetch for deep library/framework detection
KNOWN_MANIFEST_NAMES = {
    "package.json",
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    "pom.xml",
    "cargo.toml",
}


def extract_repository_context(
    owner: str,
    repo: str,
    token: str,
    base_ref: str,
    head_ref: str,
    conflicting_files: Optional[List[str]] = None,
    client: Optional[httpx.Client] = None,
) -> RepositoryContext:
    """
    Extract deterministic repository context for a pull request.

    Coordinates all read-only GitHub REST calls:
    1. README preview
    2. Directory tree structure
    3. Languages breakdown
    4. Dependency manifest fetching and technology detection
    5. Relevant neighbor file previews
    """
    conflicting_files = conflicting_files or []
    owns_client = False
    if client is None:
        client = httpx.Client(timeout=20.0)
        owns_client = True

    try:
        # 1. Fetch README
        readme_preview = fetch_readme(
            owner=owner,
            repo=repo,
            token=token,
            ref=base_ref,
            max_bytes=DEFAULT_README_MAX_BYTES,
            client=client,
        )

        # 2. Fetch language breakdown
        languages = fetch_languages(
            owner=owner,
            repo=repo,
            token=token,
            client=client,
        )

        # 3. Fetch directory tree
        tree_paths, tree_truncated = fetch_directory_tree(
            owner=owner,
            repo=repo,
            commit_sha_or_branch=base_ref,
            token=token,
            max_entries=DEFAULT_TREE_MAX_ENTRIES,
            client=client,
        )

        # 4. Find and fetch manifest files for technology detection (up to 3 manifests)
        manifest_contents = {}
        manifest_candidates = [
            p for p in tree_paths
            if p.split("/")[-1].lower() in KNOWN_MANIFEST_NAMES
        ][:3]

        for mpath in manifest_candidates:
            content, _, _ = fetch_file_content(
                owner=owner,
                repo=repo,
                path=mpath,
                token=token,
                ref=base_ref,
                max_bytes=DEFAULT_FILE_MAX_BYTES,
                client=client,
            )
            if content:
                manifest_contents[mpath] = content

        # 5. Deterministic technology detection
        detected_technologies = detect_technologies(
            directory_paths=tree_paths,
            manifest_contents=manifest_contents,
            github_languages=languages,
        )

        # 6. Relevant neighbor file selection and preview fetching
        relevant_candidates = find_relevant_paths(
            conflicting_file_paths=conflicting_files,
            directory_tree_paths=tree_paths,
        )

        relevant_file_previews: List[FilePreview] = []
        for rpath, reason in relevant_candidates:
            fcontent, fsize, ftrunc = fetch_file_content(
                owner=owner,
                repo=repo,
                path=rpath,
                token=token,
                ref=base_ref,
                max_bytes=DEFAULT_FILE_MAX_BYTES,
                client=client,
            )
            if fcontent is not None:
                relevant_file_previews.append(
                    FilePreview(
                        path=rpath,
                        content=fcontent,
                        size=fsize,
                        truncated=ftrunc,
                        reason=reason,
                    )
                )

        logger.info(
            "Extracted repository context for %s/%s: %d tree paths, %d technologies, %d relevant files",
            owner,
            repo,
            len(tree_paths),
            len(detected_technologies),
            len(relevant_file_previews),
        )

        return RepositoryContext(
            repository=f"{owner}/{repo}",
            base_ref=base_ref,
            head_ref=head_ref,
            readme_preview=readme_preview,
            directory_structure=tree_paths,
            tree_truncated=tree_truncated,
            detected_technologies=detected_technologies,
            languages=languages,
            relevant_files=relevant_file_previews,
            total_files_examined=len(tree_paths),
        )

    finally:
        if owns_client:
            client.close()

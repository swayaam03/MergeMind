"""Context extractor orchestrator for MergeMind.

Deterministically coordinates the retrieval of repository documentation,
compact directory structure, technology detection, and prioritized relevant files.
Integrates directly with Tree-sitter AST analysis and conflict extraction data.
Safe for downstream consumption by the LLM Merge Agent.
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

from app.context.github_content import (
    DEFAULT_FILE_MAX_BYTES,
    DEFAULT_README_MAX_BYTES,
    DEFAULT_TREE_MAX_ENTRIES,
    fetch_directory_tree,
    fetch_documentation_files,
    fetch_file_content,
    fetch_languages,
    fetch_readme,
    generate_compact_tree,
)
from app.context.models import (
    DocumentationContext,
    RelevantFile,
    RepositoryContext,
    RepositoryRef,
    StructureContext,
)
from app.context.relevance import DEFAULT_MAX_RELEVANT_FILES, find_relevant_paths
from app.context.technology import build_project_info, detect_technologies
from app.core.config import settings

logger = logging.getLogger(__name__)

# Key manifest file paths to fetch for deep library/framework detection
KNOWN_MANIFEST_NAMES = {
    "package.json",
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    "pom.xml",
    "build.gradle",
    "cargo.toml",
}


def extract_repository_context(
    owner: str,
    repo: str,
    token: str,
    base_ref: str,
    head_ref: str,
    conflicting_files: Optional[List[str]] = None,
    ast_analyses: Optional[Dict[str, Any]] = None,
    conflict_sources: Optional[Dict[str, str]] = None,
    client: Optional[httpx.Client] = None,
) -> RepositoryContext:
    """
    Extract deterministic repository context for a pull request.

    Coordinates all read-only GitHub REST calls and static inspections:
    1. Directory tree structure (filtered, safe, bounded)
    2. Compact visual tree generation
    3. Documentation files (README.md, ProjectInfo.md, etc.) and project description
    4. Language statistics
    5. Dependency manifests and technology detection
    6. Relevant files prioritized:
       - Conflicting file(s)
       - Conflicting AST functions/classes
       - Directly imported local modules
       - Associated tests
       - Same-directory source files
    """
    conflicting_files = conflicting_files or []
    ast_analyses = ast_analyses or {}
    conflict_sources = conflict_sources or {}

    max_tree_entries = getattr(settings, "MERGEMIND_MAX_TREE_ENTRIES", DEFAULT_TREE_MAX_ENTRIES)
    max_doc_chars = getattr(settings, "MERGEMIND_MAX_DOCUMENTATION_CHARS", DEFAULT_README_MAX_BYTES)
    max_relevant = getattr(settings, "MERGEMIND_MAX_RELEVANT_FILES", DEFAULT_MAX_RELEVANT_FILES)

    owns_client = False
    if client is None:
        client = httpx.Client(timeout=20.0)
        owns_client = True

    try:
        # 1. Fetch directory tree
        tree_paths, tree_truncated = fetch_directory_tree(
            owner=owner,
            repo=repo,
            commit_sha_or_branch=base_ref,
            token=token,
            max_entries=max_tree_entries,
            client=client,
        )

        # 2. Generate compact visual tree representation
        compact_tree = generate_compact_tree(tree_paths)

        # 3. Fetch documentation files and extract project description
        doc_files, project_desc = fetch_documentation_files(
            owner=owner,
            repo=repo,
            token=token,
            tree_paths=tree_paths,
            ref=base_ref,
            max_total_chars=max_doc_chars,
            client=client,
        )

        # Primary README preview for backward compatibility
        primary_readme_content = doc_files[0].content if doc_files else None

        # 4. Fetch language breakdown
        languages = fetch_languages(
            owner=owner,
            repo=repo,
            token=token,
            client=client,
        )

        # 5. Find and fetch manifest files for technology detection (up to 3 manifests)
        manifest_contents: Dict[str, str] = {}
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

        # 6. Deterministic technology detection & ProjectInfo
        detected_technologies = detect_technologies(
            directory_paths=tree_paths,
            manifest_contents=manifest_contents,
            github_languages=languages,
        )

        project_info = build_project_info(
            directory_paths=tree_paths,
            manifest_contents=manifest_contents,
            github_languages=languages,
            description=project_desc,
        )

        # 7. Relevant file selection
        relevant_candidates = find_relevant_paths(
            conflicting_file_paths=conflicting_files,
            directory_tree_paths=tree_paths,
            ast_analyses=ast_analyses,
            conflict_sources=conflict_sources,
            max_files=max_relevant,
        )

        relevant_file_objects: List[RelevantFile] = []
        for rpath, reason, ast_nodes in relevant_candidates:
            # If we already have the source in memory from conflict data, reuse it
            if rpath in conflict_sources:
                content = conflict_sources[rpath]
                fsize = len(content.encode("utf-8"))
                ftrunc = fsize > DEFAULT_FILE_MAX_BYTES
                capped_content = content[:DEFAULT_FILE_MAX_BYTES]
                relevant_file_objects.append(
                    RelevantFile(
                        path=rpath,
                        reason=reason,
                        content=capped_content,
                        size=fsize,
                        truncated=ftrunc,
                        ast_elements=ast_nodes,
                    )
                )
            else:
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
                    relevant_file_objects.append(
                        RelevantFile(
                            path=rpath,
                            reason=reason,
                            content=fcontent,
                            size=fsize,
                            truncated=ftrunc,
                            ast_elements=ast_nodes,
                        )
                    )

        logger.info(
            "Extracted repository context for %s/%s: %d tree paths, %d docs, %d technologies, %d relevant files",
            owner,
            repo,
            len(tree_paths),
            len(doc_files),
            len(detected_technologies),
            len(relevant_file_objects),
        )

        return RepositoryContext(
            repository=RepositoryRef(owner=owner, name=repo),
            project=project_info,
            documentation=DocumentationContext(files=doc_files),
            structure=StructureContext(tree=compact_tree, truncated=tree_truncated),
            relevant_files=relevant_file_objects,
            # Backward compatibility fields
            base_ref=base_ref,
            head_ref=head_ref,
            readme_preview=primary_readme_content,
            directory_structure=tree_paths,
            tree_truncated=tree_truncated,
            detected_technologies=detected_technologies,
            languages=languages,
            total_files_examined=len(tree_paths),
        )

    finally:
        if owns_client:
            client.close()

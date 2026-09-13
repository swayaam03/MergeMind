"""Deterministic selection of relevant neighbor files for conflicting PRs.

Selects contextually relevant files (same-directory siblings, package index/init files,
corresponding unit tests) to supply to the downstream LLM Merge Agent.
Never includes the conflicting files themselves.
"""

from pathlib import PurePosixPath
from typing import List, Set, Tuple

# Path prefixes to ignore
IGNORED_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    ".next",
    ".cache",
    ".pytest_cache",
}

# Max relevant files to retrieve
DEFAULT_MAX_RELEVANT_FILES = 10


def is_ignored_path(path: str) -> bool:
    """Check if a file path is located in an ignored directory."""
    parts = PurePosixPath(path).parts
    return any(p in IGNORED_DIRS for p in parts)


def find_relevant_paths(
    conflicting_file_paths: List[str],
    directory_tree_paths: List[str],
    max_files: int = DEFAULT_MAX_RELEVANT_FILES,
) -> List[Tuple[str, str]]:
    """
    Find relevant neighbor files in the repository given the list of conflicting files.

    Returns a list of tuples: (file_path, reason_string)
    Prioritizes:
    1. Direct unit test files matching the conflicting file (e.g. test_calculator.py for calculator.py).
    2. Package init or index files in the same or immediate parent directory (__init__.py, index.js).
    3. Same-directory siblings sharing the same language extension.
    4. General sibling files in the same directory.
    """
    conflicting_set: Set[str] = {p.strip("/") for p in conflicting_file_paths}
    relevant: List[Tuple[str, str]] = []
    seen: Set[str] = set()

    clean_tree = [p for p in directory_tree_paths if not is_ignored_path(p)]

    for conflict_path in conflicting_file_paths:
        conflict_pure = PurePosixPath(conflict_path.strip("/"))
        conflict_dir = conflict_pure.parent
        conflict_stem = conflict_pure.stem
        conflict_suffix = conflict_pure.suffix.lower()

        # 1. Search for matching test files
        # e.g., test_<stem>.py, <stem>_test.py, <stem>.test.js, <stem>.spec.ts
        test_patterns = {
            f"test_{conflict_stem}{conflict_suffix}",
            f"{conflict_stem}_test{conflict_suffix}",
            f"{conflict_stem}.test{conflict_suffix}",
            f"{conflict_stem}.spec{conflict_suffix}",
        }

        for path in clean_tree:
            p_pure = PurePosixPath(path)
            clean_str = str(p_pure)
            if clean_str in conflicting_set or clean_str in seen:
                continue

            if p_pure.name.lower() in test_patterns:
                seen.add(clean_str)
                relevant.append((clean_str, f"matching_test_for_{conflict_pure.name}"))
                if len(relevant) >= max_files:
                    return relevant

        # 2. Package init or index files in same directory or parent
        for path in clean_tree:
            p_pure = PurePosixPath(path)
            clean_str = str(p_pure)
            if clean_str in conflicting_set or clean_str in seen:
                continue

            if p_pure.parent == conflict_dir or p_pure.parent == conflict_dir.parent:
                if p_pure.name.lower() in ("__init__.py", "index.js", "index.ts", "mod.rs"):
                    seen.add(clean_str)
                    relevant.append((clean_str, f"package_init_for_{p_pure.parent}"))
                    if len(relevant) >= max_files:
                        return relevant

        # 3. Same-directory sibling files with matching language extension
        for path in clean_tree:
            p_pure = PurePosixPath(path)
            clean_str = str(p_pure)
            if clean_str in conflicting_set or clean_str in seen:
                continue

            if p_pure.parent == conflict_dir and p_pure.suffix.lower() == conflict_suffix:
                seen.add(clean_str)
                relevant.append((clean_str, f"same_directory_sibling_({p_pure.name})"))
                if len(relevant) >= max_files:
                    return relevant

        # 4. Other same-directory sibling files
        for path in clean_tree:
            p_pure = PurePosixPath(path)
            clean_str = str(p_pure)
            if clean_str in conflicting_set or clean_str in seen:
                continue

            if p_pure.parent == conflict_dir:
                seen.add(clean_str)
                relevant.append((clean_str, f"same_directory_neighbor_({p_pure.name})"))
                if len(relevant) >= max_files:
                    return relevant

    return relevant[:max_files]

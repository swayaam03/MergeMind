"""Deterministic selection of relevant files for conflicting pull requests.

Prioritizes files in strict accordance with the MergeMind architecture:
1. Conflicting file itself (highest priority)
2. Conflicting AST functions/classes
3. Directly imported local modules
4. Associated unit tests
5. Same-directory relevant source files

Never recursively pulls the entire dependency graph.
Strictly bounds results by MERGEMIND_MAX_RELEVANT_FILES.
"""

import re
from pathlib import PurePosixPath
from typing import Any, Dict, List, Optional, Set, Tuple

from app.context.github_content import is_safe_repo_path
from app.core.config import settings

DEFAULT_MAX_RELEVANT_FILES = getattr(settings, "MERGEMIND_MAX_RELEVANT_FILES", 10)


def is_ignored_path(path: str) -> bool:
    """Backward compatibility helper checking if a path is ignored."""
    return not is_safe_repo_path(path)


def extract_conflicting_ast_nodes(ast_analysis: Optional[Dict[str, Any]]) -> List[str]:
    """
    Extract names of functions or classes impacted by conflicts from existing AST analysis.
    Does not re-parse source code; reuses existing Tree-sitter classification data.
    """
    if not ast_analysis or not isinstance(ast_analysis, dict):
        return []

    node_names: Set[str] = set()

    # 1. Check structural changes
    changes = ast_analysis.get("changes") or {}
    for change_list in changes.values():
        if isinstance(change_list, list):
            for ch in change_list:
                if isinstance(ch, dict) and ch.get("node_name"):
                    node_names.add(str(ch["node_name"]))

    # 2. Check FileAST nodes in conflict region if changes was empty
    for side in ("base", "local", "remote"):
        side_ast = ast_analysis.get(side) or {}
        nodes = side_ast.get("nodes") or []
        for n in nodes:
            if isinstance(n, dict) and n.get("name"):
                node_names.add(str(n["name"]))

    return sorted(node_names)


def find_local_imports(
    source_code: str,
    file_path: str,
    directory_tree_paths: List[str],
) -> List[str]:
    """
    Deterministically find directly imported local modules by inspecting imports in source code.
    Static regex analysis only — never dynamically imports or executes repository code.
    """
    if not source_code or not source_code.strip():
        return []

    tree_set = {p.strip("/") for p in directory_tree_paths}
    pure_path = PurePosixPath(file_path.strip("/"))
    file_dir = pure_path.parent

    # Python imports: from .utils import ..., from utils import ..., import utils
    py_from = re.findall(r"(?:^|\n)\s*from\s+([\.a-zA-Z0-9_\-]+)\s+import", source_code)
    py_import = re.findall(r"(?:^|\n)\s*import\s+([a-zA-Z0-9_\-]+)", source_code)

    # JS/TS imports: import ... from './utils', require('./utils')
    js_imports = re.findall(
        r"(?:import\s+.*?from\s+|require\s*\(\s*)['\"](\./[^'\"]+|\.\./[^'\"]+)['\"]",
        source_code,
    )

    imported_candidates: List[str] = []

    # Process Python candidate names
    for imp in py_from + py_import:
        mod_name = imp.lstrip(".").split(".")[0]
        if not mod_name:
            continue
        # Direct sibling or root candidate
        candidates = [
            f"{mod_name}.py",
            f"{mod_name}/__init__.py",
        ]
        if file_dir != PurePosixPath("."):
            candidates.insert(0, f"{file_dir}/{mod_name}.py")
            candidates.insert(1, f"{file_dir}/{mod_name}/__init__.py")

        for c in candidates:
            if c in tree_set and c not in imported_candidates:
                imported_candidates.append(c)

    # Process JS candidate paths
    for imp in js_imports:
        clean = imp.lstrip("./")
        target_dir = file_dir if file_dir != PurePosixPath(".") else PurePosixPath("")
        base_cand = f"{target_dir}/{clean}".strip("/")
        candidates = [
            f"{base_cand}.js",
            f"{base_cand}.jsx",
            f"{base_cand}.ts",
            f"{base_cand}.tsx",
            f"{base_cand}/index.js",
            f"{base_cand}/index.ts",
        ]
        for c in candidates:
            if c in tree_set and c not in imported_candidates:
                imported_candidates.append(c)

    return sorted(imported_candidates)


def find_relevant_paths(
    conflicting_file_paths: List[str],
    directory_tree_paths: List[str],
    ast_analyses: Optional[Dict[str, Any]] = None,
    conflict_sources: Optional[Dict[str, str]] = None,
    max_files: int = DEFAULT_MAX_RELEVANT_FILES,
) -> List[Tuple[str, str, List[str]]]:
    """
    Find prioritized relevant files for conflict resolution.

    Returns list of tuples: (file_path, reason, ast_elements)

    Priority order:
    1. Conflicting file itself (highest priority)
    2. Directly imported local modules
    3. Associated unit tests
    4. Same-directory sibling files
    """
    ast_analyses = ast_analyses or {}
    conflict_sources = conflict_sources or {}

    safe_tree = [p for p in directory_tree_paths if is_safe_repo_path(p)]
    tree_set = {p.strip("/") for p in safe_tree}

    relevant: List[Tuple[str, str, List[str]]] = []
    seen: Set[str] = set()

    clean_conflicts = [p.strip("/") for p in conflicting_file_paths if p and p.strip()]

    # Priority 1: The conflicting files themselves (highest priority)
    for cpath in clean_conflicts:
        if cpath not in seen:
            seen.add(cpath)
            ast_data = ast_analyses.get(cpath)
            ast_nodes = extract_conflicting_ast_nodes(ast_data)
            relevant.append((cpath, "conflicting file", ast_nodes))
            if len(relevant) >= max_files:
                return relevant

    # Priority 2: Directly imported local modules
    for cpath in clean_conflicts:
        source_code = conflict_sources.get(cpath, "")
        local_mods = find_local_imports(source_code, cpath, safe_tree)
        for mod_path in local_mods:
            if mod_path not in seen and is_safe_repo_path(mod_path):
                seen.add(mod_path)
                relevant.append((mod_path, f"imported local module for {cpath}", []))
                if len(relevant) >= max_files:
                    return relevant

    # Priority 3: Associated unit tests
    for cpath in clean_conflicts:
        pure = PurePosixPath(cpath)
        stem = pure.stem
        suffix = pure.suffix.lower()
        test_names = {
            f"test_{stem}{suffix}".lower(),
            f"{stem}_test{suffix}".lower(),
            f"{stem}.test{suffix}".lower(),
            f"{stem}.spec{suffix}".lower(),
        }

        for path in sorted(safe_tree):
            p_pure = PurePosixPath(path)
            clean_str = str(p_pure)
            if clean_str in seen:
                continue

            # Check filename match or path containing tests/test_<stem>
            if p_pure.name.lower() in test_names or (
                "test" in p_pure.parts and p_pure.name.lower().startswith(f"test_{stem.lower()}")
            ):
                seen.add(clean_str)
                relevant.append((clean_str, f"associated test for {pure.name}", []))
                if len(relevant) >= max_files:
                    return relevant

    # Priority 4: Package init / index files in same or parent directory
    for cpath in clean_conflicts:
        pure = PurePosixPath(cpath)
        cdir = pure.parent
        for path in sorted(safe_tree):
            p_pure = PurePosixPath(path)
            clean_str = str(p_pure)
            if clean_str in seen:
                continue

            if p_pure.parent == cdir or p_pure.parent == cdir.parent:
                if p_pure.name.lower() in ("__init__.py", "index.js", "index.ts"):
                    seen.add(clean_str)
                    relevant.append((clean_str, f"package init for {p_pure.parent}", []))
                    if len(relevant) >= max_files:
                        return relevant

    # Priority 5: Same-directory sibling files
    for cpath in clean_conflicts:
        pure = PurePosixPath(cpath)
        cdir = pure.parent
        suffix = pure.suffix.lower()
        for path in sorted(safe_tree):
            p_pure = PurePosixPath(path)
            clean_str = str(p_pure)
            if clean_str in seen:
                continue

            if p_pure.parent == cdir and p_pure.suffix.lower() == suffix:
                seen.add(clean_str)
                relevant.append((clean_str, f"same-directory sibling of {pure.name}", []))
                if len(relevant) >= max_files:
                    return relevant

    return relevant[:max_files]

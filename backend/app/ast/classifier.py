"""Deterministic structural AST comparison and conflict classifier for MergeMind."""

import logging
from typing import Any

from app.ast.models import (
    ConflictCategory,
    ConflictClassification,
    FileAST,
    FileConflictASTAnalysis,
    StructuralChange,
)
from app.ast.parser import parse_code

logger = logging.getLogger(__name__)


def compare_ast(base_ast: FileAST, side_ast: FileAST) -> list[StructuralChange]:
    """
    Deterministically compare Base AST against a branch side (Local or Remote).
    Identifies added, removed, and modified structural nodes.
    """
    changes: list[StructuralChange] = []

    if not base_ast.parse_success or not side_ast.parse_success:
        return changes

    # Index primary named structural elements: (node_type, name) -> ASTNodeInfo
    # Focus comparison on major semantic elements: functions, methods, classes, imports
    base_major = {
        (n.type, n.name): n
        for n in base_ast.nodes
        if n.name and n.type in (
            "function_definition",
            "function_declaration",
            "arrow_function",
            "class_definition",
            "class_declaration",
            "method_declaration",
        )
    }

    side_major = {
        (n.type, n.name): n
        for n in side_ast.nodes
        if n.name and n.type in (
            "function_definition",
            "function_declaration",
            "arrow_function",
            "class_definition",
            "class_declaration",
            "method_declaration",
        )
    }

    # 1. Detect major structural additions and modifications
    for (ntype, name), side_node in side_major.items():
        if (ntype, name) not in base_major:
            is_func = "function" in ntype or "method" in ntype
            is_class = "class" in ntype
            change_type = "added_function" if is_func else ("added_class" if is_class else f"added_{ntype}")
            changes.append(
                StructuralChange(
                    change_type=change_type,
                    node_type=ntype,
                    node_name=name,
                    start_line=side_node.start_line,
                    end_line=side_node.end_line,
                    details=f"Added {ntype} '{name}' at lines {side_node.start_line}-{side_node.end_line}",
                )
            )
        else:
            base_node = base_major[(ntype, name)]
            if base_node.content_hash != side_node.content_hash:
                is_func = "function" in ntype or "method" in ntype
                is_class = "class" in ntype
                change_type = "modified_function" if is_func else ("modified_class" if is_class else f"modified_{ntype}")
                changes.append(
                    StructuralChange(
                        change_type=change_type,
                        node_type=ntype,
                        node_name=name,
                        start_line=side_node.start_line,
                        end_line=side_node.end_line,
                        details=f"Modified {ntype} '{name}' at lines {side_node.start_line}-{side_node.end_line}",
                    )
                )

    # 2. Detect major structural removals
    for (ntype, name), base_node in base_major.items():
        if (ntype, name) not in side_major:
            is_func = "function" in ntype or "method" in ntype
            is_class = "class" in ntype
            change_type = "removed_function" if is_func else ("removed_class" if is_class else f"removed_{ntype}")
            changes.append(
                StructuralChange(
                    change_type=change_type,
                    node_type=ntype,
                    node_name=name,
                    start_line=base_node.start_line,
                    end_line=base_node.end_line,
                    details=f"Removed {ntype} '{name}' (was at lines {base_node.start_line}-{base_node.end_line})",
                )
            )

    # 3. Detect Import changes
    base_imports = {
        n.name for n in base_ast.nodes if "import" in n.type and n.name
    }
    side_imports = {
        n.name for n in side_ast.nodes if "import" in n.type and n.name
    }

    added_imports = side_imports - base_imports
    removed_imports = base_imports - side_imports

    for imp in added_imports:
        changes.append(
            StructuralChange(
                change_type="added_import",
                node_type="import",
                node_name=imp,
                details=f"Added import: {imp}",
            )
        )
    for imp in removed_imports:
        changes.append(
            StructuralChange(
                change_type="removed_import",
                node_type="import",
                node_name=imp,
                details=f"Removed import: {imp}",
            )
        )

    # 4. Detect other micro structural changes if no major changes detected
    if not changes:
        # Check assignments, calls, returns
        base_stmts = [n for n in base_ast.nodes if n.type in ("assignment", "return_statement", "call", "call_expression", "variable_declarator")]
        side_stmts = [n for n in side_ast.nodes if n.type in ("assignment", "return_statement", "call", "call_expression", "variable_declarator")]

        base_hashes = {n.content_hash for n in base_stmts}
        side_hashes = {n.content_hash for n in side_stmts}

        if base_hashes != side_hashes:
            for s in side_stmts:
                if s.content_hash not in base_hashes:
                    c_type = f"modified_{s.type}"
                    if s.type == "call_expression":
                        c_type = "modified_call"
                    elif s.type == "variable_declarator":
                        c_type = "modified_assignment"
                    changes.append(
                        StructuralChange(
                            change_type=c_type,
                            node_type=s.type,
                            node_name=s.name,
                            start_line=s.start_line,
                            end_line=s.end_line,
                            details=f"Modified {s.type} '{s.name or s.signature}' at line {s.start_line}",
                        )
                    )

    return changes


def classify_conflict(
    base_ast: FileAST,
    local_ast: FileAST,
    remote_ast: FileAST,
    local_changes: list[StructuralChange],
    remote_changes: list[StructuralChange],
) -> ConflictClassification:
    """
    Deterministically classify the conflict into one of 7 categories:
    1. SAME_REGION
    2. DIFFERENT_REGION
    3. ADD_ADD
    4. DELETE_MODIFY
    5. MODIFY_MODIFY
    6. IMPORT_IMPORT
    7. UNKNOWN
    """
    if base_ast.language == "unsupported":
        return ConflictClassification(
            category="UNKNOWN",
            confidence="deterministic",
            reason="Language is unsupported for AST classification.",
        )

    if not base_ast.parse_success or not local_ast.parse_success or not remote_ast.parse_success:
        return ConflictClassification(
            category="UNKNOWN",
            confidence="deterministic",
            reason="Failed to parse one or more versions into a valid AST.",
        )

    # Rule 1: IMPORT_IMPORT
    # All changes on both sides are import additions or removals
    local_is_all_imports = local_changes and all(c.node_type == "import" for c in local_changes)
    remote_is_all_imports = remote_changes and all(c.node_type == "import" for c in remote_changes)
    if local_is_all_imports and remote_is_all_imports:
        return ConflictClassification(
            category="IMPORT_IMPORT",
            confidence="deterministic",
            reason="Both branches independently modified import/dependency declarations.",
        )

    # Rule 2: DELETE_MODIFY
    # One side removes an element that the other side modified
    local_removed_names = {c.node_name for c in local_changes if "removed" in c.change_type and c.node_name}
    remote_removed_names = {c.node_name for c in remote_changes if "removed" in c.change_type and c.node_name}

    local_modified_names = {c.node_name for c in local_changes if "modified" in c.change_type and c.node_name}
    remote_modified_names = {c.node_name for c in remote_changes if "modified" in c.change_type and c.node_name}

    if (local_removed_names & remote_modified_names) or (remote_removed_names & local_modified_names):
        conflict_name = list((local_removed_names & remote_modified_names) | (remote_removed_names & local_modified_names))[0]
        return ConflictClassification(
            category="DELETE_MODIFY",
            confidence="deterministic",
            reason=f"One branch deleted '{conflict_name}' while the other branch modified it.",
        )

    # Rule 3: ADD_ADD
    # Both sides added a new element with the same name or signature
    local_added_names = {c.node_name for c in local_changes if "added" in c.change_type and c.node_name and c.node_type != "import"}
    remote_added_names = {c.node_name for c in remote_changes if "added" in c.change_type and c.node_name and c.node_type != "import"}

    if local_added_names and remote_added_names and (local_added_names & remote_added_names):
        common_added = list(local_added_names & remote_added_names)[0]
        return ConflictClassification(
            category="ADD_ADD",
            confidence="deterministic",
            reason=f"Both branches added a new element with the same name: '{common_added}'.",
        )

    # Rule 4: MODIFY_MODIFY
    # Both sides modified the same existing element
    if local_modified_names and remote_modified_names and (local_modified_names & remote_modified_names):
        common_mod = list(local_modified_names & remote_modified_names)[0]
        return ConflictClassification(
            category="MODIFY_MODIFY",
            confidence="deterministic",
            reason=f"Both branches modified the same element: '{common_mod}'.",
        )

    # Rule 5: Check line range overlap (SAME_REGION vs DIFFERENT_REGION)
    # Collect line ranges modified by local and remote
    local_ranges = [
        (c.start_line, c.end_line)
        for c in local_changes
        if c.start_line is not None and c.end_line is not None
    ]
    remote_ranges = [
        (c.start_line, c.end_line)
        for c in remote_changes
        if c.start_line is not None and c.end_line is not None
    ]

    has_overlap = False
    for l_start, l_end in local_ranges:
        for r_start, r_end in remote_ranges:
            if max(l_start, r_start) <= min(l_end, r_end):
                has_overlap = True
                break
        if has_overlap:
            break

    if has_overlap:
        return ConflictClassification(
            category="SAME_REGION",
            confidence="deterministic",
            reason="Both branches modified overlapping structural line ranges.",
        )

    if local_ranges and remote_ranges and not has_overlap:
        return ConflictClassification(
            category="DIFFERENT_REGION",
            confidence="deterministic",
            reason="Local and Remote modified different, non-overlapping structural regions.",
        )

    # Fallback if no specific condition matched
    if not local_changes and not remote_changes:
        return ConflictClassification(
            category="UNKNOWN",
            confidence="deterministic",
            reason="No structural AST changes detected between versions.",
        )

    return ConflictClassification(
        category="UNKNOWN",
        confidence="deterministic",
        reason="Structural changes could not be classified into a standard category.",
    )


def analyze_conflicted_file(
    path: str,
    base_code: str,
    local_code: str,
    remote_code: str,
) -> FileConflictASTAnalysis:
    """
    Parse Base, Local, and Remote versions independently and produce
    a complete structural AST conflict analysis and deterministic classification.
    """
    base_ast = parse_code(path, base_code)
    local_ast = parse_code(path, local_code)
    remote_ast = parse_code(path, remote_code)

    local_changes = compare_ast(base_ast, local_ast)
    remote_changes = compare_ast(base_ast, remote_ast)

    classification = classify_conflict(
        base_ast=base_ast,
        local_ast=local_ast,
        remote_ast=remote_ast,
        local_changes=local_changes,
        remote_changes=remote_changes,
    )

    return FileConflictASTAnalysis(
        path=path,
        language=base_ast.language,
        base={
            "parse_success": base_ast.parse_success,
            "has_error": base_ast.has_error,
            "root_type": base_ast.root_type,
            "node_count": len(base_ast.nodes),
        },
        local={
            "parse_success": local_ast.parse_success,
            "has_error": local_ast.has_error,
            "root_type": local_ast.root_type,
            "node_count": len(local_ast.nodes),
        },
        remote={
            "parse_success": remote_ast.parse_success,
            "has_error": remote_ast.has_error,
            "root_type": remote_ast.root_type,
            "node_count": len(remote_ast.nodes),
        },
        changes={
            "local": [c.model_dump() for c in local_changes],
            "remote": [c.model_dump() for c in remote_changes],
        },
        classification=classification,
    )

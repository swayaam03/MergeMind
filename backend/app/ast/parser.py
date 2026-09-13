"""Tree-sitter parser and structured AST extractor for MergeMind."""

import hashlib
import logging
from typing import Any
from tree_sitter import Node

from app.ast.languages import detect_language, get_parser_for_language
from app.ast.models import ASTNodeInfo, FileAST

logger = logging.getLogger(__name__)


def _compute_hash(node_text: bytes) -> str:
    """Compute truncated SHA-256 hash of node text for change detection."""
    return hashlib.sha256(node_text).hexdigest()[:16]


def _extract_name_python(node: Node) -> str | None:
    """Extract identifier name for Python AST nodes."""
    if node.type in ("function_definition", "class_definition"):
        name_node = node.child_by_field_name("name")
        return name_node.text.decode("utf-8", errors="replace") if name_node else None

    if node.type in ("import_statement", "import_from_statement"):
        return node.text.decode("utf-8", errors="replace").strip()

    if node.type == "assignment":
        left_node = node.child_by_field_name("left")
        return left_node.text.decode("utf-8", errors="replace").strip() if left_node else None

    if node.type == "call":
        func_node = node.child_by_field_name("function")
        return func_node.text.decode("utf-8", errors="replace").strip() if func_node else None

    if node.type == "return_statement":
        return node.text.decode("utf-8", errors="replace").strip()

    return None


def _extract_name_javascript(node: Node) -> str | None:
    """Extract identifier name for JavaScript AST nodes."""
    if node.type in ("function_declaration", "class_declaration"):
        name_node = node.child_by_field_name("name")
        return name_node.text.decode("utf-8", errors="replace") if name_node else None

    if node.type == "arrow_function":
        parent = node.parent
        if parent and parent.type == "variable_declarator":
            name_node = parent.child_by_field_name("name")
            return name_node.text.decode("utf-8", errors="replace") if name_node else None
        return "anonymous_arrow_function"

    if node.type == "variable_declarator":
        name_node = node.child_by_field_name("name")
        return name_node.text.decode("utf-8", errors="replace") if name_node else None

    if node.type == "import_statement":
        return node.text.decode("utf-8", errors="replace").strip()

    if node.type == "call_expression":
        func_node = node.child_by_field_name("function")
        return func_node.text.decode("utf-8", errors="replace").strip() if func_node else None

    if node.type == "return_statement":
        return node.text.decode("utf-8", errors="replace").strip()

    return None


def _extract_name_java(node: Node) -> str | None:
    """Extract identifier name for Java AST nodes."""
    if node.type in ("class_declaration", "method_declaration"):
        name_node = node.child_by_field_name("name")
        return name_node.text.decode("utf-8", errors="replace") if name_node else None

    if node.type == "import_declaration":
        return node.text.decode("utf-8", errors="replace").strip()

    if node.type == "variable_declarator":
        name_node = node.child_by_field_name("name")
        return name_node.text.decode("utf-8", errors="replace") if name_node else None

    if node.type == "method_invocation":
        name_node = node.child_by_field_name("name")
        return name_node.text.decode("utf-8", errors="replace") if name_node else None

    if node.type == "return_statement":
        return node.text.decode("utf-8", errors="replace").strip()

    return None


TARGET_NODE_TYPES = {
    "python": {
        "function_definition",
        "class_definition",
        "import_statement",
        "import_from_statement",
        "assignment",
        "return_statement",
        "call",
    },
    "javascript": {
        "function_declaration",
        "arrow_function",
        "class_declaration",
        "import_statement",
        "variable_declaration",
        "variable_declarator",
        "return_statement",
        "call_expression",
    },
    "java": {
        "class_declaration",
        "method_declaration",
        "import_declaration",
        "variable_declarator",
        "method_invocation",
        "return_statement",
    },
}


def _walk_tree(node: Node):
    """Depth-first traversal yielding all nodes in the Tree-sitter tree."""
    yield node
    for child in node.children:
        yield from _walk_tree(child)


def parse_code(path: str, source_code: str) -> FileAST:
    """
    Parse source code into structured AST information using Tree-sitter.

    Deterministic and robust:
    - Never executes source code.
    - Handles syntax errors gracefully without crashing.
    - Extracts key structural elements (functions, classes, imports, etc.).
    """
    language = detect_language(path)
    if language == "unsupported":
        return FileAST(
            path=path,
            language="unsupported",
            parse_success=False,
            has_error=False,
            root_type="",
            nodes=[],
            errors=[f"Unsupported language for path: {path}"],
        )

    parser = get_parser_for_language(language)
    if parser is None:
        return FileAST(
            path=path,
            language=language,
            parse_success=False,
            has_error=True,
            root_type="",
            nodes=[],
            errors=[f"Failed to load Tree-sitter parser for {language}"],
        )

    source_bytes = source_code.encode("utf-8")
    try:
        tree = parser.parse(source_bytes)
    except Exception as exc:
        logger.exception("Tree-sitter parse exception on %s", path)
        return FileAST(
            path=path,
            language=language,
            parse_success=False,
            has_error=True,
            root_type="",
            nodes=[],
            errors=[f"Tree-sitter parse exception: {str(exc)}"],
        )

    root = tree.root_node
    root_type = root.type
    has_syntax_error = root.has_error

    syntax_errors: list[str] = []
    extracted_nodes: list[ASTNodeInfo] = []
    target_types = TARGET_NODE_TYPES.get(language, set())

    # Single pass traversal to collect target nodes and detect errors
    for node in _walk_tree(root):
        if node.type == "ERROR" or node.is_missing:
            has_syntax_error = True
            syntax_errors.append(
                f"Syntax error near line {node.start_point.row + 1}, column {node.start_point.column + 1}"
            )

        if node.type in target_types:
            name: str | None = None
            if language == "python":
                name = _extract_name_python(node)
            elif language == "javascript":
                name = _extract_name_javascript(node)
            elif language == "java":
                name = _extract_name_java(node)

            start_line = node.start_point.row + 1
            end_line = node.end_point.row + 1

            # Extract compact signature (first line of node text)
            raw_node_text = node.text
            first_line = raw_node_text.splitlines()[0].decode("utf-8", errors="replace").strip() if raw_node_text else ""
            signature = first_line[:120] if first_line else None

            extracted_nodes.append(
                ASTNodeInfo(
                    type=node.type,
                    name=name,
                    start_line=start_line,
                    end_line=end_line,
                    signature=signature,
                    content_hash=_compute_hash(raw_node_text),
                )
            )

    return FileAST(
        path=path,
        language=language,
        parse_success=True,
        has_error=has_syntax_error,
        root_type=root_type,
        nodes=extracted_nodes,
        errors=syntax_errors,
    )

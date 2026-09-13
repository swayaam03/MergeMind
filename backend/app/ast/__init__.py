"""MergeMind AST package for deterministic Tree-sitter parsing and conflict classification."""

from app.ast.classifier import (
    analyze_conflicted_file,
    classify_conflict,
    compare_ast,
)
from app.ast.languages import detect_language, get_parser_for_language
from app.ast.models import (
    ASTNodeInfo,
    ConflictCategory,
    ConflictClassification,
    FileAST,
    FileConflictASTAnalysis,
    StructuralChange,
)
from app.ast.parser import parse_code

__all__ = [
    "detect_language",
    "get_parser_for_language",
    "parse_code",
    "compare_ast",
    "classify_conflict",
    "analyze_conflicted_file",
    "ASTNodeInfo",
    "FileAST",
    "StructuralChange",
    "ConflictCategory",
    "ConflictClassification",
    "FileConflictASTAnalysis",
]

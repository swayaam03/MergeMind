"""Pydantic data models for structured Tree-sitter AST extraction and conflict classification."""

from typing import Any, Literal
from pydantic import BaseModel, Field


class ASTNodeInfo(BaseModel):
    """Compact structural representation of a key AST node."""
    type: str = Field(description="Tree-sitter node type (e.g. function_definition, class_declaration)")
    name: str | None = Field(default=None, description="Identifier name of the symbol (function, class, variable)")
    start_line: int = Field(description="1-indexed start line number")
    end_line: int = Field(description="1-indexed end line number")
    signature: str | None = Field(default=None, description="Brief signature or declaration header")
    content_hash: str = Field(default="", description="SHA-256 hash of the node source text for change detection")


class FileAST(BaseModel):
    """Normalized structured AST representation for a source file."""
    path: str
    language: str
    parse_success: bool
    has_error: bool = False
    root_type: str = ""
    nodes: list[ASTNodeInfo] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class StructuralChange(BaseModel):
    """Represents a structural delta between Base and a branch side."""
    change_type: str = Field(description="e.g. added_function, modified_function, removed_function, added_class, etc.")
    node_type: str
    node_name: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    details: str = ""


ConflictCategory = Literal[
    "SAME_REGION",
    "DIFFERENT_REGION",
    "ADD_ADD",
    "DELETE_MODIFY",
    "MODIFY_MODIFY",
    "IMPORT_IMPORT",
    "UNKNOWN",
]


class ConflictClassification(BaseModel):
    """Deterministic structural conflict classification result."""
    category: ConflictCategory
    confidence: Literal["deterministic"] = "deterministic"
    reason: str


class FileConflictASTAnalysis(BaseModel):
    """Complete 3-way AST structural comparison and classification for a conflicted file."""
    path: str
    language: str
    base: dict[str, Any]
    local: dict[str, Any]
    remote: dict[str, Any]
    changes: dict[str, list[dict[str, Any]]]
    classification: ConflictClassification

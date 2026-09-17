"""Pydantic models for repository context extraction.

Represents structured repository-level information (README, documentation,
compact directory tree, detected technologies, relevant files, and metadata)
needed by the downstream LLM Merge Agent.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RepositoryRef(BaseModel):
    """Repository identification."""

    owner: str = Field(..., description="Repository owner login")
    name: str = Field(..., description="Repository name")


class ProjectInfo(BaseModel):
    """Deterministic project metadata extracted from manifests and documentation."""

    description: Optional[str] = Field(
        default=None,
        description="Deterministic project summary extracted from README or ProjectInfo",
    )
    languages: List[str] = Field(
        default_factory=list,
        description="List of detected programming languages (normalized lowercase)",
    )
    frameworks: List[str] = Field(
        default_factory=list,
        description="List of detected libraries and frameworks",
    )
    package_managers: List[str] = Field(
        default_factory=list,
        description="List of detected package managers and build tools",
    )


class DocumentationFile(BaseModel):
    """Single documentation file content and metadata."""

    path: str = Field(..., description="Repository-relative path of the documentation file")
    content: str = Field(..., description="Extracted UTF-8 content of the documentation file")
    truncated: bool = Field(default=False, description="Whether documentation was capped at character limit")


class DocumentationContext(BaseModel):
    """Collection of prioritized project documentation."""

    files: List[DocumentationFile] = Field(
        default_factory=list,
        description="Documentation files (README.md, ProjectInfo.md, etc.) in priority order",
    )


class StructureContext(BaseModel):
    """Visual compact directory tree representation."""

    tree: str = Field(..., description="Compact formatted text tree of non-vendor repository files")
    truncated: bool = Field(default=False, description="Whether directory tree was capped at max entries limit")


class RelevantFile(BaseModel):
    """Preview and relevance justification for a relevant source or test file."""

    path: str = Field(..., description="Repository-relative file path")
    reason: Optional[str] = Field(
        default="relevant file",
        description="Deterministic justification (e.g. 'conflicting file', 'associated test', 'imported local module', 'same-directory sibling')",
    )
    content: Optional[str] = Field(default=None, description="UTF-8 decoded file content preview")
    size: int = Field(default=0, description="Original file size in bytes")
    truncated: bool = Field(default=False, description="Whether content was capped at byte limit")
    ast_elements: List[str] = Field(
        default_factory=list,
        description="Names of conflicting AST functions or classes associated with this file",
    )


# Alias for backward compatibility with earlier tests
FilePreview = RelevantFile


class TechnologyInfo(BaseModel):
    """Detailed technology, framework, runtime, or build tool detection item."""

    name: str = Field(..., description="Standardized name of the technology/framework")
    category: str = Field(
        ...,
        description="Category: 'language', 'framework', 'package_manager', 'testing', 'runtime', 'build'",
    )
    detected_from: str = Field(
        ...,
        description="Source file or signal triggering detection (e.g. 'requirements.txt', 'package.json')",
    )
    version: Optional[str] = Field(default=None, description="Extracted version or constraint if parsed")


class RepositoryContext(BaseModel):
    """Complete structured repository context for a pull request."""

    repository: RepositoryRef = Field(..., description="Repository owner and name")
    project: ProjectInfo = Field(..., description="Deterministic project metadata and technologies")
    documentation: DocumentationContext = Field(
        default_factory=DocumentationContext,
        description="Extracted documentation files",
    )
    structure: StructureContext = Field(..., description="Compact repository directory tree")
    relevant_files: List[RelevantFile] = Field(
        default_factory=list,
        description="Prioritized relevant files (conflicting file, local imports, associated tests, siblings)",
    )

    # Backward compatibility fields for existing frontend & API consumers
    base_ref: str = Field(default="", description="Target base branch/ref of the PR")
    head_ref: str = Field(default="", description="Source branch/ref of the PR")
    readme_preview: Optional[str] = Field(
        default=None,
        description="Truncated UTF-8 content of primary README",
    )
    directory_structure: List[str] = Field(
        default_factory=list,
        description="List of file paths representing filtered repository tree",
    )
    tree_truncated: bool = Field(
        default=False,
        description="Whether directory tree was truncated to limits",
    )
    detected_technologies: List[TechnologyInfo] = Field(
        default_factory=list,
        description="Detailed list of all detected technologies and tools",
    )
    languages: Dict[str, int] = Field(
        default_factory=dict,
        description="GitHub detected language byte counts",
    )
    total_files_examined: int = Field(
        default=0,
        description="Count of files traversed in repository tree",
    )

    @classmethod
    def from_raw(cls, **kwargs):
        """Helper constructor."""
        return cls(**kwargs)

    @classmethod
    def _normalize_dict(cls, data: dict) -> dict:
        raw_repo = data.get("repository")
        if isinstance(raw_repo, str):
            parts = raw_repo.split("/")
            data["repository"] = {
                "owner": parts[0] if parts else "",
                "name": parts[1] if len(parts) > 1 else "",
            }
        if "project" not in data or data["project"] is None:
            data["project"] = {
                "description": None,
                "languages": list(data.get("languages", {}).keys()),
                "frameworks": [],
                "package_managers": [],
            }
        if "structure" not in data or data["structure"] is None:
            data["structure"] = {
                "tree": "\n".join(data.get("directory_structure", [])),
                "truncated": bool(data.get("tree_truncated", False)),
            }
        if "documentation" not in data or data["documentation"] is None:
            doc_files = []
            if data.get("readme_preview"):
                doc_files.append({"path": "README.md", "content": data["readme_preview"], "truncated": False})
            data["documentation"] = {"files": doc_files}
        return data

    def __init__(self, **data: Any):
        normalized = self._normalize_dict(data)
        super().__init__(**normalized)

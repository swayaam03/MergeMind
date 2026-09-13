"""Pydantic models for repository context extraction.

Represents structured repository-level information (README, directory tree,
detected technologies, relevant neighbor files, and metadata) needed by
the downstream LLM Merge Agent.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FilePreview(BaseModel):
    """Preview of a file discovered in the repository."""

    path: str = Field(..., description="Repository-relative file path")
    content: str = Field(..., description="UTF-8 decoded file content (may be truncated)")
    size: int = Field(..., description="Original file size in bytes")
    truncated: bool = Field(default=False, description="Whether content was capped at byte limit")
    reason: Optional[str] = Field(
        default=None,
        description="Reason why this file was included (e.g. 'same_directory', 'package_init')"
    )


class TechnologyInfo(BaseModel):
    """Identified technology, framework, runtime, or build tool."""

    name: str = Field(..., description="Standardized name of the technology/framework")
    category: str = Field(
        ...,
        description="Category: 'language', 'framework', 'package_manager', 'testing', 'runtime', 'build'"
    )
    detected_from: str = Field(
        ...,
        description="Source file or signal triggering detection (e.g. 'requirements.txt', 'package.json')"
    )
    version: Optional[str] = Field(default=None, description="Extracted version or constraint if parsed")


class RepositoryContext(BaseModel):
    """Complete structured repository context for a pull request."""

    repository: str = Field(..., description="Full repository name: owner/repo")
    base_ref: str = Field(..., description="Target base branch/ref of the PR")
    head_ref: str = Field(..., description="Source branch/ref of the PR")
    readme_preview: Optional[str] = Field(
        default=None,
        description="Truncated UTF-8 content of repository root README (max 10 KB)"
    )
    directory_structure: List[str] = Field(
        default_factory=list,
        description="List of file paths representing repository tree"
    )
    tree_truncated: bool = Field(
        default=False,
        description="Whether directory tree was truncated to limits"
    )
    detected_technologies: List[TechnologyInfo] = Field(
        default_factory=list,
        description="Technologies, frameworks, and tools detected deterministically"
    )
    languages: Dict[str, int] = Field(
        default_factory=dict,
        description="GitHub detected language byte counts"
    )
    relevant_files: List[FilePreview] = Field(
        default_factory=list,
        description="Previews of non-conflicting files relevant to the conflict scope"
    )
    total_files_examined: int = Field(
        default=0,
        description="Count of files traversed or queried"
    )

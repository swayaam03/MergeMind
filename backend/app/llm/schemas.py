"""Pydantic request and response schemas for the LLM Merge Agent."""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field

ProposalStatus = Literal["resolved", "unresolved"]


class MergeProposal(BaseModel):
    """Strict Pydantic schema for the LLM Merge Agent's resolution proposal."""

    status: ProposalStatus = Field(
        ...,
        description="'resolved' if a coherent merged code proposal was generated; 'unresolved' if conflict cannot be safely resolved",
    )
    merged_code: str = Field(
        default="",
        description="The proposed resolved file content. Must be non-empty when status is 'resolved'",
    )
    explanation: str = Field(
        ...,
        description="Plain text explanation of how the conflict was reasoned about and resolved, or why it cannot be resolved",
    )
    preserved_changes: List[str] = Field(
        default_factory=list,
        description="Specific changes, behaviors, or logic preserved from Local and Remote sides",
    )
    risks: List[str] = Field(
        default_factory=list,
        description="Identified risks, caveats, or potential regressions that human reviewers should watch out for",
    )
    file_path: Optional[str] = Field(
        default=None,
        description="Repository-relative file path of the conflicted file",
    )
    model: Optional[str] = Field(
        default=None,
        description="LLM model used to generate this merge proposal",
    )


class MergeProposalRequest(BaseModel):
    """Request payload for merge proposal endpoint."""

    file_path: Optional[str] = Field(
        default=None,
        description="Optional repository-relative file path of the conflicted file to resolve. If omitted, the first conflicted file is targeted.",
    )

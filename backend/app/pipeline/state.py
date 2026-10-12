"""MergeState definitions for LangGraph orchestration in MergeMind."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict


class MergeAttemptRecord(TypedDict, total=False):
    """Snapshot of a single merge attempt and its verification result."""

    attempt_number: int
    proposal: Dict[str, Any]
    verification: Optional[Dict[str, Any]]
    feedback_provided: Optional[str]
    timestamp: float


class PipelineEvent(TypedDict, total=False):
    """Structured event for real-time progress tracking."""

    event_type: str  # e.g., "state_change", "attempt_started", "verification_completed", "escalated"
    message: str
    timestamp: float
    data: Optional[Dict[str, Any]]


class MergeState(TypedDict, total=False):
    """
    Shared state object passed through the LangGraph StateGraph.

    Carries:
    - Conflict information (Base, Local, Remote versions)
    - AST classification summary
    - Extracted repository context
    - Full merge attempt history
    - Retry counter and maximum allowed retries
    - Most recent verification and security results
    - Explanation Agent report (if retries exhausted)
    - Current lifecycle status and event logs
    """

    # Target file details
    file_path: str
    language: str
    conflicted_file: Dict[str, Any]

    # Deterministic metadata
    ast_analysis: Optional[Dict[str, Any]]
    repository_context: Optional[Dict[str, Any]]
    source_dir: Optional[str]  # Root repo workspace for Docker verification

    # Retry tracking
    retry_count: int
    max_retries: int

    # Current proposal and verification
    current_proposal: Optional[Dict[str, Any]]
    current_verification: Optional[Dict[str, Any]]

    # History of past attempts in this workflow run
    history: List[MergeAttemptRecord]

    # Human-in-the-loop explanation if automated retries fail
    explanation: Optional[Dict[str, Any]]

    # High-level status:
    # "initialized", "merging", "verifying", "retrying", "verified", "escalated", "failed"
    status: str

    # Pipeline event logs
    events: List[PipelineEvent]

    # Error message if fatal exception occurs
    error: Optional[str]

"""Database models and Pydantic schemas for User Authentication and GitHub Account Linking."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=5, max_length=120)
    password: str = Field(..., min_length=6, max_length=128)


class UserLoginRequest(BaseModel):
    username_or_email: str
    password: str


class GitHubConnectRequest(BaseModel):
    installation_id: int = Field(..., gt=0)


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    github_installation_id: Optional[int] = None
    github_username: Optional[str] = None
    github_connected_at: Optional[str] = None
    is_github_connected: bool = False
    repository_count: Optional[int] = None
    created_at: str


class AuthResponse(BaseModel):
    user: UserResponse
    token: str
    message: str = "Success"


class RepositoryRecord(BaseModel):
    id: str
    owner: str
    name: str
    full_name: str
    default_branch: str = "main"
    is_private: bool = False
    installation_id: Optional[int] = None
    created_at: str
    updated_at: str


class PullRequestRecord(BaseModel):
    id: str
    repository_full_name: str
    number: int
    title: str
    state: str = "open"
    base_branch: str
    head_branch: str
    mergeable_state: Optional[str] = None
    has_conflicts: bool = False
    created_at: str
    updated_at: str


class ConflictRecord(BaseModel):
    id: str
    repository_full_name: str
    pull_request_number: int
    file_path: str
    conflict_type: Optional[str] = None
    base_code: Optional[str] = None
    local_code: Optional[str] = None
    remote_code: Optional[str] = None
    created_at: str


class MergeAttemptRecord(BaseModel):
    id: str
    merge_run_id: str
    attempt_number: int
    model_used: Optional[str] = None
    resolved_code: Optional[str] = None
    reasoning: Optional[str] = None
    confidence: Optional[float] = None
    verification_passed: bool = False
    security_passed: bool = False
    failure_reason: Optional[str] = None
    created_at: str


class MergeRunRecord(BaseModel):
    id: str
    repository_full_name: str
    pull_request_number: int
    file_path: str
    status: str
    total_attempts: int = 0
    resolved_code: Optional[str] = None
    explanation: Optional[str] = None
    human_decision: Optional[str] = None
    human_decision_at: Optional[str] = None
    created_at: str
    updated_at: str


class HumanDecisionRequest(BaseModel):
    decision: str = Field(..., description="Action: 'accept', 'edit', or 'reject'")
    file_path: str = Field(..., description="Target conflicted file path")
    final_code: Optional[str] = Field(default=None, description="Final resolved code (if accepted or edited)")
    notes: Optional[str] = Field(default=None, description="Optional developer rationale or review comments")


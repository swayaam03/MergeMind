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

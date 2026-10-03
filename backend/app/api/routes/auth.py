"""Authentication API routes for MergeMind user accounts and GitHub linking."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Cookie, Header, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse

from app.db import database as db
from app.db.models import (
    AuthResponse,
    GitHubConnectRequest,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.git.github import (
    GitHubAPIError,
    GitHubAuthError,
    GitHubConfigError,
    list_repositories_for_installation,
    verify_installation,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


def get_current_user(
    request: Request,
    session_token_cookie: Optional[str] = None,
    session_token_header: Optional[str] = None,
    auth_header: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Extract authenticated user from session cookie, custom header, or Bearer auth header."""
    token: Optional[str] = None

    if isinstance(session_token_cookie, str) and session_token_cookie:
        token = session_token_cookie
    elif "session_token" in request.cookies:
        token = request.cookies.get("session_token")
    elif isinstance(session_token_header, str) and session_token_header:
        token = session_token_header
    elif "x-session-token" in request.headers:
        token = request.headers.get("x-session-token")

    if not token:
        raw_auth = auth_header if isinstance(auth_header, str) else request.headers.get("authorization", "")
        if raw_auth and raw_auth.startswith("Bearer "):
            token = raw_auth.split(" ", 1)[1].strip()

    if not token or not isinstance(token, str) or not token.strip():
        return None

    return db.get_user_by_session_token(token)


def format_user_response(user: Dict[str, Any]) -> UserResponse:
    """Format raw database row into UserResponse model, checking repository count if connected."""
    installation_id = user.get("github_installation_id")
    repo_count: Optional[int] = None
    is_connected = bool(installation_id and installation_id > 0)

    if is_connected:
        try:
            repos = list_repositories_for_installation(installation_id)
            repo_count = len(repos)
        except Exception as exc:
            logger.debug("Failed to list repos for installation %s: %s", installation_id, exc)

    return UserResponse(
        id=user["id"],
        username=user["username"],
        email=user["email"],
        github_installation_id=installation_id,
        github_username=user.get("github_username"),
        github_connected_at=user.get("github_connected_at"),
        is_github_connected=is_connected,
        repository_count=repo_count,
        created_at=user["created_at"],
    )


@router.post("/register", response_model=AuthResponse)
def register(req: UserRegisterRequest, response: Response):
    """Register a new user account."""
    try:
        user = db.create_user(req.username, req.email, req.password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    token = db.create_session(user["id"])
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=86400 * 14,
        path="/",
    )
    user_res = format_user_response(user)
    return AuthResponse(user=user_res, token=token, message="Registration successful")


@router.post("/login", response_model=AuthResponse)
def login(req: UserLoginRequest, response: Response):
    """Login with username or email and password."""
    user = db.authenticate_user(req.username_or_email, req.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password.",
        )

    token = db.create_session(user["id"])
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=86400 * 14,
        path="/",
    )
    user_res = format_user_response(user)
    return AuthResponse(user=user_res, token=token, message="Login successful")


@router.get("/me", response_model=UserResponse)
def get_me(request: Request):
    """Get the current authenticated user's profile and GitHub connection status."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
        )
    return format_user_response(user)


@router.post("/connect-github", response_model=UserResponse)
def connect_github(req: GitHubConnectRequest, request: Request):
    """Manually link a GitHub App installation ID to the current account."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You must be logged in to connect your GitHub account.",
        )

    try:
        # Verify the installation exists on GitHub
        repo_names = verify_installation(req.installation_id)
        # Try to discover account login
        from app.git.github import generate_jwt, GITHUB_API_BASE, GITHUB_API_VERSION
        import httpx
        jwt = generate_jwt()
        headers = {
            "Authorization": f"Bearer {jwt}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
        }
        gh_user_resp = httpx.get(
            f"{GITHUB_API_BASE}/app/installations/{req.installation_id}",
            headers=headers,
            timeout=5,
        )
        gh_login = None
        if gh_user_resp.status_code == 200:
            gh_login = gh_user_resp.json().get("account", {}).get("login")

        updated_user = db.link_github_installation(
            user_id=user["id"],
            installation_id=req.installation_id,
            github_username=gh_login,
        )
        return format_user_response(updated_user)

    except (GitHubConfigError, GitHubAuthError, GitHubAPIError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to verify GitHub installation: {str(exc)}",
        ) from exc


@router.post("/disconnect-github", response_model=UserResponse)
def disconnect_github(request: Request):
    """Unlink GitHub account from the user profile."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
        )
    updated = db.unlink_github_installation(user["id"])
    return format_user_response(updated)


@router.post("/logout")
def logout(request: Request, response: Response):
    """Log out the current user and invalidate the session."""
    user = get_current_user(request)
    token = request.cookies.get("session_token")
    if token:
        db.delete_session(token)
    response.delete_cookie(key="session_token", path="/")
    return {"message": "Logged out successfully"}

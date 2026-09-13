"""API route for repository context extraction."""

import logging
from typing import Any, List, Optional

from fastapi import APIRouter, Cookie, Header, HTTPException, Query, Request, status

from app.api.routes.pull_requests import resolve_installation_id
from app.context.extractor import extract_repository_context
from app.git.github import (
    GitHubAPIError,
    GitHubAuthError,
    GitHubConfigError,
    get_installation_access_token,
    get_installation_repositories,
    get_pull_request_detail,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/github", tags=["context"])


@router.get("/repositories/{owner}/{repo}/pulls/{pull_number}/context")
def get_repository_context(
    owner: str,
    repo: str,
    pull_number: int,
    request: Request,
    conflicting_files: Optional[List[str]] = Query(
        default=None,
        description="Optional list of conflicting file paths to discover relevant neighbor files for",
    ),
    installation_id_cookie: Optional[str] = Cookie(
        default=None,
        alias="installation_id",
        description="GitHub App installation ID stored in HttpOnly cookie",
    ),
    installation_id_query: Optional[int] = Query(
        default=None,
        alias="installation_id",
        description="Optional installation ID override for testing or direct API clients",
    ),
    installation_id_header: Optional[str] = Header(
        default=None,
        alias="x-installation-id",
        description="Optional installation ID provided via HTTP header",
    ),
) -> dict[str, Any]:
    """
    Retrieve deterministic repository context for a pull request.

    Collects:
    - Truncated repository README preview
    - Repository directory tree structure
    - GitHub language breakdown
    - Deterministically detected technologies & frameworks
    - Non-conflicting neighbor and test file previews
    """
    target_installation_id = resolve_installation_id(
        request=request,
        installation_id_cookie=installation_id_cookie,
        installation_id_header=installation_id_header,
        installation_id_query=installation_id_query,
        endpoint_name=f"GET /repositories/{owner}/{repo}/pulls/{pull_number}/context",
    )

    try:
        installation_token = get_installation_access_token(target_installation_id)

        # 1. Verify repository accessibility
        accessible_repos = get_installation_repositories(installation_token)
        target_full_name = f"{owner}/{repo}".lower()
        is_accessible = any(
            str(r.get("full_name", "")).lower() == target_full_name
            for r in accessible_repos
        )

        if not is_accessible:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Repository '{owner}/{repo}' is not accessible to this installation.",
            )

        # 2. Retrieve PR detail to determine base and head branches
        pr_data = get_pull_request_detail(
            owner=owner,
            repo=repo,
            pull_number=pull_number,
            installation_token=installation_token,
        )

        base_obj = pr_data.get("base") or {}
        head_obj = pr_data.get("head") or {}
        base_ref = base_obj.get("ref", "main")
        head_ref = head_obj.get("ref", "")

        # 3. Extract repository context
        context_result = extract_repository_context(
            owner=owner,
            repo=repo,
            token=installation_token,
            base_ref=base_ref,
            head_ref=head_ref,
            conflicting_files=conflicting_files or [],
        )

        return context_result.model_dump()

    except HTTPException:
        raise
    except GitHubConfigError as exc:
        logger.error("GitHub App configuration error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GitHub App configuration is missing or invalid.",
        ) from exc
    except GitHubAuthError as exc:
        logger.error(
            "GitHub App authentication failed for installation %d: %s",
            target_installation_id,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="GitHub App authentication failed.",
        ) from exc
    except GitHubAPIError as exc:
        logger.error(
            "GitHub API error for %s/%s PR #%d: %s (status=%d)",
            owner,
            repo,
            pull_number,
            exc,
            exc.status_code,
        )
        if exc.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pull request #{pull_number} or repository '{owner}/{repo}' not found on GitHub.",
            ) from exc
        if exc.status_code == 403:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Repository '{owner}/{repo}' is not accessible to this installation.",
            ) from exc
        raise HTTPException(
            status_code=exc.status_code if 400 <= exc.status_code < 600 else status.HTTP_502_BAD_GATEWAY,
            detail="GitHub API error while retrieving pull request context.",
        ) from exc
    except Exception as exc:
        logger.exception(
            "Unexpected error extracting context for %s/%s PR #%d",
            owner,
            repo,
            pull_number,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while extracting repository context.",
        ) from exc

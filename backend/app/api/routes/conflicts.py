"""API routes for merge conflict detection and extraction."""

import logging
from typing import Any
from fastapi import APIRouter, Cookie, Header, HTTPException, Query, Request, status

from app.api.routes.pull_requests import resolve_installation_id
from app.git.conflicts import GitConflictError, simulate_merge_and_extract_conflicts
from app.git.github import (
    GitHubAPIError,
    GitHubAuthError,
    GitHubConfigError,
    get_installation_access_token,
    get_installation_repositories,
    get_pull_request_detail,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/github", tags=["conflicts"])


@router.get("/repositories/{owner}/{repo}/pulls/{pull_number}/conflicts")
def get_pull_request_conflicts(
    owner: str,
    repo: str,
    pull_number: int,
    request: Request,
    installation_id_cookie: str | None = Cookie(
        default=None,
        alias="installation_id",
        description="GitHub App installation ID stored in HttpOnly cookie",
    ),
    installation_id_query: int | None = Query(
        default=None,
        alias="installation_id",
        description="Optional installation ID override for testing or direct API clients",
    ),
    installation_id_header: str | None = Header(
        default=None,
        alias="x-installation-id",
        description="Optional installation ID provided via HTTP header",
    ),
) -> dict[str, Any]:
    """
    Retrieve and extract merge conflict details for a pull request in an accessible repository.

    Flow:
    1. Read and validate installation context.
    2. Verify repository accessibility.
    3. Retrieve pull request detail and mergeability from GitHub.
    4. If mergeable is True, return indicating no conflict analysis required.
    5. If mergeable is None, return indicating mergeability is still being calculated.
    6. If mergeable is False, perform Git merge simulation in isolated temporary environment
       to extract Base, Local, and Remote file contents and conflict markers.
    """
    target_installation_id = resolve_installation_id(
        request=request,
        installation_id_cookie=installation_id_cookie,
        installation_id_header=installation_id_header,
        installation_id_query=installation_id_query,
        endpoint_name=f"GET /repositories/{owner}/{repo}/pulls/{pull_number}/conflicts",
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

        # 2. Retrieve pull request detail from GitHub
        pr_data = get_pull_request_detail(
            owner=owner,
            repo=repo,
            pull_number=pull_number,
            installation_token=installation_token,
        )

        base_obj = pr_data.get("base") or {}
        head_obj = pr_data.get("head") or {}

        base_branch = base_obj.get("ref", "main")
        head_branch = head_obj.get("ref", "")
        base_sha = base_obj.get("sha", "")
        head_sha = head_obj.get("sha", "")

        mergeable = pr_data.get("mergeable")
        mergeable_state = pr_data.get("mergeable_state")

        pr_info = {
            "number": pr_data.get("number", pull_number),
            "base_branch": base_branch,
            "head_branch": head_branch,
            "base_sha": base_sha,
            "head_sha": head_sha,
            "mergeable": mergeable,
            "mergeable_state": mergeable_state,
        }

        # 3. Check mergeability state
        if mergeable is True:
            return {
                "repository": {
                    "owner": owner,
                    "name": repo,
                },
                "pull_request": pr_info,
                "changed_files": [],
                "conflicting_files": [],
                "conflicts": [],
                "message": "Pull request has no merge conflicts (mergeable = true). No conflict analysis required.",
            }

        if mergeable is None:
            return {
                "repository": {
                    "owner": owner,
                    "name": repo,
                },
                "pull_request": pr_info,
                "changed_files": [],
                "conflicting_files": [],
                "conflicts": [],
                "message": "GitHub is still calculating mergeability for this pull request.",
            }

        # 4. PR is conflicted (mergeable is False) — proceed with deterministic Git simulation
        extraction_result = simulate_merge_and_extract_conflicts(
            owner=owner,
            repo=repo,
            pull_number=pull_number,
            base_branch=base_branch,
            head_branch=head_branch,
            base_sha=base_sha,
            head_sha=head_sha,
            installation_token=installation_token,
        )

        conflicts = extraction_result["conflicts"]
        msg = (
            "Conflict data extracted successfully."
            if conflicts
            else "No conflicting files detected."
        )

        return {
            "repository": {
                "owner": owner,
                "name": repo,
            },
            "pull_request": pr_info,
            "changed_files": extraction_result["changed_files"],
            "conflicting_files": extraction_result["conflicting_files"],
            "conflicts": conflicts,
            "message": msg,
        }

    except HTTPException:
        raise
    except GitHubConfigError as exc:
        logger.error("GitHub App configuration error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GitHub App configuration is missing or invalid.",
        ) from exc
    except GitHubAuthError as exc:
        logger.error("GitHub App authentication failed for installation %d: %s", target_installation_id, exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="GitHub App authentication failed.",
        ) from exc
    except GitHubAPIError as exc:
        logger.error("GitHub API error for %s/%s PR #%d: %s (status=%d)", owner, repo, pull_number, exc, exc.status_code)
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
            detail="GitHub API error while retrieving pull request.",
        ) from exc
    except GitConflictError as exc:
        logger.error("Git conflict simulation failed for %s/%s PR #%d: %s", owner, repo, pull_number, exc)
        raise HTTPException(
            status_code=exc.status_code,
            detail=f"Git conflict extraction failed: {str(exc)}",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error extracting conflicts for %s/%s PR #%d", owner, repo, pull_number)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while extracting merge conflicts.",
        ) from exc

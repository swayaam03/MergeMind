"""API route for repository context extraction."""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Cookie, Header, HTTPException, Query, Request, status

from app.api.routes.pull_requests import resolve_installation_id
from app.ast import analyze_conflicted_file
from app.context.extractor import extract_repository_context
from app.git.conflicts import simulate_merge_and_extract_conflicts
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
        description="Optional explicit list of conflicting file paths",
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

    Pipeline:
    1. Authenticate using existing GitHub App installation context.
    2. Verify repository access.
    3. Retrieve pull request detail (base/head branches, mergeability).
    4. Retrieve conflict data & AST analysis if PR is conflicted.
    5. Run deterministic Repository Context extraction.
    6. Return structured context matching Section 11 model.

    Never exposes tokens, private keys, or credentials.
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
        base_sha = base_obj.get("sha", "")
        head_sha = head_obj.get("sha", "")
        mergeable = pr_data.get("mergeable")

        conflicts_list: List[str] = list(conflicting_files or [])
        ast_analyses: Dict[str, Any] = {}
        conflict_sources: Dict[str, str] = {}

        # 3. Retrieve conflict data and AST analysis if PR is conflicted
        if mergeable is False and not conflicts_list:
            try:
                extraction = simulate_merge_and_extract_conflicts(
                    owner=owner,
                    repo=repo,
                    pull_number=pull_number,
                    base_branch=base_ref,
                    head_branch=head_ref,
                    base_sha=base_sha,
                    head_sha=head_sha,
                    installation_token=installation_token,
                )
                conflicts = extraction.get("conflicts", [])
                for c in conflicts:
                    cpath = c.get("path", "")
                    if cpath:
                        conflicts_list.append(cpath)
                        conflict_sources[cpath] = c.get("local", "") or c.get("base", "")
                        # Reuse Tree-sitter AST analysis
                        ast_res = analyze_conflicted_file(
                            path=cpath,
                            base_code=c.get("base", ""),
                            local_code=c.get("local", ""),
                            remote_code=c.get("remote", ""),
                        )
                        ast_analyses[cpath] = ast_res.model_dump()
            except Exception as exc:
                logger.warning(
                    "Could not extract live conflicts for context on %s/%s #%d: %s",
                    owner,
                    repo,
                    pull_number,
                    exc,
                )

        # 4. Extract repository context
        context_result = extract_repository_context(
            owner=owner,
            repo=repo,
            token=installation_token,
            base_ref=base_ref,
            head_ref=head_ref,
            conflicting_files=conflicts_list,
            ast_analyses=ast_analyses,
            conflict_sources=conflict_sources,
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

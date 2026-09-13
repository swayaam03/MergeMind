import logging
import re
from typing import Any
from fastapi import APIRouter, Cookie, Header, HTTPException, Query, Request, status

from app.git.github import (
    GitHubAPIError,
    GitHubAuthError,
    GitHubConfigError,
    get_pull_request_for_repo,
    list_pull_requests_for_repo,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/github", tags=["pull_requests"])


def resolve_installation_id(
    request: Request,
    installation_id_cookie: str | None = None,
    installation_id_header: str | None = None,
    installation_id_query: int | None = None,
    endpoint_name: str = "endpoint",
) -> int:
    """
    Resolve the installation ID using the robust multi-layer resolution hierarchy:
    1. FastAPI Cookie dependency
    2. request.cookies['installation_id']
    3. Raw Cookie header regex parse
    4. HTTP header: X-Installation-Id
    5. Query param: ?installation_id=<ID>

    Raises HTTPException(401) if no valid positive installation ID is found.
    """
    target_installation_id: int | None = None
    selected_source: str | None = None

    # 1. FastAPI Cookie dependency
    if installation_id_cookie:
        try:
            cleaned_val = str(installation_id_cookie).strip().strip('"').strip("'")
            val = int(cleaned_val)
            if val > 0:
                target_installation_id = val
                selected_source = "cookie (fastapi dependency)"
        except ValueError:
            pass

    # 2. request.cookies dictionary fallback
    if target_installation_id is None:
        cookie_val = request.cookies.get("installation_id")
        if cookie_val:
            try:
                cleaned_val = str(cookie_val).strip().strip('"').strip("'")
                val = int(cleaned_val)
                if val > 0:
                    target_installation_id = val
                    selected_source = "cookie (request.cookies)"
            except ValueError:
                pass

    # 3. Raw Cookie header regex parse fallback
    if target_installation_id is None:
        raw_cookie_header = request.headers.get("cookie", "")
        if "installation_id" in raw_cookie_header:
            match = re.search(r'(?:^|;\s*)installation_id=([^;]+)', raw_cookie_header)
            if match:
                try:
                    cleaned_val = match.group(1).strip().strip('"').strip("'")
                    val = int(cleaned_val)
                    if val > 0:
                        target_installation_id = val
                        selected_source = "cookie (raw header regex)"
                except ValueError:
                    pass

    # 4. HTTP header (x-installation-id)
    if target_installation_id is None and installation_id_header:
        try:
            val = int(str(installation_id_header).strip())
            if val > 0:
                target_installation_id = val
                selected_source = "header (x-installation-id)"
        except ValueError:
            pass

    # 5. Query parameter (?installation_id=...)
    if target_installation_id is None and installation_id_query:
        if installation_id_query > 0:
            target_installation_id = installation_id_query
            selected_source = "query parameter"

    cookie_present = bool(
        installation_id_cookie
        or request.cookies.get("installation_id")
        or ("installation_id=" in request.headers.get("cookie", ""))
    )
    logger.info(
        "%s context: cookie_exists=%s, header_exists=%s, query_exists=%s, selected_source=%s",
        endpoint_name,
        cookie_present,
        bool(installation_id_header),
        bool(installation_id_query),
        selected_source,
    )

    if target_installation_id is None or target_installation_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing installation context. Please connect your GitHub account via /api/github/install first.",
        )

    return target_installation_id


@router.get("/repositories/{owner}/{repo}/pulls")
def get_repository_pull_requests(
    owner: str,
    repo: str,
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
):
    """
    Retrieve open pull requests for a specific repository under the active installation.
    Validates that the repository is accessible to the installed GitHub App before querying GitHub.
    Returns only open pull requests with safe UI metadata.
    """
    target_installation_id = resolve_installation_id(
        request=request,
        installation_id_cookie=installation_id_cookie,
        installation_id_header=installation_id_header,
        installation_id_query=installation_id_query,
        endpoint_name=f"GET /repositories/{owner}/{repo}/pulls",
    )

    try:
        data = list_pull_requests_for_repo(target_installation_id, owner, repo)
        return data
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
        logger.error("GitHub API error for %s/%s under installation %d: %s (status=%d)", owner, repo, target_installation_id, exc, exc.status_code)
        if exc.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository '{owner}/{repo}' not found on GitHub.",
            ) from exc
        if exc.status_code == 403:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Repository '{owner}/{repo}' is not accessible to this installation.",
            ) from exc
        raise HTTPException(
            status_code=exc.status_code if 400 <= exc.status_code < 600 else status.HTTP_502_BAD_GATEWAY,
            detail="GitHub API error while retrieving pull requests.",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error listing pull requests for %s/%s under installation %d", owner, repo, target_installation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving pull requests.",
        ) from exc


@router.get("/repositories/{owner}/{repo}/pulls/{pull_number}")
def get_single_pull_request(
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
):
    """
    Retrieve details and mergeability status for a single pull request in an accessible repository.
    Verifies installation context, repository accessibility, and queries GitHub PR details.
    Returns safe PR metadata including mergeable boolean and mergeable_state.
    """
    target_installation_id = resolve_installation_id(
        request=request,
        installation_id_cookie=installation_id_cookie,
        installation_id_header=installation_id_header,
        installation_id_query=installation_id_query,
        endpoint_name=f"GET /repositories/{owner}/{repo}/pulls/{pull_number}",
    )

    try:
        data = get_pull_request_for_repo(
            installation_id=target_installation_id,
            owner=owner,
            repo=repo,
            pull_number=pull_number,
        )
        return data
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
        logger.error("GitHub API error for PR #%d in %s/%s under installation %d: %s (status=%d)", pull_number, owner, repo, target_installation_id, exc, exc.status_code)
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
    except Exception as exc:
        logger.exception("Unexpected error retrieving pull request #%d for %s/%s under installation %d", pull_number, owner, repo, target_installation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving pull request.",
        ) from exc

import logging
import re
from fastapi import APIRouter, Cookie, Header, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.git.github import (
    GitHubAPIError,
    GitHubAuthError,
    GitHubConfigError,
    list_repositories_for_installation,
    verify_installation,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/github", tags=["github"])


@router.get("/install")
def install_github_app():
    """
    Redirect the browser to the GitHub App installation URL.
    Format: https://github.com/apps/<GITHUB_APP_SLUG>/installations/new
    """
    installation_url = settings.github_installation_url
    if not installation_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GITHUB_APP_SLUG is not configured. Please define GITHUB_APP_SLUG in your .env file.",
        )

    return RedirectResponse(
        url=installation_url,
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )


@router.get("/setup")
def setup_github_installation(
    request: Request,
    installation_id: int | None = Query(
        default=None,
        description="GitHub App installation ID provided by GitHub after app installation.",
    ),
):
    """
    Handle the GitHub App installation callback.

    GitHub redirects to this route after an app installation:
    GET /api/github/setup?installation_id=<ID>

    Validates installation_id, authenticates with GitHub using the App JWT,
    verifies accessible repositories, and redirects the browser to /repositories.
    """
    # Normalize 127.0.0.1 to localhost consistently to prevent cross-origin cookie loss
    if request.url.hostname == "127.0.0.1":
        query_str = f"?{request.url.query}" if request.url.query else ""
        normalized_target = f"http://localhost:8000/api/github/setup{query_str}"
        return RedirectResponse(
            url=normalized_target,
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )

    if installation_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required query parameter: installation_id",
        )

    if installation_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="installation_id must be a positive integer",
        )

    try:
        # Authenticate installation and verify accessible repositories
        repo_names = verify_installation(installation_id)
        logger.info(
            "Installation %d setup complete with %d verified repositories.",
            installation_id,
            len(repo_names),
        )
    except GitHubConfigError as exc:
        logger.error("GitHub App configuration error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GitHub App configuration is missing or invalid.",
        ) from exc
    except GitHubAuthError as exc:
        logger.error("GitHub App authentication failed for installation %d: %s", installation_id, exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="GitHub App authentication failed.",
        ) from exc
    except GitHubAPIError as exc:
        logger.error("GitHub API error for installation %d: %s", installation_id, exc)
        if exc.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="GitHub App installation not found.",
            ) from exc
        raise HTTPException(
            status_code=exc.status_code if 400 <= exc.status_code < 600 else status.HTTP_502_BAD_GATEWAY,
            detail="GitHub API error during installation setup.",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error during installation setup for %d", installation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during installation setup.",
        ) from exc

    # Redirect to frontend repositories route and establish installation context via HttpOnly cookie
    frontend_base = settings.FRONTEND_URL.rstrip("/")
    redirect_url = f"{frontend_base}/repositories"

    response = RedirectResponse(
        url=redirect_url,
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )
    # Secure HTTP-only cookie preserving installation context without exposing tokens
    response.set_cookie(
        key="installation_id",
        value=str(installation_id),
        httponly=True,
        samesite="lax",
        secure=False,  # Allow local HTTP development
        max_age=86400 * 7,  # 7 days
        path="/",
    )
    return response


def extract_installation_id(
    request: Request,
    installation_id_cookie: str | None = None,
    installation_id_header: str | None = None,
    installation_id_query: int | None = None,
) -> int | None:
    """
    Extract and validate installation ID across the resolution hierarchy:
    1. FastAPI Cookie dependency
    2. request.cookies['installation_id']
    3. Raw Cookie header regex parse
    4. HTTP header: X-Installation-Id
    5. Query param: ?installation_id=<ID>

    Returns positive integer if found, or None if absent/invalid.
    """
    target_installation_id: int | None = None

    # 1. FastAPI Cookie dependency
    if installation_id_cookie:
        try:
            cleaned_val = str(installation_id_cookie).strip().strip('"').strip("'")
            val = int(cleaned_val)
            if val > 0:
                target_installation_id = val
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
            except ValueError:
                pass

    # 3. Raw Cookie header regex parse fallback (handles quotes, semicolons, or foreign malformed cookies)
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
                except ValueError:
                    pass

    # 4. HTTP header (x-installation-id)
    if target_installation_id is None and installation_id_header:
        try:
            val = int(str(installation_id_header).strip())
            if val > 0:
                target_installation_id = val
        except ValueError:
            pass

    # 5. Query parameter (?installation_id=...)
    if target_installation_id is None and installation_id_query:
        if installation_id_query > 0:
            target_installation_id = installation_id_query

    return target_installation_id


@router.get("/status")
def get_github_status(
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
    Check if the current browser session has a valid GitHub App installation context.

    Returns:
      {"connected": True, "repository_count": N} when valid context exists.
      {"connected": False} when no valid context exists or if installation is revoked.

    Never exposes tokens, JWTs, private keys, or client secrets.
    """
    target_installation_id = extract_installation_id(
        request=request,
        installation_id_cookie=installation_id_cookie,
        installation_id_header=installation_id_header,
        installation_id_query=installation_id_query,
    )

    if target_installation_id is None or target_installation_id <= 0:
        return {"connected": False}

    try:
        repos = list_repositories_for_installation(target_installation_id)
        return {
            "connected": True,
            "repository_count": len(repos),
        }
    except (GitHubConfigError, GitHubAuthError, GitHubAPIError) as exc:
        logger.warning(
            "GitHub status verification failed for installation %d: %s",
            target_installation_id,
            exc,
        )
        return {"connected": False}
    except Exception as exc:
        logger.exception(
            "Unexpected error verifying GitHub status for installation %d",
            target_installation_id,
        )
        return {"connected": False}


@router.get("/repositories")
def get_github_repositories(
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
    Retrieve repositories accessible to the currently authenticated GitHub App installation.

    Context Resolution Hierarchy:
    1. HTTP-only cookie: installation_id (via FastAPI Cookie dependency)
    2. Request cookies map: request.cookies['installation_id']
    3. Raw Cookie header regex parse (fallback against adjacent malformed cookies)
    4. HTTP header: X-Installation-Id (programmatic API clients)
    5. Query param: ?installation_id=<ID> (explicit override / direct testing)

    Never exposes or returns access tokens, JWTs, private keys, or client secrets.
    """
    target_installation_id = extract_installation_id(
        request=request,
        installation_id_cookie=installation_id_cookie,
        installation_id_header=installation_id_header,
        installation_id_query=installation_id_query,
    )

    cookie_present = bool(
        installation_id_cookie
        or request.cookies.get("installation_id")
        or ("installation_id=" in request.headers.get("cookie", ""))
    )
    header_present = bool(installation_id_header or request.headers.get("x-installation-id"))
    query_present = bool(installation_id_query)

    logger.info(
        "GET /api/github/repositories context: cookie_exists=%s, header_exists=%s, query_exists=%s, target_installation_id=%s",
        cookie_present,
        header_present,
        query_present,
        target_installation_id,
    )

    if target_installation_id is None or target_installation_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing installation context. Please connect your GitHub account via /api/github/install first.",
        )

    try:
        repos = list_repositories_for_installation(target_installation_id)
        return {"repositories": repos}
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
        logger.error("GitHub API error for installation %d: %s", target_installation_id, exc)
        if exc.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="GitHub App installation not found.",
            ) from exc
        raise HTTPException(
            status_code=exc.status_code if 400 <= exc.status_code < 600 else status.HTTP_502_BAD_GATEWAY,
            detail="GitHub API error while listing repositories.",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error listing repositories for installation %d", target_installation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving repositories.",
        ) from exc

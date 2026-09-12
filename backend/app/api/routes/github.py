import logging
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.git.github import (
    GitHubAPIError,
    GitHubAuthError,
    GitHubConfigError,
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

    # Redirect to frontend repositories placeholder route
    frontend_base = settings.FRONTEND_URL.rstrip("/")
    redirect_url = f"{frontend_base}/repositories"

    return RedirectResponse(
        url=redirect_url,
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )

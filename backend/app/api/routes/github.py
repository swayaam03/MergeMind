from fastapi import APIRouter, HTTPException, status
from fastapi.responses import RedirectResponse
from app.core.config import settings

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

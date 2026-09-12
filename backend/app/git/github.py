"""GitHub App authentication and integration helpers for MergeMind."""

import base64
import json
import logging
import time
from pathlib import Path
from typing import Any

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey

from app.core.config import ROOT_DIR, settings

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"
GITHUB_API_VERSION = "2022-11-28"


class GitHubConfigError(Exception):
    """Raised when GitHub App configuration or private key is missing/invalid."""


class GitHubAuthError(Exception):
    """Raised when GitHub App authentication or token creation fails."""

    def __init__(self, message: str, status_code: int = 401) -> None:
        super().__init__(message)
        self.status_code = status_code


class GitHubAPIError(Exception):
    """Raised when a GitHub API request returns an error."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


def get_private_key_path() -> Path:
    """Resolve the GitHub App private key path from configuration."""
    raw_path = settings.GITHUB_PRIVATE_KEY_PATH.strip()
    if not raw_path:
        raise GitHubConfigError("GITHUB_PRIVATE_KEY_PATH is not configured.")

    path = Path(raw_path)
    if not path.is_absolute():
        path = ROOT_DIR / path

    if not path.is_file():
        raise GitHubConfigError("GitHub App private key file not found.")

    return path


def load_private_key() -> RSAPrivateKey:
    """Load and deserialize the RSA private key from the configured PEM file."""
    key_path = get_private_key_path()
    try:
        key_bytes = key_path.read_bytes()
        private_key = serialization.load_pem_private_key(key_bytes, password=None)
        if not isinstance(private_key, RSAPrivateKey):
            raise GitHubConfigError("Private key is not a valid RSA key.")
        return private_key
    except Exception as exc:
        if isinstance(exc, GitHubConfigError):
            raise
        raise GitHubConfigError("Failed to load GitHub App private key.") from exc


def generate_jwt(expires_in_seconds: int = 600) -> str:
    """
    Generate a RS256-signed JWT for the GitHub App.

    Max expiration allowed by GitHub is 10 minutes (600 seconds).
    Issued 60 seconds in the past to prevent clock drift issues.
    """
    app_id = settings.GITHUB_APP_ID.strip()
    if not app_id:
        raise GitHubConfigError("GITHUB_APP_ID is not configured.")

    private_key = load_private_key()
    now = int(time.time())

    header = {"alg": "RS256", "typ": "JWT"}
    payload = {
        "iat": now - 60,
        "exp": now + expires_in_seconds,
        "iss": app_id,
    }

    header_b64 = (
        base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b"=").decode()
    )
    payload_b64 = (
        base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    )
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")

    signature = private_key.sign(
        signing_input,
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    signature_b64 = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()

    return f"{header_b64}.{payload_b64}.{signature_b64}"


def get_installation_access_token(
    installation_id: int,
    client: httpx.Client | None = None,
) -> str:
    """
    Exchange the GitHub App JWT for a scoped installation access token.

    POST /app/installations/{installation_id}/access_tokens
    The returned token must remain strictly backend-only.
    """
    jwt_token = generate_jwt()
    url = f"{GITHUB_API_BASE}/app/installations/{installation_id}/access_tokens"
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
    }

    owns_client = False
    if client is None:
        client = httpx.Client(timeout=10.0)
        owns_client = True

    try:
        response = client.post(url, headers=headers)
    except httpx.RequestError as exc:
        raise GitHubAPIError("Failed to reach GitHub API.", status_code=502) from exc
    finally:
        if owns_client:
            client.close()

    if response.status_code == 201:
        token_data = response.json()
        token = token_data.get("token")
        if not token:
            raise GitHubAuthError("Missing access token in GitHub response.")
        return str(token)

    if response.status_code == 404:
        raise GitHubAPIError("GitHub App installation not found.", status_code=404)
    if response.status_code in (401, 403):
        raise GitHubAuthError("GitHub App authentication failed.", status_code=response.status_code)

    raise GitHubAPIError(
        "Unexpected error from GitHub while obtaining installation token.",
        status_code=response.status_code,
    )


def get_installation_repositories(
    installation_token: str,
    client: httpx.Client | None = None,
) -> list[dict[str, Any]]:
    """
    Retrieve list of repositories accessible to the installation.

    GET /installation/repositories
    """
    url = f"{GITHUB_API_BASE}/installation/repositories"
    headers = {
        "Authorization": f"Bearer {installation_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
    }

    owns_client = False
    if client is None:
        client = httpx.Client(timeout=10.0)
        owns_client = True

    try:
        response = client.get(url, headers=headers)
    except httpx.RequestError as exc:
        raise GitHubAPIError("Failed to reach GitHub API.", status_code=502) from exc
    finally:
        if owns_client:
            client.close()

    if response.status_code == 200:
        data = response.json()
        return data.get("repositories", [])

    if response.status_code in (401, 403):
        raise GitHubAuthError("Invalid or expired installation access token.", status_code=response.status_code)

    raise GitHubAPIError(
        "Failed to retrieve installation repositories from GitHub.",
        status_code=response.status_code,
    )


def verify_installation(
    installation_id: int,
    client: httpx.Client | None = None,
) -> list[str]:
    """
    Authenticate an installation, retrieve accessible repositories, and log safely.

    Returns the list of repository full names (e.g. ["owner/repo"]).
    Never logs or exposes tokens, JWTs, or private keys.
    """
    installation_token = get_installation_access_token(installation_id, client=client)
    repositories = get_installation_repositories(installation_token, client=client)

    repo_names = [
        str(repo.get("full_name", ""))
        for repo in repositories
        if repo.get("full_name")
    ]

    # Safe logging: only installation_id and repository names
    logger.info(
        "GitHub installation verified successfully: installation_id=%d, total_repos=%d, repositories=%s",
        installation_id,
        len(repo_names),
        repo_names,
    )

    return repo_names


def list_repositories_for_installation(
    installation_id: int,
    client: httpx.Client | None = None,
) -> list[dict[str, Any]]:
    """
    Fetch and format safe repository metadata for a given GitHub App installation.

    Freshly generates a JWT and obtains a short-lived installation access token.
    Never exposes or persists the installation access token.
    """
    installation_token = get_installation_access_token(installation_id, client=client)
    raw_repos = get_installation_repositories(installation_token, client=client)

    safe_repos = []
    for repo in raw_repos:
        safe_repos.append({
            "id": repo.get("id"),
            "name": repo.get("name", ""),
            "full_name": repo.get("full_name", ""),
            "private": bool(repo.get("private", False)),
            "default_branch": repo.get("default_branch", "main"),
            "html_url": repo.get("html_url", ""),
            "description": repo.get("description") or "",
        })

    logger.info(
        "Retrieved %d repositories for installation_id=%d",
        len(safe_repos),
        installation_id,
    )
    return safe_repos

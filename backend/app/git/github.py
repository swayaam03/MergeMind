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
        raw_owner = repo.get("owner")
        owner_name = ""
        if isinstance(raw_owner, dict):
            owner_name = raw_owner.get("login", "")
        elif isinstance(raw_owner, str):
            owner_name = raw_owner
        if not owner_name and "/" in repo.get("full_name", ""):
            owner_name = repo.get("full_name", "").split("/")[0]

        safe_repos.append({
            "id": repo.get("id"),
            "name": repo.get("name", ""),
            "owner": owner_name,
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


def get_repository_pull_requests(
    owner: str,
    repo: str,
    installation_token: str,
    client: httpx.Client | None = None,
) -> list[dict[str, Any]]:
    """
    Retrieve open pull requests for a given repository using GitHub REST API.

    GET /repos/{owner}/{repo}/pulls?state=open
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls"
    params = {"state": "open"}
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
        response = client.get(url, params=params, headers=headers)
    except httpx.RequestError as exc:
        raise GitHubAPIError("Failed to reach GitHub API.", status_code=502) from exc
    finally:
        if owns_client:
            client.close()

    if response.status_code == 200:
        return response.json()

    if response.status_code == 404:
        raise GitHubAPIError(f"Repository {owner}/{repo} not found on GitHub.", status_code=404)
    if response.status_code in (401, 403):
        raise GitHubAuthError("GitHub App authentication failed or repository access denied.", status_code=response.status_code)

    raise GitHubAPIError(
        f"GitHub API error fetching pull requests for {owner}/{repo}.",
        status_code=response.status_code,
    )


def list_pull_requests_for_repo(
    installation_id: int,
    owner: str,
    repo: str,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """
    Validate repository accessibility, fetch open pull requests, and format safe metadata.

    Ensures the requested repository is part of the accessible repositories for the installation.
    Never exposes tokens, JWTs, or private keys.
    """
    installation_token = get_installation_access_token(installation_id, client=client)

    # 1. Validate repository accessibility
    accessible_repos = get_installation_repositories(installation_token, client=client)
    target_full_name = f"{owner}/{repo}".lower()

    is_accessible = any(
        str(r.get("full_name", "")).lower() == target_full_name
        for r in accessible_repos
    )

    if not is_accessible:
        raise GitHubAPIError(
            f"Repository '{owner}/{repo}' is not accessible to this installation.",
            status_code=403,
        )

    # 2. Fetch open pull requests
    raw_prs = get_repository_pull_requests(owner, repo, installation_token, client=client)

    safe_prs = []
    for pr in raw_prs:
        safe_prs.append({
            "number": pr.get("number"),
            "title": pr.get("title", ""),
            "state": pr.get("state", "open"),
            "html_url": pr.get("html_url", ""),
            "user": {
                "login": pr.get("user", {}).get("login", "") if isinstance(pr.get("user"), dict) else "",
            },
            "head": {
                "ref": pr.get("head", {}).get("ref", "") if isinstance(pr.get("head"), dict) else "",
            },
            "base": {
                "ref": pr.get("base", {}).get("ref", "") if isinstance(pr.get("base"), dict) else "",
            },
            "draft": bool(pr.get("draft", False)),
        })

    logger.info(
        "Retrieved %d open pull requests for %s/%s (installation_id=%d)",
        len(safe_prs),
        owner,
        repo,
        installation_id,
    )

    return {
        "repository": {
            "owner": owner,
            "name": repo,
            "full_name": f"{owner}/{repo}",
        },
        "pull_requests": safe_prs,
    }


def get_pull_request_detail(
    owner: str,
    repo: str,
    pull_number: int,
    installation_token: str,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """
    Retrieve details for a single pull request from GitHub REST API.

    GET /repos/{owner}/{repo}/pulls/{pull_number}
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls/{pull_number}"
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
        return response.json()

    if response.status_code == 404:
        raise GitHubAPIError(
            f"Pull request #{pull_number} not found in {owner}/{repo}.",
            status_code=404,
        )
    if response.status_code in (401, 403):
        raise GitHubAuthError(
            "GitHub App authentication failed or pull request access denied.",
            status_code=response.status_code,
        )

    raise GitHubAPIError(
        f"GitHub API error fetching pull request #{pull_number} for {owner}/{repo}.",
        status_code=response.status_code,
    )


def get_pull_request_for_repo(
    installation_id: int,
    owner: str,
    repo: str,
    pull_number: int,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """
    Validate repository accessibility, retrieve single PR details, and extract mergeability.

    Ensures the requested repository is part of the accessible repositories for the installation.
    Never exposes tokens, JWTs, or private keys.
    """
    installation_token = get_installation_access_token(installation_id, client=client)

    # 1. Validate repository accessibility
    accessible_repos = get_installation_repositories(installation_token, client=client)
    target_full_name = f"{owner}/{repo}".lower()

    is_accessible = any(
        str(r.get("full_name", "")).lower() == target_full_name
        for r in accessible_repos
    )

    if not is_accessible:
        raise GitHubAPIError(
            f"Repository '{owner}/{repo}' is not accessible to this installation.",
            status_code=403,
        )

    # 2. Fetch pull request detail
    raw_pr = get_pull_request_detail(
        owner=owner,
        repo=repo,
        pull_number=pull_number,
        installation_token=installation_token,
        client=client,
    )

    user_obj = raw_pr.get("user") or {}
    head_obj = raw_pr.get("head") or {}
    base_obj = raw_pr.get("base") or {}

    author = user_obj.get("login", "") if isinstance(user_obj, dict) else ""
    head_branch = head_obj.get("ref", "") if isinstance(head_obj, dict) else ""
    base_branch = base_obj.get("ref", "") if isinstance(base_obj, dict) else ""

    safe_pr = {
        "number": raw_pr.get("number", pull_number),
        "title": raw_pr.get("title", ""),
        "state": raw_pr.get("state", "open"),
        "draft": bool(raw_pr.get("draft", False)),
        "author": author,
        "head_branch": head_branch,
        "base_branch": base_branch,
        "html_url": raw_pr.get("html_url", ""),
        "mergeable": raw_pr.get("mergeable"),  # True, False, or None
        "mergeable_state": raw_pr.get("mergeable_state"),
    }

    logger.info(
        "Retrieved PR #%d for %s/%s (mergeable=%s, mergeable_state=%s)",
        pull_number,
        owner,
        repo,
        safe_pr["mergeable"],
        safe_pr["mergeable_state"],
    )

    return {
        "repository": {
            "owner": owner,
            "name": repo,
            "full_name": f"{owner}/{repo}",
        },
        "pull_request": safe_pr,
    }


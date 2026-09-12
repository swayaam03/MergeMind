from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.git.github import GitHubAuthError, GitHubAPIError, GitHubConfigError


@pytest.fixture
def client():
    return TestClient(app, follow_redirects=False)


def test_repositories_missing_installation_context(client):
    """GET /api/github/repositories without cookie, header, or query param returns 401."""
    response = client.get("/api/github/repositories")
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "Missing installation context" in data["detail"]


@patch("app.api.routes.github.list_repositories_for_installation")
def test_repositories_success_via_cookie(mock_list, client):
    """GET /api/github/repositories succeeds when installation_id cookie is present."""
    mock_list.return_value = [
        {
            "id": 101,
            "name": "project-alpha",
            "full_name": "org/project-alpha",
            "private": True,
            "default_branch": "main",
            "html_url": "https://github.com/org/project-alpha",
            "description": "Alpha repo",
        }
    ]

    client.cookies.set("installation_id", "456789")
    response = client.get("/api/github/repositories")

    assert response.status_code == 200
    data = response.json()
    assert "repositories" in data
    assert len(data["repositories"]) == 1
    repo = data["repositories"][0]
    assert repo["id"] == 101
    assert repo["name"] == "project-alpha"
    assert repo["full_name"] == "org/project-alpha"
    assert repo["private"] is True
    assert repo["default_branch"] == "main"
    assert repo["html_url"] == "https://github.com/org/project-alpha"
    mock_list.assert_called_once_with(456789)


@patch("app.api.routes.github.list_repositories_for_installation")
def test_repositories_success_via_header(mock_list, client):
    """GET /api/github/repositories succeeds when X-Installation-Id header is provided."""
    mock_list.return_value = [
        {
            "id": 102,
            "name": "project-beta",
            "full_name": "org/project-beta",
            "private": False,
            "default_branch": "develop",
            "html_url": "https://github.com/org/project-beta",
            "description": "",
        }
    ]

    response = client.get(
        "/api/github/repositories",
        headers={"X-Installation-Id": "987654"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["repositories"]) == 1
    assert data["repositories"][0]["name"] == "project-beta"
    mock_list.assert_called_once_with(987654)


@patch("app.api.routes.github.list_repositories_for_installation")
def test_repositories_empty_list(mock_list, client):
    """GET /api/github/repositories returns an empty array when no repositories are connected."""
    mock_list.return_value = []

    client.cookies.set("installation_id", "12345")
    response = client.get("/api/github/repositories")

    assert response.status_code == 200
    data = response.json()
    assert "repositories" in data
    assert data["repositories"] == []


@patch("app.api.routes.github.list_repositories_for_installation")
def test_repositories_github_auth_failure(mock_list, client):
    """GET /api/github/repositories returns 401 when GitHub authentication fails."""
    mock_list.side_effect = GitHubAuthError("GitHub App authentication failed.", status_code=401)

    client.cookies.set("installation_id", "12345")
    response = client.get("/api/github/repositories")

    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "GitHub App authentication failed."


@patch("app.api.routes.github.list_repositories_for_installation")
def test_repositories_github_api_failure(mock_list, client):
    """GET /api/github/repositories returns 502 on upstream GitHub API failure."""
    mock_list.side_effect = GitHubAPIError("GitHub API timeout", status_code=502)

    client.cookies.set("installation_id", "12345")
    response = client.get("/api/github/repositories")

    assert response.status_code == 502
    data = response.json()
    assert data["detail"] == "GitHub API error while listing repositories."


@patch("app.api.routes.github.list_repositories_for_installation")
def test_repositories_installation_not_found(mock_list, client):
    """GET /api/github/repositories returns 404 when the installation does not exist."""
    mock_list.side_effect = GitHubAPIError("Installation not found", status_code=404)

    client.cookies.set("installation_id", "999999999")
    response = client.get("/api/github/repositories")

    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "GitHub App installation not found."


@patch("app.api.routes.github.list_repositories_for_installation")
def test_repositories_no_tokens_or_secrets_returned(mock_list, client):
    """Ensure response payload never includes tokens, keys, or secrets."""
    mock_list.return_value = [
        {
            "id": 103,
            "name": "safe-repo",
            "full_name": "org/safe-repo",
            "private": False,
            "default_branch": "main",
            "html_url": "https://github.com/org/safe-repo",
            "description": "Safe repository",
        }
    ]

    client.cookies.set("installation_id", "12345")
    response = client.get("/api/github/repositories")

    assert response.status_code == 200
    all_content = f"{response.text} {str(response.headers)}".lower()

    # Verify no tokens or secrets are leaked
    assert "token" not in response.json()["repositories"][0]
    assert "ghs_" not in all_content
    assert "ghp_" not in all_content
    assert "bearer" not in all_content
    assert "private_key" not in all_content
    assert "client_secret" not in all_content


@patch("app.api.routes.github.verify_installation")
@patch("app.api.routes.github.list_repositories_for_installation")
def test_installation_context_established_from_setup_to_repositories(
    mock_list,
    mock_verify,
    client,
):
    """
    End-to-end integration flow:
    1. GET /api/github/setup?installation_id=884422 sets HttpOnly cookie and redirects.
    2. GET /api/github/repositories automatically uses that cookie to fetch repos dynamically.
    """
    mock_verify.return_value = ["dynamic-org/dynamic-repo"]
    mock_list.return_value = [
        {
            "id": 888,
            "name": "dynamic-repo",
            "full_name": "dynamic-org/dynamic-repo",
            "private": False,
            "default_branch": "main",
            "html_url": "https://github.com/dynamic-org/dynamic-repo",
            "description": "Dynamic repo",
        }
    ]

    # Step 1: Hit setup callback
    setup_res = client.get("/api/github/setup?installation_id=884422")
    assert setup_res.status_code == 307
    assert "set-cookie" in setup_res.headers
    assert "installation_id=884422" in setup_res.headers["set-cookie"]

    # Step 2: Hit repositories endpoint using the established cookie
    repos_res = client.get("/api/github/repositories")
    assert repos_res.status_code == 200
    data = repos_res.json()
    assert len(data["repositories"]) == 1
    assert data["repositories"][0]["full_name"] == "dynamic-org/dynamic-repo"
    # Verifies dynamic ID was used
    mock_list.assert_called_once_with(884422)


def test_list_repositories_for_installation_helper():
    """Unit test list_repositories_for_installation helper with mocked httpx client."""
    from app.git.github import list_repositories_for_installation

    mock_client = MagicMock()
    # Mock access token response (201)
    mock_token_res = MagicMock()
    mock_token_res.status_code = 201
    mock_token_res.json.return_value = {"token": "ghs_test_token_123"}

    # Mock repositories response (200)
    mock_repos_res = MagicMock()
    mock_repos_res.status_code = 200
    mock_repos_res.json.return_value = {
        "repositories": [
            {
                "id": 501,
                "name": "app-repo",
                "full_name": "owner/app-repo",
                "private": True,
                "default_branch": "main",
                "html_url": "https://github.com/owner/app-repo",
                "description": "An awesome app",
                "extra_internal_field": "do_not_leak",
            }
        ]
    }

    mock_client.post.return_value = mock_token_res
    mock_client.get.return_value = mock_repos_res

    repos = list_repositories_for_installation(55555, client=mock_client)
    assert len(repos) == 1
    r = repos[0]
    assert r["id"] == 501
    assert r["name"] == "app-repo"
    assert r["full_name"] == "owner/app-repo"
    assert r["private"] is True
    assert r["default_branch"] == "main"
    assert r["html_url"] == "https://github.com/owner/app-repo"
    assert "extra_internal_field" not in r


@patch("app.api.routes.github.list_repositories_for_installation")
def test_repositories_quoted_cookie_parsed_correctly(mock_list, client):
    """GET /api/github/repositories handles quoted installation_id cookie e.g. installation_id=\"12345\"."""
    mock_list.return_value = [{"id": 1, "name": "quoted-repo", "full_name": "org/quoted-repo", "private": False, "default_branch": "main", "html_url": "https://github.com/org/quoted-repo", "description": ""}]

    response = client.get(
        "/api/github/repositories",
        headers={"Cookie": 'other_cookie=xyz; installation_id="998877"; tracking=true'},
    )
    assert response.status_code == 200
    mock_list.assert_called_once_with(998877)


@patch("app.api.routes.github.list_repositories_for_installation")
def test_repositories_raw_cookie_header_regex_fallback(mock_list, client):
    """GET /api/github/repositories extracts installation_id even with unparsed raw Cookie header string."""
    mock_list.return_value = [{"id": 2, "name": "fallback-repo", "full_name": "org/fallback-repo", "private": False, "default_branch": "main", "html_url": "https://github.com/org/fallback-repo", "description": ""}]

    response = client.get(
        "/api/github/repositories",
        headers={"Cookie": 'malformed=cookie[with]bracket; installation_id=554433'},
    )
    assert response.status_code == 200
    mock_list.assert_called_once_with(554433)

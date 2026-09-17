from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.git.github import GitHubAuthError, GitHubAPIError, GitHubConfigError


@pytest.fixture
def client():
    return TestClient(app, follow_redirects=False)


def test_status_disconnected_no_context(client):
    """GET /api/github/status returns connected: false when no cookie, header, or query is present."""
    response = client.get("/api/github/status")
    assert response.status_code == 200
    data = response.json()
    assert data == {"connected": False}
    # Verify no sensitive tokens or keys leaked
    assert "token" not in data
    assert "access_token" not in data
    assert "jwt" not in data


@patch("app.api.routes.github.list_repositories_for_installation")
def test_status_connected_via_cookie(mock_list, client):
    """GET /api/github/status returns connected: true with repository_count when valid cookie is present."""
    mock_list.return_value = [
        {"id": 1, "name": "repo1", "owner": "testorg"},
        {"id": 2, "name": "repo2", "owner": "testorg"},
    ]

    client.cookies.set("installation_id", "54321")
    response = client.get("/api/github/status")

    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is True
    assert data["repository_count"] == 2
    # Verify security: no tokens
    assert "token" not in data
    assert "installation_id" not in data
    mock_list.assert_called_once_with(54321)


@patch("app.api.routes.github.list_repositories_for_installation")
def test_status_connected_via_header(mock_list, client):
    """GET /api/github/status returns connected: true when valid X-Installation-Id header is passed."""
    mock_list.return_value = [{"id": 1, "name": "repo1", "owner": "testorg"}]

    response = client.get(
        "/api/github/status",
        headers={"X-Installation-Id": "999888"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is True
    assert data["repository_count"] == 1
    mock_list.assert_called_once_with(999888)


@patch("app.api.routes.github.list_repositories_for_installation")
def test_status_revoked_installation_auth_error(mock_list, client):
    """GET /api/github/status returns connected: false when GitHub rejects authentication."""
    mock_list.side_effect = GitHubAuthError("Installation revoked or expired.", status_code=401)

    client.cookies.set("installation_id", "54321")
    response = client.get("/api/github/status")

    assert response.status_code == 200
    data = response.json()
    assert data == {"connected": False}


@patch("app.api.routes.github.list_repositories_for_installation")
def test_status_not_found_on_github(mock_list, client):
    """GET /api/github/status returns connected: false when installation is not found (uninstalled)."""
    mock_list.side_effect = GitHubAPIError("GitHub App installation not found.", status_code=404)

    client.cookies.set("installation_id", "54321")
    response = client.get("/api/github/status")

    assert response.status_code == 200
    data = response.json()
    assert data == {"connected": False}

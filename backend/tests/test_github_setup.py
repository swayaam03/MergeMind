from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.git.github import GitHubConfigError, GitHubAuthError, GitHubAPIError


@pytest.fixture
def client():
    return TestClient(app, follow_redirects=False)


def test_setup_missing_installation_id(client):
    """GET /api/github/setup without installation_id returns 400 Bad Request."""
    response = client.get("/api/github/setup")
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "installation_id" in data["detail"]


def test_setup_invalid_installation_id_zero(client):
    """GET /api/github/setup with installation_id=0 returns 400 Bad Request."""
    response = client.get("/api/github/setup?installation_id=0")
    assert response.status_code == 400
    data = response.json()
    assert "positive integer" in data["detail"]


def test_setup_invalid_installation_id_negative(client):
    """GET /api/github/setup with negative installation_id returns 400 Bad Request."""
    response = client.get("/api/github/setup?installation_id=-100")
    assert response.status_code == 400
    data = response.json()
    assert "positive integer" in data["detail"]


def test_setup_invalid_installation_id_non_integer(client):
    """GET /api/github/setup with non-integer installation_id returns 422 Unprocessable Entity."""
    response = client.get("/api/github/setup?installation_id=abc")
    assert response.status_code == 422


@patch("app.api.routes.github.verify_installation")
def test_setup_success_redirect(mock_verify, client):
    """GET /api/github/setup with valid installation_id authenticates, verifies, and redirects to /repositories."""
    mock_verify.return_value = ["test-owner/test-repo"]
    settings.FRONTEND_URL = "http://localhost:5173"

    response = client.get("/api/github/setup?installation_id=12345678")

    assert response.status_code == 307
    assert response.headers["location"] == "http://localhost:5173/repositories"
    mock_verify.assert_called_once_with(12345678)


@patch("app.api.routes.github.verify_installation")
def test_setup_config_error(mock_verify, client):
    """GET /api/github/setup handles GitHubConfigError safely with 500 without leaking secrets."""
    mock_verify.side_effect = GitHubConfigError("Private key file not found.")

    response = client.get("/api/github/setup?installation_id=12345")

    assert response.status_code == 500
    data = response.json()
    assert data["detail"] == "GitHub App configuration is missing or invalid."
    # Ensure no file paths or sensitive keys leaked
    assert "secrets" not in str(data).lower()
    assert ".pem" not in str(data).lower()


@patch("app.api.routes.github.verify_installation")
def test_setup_auth_error(mock_verify, client):
    """GET /api/github/setup handles GitHubAuthError safely with 401."""
    mock_verify.side_effect = GitHubAuthError("GitHub App authentication failed.")

    response = client.get("/api/github/setup?installation_id=12345")

    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "GitHub App authentication failed."


@patch("app.api.routes.github.verify_installation")
def test_setup_api_not_found(mock_verify, client):
    """GET /api/github/setup handles installation not found with 404."""
    mock_verify.side_effect = GitHubAPIError("Installation not found", status_code=404)

    response = client.get("/api/github/setup?installation_id=999999999")

    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "GitHub App installation not found."


@patch("app.api.routes.github.verify_installation")
def test_no_credentials_leaked_in_response(mock_verify, client):
    """Ensure no tokens, JWTs, or client secrets ever leak in the response body or headers."""
    mock_verify.return_value = ["test-owner/test-repo"]

    response = client.get("/api/github/setup?installation_id=12345")

    all_response_text = f"{response.text} {str(response.headers)}"
    assert "token" not in response.headers
    assert "bearer" not in all_response_text.lower()
    assert "ghs_" not in all_response_text
    assert "ghp_" not in all_response_text


def test_generate_jwt_success():
    """Verify that generate_jwt produces a valid 3-part RS256 JWT."""
    from app.git.github import generate_jwt
    jwt_token = generate_jwt()
    parts = jwt_token.split(".")
    assert len(parts) == 3
    assert len(parts[0]) > 0
    assert len(parts[1]) > 0
    assert len(parts[2]) > 0


def test_get_installation_access_token_mock():
    """Verify get_installation_access_token handles 201 response properly with mocked client."""
    from app.git.github import get_installation_access_token

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"token": "ghs_mocked_token_12345"}
    mock_client.post.return_value = mock_response

    token = get_installation_access_token(12345, client=mock_client)
    assert token == "ghs_mocked_token_12345"


def test_get_installation_repositories_mock():
    """Verify get_installation_repositories handles 200 response properly with mocked client."""
    from app.git.github import get_installation_repositories

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "repositories": [{"full_name": "test-owner/test-repo"}]
    }
    mock_client.get.return_value = mock_response

    repos = get_installation_repositories("ghs_mocked_token_12345", client=mock_client)
    assert len(repos) == 1
    assert repos[0]["full_name"] == "test-owner/test-repo"

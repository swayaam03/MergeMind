"""Unit tests for User Accounts, Authentication, and GitHub Account Linking."""

from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.db import database as db
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    """Ensure clean database before each test."""
    db.init_db()
    with db.get_db_connection() as conn:
        conn.execute("DELETE FROM sessions;")
        conn.execute("DELETE FROM users;")
        conn.commit()


def test_user_registration_and_login(client):
    """Test user registration, duplicate prevention, and login."""
    # Register
    reg_resp = client.post(
        "/api/auth/register",
        json={"username": "alice", "email": "alice@example.com", "password": "password123"},
    )
    assert reg_resp.status_code == 200
    data = reg_resp.json()
    assert data["user"]["username"] == "alice"
    assert data["user"]["email"] == "alice@example.com"
    assert "token" in data

    # Duplicate registration should fail
    dup_resp = client.post(
        "/api/auth/register",
        json={"username": "alice", "email": "alice2@example.com", "password": "password123"},
    )
    assert dup_resp.status_code == 400

    # Login with valid credentials
    login_resp = client.post(
        "/api/auth/login",
        json={"username_or_email": "alice", "password": "password123"},
    )
    assert login_resp.status_code == 200
    assert "token" in login_resp.json()

    # Login with invalid password
    bad_login = client.post(
        "/api/auth/login",
        json={"username_or_email": "alice", "password": "wrongpassword"},
    )
    assert bad_login.status_code == 401


def test_get_current_user_profile(client):
    """Test /api/auth/me for authenticated and unauthenticated requests."""
    # Unauthenticated
    unauth_resp = client.get("/api/auth/me")
    assert unauth_resp.status_code == 401

    # Register and get session
    reg_resp = client.post(
        "/api/auth/register",
        json={"username": "bob", "email": "bob@example.com", "password": "password123"},
    )
    token = reg_resp.json()["token"]

    # Authenticated via Bearer header
    me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == "bob"
    assert me_resp.json()["is_github_connected"] is False


def test_connect_and_disconnect_github(client):
    """Test linking a GitHub App installation ID to a user account."""
    reg_resp = client.post(
        "/api/auth/register",
        json={"username": "charlie", "email": "charlie@example.com", "password": "password123"},
    )
    token = reg_resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    with patch("app.api.routes.auth.verify_installation", return_value=["repo-a"]):
        with patch("httpx.get") as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                json=lambda: {"account": {"login": "swayaam03"}},
            )

            connect_resp = client.post(
                "/api/auth/connect-github",
                json={"installation_id": 167531148},
                headers=headers,
            )
            assert connect_resp.status_code == 200
            user_data = connect_resp.json()
            assert user_data["is_github_connected"] is True
            assert user_data["github_installation_id"] == 167531148

    # Disconnect
    disc_resp = client.post("/api/auth/disconnect-github", headers=headers)
    assert disc_resp.status_code == 200
    assert disc_resp.json()["is_github_connected"] is False
    assert disc_resp.json()["github_installation_id"] is None

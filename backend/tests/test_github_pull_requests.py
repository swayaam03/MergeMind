from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.git.github import GitHubAuthError, GitHubAPIError, GitHubConfigError


@pytest.fixture
def client():
    return TestClient(app, follow_redirects=False)


def test_pull_requests_missing_installation_context(client):
    """GET /api/github/repositories/{owner}/{repo}/pulls without installation context returns 401."""
    response = client.get("/api/github/repositories/test-owner/test-repo/pulls")
    assert response.status_code == 401
    data = response.json()
    assert "Missing installation context" in data["detail"]


@patch("app.api.routes.pull_requests.list_pull_requests_for_repo")
def test_pull_requests_success(mock_list_prs, client):
    """GET /api/github/repositories/{owner}/{repo}/pulls succeeds with valid installation context."""
    mock_list_prs.return_value = {
        "repository": {
            "owner": "test-owner",
            "name": "test-repo",
            "full_name": "test-owner/test-repo",
        },
        "pull_requests": [
            {
                "number": 12,
                "title": "Add authentication",
                "state": "open",
                "html_url": "https://github.com/test-owner/test-repo/pull/12",
                "user": {"login": "testdev"},
                "head": {"ref": "feature/auth"},
                "base": {"ref": "main"},
                "draft": False,
            }
        ],
    }

    client.cookies.set("installation_id", "123456")
    response = client.get("/api/github/repositories/test-owner/test-repo/pulls")

    assert response.status_code == 200
    data = response.json()
    assert data["repository"]["full_name"] == "test-owner/test-repo"
    assert len(data["pull_requests"]) == 1
    pr = data["pull_requests"][0]
    assert pr["number"] == 12
    assert pr["title"] == "Add authentication"
    assert pr["state"] == "open"
    assert pr["user"]["login"] == "testdev"
    assert pr["head"]["ref"] == "feature/auth"
    assert pr["base"]["ref"] == "main"
    assert pr["draft"] is False
    mock_list_prs.assert_called_once_with(123456, "test-owner", "test-repo")


@patch("app.api.routes.pull_requests.list_pull_requests_for_repo")
def test_pull_requests_empty_list(mock_list_prs, client):
    """GET /api/github/repositories/{owner}/{repo}/pulls returns an empty list when no open PRs exist."""
    mock_list_prs.return_value = {
        "repository": {
            "owner": "test-owner",
            "name": "test-repo",
            "full_name": "test-owner/test-repo",
        },
        "pull_requests": [],
    }

    client.cookies.set("installation_id", "123456")
    response = client.get("/api/github/repositories/test-owner/test-repo/pulls")

    assert response.status_code == 200
    data = response.json()
    assert data["pull_requests"] == []


@patch("app.api.routes.pull_requests.list_pull_requests_for_repo")
def test_pull_requests_github_auth_failure(mock_list_prs, client):
    """GET /api/github/repositories/{owner}/{repo}/pulls returns 401 when GitHub authentication fails."""
    mock_list_prs.side_effect = GitHubAuthError("GitHub App authentication failed.", status_code=401)

    client.cookies.set("installation_id", "123456")
    response = client.get("/api/github/repositories/test-owner/test-repo/pulls")

    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "GitHub App authentication failed."


@patch("app.api.routes.pull_requests.list_pull_requests_for_repo")
def test_pull_requests_repo_not_found(mock_list_prs, client):
    """GET /api/github/repositories/{owner}/{repo}/pulls returns 404 when repository does not exist on GitHub."""
    mock_list_prs.side_effect = GitHubAPIError("Repository not found on GitHub.", status_code=404)

    client.cookies.set("installation_id", "123456")
    response = client.get("/api/github/repositories/test-owner/nonexistent-repo/pulls")

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


@patch("app.api.routes.pull_requests.list_pull_requests_for_repo")
def test_pull_requests_repo_inaccessible(mock_list_prs, client):
    """GET /api/github/repositories/{owner}/{repo}/pulls returns 403 when repository is not accessible to installation."""
    mock_list_prs.side_effect = GitHubAPIError("Repository is not accessible to this installation.", status_code=403)

    client.cookies.set("installation_id", "123456")
    response = client.get("/api/github/repositories/other-owner/private-repo/pulls")

    assert response.status_code == 403
    data = response.json()
    assert "not accessible" in data["detail"].lower()


@patch("app.api.routes.pull_requests.list_pull_requests_for_repo")
def test_pull_requests_api_failure(mock_list_prs, client):
    """GET /api/github/repositories/{owner}/{repo}/pulls returns 502 on upstream GitHub API failure."""
    mock_list_prs.side_effect = GitHubAPIError("GitHub API failure", status_code=502)

    client.cookies.set("installation_id", "123456")
    response = client.get("/api/github/repositories/test-owner/test-repo/pulls")

    assert response.status_code == 502
    data = response.json()
    assert "GitHub API error" in data["detail"]


@patch("app.api.routes.pull_requests.list_pull_requests_for_repo")
def test_pull_requests_safe_response_no_secrets(mock_list_prs, client):
    """Ensure PR response never contains tokens, JWTs, private keys, or client secrets."""
    mock_list_prs.return_value = {
        "repository": {"owner": "test-owner", "name": "test-repo", "full_name": "test-owner/test-repo"},
        "pull_requests": [
            {
                "number": 1,
                "title": "Refactor auth",
                "state": "open",
                "html_url": "https://github.com/test-owner/test-repo/pull/1",
                "user": {"login": "dev1"},
                "head": {"ref": "patch-1"},
                "base": {"ref": "main"},
                "draft": False,
            }
        ],
    }

    client.cookies.set("installation_id", "123456")
    response = client.get("/api/github/repositories/test-owner/test-repo/pulls")

    assert response.status_code == 200
    all_content = f"{response.text} {str(response.headers)}".lower()
    assert "ghs_" not in all_content
    assert "ghp_" not in all_content
    assert "token" not in response.json()["pull_requests"][0]
    assert "bearer" not in all_content
    assert "private_key" not in all_content
    assert "client_secret" not in all_content


@patch("app.git.github.get_installation_access_token")
@patch("app.git.github.get_installation_repositories")
@patch("app.git.github.get_repository_pull_requests")
def test_list_pull_requests_for_repo_helper_accessibility_validation(
    mock_get_prs,
    mock_get_repos,
    mock_get_token,
):
    """Verify list_pull_requests_for_repo enforces repository accessibility check before fetching PRs."""
    from app.git.github import list_pull_requests_for_repo

    mock_get_token.return_value = "ghs_mocked_token"
    # Installation only has access to test-owner/repo-a
    mock_get_repos.return_value = [
        {"full_name": "test-owner/repo-a"}
    ]

    # Querying repo-a succeeds
    mock_get_prs.return_value = [
        {
            "number": 5,
            "title": "PR 5",
            "state": "open",
            "html_url": "https://github.com/test-owner/repo-a/pull/5",
            "user": {"login": "alice"},
            "head": {"ref": "feat-a"},
            "base": {"ref": "main"},
            "draft": False,
        }
    ]

    result = list_pull_requests_for_repo(12345, "test-owner", "repo-a")
    assert result["repository"]["full_name"] == "test-owner/repo-a"
    assert len(result["pull_requests"]) == 1

    # Querying an inaccessible repo raises GitHubAPIError with status_code=403
    with pytest.raises(GitHubAPIError) as exc_info:
        list_pull_requests_for_repo(12345, "test-owner", "unauthorized-repo")
    assert exc_info.value.status_code == 403
    assert "not accessible" in str(exc_info.value)


def test_get_repository_pull_requests_requests_only_open_state():
    """Verify get_repository_pull_requests explicitly queries state=open."""
    from app.git.github import get_repository_pull_requests

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = []
    mock_client.get.return_value = mock_response

    get_repository_pull_requests("my-org", "my-repo", "ghs_token_123", client=mock_client)

    mock_client.get.assert_called_once()
    call_args, call_kwargs = mock_client.get.call_args
    assert call_args[0] == "https://api.github.com/repos/my-org/my-repo/pulls"
    assert call_kwargs.get("params") == {"state": "open"}


# ---------------------------------------------------------------------------
# Task 5: Single PR Mergeability & Conflict Detection Tests
# ---------------------------------------------------------------------------

def test_single_pr_missing_installation_context(client):
    """GET /api/github/repositories/{owner}/{repo}/pulls/{pull_number} without context returns 401."""
    response = client.get("/api/github/repositories/test-owner/test-repo/pulls/1")
    assert response.status_code == 401
    data = response.json()
    assert "Missing installation context" in data["detail"]


@patch("app.api.routes.pull_requests.get_pull_request_for_repo")
def test_single_pr_mergeable_true(mock_get_pr, client):
    """GET /api/github/repositories/{owner}/{repo}/pulls/1 returns mergeable=True."""
    mock_get_pr.return_value = {
        "repository": {
            "owner": "test-owner",
            "name": "test-repo",
            "full_name": "test-owner/test-repo",
        },
        "pull_request": {
            "number": 1,
            "title": "Clean PR",
            "state": "open",
            "draft": False,
            "author": "swayaam03",
            "head_branch": "feature/clean",
            "base_branch": "main",
            "html_url": "https://github.com/test-owner/test-repo/pull/1",
            "mergeable": True,
            "mergeable_state": "clean",
        },
    }

    client.cookies.set("installation_id", "123456")
    response = client.get("/api/github/repositories/test-owner/test-repo/pulls/1")

    assert response.status_code == 200
    data = response.json()
    assert data["repository"]["full_name"] == "test-owner/test-repo"
    assert data["pull_request"]["number"] == 1
    assert data["pull_request"]["mergeable"] is True
    assert data["pull_request"]["mergeable_state"] == "clean"
    mock_get_pr.assert_called_once_with(
        installation_id=123456,
        owner="test-owner",
        repo="test-repo",
        pull_number=1,
    )


@patch("app.api.routes.pull_requests.get_pull_request_for_repo")
def test_single_pr_mergeable_false(mock_get_pr, client):
    """GET /api/github/repositories/{owner}/{repo}/pulls/12 returns mergeable=False (conflict)."""
    mock_get_pr.return_value = {
        "repository": {
            "owner": "test-owner",
            "name": "test-repo",
            "full_name": "test-owner/test-repo",
        },
        "pull_request": {
            "number": 12,
            "title": "Conflicting PR",
            "state": "open",
            "draft": False,
            "author": "swayaam03",
            "head_branch": "feature/conflict",
            "base_branch": "main",
            "html_url": "https://github.com/test-owner/test-repo/pull/12",
            "mergeable": False,
            "mergeable_state": "dirty",
        },
    }

    client.cookies.set("installation_id", "123456")
    response = client.get("/api/github/repositories/test-owner/test-repo/pulls/12")

    assert response.status_code == 200
    data = response.json()
    assert data["pull_request"]["number"] == 12
    assert data["pull_request"]["mergeable"] is False
    assert data["pull_request"]["mergeable_state"] == "dirty"


@patch("app.api.routes.pull_requests.get_pull_request_for_repo")
def test_single_pr_mergeable_null(mock_get_pr, client):
    """GET /api/github/repositories/{owner}/{repo}/pulls/99 returns mergeable=None (checking)."""
    mock_get_pr.return_value = {
        "repository": {
            "owner": "test-owner",
            "name": "test-repo",
            "full_name": "test-owner/test-repo",
        },
        "pull_request": {
            "number": 99,
            "title": "Computing mergeability",
            "state": "open",
            "draft": False,
            "author": "swayaam03",
            "head_branch": "feature/pending",
            "base_branch": "main",
            "html_url": "https://github.com/test-owner/test-repo/pull/99",
            "mergeable": None,
            "mergeable_state": "unknown",
        },
    }

    client.cookies.set("installation_id", "123456")
    response = client.get("/api/github/repositories/test-owner/test-repo/pulls/99")

    assert response.status_code == 200
    data = response.json()
    assert data["pull_request"]["mergeable"] is None
    assert data["pull_request"]["mergeable_state"] == "unknown"


@patch("app.api.routes.pull_requests.get_pull_request_for_repo")
def test_single_pr_repo_inaccessible(mock_get_pr, client):
    """GET /api/github/repositories/{owner}/{repo}/pulls/{pull_number} returns 403 when repo is inaccessible."""
    mock_get_pr.side_effect = GitHubAPIError("Repository 'other/private' is not accessible to this installation.", status_code=403)

    client.cookies.set("installation_id", "123456")
    response = client.get("/api/github/repositories/other/private/pulls/1")

    assert response.status_code == 403
    assert "not accessible" in response.json()["detail"].lower()


@patch("app.api.routes.pull_requests.get_pull_request_for_repo")
def test_single_pr_not_found(mock_get_pr, client):
    """GET /api/github/repositories/{owner}/{repo}/pulls/{pull_number} returns 404 when PR not found."""
    mock_get_pr.side_effect = GitHubAPIError("Pull request #999 not found in test-owner/test-repo.", status_code=404)

    client.cookies.set("installation_id", "123456")
    response = client.get("/api/github/repositories/test-owner/test-repo/pulls/999")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@patch("app.api.routes.pull_requests.get_pull_request_for_repo")
def test_single_pr_github_auth_failure(mock_get_pr, client):
    """GET /api/github/repositories/{owner}/{repo}/pulls/{pull_number} returns 401 on GitHub auth failure."""
    mock_get_pr.side_effect = GitHubAuthError("GitHub App authentication failed.", status_code=401)

    client.cookies.set("installation_id", "123456")
    response = client.get("/api/github/repositories/test-owner/test-repo/pulls/1")

    assert response.status_code == 401
    assert "authentication failed" in response.json()["detail"].lower()


@patch("app.api.routes.pull_requests.get_pull_request_for_repo")
def test_single_pr_github_api_failure(mock_get_pr, client):
    """GET /api/github/repositories/{owner}/{repo}/pulls/{pull_number} returns 502 on GitHub API failure."""
    mock_get_pr.side_effect = GitHubAPIError("GitHub API error", status_code=502)

    client.cookies.set("installation_id", "123456")
    response = client.get("/api/github/repositories/test-owner/test-repo/pulls/1")

    assert response.status_code == 502
    assert "github api error" in response.json()["detail"].lower()


@patch("app.api.routes.pull_requests.get_pull_request_for_repo")
def test_single_pr_safe_response_no_secrets(mock_get_pr, client):
    """Verify single PR endpoint never leaks tokens, keys, or secrets."""
    mock_get_pr.return_value = {
        "repository": {"owner": "test-owner", "name": "test-repo", "full_name": "test-owner/test-repo"},
        "pull_request": {
            "number": 1,
            "title": "Secret Test",
            "state": "open",
            "draft": False,
            "author": "swayaam03",
            "head_branch": "test",
            "base_branch": "main",
            "html_url": "https://github.com/test-owner/test-repo/pull/1",
            "mergeable": True,
            "mergeable_state": "clean",
        },
    }

    client.cookies.set("installation_id", "123456")
    response = client.get("/api/github/repositories/test-owner/test-repo/pulls/1")

    assert response.status_code == 200
    all_content = f"{response.text} {str(response.headers)}".lower()
    assert "ghs_" not in all_content
    assert "ghp_" not in all_content
    assert "token" not in response.json()["pull_request"]
    assert "private_key" not in all_content
    assert "client_secret" not in all_content


@patch("app.git.github.get_installation_access_token")
@patch("app.git.github.get_installation_repositories")
@patch("app.git.github.get_pull_request_detail")
def test_get_pull_request_for_repo_helper_logic(
    mock_get_pr_detail,
    mock_get_repos,
    mock_get_token,
):
    """Test get_pull_request_for_repo accessibility check and data mapping."""
    from app.git.github import get_pull_request_for_repo

    mock_get_token.return_value = "ghs_test_token"
    mock_get_repos.return_value = [{"full_name": "my-org/my-repo"}]
    mock_get_pr_detail.return_value = {
        "number": 42,
        "title": "Fix memory leak",
        "state": "open",
        "draft": False,
        "user": {"login": "octocat"},
        "head": {"ref": "fix-leak"},
        "base": {"ref": "main"},
        "html_url": "https://github.com/my-org/my-repo/pull/42",
        "mergeable": False,
        "mergeable_state": "dirty",
    }

    result = get_pull_request_for_repo(12345, "my-org", "my-repo", 42)
    assert result["repository"]["full_name"] == "my-org/my-repo"
    assert result["pull_request"]["number"] == 42
    assert result["pull_request"]["author"] == "octocat"
    assert result["pull_request"]["head_branch"] == "fix-leak"
    assert result["pull_request"]["base_branch"] == "main"
    assert result["pull_request"]["mergeable"] is False
    assert result["pull_request"]["mergeable_state"] == "dirty"

    # Inaccessible repo
    with pytest.raises(GitHubAPIError) as exc:
        get_pull_request_for_repo(12345, "other-org", "forbidden-repo", 42)
    assert exc.value.status_code == 403


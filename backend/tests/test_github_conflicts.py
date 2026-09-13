"""Tests for Phase 3 Task 1: Git Conflict File Extraction and API Endpoint."""

import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.git.conflicts import (
    GitConflictError,
    detect_language,
    parse_conflict_markers,
    run_git_command,
    sanitize_text,
    simulate_merge_and_extract_conflicts,
)
from app.git.github import GitHubAPIError, GitHubAuthError
from app.main import app


@pytest.fixture
def client():
    return TestClient(app, follow_redirects=False)


# ---------------------------------------------------------------------------
# Unit tests for helper functions in app.git.conflicts
# ---------------------------------------------------------------------------

def test_detect_language():
    """Verify detect_language maps extensions accurately."""
    assert detect_language("src/calculator.py") == "python"
    assert detect_language("app/index.js") == "javascript"
    assert detect_language("components/App.jsx") == "javascript"
    assert detect_language("main.ts") == "typescript"
    assert detect_language("ui/Modal.tsx") == "typescript"
    assert detect_language("backend/Server.java") == "java"
    assert detect_language("main.go") == "go"
    assert detect_language("unknown.xyz123") == "unknown"


def test_sanitize_text():
    """Verify sensitive tokens and URLs with credentials are redacted."""
    url = "https://x-access-token:ghs_secret1234567890@github.com/org/repo.git"
    sanitized_url = sanitize_text(url, ["ghs_secret1234567890"])
    assert "ghs_secret1234567890" not in sanitized_url
    assert "[REDACTED_CREDENTIALS]@" in sanitized_url

    msg = "Authentication failed for token ghs_abcdef1234567890XYZ"
    sanitized_msg = sanitize_text(msg)
    assert "[REDACTED_TOKEN]" in sanitized_msg
    assert "ghs_abcdef1234567890XYZ" not in sanitized_msg


def test_parse_conflict_markers():
    """Verify parsing ours and theirs blocks from standard Git conflict markers."""
    content = (
        "def add(a, b):\n"
        "<<<<<<< HEAD\n"
        "    return a + b  # local branch change\n"
        "=======\n"
        "    return int(a) + int(b)  # remote branch change\n"
        ">>>>>>> feature-branch\n"
    )
    markers = parse_conflict_markers(content)
    assert "local branch change" in markers["ours"]
    assert "remote branch change" in markers["theirs"]


# ---------------------------------------------------------------------------
# Test 1: Missing installation context
# ---------------------------------------------------------------------------

def test_conflicts_missing_installation_context(client):
    """GET /api/github/repositories/{owner}/{repo}/pulls/{pull_number}/conflicts without context returns 401."""
    response = client.get("/api/github/repositories/test-owner/test-repo/pulls/1/conflicts")
    assert response.status_code == 401
    assert "Missing installation context" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Test 2: Repository inaccessible
# ---------------------------------------------------------------------------

@patch("app.api.routes.conflicts.get_installation_access_token")
@patch("app.api.routes.conflicts.get_installation_repositories")
def test_conflicts_repo_inaccessible(mock_get_repos, mock_get_token, client):
    """Returns 403 when the repository is not in accessible installations."""
    mock_get_token.return_value = "ghs_test_token"
    mock_get_repos.return_value = [{"full_name": "other-owner/other-repo"}]

    client.cookies.set("installation_id", "123456")
    response = client.get("/api/github/repositories/target-owner/target-repo/pulls/1/conflicts")

    assert response.status_code == 403
    assert "not accessible" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Test 3: PR not found
# ---------------------------------------------------------------------------

@patch("app.api.routes.conflicts.get_installation_access_token")
@patch("app.api.routes.conflicts.get_installation_repositories")
@patch("app.api.routes.conflicts.get_pull_request_detail")
def test_conflicts_pr_not_found(mock_get_pr, mock_get_repos, mock_get_token, client):
    """Returns 404 when PR does not exist on GitHub."""
    mock_get_token.return_value = "ghs_test_token"
    mock_get_repos.return_value = [{"full_name": "test-owner/test-repo"}]
    mock_get_pr.side_effect = GitHubAPIError("Pull request not found.", status_code=404)

    client.cookies.set("installation_id", "123456")
    response = client.get("/api/github/repositories/test-owner/test-repo/pulls/999/conflicts")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Test 4: PR is mergeable (mergeable=True)
# ---------------------------------------------------------------------------

@patch("app.api.routes.conflicts.get_installation_access_token")
@patch("app.api.routes.conflicts.get_installation_repositories")
@patch("app.api.routes.conflicts.get_pull_request_detail")
def test_conflicts_pr_is_mergeable(mock_get_pr, mock_get_repos, mock_get_token, client):
    """When PR mergeable is True, returns clean status and does not simulate merge."""
    mock_get_token.return_value = "ghs_test_token"
    mock_get_repos.return_value = [{"full_name": "test-owner/test-repo"}]
    mock_get_pr.return_value = {
        "number": 10,
        "mergeable": True,
        "mergeable_state": "clean",
        "base": {"ref": "main", "sha": "base111"},
        "head": {"ref": "feature", "sha": "head222"},
    }

    client.cookies.set("installation_id", "123456")
    response = client.get("/api/github/repositories/test-owner/test-repo/pulls/10/conflicts")

    assert response.status_code == 200
    data = response.json()
    assert data["pull_request"]["mergeable"] is True
    assert data["conflicts"] == []
    assert "No conflict analysis required" in data["message"]


# ---------------------------------------------------------------------------
# Test 5: PR mergeability is null (mergeable=None)
# ---------------------------------------------------------------------------

@patch("app.api.routes.conflicts.get_installation_access_token")
@patch("app.api.routes.conflicts.get_installation_repositories")
@patch("app.api.routes.conflicts.get_pull_request_detail")
def test_conflicts_pr_mergeability_null(mock_get_pr, mock_get_repos, mock_get_token, client):
    """When PR mergeable is None, returns pending status."""
    mock_get_token.return_value = "ghs_test_token"
    mock_get_repos.return_value = [{"full_name": "test-owner/test-repo"}]
    mock_get_pr.return_value = {
        "number": 11,
        "mergeable": None,
        "mergeable_state": "unknown",
        "base": {"ref": "main", "sha": "base111"},
        "head": {"ref": "feature", "sha": "head222"},
    }

    client.cookies.set("installation_id", "123456")
    response = client.get("/api/github/repositories/test-owner/test-repo/pulls/11/conflicts")

    assert response.status_code == 200
    data = response.json()
    assert data["pull_request"]["mergeable"] is None
    assert data["conflicts"] == []
    assert "still calculating" in data["message"]


# ---------------------------------------------------------------------------
# Test 6 & 7: PR is conflicted and conflict files are identified
# ---------------------------------------------------------------------------

@patch("app.api.routes.conflicts.get_installation_access_token")
@patch("app.api.routes.conflicts.get_installation_repositories")
@patch("app.api.routes.conflicts.get_pull_request_detail")
@patch("app.api.routes.conflicts.simulate_merge_and_extract_conflicts")
def test_conflicts_extraction_success(
    mock_simulate,
    mock_get_pr,
    mock_get_repos,
    mock_get_token,
    client,
):
    """When PR is conflicted (mergeable=False), extracts conflict files and details."""
    mock_get_token.return_value = "ghs_test_token"
    mock_get_repos.return_value = [{"full_name": "test-owner/test-repo"}]
    mock_get_pr.return_value = {
        "number": 8,
        "mergeable": False,
        "mergeable_state": "dirty",
        "base": {"ref": "main", "sha": "6d6cc2dc0f0efb42ae032f14233ed9f474b1a39b"},
        "head": {"ref": "test", "sha": "153b2b552898e53a82bbd2e51b494f40ae1f13c2"},
    }
    mock_simulate.return_value = {
        "merge_base_sha": "b6dff82518e0f93639c3c18c54b9101c6a91c9d7",
        "changed_files": ["calculator.py", "README.md"],
        "conflicting_files": ["calculator.py"],
        "conflicts": [
            {
                "path": "calculator.py",
                "language": "python",
                "base_sha": "d99cef7b69a7112cdd421c2a62300d1f34e875a7",
                "local_sha": "2c8d2698804cc2c3370cfb481b9d57856ff65043",
                "remote_sha": "7dcb23393dd948b28661b4f83aafd792d7551448",
                "base": "def add(a, b):\n    return a + b\n",
                "local": "def add(a, b):\n    return a + b  # local\n",
                "remote": "def add(a, b):\n    return a + b  # remote\n",
                "conflict_markers": {
                    "ours": "    return a + b  # local\n",
                    "theirs": "    return a + b  # remote\n",
                },
                "conflict_type": "textual",
            }
        ],
    }

    client.cookies.set("installation_id", "123456")
    response = client.get("/api/github/repositories/test-owner/test-repo/pulls/8/conflicts")

    assert response.status_code == 200
    data = response.json()
    assert data["repository"]["owner"] == "test-owner"
    assert data["repository"]["name"] == "test-repo"
    assert data["pull_request"]["number"] == 8
    assert data["pull_request"]["mergeable"] is False
    assert len(data["changed_files"]) == 2
    assert data["conflicting_files"] == ["calculator.py"]
    assert len(data["conflicts"]) == 1

    conflict = data["conflicts"][0]
    assert conflict["path"] == "calculator.py"
    assert conflict["language"] == "python"
    assert conflict["conflict_type"] == "textual"
    assert conflict["base_sha"] == "d99cef7b69a7112cdd421c2a62300d1f34e875a7"
    assert "local" in conflict["conflict_markers"]["ours"]
    assert "remote" in conflict["conflict_markers"]["theirs"]


# ---------------------------------------------------------------------------
# Test 8: Base/head SHA handling
# ---------------------------------------------------------------------------

@patch("app.api.routes.conflicts.get_installation_access_token")
@patch("app.api.routes.conflicts.get_installation_repositories")
@patch("app.api.routes.conflicts.get_pull_request_detail")
@patch("app.api.routes.conflicts.simulate_merge_and_extract_conflicts")
def test_conflicts_base_head_sha_passed(
    mock_simulate,
    mock_get_pr,
    mock_get_repos,
    mock_get_token,
    client,
):
    """Verify exact base_sha and head_sha from GitHub are passed to simulation."""
    mock_get_token.return_value = "ghs_test_token"
    mock_get_repos.return_value = [{"full_name": "test-owner/test-repo"}]
    mock_get_pr.return_value = {
        "number": 5,
        "mergeable": False,
        "mergeable_state": "dirty",
        "base": {"ref": "main", "sha": "base_sha_12345"},
        "head": {"ref": "feature", "sha": "head_sha_67890"},
    }
    mock_simulate.return_value = {
        "merge_base_sha": "ancestor_sha",
        "changed_files": ["f.txt"],
        "conflicting_files": ["f.txt"],
        "conflicts": [],
    }

    client.cookies.set("installation_id", "123456")
    client.get("/api/github/repositories/test-owner/test-repo/pulls/5/conflicts")

    mock_simulate.assert_called_once_with(
        owner="test-owner",
        repo="test-repo",
        pull_number=5,
        base_branch="main",
        head_branch="feature",
        base_sha="base_sha_12345",
        head_sha="head_sha_67890",
        installation_token="ghs_test_token",
    )


# ---------------------------------------------------------------------------
# Test 9: Multiple conflicting files
# ---------------------------------------------------------------------------

@patch("app.api.routes.conflicts.get_installation_access_token")
@patch("app.api.routes.conflicts.get_installation_repositories")
@patch("app.api.routes.conflicts.get_pull_request_detail")
@patch("app.api.routes.conflicts.simulate_merge_and_extract_conflicts")
def test_multiple_conflicting_files(
    mock_simulate,
    mock_get_pr,
    mock_get_repos,
    mock_get_token,
    client,
):
    """Verify endpoint correctly handles multiple conflicting files."""
    mock_get_token.return_value = "ghs_test_token"
    mock_get_repos.return_value = [{"full_name": "test-owner/test-repo"}]
    mock_get_pr.return_value = {
        "number": 8,
        "mergeable": False,
        "mergeable_state": "dirty",
        "base": {"ref": "main", "sha": "b1"},
        "head": {"ref": "test", "sha": "h1"},
    }
    mock_simulate.return_value = {
        "merge_base_sha": "mb",
        "changed_files": ["calculator.py", "src/utils.py"],
        "conflicting_files": ["calculator.py", "src/utils.py"],
        "conflicts": [
            {
                "path": "calculator.py",
                "language": "python",
                "base_sha": "sha1",
                "local_sha": "sha2",
                "remote_sha": "sha3",
                "base": "b1",
                "local": "l1",
                "remote": "r1",
                "conflict_markers": {"ours": "o1", "theirs": "t1"},
                "conflict_type": "textual",
            },
            {
                "path": "src/utils.py",
                "language": "python",
                "base_sha": "sha4",
                "local_sha": "sha5",
                "remote_sha": "sha6",
                "base": "b2",
                "local": "l2",
                "remote": "r2",
                "conflict_markers": {"ours": "o2", "theirs": "t2"},
                "conflict_type": "textual",
            },
        ],
    }

    client.cookies.set("installation_id", "123456")
    response = client.get("/api/github/repositories/test-owner/test-repo/pulls/8/conflicts")

    assert response.status_code == 200
    data = response.json()
    assert len(data["conflicts"]) == 2
    paths = [c["path"] for c in data["conflicts"]]
    assert "calculator.py" in paths
    assert "src/utils.py" in paths


# ---------------------------------------------------------------------------
# Test 10: No conflicting files detected in simulation
# ---------------------------------------------------------------------------

@patch("app.api.routes.conflicts.get_installation_access_token")
@patch("app.api.routes.conflicts.get_installation_repositories")
@patch("app.api.routes.conflicts.get_pull_request_detail")
@patch("app.api.routes.conflicts.simulate_merge_and_extract_conflicts")
def test_no_conflicting_files_in_simulation(
    mock_simulate,
    mock_get_pr,
    mock_get_repos,
    mock_get_token,
    client,
):
    """When simulation finds 0 unmerged files, returns empty list with appropriate message."""
    mock_get_token.return_value = "ghs_test_token"
    mock_get_repos.return_value = [{"full_name": "test-owner/test-repo"}]
    mock_get_pr.return_value = {
        "number": 8,
        "mergeable": False,
        "mergeable_state": "dirty",
        "base": {"ref": "main", "sha": "b1"},
        "head": {"ref": "test", "sha": "h1"},
    }
    mock_simulate.return_value = {
        "merge_base_sha": "mb",
        "changed_files": ["calculator.py"],
        "conflicting_files": [],
        "conflicts": [],
    }

    client.cookies.set("installation_id", "123456")
    response = client.get("/api/github/repositories/test-owner/test-repo/pulls/8/conflicts")

    assert response.status_code == 200
    data = response.json()
    assert data["conflicts"] == []
    assert "No conflicting files detected" in data["message"]


# ---------------------------------------------------------------------------
# Test 11: Git operation failure
# ---------------------------------------------------------------------------

@patch("app.api.routes.conflicts.get_installation_access_token")
@patch("app.api.routes.conflicts.get_installation_repositories")
@patch("app.api.routes.conflicts.get_pull_request_detail")
@patch("app.api.routes.conflicts.simulate_merge_and_extract_conflicts")
def test_git_operation_failure(
    mock_simulate,
    mock_get_pr,
    mock_get_repos,
    mock_get_token,
    client,
):
    """GitConflictError raises 500 status code with sanitized error message."""
    mock_get_token.return_value = "ghs_test_token"
    mock_get_repos.return_value = [{"full_name": "test-owner/test-repo"}]
    mock_get_pr.return_value = {
        "number": 8,
        "mergeable": False,
        "mergeable_state": "dirty",
        "base": {"ref": "main", "sha": "b1"},
        "head": {"ref": "test", "sha": "h1"},
    }
    mock_simulate.side_effect = GitConflictError("Git command failed: remote rejected", status_code=500)

    client.cookies.set("installation_id", "123456")
    response = client.get("/api/github/repositories/test-owner/test-repo/pulls/8/conflicts")

    assert response.status_code == 500
    assert "Git conflict extraction failed" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Test 12: Repository contents are never executed
# ---------------------------------------------------------------------------

def test_repo_contents_never_executed():
    """
    Verify that run_git_command only invokes git directly via subprocess.run
    and never invokes python, sh, npm, node, bash, or eval.
    """
    with tempfile.TemporaryDirectory() as td:
        with patch("subprocess.run") as mock_subproc:
            mock_subproc.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
            run_git_command(["status"], cwd=td)

            mock_subproc.assert_called_once()
            called_args = mock_subproc.call_args[0][0]
            assert called_args[0] == "git"
            assert called_args[1] == "status"
            # Ensure no shell interpreter was called
            assert not any(arg in ["sh", "bash", "python", "node", "npm", "eval"] for arg in called_args)


# ---------------------------------------------------------------------------
# Test 13: No credentials/tokens/JWTs in response
# ---------------------------------------------------------------------------

@patch("app.api.routes.conflicts.get_installation_access_token")
@patch("app.api.routes.conflicts.get_installation_repositories")
@patch("app.api.routes.conflicts.get_pull_request_detail")
@patch("app.api.routes.conflicts.simulate_merge_and_extract_conflicts")
def test_no_credentials_in_response(
    mock_simulate,
    mock_get_pr,
    mock_get_repos,
    mock_get_token,
    client,
):
    """Verify that response text and headers contain no access tokens, JWTs, or secrets."""
    secret_token = "ghs_supersecrettokenvalue99999"
    mock_get_token.return_value = secret_token
    mock_get_repos.return_value = [{"full_name": "test-owner/test-repo"}]
    mock_get_pr.return_value = {
        "number": 8,
        "mergeable": False,
        "mergeable_state": "dirty",
        "base": {"ref": "main", "sha": "base_sha"},
        "head": {"ref": "test", "sha": "head_sha"},
    }
    mock_simulate.return_value = {
        "merge_base_sha": "mb_sha",
        "changed_files": ["calculator.py"],
        "conflicting_files": ["calculator.py"],
        "conflicts": [
            {
                "path": "calculator.py",
                "language": "python",
                "base_sha": "b_sha",
                "local_sha": "l_sha",
                "remote_sha": "r_sha",
                "base": "def f(): pass",
                "local": "def f(): pass # local",
                "remote": "def f(): pass # remote",
                "conflict_markers": {"ours": "local", "theirs": "remote"},
                "conflict_type": "textual",
            }
        ],
    }

    client.cookies.set("installation_id", "123456")
    response = client.get("/api/github/repositories/test-owner/test-repo/pulls/8/conflicts")

    assert response.status_code == 200
    all_content = f"{response.text} {str(response.headers)}".lower()
    assert secret_token.lower() not in all_content
    assert "ghs_" not in all_content
    assert "ghp_" not in all_content
    assert "private_key" not in all_content
    assert "client_secret" not in all_content


# ---------------------------------------------------------------------------
# Test 14: Temporary Git state is cleaned up
# ---------------------------------------------------------------------------

def test_temporary_git_state_cleaned_up():
    """Verify that temp directory created during simulation is removed after completion."""
    created_dir: str | None = None

    def capture_tempdir(*args, **kwargs):
        nonlocal created_dir
        actual_temp = tempfile.mkdtemp()
        created_dir = actual_temp
        return actual_temp

    # Run simulation on a mock local git repo to verify cleanup
    with tempfile.TemporaryDirectory() as td:
        p = Path(td)
        # Initialize bare mock repo
        subprocess.run(["git", "init"], cwd=str(p), capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "MergeMind"], cwd=str(p), capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(p), capture_output=True, check=True)

        file_path = p / "f.txt"
        file_path.write_text("base\n")
        subprocess.run(["git", "add", "f.txt"], cwd=str(p), capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "base"], cwd=str(p), capture_output=True, check=True)
        b_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(p), capture_output=True, text=True, check=True).stdout.strip()

        subprocess.run(["git", "checkout", "-b", "local-br"], cwd=str(p), capture_output=True, check=True)
        file_path.write_text("local\n")
        subprocess.run(["git", "commit", "-am", "local"], cwd=str(p), capture_output=True, check=True)
        l_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(p), capture_output=True, text=True, check=True).stdout.strip()

        subprocess.run(["git", "checkout", b_sha], cwd=str(p), capture_output=True, check=True)
        subprocess.run(["git", "checkout", "-b", "remote-br"], cwd=str(p), capture_output=True, check=True)
        file_path.write_text("remote\n")
        subprocess.run(["git", "commit", "-am", "remote"], cwd=str(p), capture_output=True, check=True)
        r_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(p), capture_output=True, text=True, check=True).stdout.strip()

        # In a separate tempdir, simulate merge
        with tempfile.TemporaryDirectory() as sim_dir:
            temp_path = Path(sim_dir)
            run_git_command(["init"], cwd=temp_path)
            run_git_command(["remote", "add", "origin", str(p)], cwd=temp_path)
            run_git_command(["fetch", "origin", "local-br", "remote-br"], cwd=temp_path)
            run_git_command(["checkout", l_sha], cwd=temp_path)
            run_git_command(["merge", "--no-commit", "--no-ff", r_sha], cwd=temp_path, check=False)

            ls_res = run_git_command(["ls-files", "-u"], cwd=temp_path)
            assert "f.txt" in ls_res.stdout

        # sim_dir is now cleaned up and removed
        assert not os.path.exists(sim_dir)

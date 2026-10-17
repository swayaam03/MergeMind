"""Unit tests for Phase 7 & 8: GitHub Webhooks, Entity Persistence, and Human Decision Reviews."""

import hashlib
import hmac
import json
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.core.config import settings
from app.db import database as db
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    """Ensure tables are cleanly initialized before each test."""
    db.init_db()
    with db.get_db_connection() as conn:
        conn.execute("DELETE FROM merge_attempts;")
        conn.execute("DELETE FROM merge_runs;")
        conn.execute("DELETE FROM conflicts;")
        conn.execute("DELETE FROM pull_requests;")
        conn.execute("DELETE FROM repositories;")
        conn.commit()


def test_repository_and_pull_request_persistence():
    """Test upserting and retrieving tracked repositories and pull requests."""
    repo = db.upsert_repository(
        owner="octocat",
        name="Hello-World",
        full_name="octocat/hello-world",
        default_branch="main",
        is_private=False,
        installation_id=12345,
    )
    assert repo["full_name"] == "octocat/hello-world"
    assert repo["installation_id"] == 12345

    repos = db.get_tracked_repositories(installation_id=12345)
    assert len(repos) == 1
    assert repos[0]["name"] == "Hello-World"

    pr = db.upsert_pull_request(
        repository_full_name="octocat/hello-world",
        number=42,
        title="Add new greeting feature",
        state="open",
        base_branch="main",
        head_branch="feature",
        mergeable_state="dirty",
        has_conflicts=True,
    )
    assert pr["number"] == 42
    assert pr["has_conflicts"] == 1

    prs = db.get_tracked_pull_requests("octocat/hello-world")
    assert len(prs) == 1
    assert prs[0]["title"] == "Add new greeting feature"


def test_merge_run_and_human_decision_persistence():
    """Test creating a merge run, recording attempts, and saving a human review decision."""
    run = db.create_merge_run(
        repository_full_name="octocat/hello-world",
        pull_request_number=10,
        file_path="src/main.py",
        status="in_progress",
    )
    run_id = run["id"]
    assert run["status"] == "in_progress"

    att = db.record_merge_attempt(
        merge_run_id=run_id,
        attempt_number=1,
        model_used="openrouter/qwen3",
        resolved_code="def main(): return 'merged'",
        reasoning="Combined local and remote branches",
        confidence=0.95,
        verification_passed=True,
        security_passed=True,
    )
    assert att["attempt_number"] == 1
    assert att["verification_passed"] == 1

    # Record Human Decision: ACCEPT
    updated_run = db.record_human_decision(
        merge_run_id=run_id,
        decision="accept",
        final_code="def main(): return 'merged'",
    )
    assert updated_run["human_decision"] == "accept"
    assert updated_run["status"] == "human_accepted"

    runs = db.get_merge_runs_by_pr("octocat/hello-world", 10)
    assert len(runs) == 1
    assert runs[0]["id"] == run_id
    assert len(runs[0]["attempts"]) == 1


def test_webhook_ping_event(client):
    """Test receiving a GitHub webhook ping event."""
    payload = json.dumps({"zen": "Mind your merge conflicts.", "hook_id": 99}).encode("utf-8")
    sig = "sha256=" + hmac.new(
        key=settings.GITHUB_WEBHOOK_SECRET.encode("utf-8"),
        msg=payload,
        digestmod=hashlib.sha256,
    ).hexdigest()

    response = client.post(
        "/api/github/webhooks",
        content=payload,
        headers={
            "X-GitHub-Event": "ping",
            "X-GitHub-Delivery": "delivery-12345",
            "X-Hub-Signature-256": sig,
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["event"] == "ping"


def test_webhook_invalid_signature_rejected(client):
    """Test that webhooks with an invalid HMAC signature are rejected with 401."""
    payload = json.dumps({"action": "opened"}).encode("utf-8")
    response = client.post(
        "/api/github/webhooks",
        content=payload,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-GitHub-Delivery": "delivery-fail",
            "X-Hub-Signature-256": "sha256=invalidhexsignature",
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 401


def test_webhook_pull_request_synchronization(client):
    """Test that a pull_request event automatically syncs repository and PR records."""
    payload_data = {
        "action": "synchronize",
        "number": 7,
        "pull_request": {
            "number": 7,
            "title": "Fix memory leak in parser",
            "state": "open",
            "mergeable_state": "dirty",
            "base": {"ref": "main"},
            "head": {"ref": "fix/leak"},
        },
        "repository": {
            "name": "super-project",
            "full_name": "developer/super-project",
            "owner": {"login": "developer"},
            "default_branch": "main",
            "private": False,
        },
        "installation": {"id": 888},
    }
    payload_bytes = json.dumps(payload_data).encode("utf-8")
    sig = "sha256=" + hmac.new(
        key=settings.GITHUB_WEBHOOK_SECRET.encode("utf-8"),
        msg=payload_bytes,
        digestmod=hashlib.sha256,
    ).hexdigest()

    response = client.post(
        "/api/github/webhooks",
        content=payload_bytes,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-GitHub-Delivery": "delivery-pr-sync",
            "X-Hub-Signature-256": sig,
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "processed"

    # Verify persisted in database
    prs = db.get_tracked_pull_requests("developer/super-project")
    assert len(prs) == 1
    assert prs[0]["number"] == 7
    assert prs[0]["has_conflicts"] == 1


def test_submit_human_decision_endpoint(client):
    """Test the POST /repositories/{owner}/{repo}/pulls/{pull_number}/decision endpoint."""
    with patch("app.api.routes.merges.resolve_installation_id", return_value=123):
        # First create a run
        run = db.create_merge_run(
            repository_full_name="swayaam03/mergemind",
            pull_request_number=5,
            file_path="app/core.py",
            status="human_review",
        )

        resp = client.post(
            "/api/github/repositories/swayaam03/mergemind/pulls/5/decision",
            json={
                "decision": "edit",
                "file_path": "app/core.py",
                "final_code": "def resolved(): return True",
                "notes": "Adjusted logic to retain both branch fixes.",
            },
            params={"run_id": run["id"], "installation_id": 123},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["action"] == "edit"
        assert data["merge_run"]["human_decision"] == "edit"

"""SQLite database management and user authentication store for MergeMind."""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.config import ROOT_DIR

logger = logging.getLogger(__name__)

DB_PATH = ROOT_DIR / "mergemind.db"


def get_db_connection() -> sqlite3.Connection:
    """Create a connection to the SQLite database with row factory enabled."""
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize database tables if they do not exist."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                github_installation_id INTEGER,
                github_username TEXT,
                github_connected_at TEXT,
                created_at TEXT NOT NULL
            );
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at REAL NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);"
        )

        # Repositories & Pull Requests tracking
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS repositories (
                id TEXT PRIMARY KEY,
                owner TEXT NOT NULL,
                name TEXT NOT NULL,
                full_name TEXT UNIQUE NOT NULL,
                default_branch TEXT NOT NULL DEFAULT 'main',
                is_private INTEGER NOT NULL DEFAULT 0,
                installation_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS pull_requests (
                id TEXT PRIMARY KEY,
                repository_full_name TEXT NOT NULL,
                number INTEGER NOT NULL,
                title TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'open',
                base_branch TEXT NOT NULL,
                head_branch TEXT NOT NULL,
                mergeable_state TEXT,
                has_conflicts INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(repository_full_name, number)
            );
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS conflicts (
                id TEXT PRIMARY KEY,
                repository_full_name TEXT NOT NULL,
                pull_request_number INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                conflict_type TEXT,
                base_code TEXT,
                local_code TEXT,
                remote_code TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(repository_full_name, pull_request_number, file_path)
            );
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS merge_runs (
                id TEXT PRIMARY KEY,
                repository_full_name TEXT NOT NULL,
                pull_request_number INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                status TEXT NOT NULL,
                total_attempts INTEGER NOT NULL DEFAULT 0,
                resolved_code TEXT,
                explanation TEXT,
                human_decision TEXT,
                human_decision_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS merge_attempts (
                id TEXT PRIMARY KEY,
                merge_run_id TEXT NOT NULL,
                attempt_number INTEGER NOT NULL,
                model_used TEXT,
                resolved_code TEXT,
                reasoning TEXT,
                confidence REAL,
                verification_passed INTEGER NOT NULL DEFAULT 0,
                security_passed INTEGER NOT NULL DEFAULT 0,
                failure_reason TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (merge_run_id) REFERENCES merge_runs (id) ON DELETE CASCADE
            );
            """
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_repo_full_name ON repositories(full_name);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_prs_repo_num ON pull_requests(repository_full_name, number);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_merge_runs_pr ON merge_runs(repository_full_name, pull_request_number);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_attempts_run_id ON merge_attempts(merge_run_id);")
        conn.commit()
    logger.debug("Database initialized at %s", DB_PATH)


def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """Hash a password using PBKDF2-HMAC-SHA256."""
    if not salt:
        salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000,
    ).hex()
    return pw_hash, salt


def verify_password(password: str, pw_hash: str, salt: str) -> bool:
    """Verify password against stored PBKDF2 hash using constant-time comparison."""
    computed, _ = hash_password(password, salt)
    return hmac.compare_digest(computed, pw_hash)


def create_user(username: str, email: str, password: str) -> Dict[str, Any]:
    """Register a new user account."""
    init_db()
    clean_username = username.strip()
    clean_email = email.strip().lower()
    pw_hash, salt = hash_password(password)
    user_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()

    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO users (id, username, email, password_hash, salt, created_at)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (user_id, clean_username, clean_email, pw_hash, salt, now_iso),
            )
            conn.commit()
        except sqlite3.IntegrityError as exc:
            msg = str(exc).lower()
            if "username" in msg:
                raise ValueError(f"Username '{clean_username}' is already taken.") from exc
            if "email" in msg:
                raise ValueError(f"Email '{clean_email}' is already registered.") from exc
            raise ValueError("User with these credentials already exists.") from exc

    return get_user_by_id(user_id)  # type: ignore


def authenticate_user(username_or_email: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate user with username or email and password."""
    init_db()
    identifier = username_or_email.strip()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM users
            WHERE username = ? OR email = ?
            LIMIT 1;
            """,
            (identifier, identifier.lower()),
        )
        row = cursor.fetchone()
        if not row:
            return None

        if not verify_password(password, row["password_hash"], row["salt"]):
            return None

        return dict(row)


def create_session(user_id: str, duration_days: int = 14) -> str:
    """Create a new session token for the user."""
    init_db()
    token = secrets.token_urlsafe(32)
    now_iso = datetime.now(timezone.utc).isoformat()
    expires_at = time.time() + (duration_days * 86400)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO sessions (token, user_id, created_at, expires_at)
            VALUES (?, ?, ?, ?);
            """,
            (token, user_id, now_iso, expires_at),
        )
        conn.commit()

    return token


def get_user_by_session_token(token: str) -> Optional[Dict[str, Any]]:
    """Retrieve user object associated with an active session token."""
    if not token or not token.strip():
        return None
    init_db()

    clean_token = token.strip()
    now_ts = time.time()

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT u.* FROM users u
            JOIN sessions s ON u.id = s.user_id
            WHERE s.token = ? AND s.expires_at > ?
            LIMIT 1;
            """,
            (clean_token, now_ts),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return dict(row)


def delete_session(token: str) -> None:
    """Invalidate a session token upon logout."""
    if not token:
        return
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE token = ?;", (token.strip(),))
        conn.commit()


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve user profile by ID."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ? LIMIT 1;", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def link_github_installation(
    user_id: str,
    installation_id: int,
    github_username: Optional[str] = None,
) -> Dict[str, Any]:
    """Link a GitHub App installation ID to a user account."""
    init_db()
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE users
            SET github_installation_id = ?,
                github_username = COALESCE(?, github_username),
                github_connected_at = ?
            WHERE id = ?;
            """,
            (installation_id, github_username, now_iso, user_id),
        )
        conn.commit()

    user = get_user_by_id(user_id)
    if not user:
        raise ValueError("User not found.")
    return user


def unlink_github_installation(user_id: str) -> Dict[str, Any]:
    """Unlink GitHub App from a user account."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE users
            SET github_installation_id = NULL,
                github_username = NULL,
                github_connected_at = NULL
            WHERE id = ?;
            """,
            (user_id,),
        )
        conn.commit()

    user = get_user_by_id(user_id)
    if not user:
        raise ValueError("User not found.")
    return user


def get_latest_user_with_github() -> Optional[Dict[str, Any]]:
    """Retrieve the most recently connected user who has a linked GitHub installation."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM users
            WHERE github_installation_id IS NOT NULL AND github_installation_id > 0
            ORDER BY github_connected_at DESC
            LIMIT 1;
            """
        )
        row = cursor.fetchone()
        return dict(row) if row else None


# =========================================================================
# Phase 7 & Phase 8: Repository, Pull Request & Merge Run Persistence
# =========================================================================

def upsert_repository(
    owner: str,
    name: str,
    full_name: str,
    default_branch: str = "main",
    is_private: bool = False,
    installation_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Insert or update a tracked GitHub repository."""
    init_db()
    now_iso = datetime.now(timezone.utc).isoformat()
    repo_id = str(uuid.uuid4())

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO repositories (id, owner, name, full_name, default_branch, is_private, installation_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(full_name) DO UPDATE SET
                owner = excluded.owner,
                name = excluded.name,
                default_branch = excluded.default_branch,
                is_private = excluded.is_private,
                installation_id = COALESCE(excluded.installation_id, repositories.installation_id),
                updated_at = excluded.updated_at;
            """,
            (
                repo_id,
                owner,
                name,
                full_name.lower(),
                default_branch,
                1 if is_private else 0,
                installation_id,
                now_iso,
                now_iso,
            ),
        )
        conn.commit()

        cursor.execute("SELECT * FROM repositories WHERE full_name = ? LIMIT 1;", (full_name.lower(),))
        row = cursor.fetchone()
        return dict(row)


def get_tracked_repositories(installation_id: Optional[int] = None) -> list[Dict[str, Any]]:
    """Retrieve all tracked repositories, optionally filtered by installation_id."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if installation_id:
            cursor.execute(
                "SELECT * FROM repositories WHERE installation_id = ? ORDER BY updated_at DESC;",
                (installation_id,),
            )
        else:
            cursor.execute("SELECT * FROM repositories ORDER BY updated_at DESC;")
        return [dict(r) for r in cursor.fetchall()]


def upsert_pull_request(
    repository_full_name: str,
    number: int,
    title: str,
    state: str = "open",
    base_branch: str = "main",
    head_branch: str = "",
    mergeable_state: Optional[str] = None,
    has_conflicts: bool = False,
) -> Dict[str, Any]:
    """Insert or update a pull request record."""
    init_db()
    now_iso = datetime.now(timezone.utc).isoformat()
    pr_id = str(uuid.uuid4())

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO pull_requests (
                id, repository_full_name, number, title, state,
                base_branch, head_branch, mergeable_state, has_conflicts,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(repository_full_name, number) DO UPDATE SET
                title = excluded.title,
                state = excluded.state,
                base_branch = excluded.base_branch,
                head_branch = excluded.head_branch,
                mergeable_state = excluded.mergeable_state,
                has_conflicts = excluded.has_conflicts,
                updated_at = excluded.updated_at;
            """,
            (
                pr_id,
                repository_full_name.lower(),
                number,
                title,
                state,
                base_branch,
                head_branch,
                mergeable_state,
                1 if has_conflicts else 0,
                now_iso,
                now_iso,
            ),
        )
        conn.commit()

        cursor.execute(
            "SELECT * FROM pull_requests WHERE repository_full_name = ? AND number = ? LIMIT 1;",
            (repository_full_name.lower(), number),
        )
        row = cursor.fetchone()
        return dict(row)


def get_tracked_pull_requests(repository_full_name: str) -> list[Dict[str, Any]]:
    """Retrieve all tracked pull requests for a repository."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM pull_requests WHERE repository_full_name = ? ORDER BY number DESC;",
            (repository_full_name.lower(),),
        )
        return [dict(r) for r in cursor.fetchall()]


def upsert_conflict(
    repository_full_name: str,
    pull_request_number: int,
    file_path: str,
    conflict_type: Optional[str] = None,
    base_code: Optional[str] = None,
    local_code: Optional[str] = None,
    remote_code: Optional[str] = None,
) -> Dict[str, Any]:
    """Record an identified conflict in a pull request."""
    init_db()
    now_iso = datetime.now(timezone.utc).isoformat()
    conflict_id = str(uuid.uuid4())

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO conflicts (
                id, repository_full_name, pull_request_number, file_path,
                conflict_type, base_code, local_code, remote_code, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(repository_full_name, pull_request_number, file_path) DO UPDATE SET
                conflict_type = excluded.conflict_type,
                base_code = excluded.base_code,
                local_code = excluded.local_code,
                remote_code = excluded.remote_code;
            """,
            (
                conflict_id,
                repository_full_name.lower(),
                pull_request_number,
                file_path,
                conflict_type,
                base_code,
                local_code,
                remote_code,
                now_iso,
            ),
        )
        conn.commit()

        cursor.execute(
            """
            SELECT * FROM conflicts
            WHERE repository_full_name = ? AND pull_request_number = ? AND file_path = ?
            LIMIT 1;
            """,
            (repository_full_name.lower(), pull_request_number, file_path),
        )
        row = cursor.fetchone()
        return dict(row)


def create_merge_run(
    repository_full_name: str,
    pull_request_number: int,
    file_path: str,
    status: str = "in_progress",
) -> Dict[str, Any]:
    """Start and persist a new MergeMind resolution run."""
    init_db()
    run_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO merge_runs (
                id, repository_full_name, pull_request_number, file_path,
                status, total_attempts, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, 0, ?, ?);
            """,
            (run_id, repository_full_name.lower(), pull_request_number, file_path, status, now_iso, now_iso),
        )
        conn.commit()

        cursor.execute("SELECT * FROM merge_runs WHERE id = ?;", (run_id,))
        row = cursor.fetchone()
        return dict(row)


def record_merge_attempt(
    merge_run_id: str,
    attempt_number: int,
    model_used: Optional[str] = None,
    resolved_code: Optional[str] = None,
    reasoning: Optional[str] = None,
    confidence: Optional[float] = None,
    verification_passed: bool = False,
    security_passed: bool = False,
    failure_reason: Optional[str] = None,
) -> Dict[str, Any]:
    """Record an individual merge iteration attempt within a merge run."""
    init_db()
    attempt_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO merge_attempts (
                id, merge_run_id, attempt_number, model_used,
                resolved_code, reasoning, confidence, verification_passed,
                security_passed, failure_reason, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                attempt_id,
                merge_run_id,
                attempt_number,
                model_used,
                resolved_code,
                reasoning,
                confidence,
                1 if verification_passed else 0,
                1 if security_passed else 0,
                failure_reason,
                now_iso,
            ),
        )
        # Update total attempts on run
        cursor.execute(
            """
            UPDATE merge_runs
            SET total_attempts = MAX(total_attempts, ?),
                updated_at = ?
            WHERE id = ?;
            """,
            (attempt_number, now_iso, merge_run_id),
        )
        conn.commit()

        cursor.execute("SELECT * FROM merge_attempts WHERE id = ?;", (attempt_id,))
        row = cursor.fetchone()
        return dict(row)


def update_merge_run_status(
    merge_run_id: str,
    status: str,
    resolved_code: Optional[str] = None,
    explanation: Optional[str] = None,
) -> Dict[str, Any]:
    """Update final or current status of a merge run."""
    init_db()
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE merge_runs
            SET status = ?,
                resolved_code = COALESCE(?, resolved_code),
                explanation = COALESCE(?, explanation),
                updated_at = ?
            WHERE id = ?;
            """,
            (status, resolved_code, explanation, now_iso, merge_run_id),
        )
        conn.commit()

        cursor.execute("SELECT * FROM merge_runs WHERE id = ?;", (merge_run_id,))
        row = cursor.fetchone()
        return dict(row)


def record_human_decision(
    merge_run_id: str,
    decision: str,  # 'accept', 'edit', 'reject'
    final_code: Optional[str] = None,
) -> Dict[str, Any]:
    """Record human reviewer decision on a proposed merge."""
    init_db()
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE merge_runs
            SET human_decision = ?,
                human_decision_at = ?,
                resolved_code = COALESCE(?, resolved_code),
                status = ?,
                updated_at = ?
            WHERE id = ?;
            """,
            (
                decision,
                now_iso,
                final_code,
                f"human_{decision}ed",
                now_iso,
                merge_run_id,
            ),
        )
        conn.commit()

        cursor.execute("SELECT * FROM merge_runs WHERE id = ?;", (merge_run_id,))
        row = cursor.fetchone()
        return dict(row)


def get_merge_runs_by_pr(
    repository_full_name: str,
    pull_request_number: int,
) -> list[Dict[str, Any]]:
    """Retrieve history of merge runs for a PR with associated attempts."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM merge_runs
            WHERE repository_full_name = ? AND pull_request_number = ?
            ORDER BY created_at DESC;
            """,
            (repository_full_name.lower(), pull_request_number),
        )
        runs = [dict(r) for r in cursor.fetchall()]

        for r in runs:
            cursor.execute(
                """
                SELECT * FROM merge_attempts
                WHERE merge_run_id = ?
                ORDER BY attempt_number ASC;
                """,
                (r["id"],),
            )
            r["attempts"] = [dict(a) for a in cursor.fetchall()]

        return runs


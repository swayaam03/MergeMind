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

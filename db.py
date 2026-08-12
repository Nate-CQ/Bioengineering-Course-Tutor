"""
Persistence layer for mastery ratings and user accounts, so progress
survives across sessions and browser refreshes, and each person's data
stays genuinely separate.

Uses SQLite. Passwords are never stored in plain text, only a salted
PBKDF2 hash, using Python's built-in hashlib so no extra dependency is
needed. This is intentionally lightweight (no email verification, no
password reset flow) since it's a study tool for a small group, not a
security-sensitive product, but it does mean two different people can't
collide on the same username the way an unauthenticated system would
allow.

Deployment note: this file-based database persists reliably for local
use and for normal day-to-day use of a deployed Streamlit app. It is
not guaranteed to survive an app that has gone fully idle and restarts,
or a redeploy, on Streamlit Community Cloud specifically, since the
container's disk is not permanent storage. For guaranteed durability
through redeploys, swap this module out for a hosted database (for
example Supabase or a managed Postgres instance) using the same
function signatures below.
"""

import hashlib
import json
import os
import sqlite3
from contextlib import closing

DB_PATH = "course_tutor.db"
_PBKDF2_ITERATIONS = 100_000


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            salt TEXT NOT NULL,
            password_hash TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ratings (
            username TEXT NOT NULL,
            course TEXT NOT NULL,
            topic TEXT NOT NULL,
            rating REAL NOT NULL,
            questions_answered INTEGER NOT NULL,
            history TEXT NOT NULL,
            PRIMARY KEY (username, course, topic)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS question_history (
            username TEXT NOT NULL,
            course TEXT NOT NULL,
            topic TEXT NOT NULL,
            question TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    return conn


def _hash_password(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS).hex()


def user_exists(username: str) -> bool:
    with closing(_connect()) as conn:
        row = conn.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone()
    return row is not None


def create_user(username: str, password: str) -> None:
    """Create a new account. Caller must check user_exists() first."""
    salt = os.urandom(16)
    password_hash = _hash_password(password, salt)
    with closing(_connect()) as conn:
        conn.execute(
            "INSERT INTO users (username, salt, password_hash) VALUES (?, ?, ?)",
            (username, salt.hex(), password_hash),
        )
        conn.commit()


def verify_password(username: str, password: str) -> bool:
    """True if the password matches the stored hash for this username.
    False (not an error) if the username doesn't exist or the password
    is wrong, so callers don't need to distinguish the two cases."""
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT salt, password_hash FROM users WHERE username = ?", (username,)
        ).fetchone()
    if row is None:
        return False
    salt_hex, stored_hash = row
    return _hash_password(password, bytes.fromhex(salt_hex)) == stored_hash


def load_ratings(username: str, course: str) -> dict:
    """Return {topic: {"rating": float, "questions_answered": int,
    "history": [[difficulty, score, rating], ...]}} for one user and course."""
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT topic, rating, questions_answered, history "
            "FROM ratings WHERE username = ? AND course = ?",
            (username, course),
        ).fetchall()
    return {
        topic: {
            "rating": rating,
            "questions_answered": questions_answered,
            "history": json.loads(history),
        }
        for topic, rating, questions_answered, history in rows
    }


def save_rating(username: str, course: str, topic: str, rating: float,
                 questions_answered: int, history: list) -> None:
    """Upsert one topic's rating for one user and course."""
    with closing(_connect()) as conn:
        conn.execute(
            """
            INSERT INTO ratings (username, course, topic, rating, questions_answered, history)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(username, course, topic) DO UPDATE SET
                rating = excluded.rating,
                questions_answered = excluded.questions_answered,
                history = excluded.history
            """,
            (username, course, topic, rating, questions_answered, json.dumps(history)),
        )
        conn.commit()


def known_usernames() -> list:
    """All registered usernames, used to show a friendly 'welcome back'
    rather than silently starting fresh."""
    with closing(_connect()) as conn:
        rows = conn.execute("SELECT username FROM users ORDER BY username").fetchall()
    return [r[0] for r in rows]


def save_question(username: str, course: str, topic: str, question_text: str) -> None:
    """Log a generated question so future generations on the same topic
    can avoid repeating it."""
    with closing(_connect()) as conn:
        conn.execute(
            "INSERT INTO question_history (username, course, topic, question) VALUES (?, ?, ?, ?)",
            (username, course, topic, question_text),
        )
        conn.commit()


def get_recent_questions(username: str, course: str, topic: str, limit: int = 10) -> list:
    """Return the most recent question texts asked on this topic, most
    recent first, used to steer generation away from repeats."""
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT question FROM question_history "
            "WHERE username = ? AND course = ? AND topic = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (username, course, topic, limit),
        ).fetchall()
    return [r[0] for r in rows]

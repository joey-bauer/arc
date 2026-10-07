import sqlite3
from pathlib import Path
from datetime import datetime, timezone

DATABASE_PATH = Path(__file__).resolve().parent / "data" / "arc.db"

def initialize_database():
    """Create session storage without removing existing records."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH)

    try:
        with connection:
            # Timestamps will be stored as timezone-aware UTC ISO strings.
            connection.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY,
                    project_id INTEGER,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    duration_seconds INTEGER,
                    CHECK (
                        (ended_at IS NULL AND duration_seconds IS NULL)
                        OR
                        ( 
                            ended_at IS NOT NULL
                            AND duration_seconds IS NOT NULL
                            AND duration_seconds >= 0
                        )
                    )
                )
            """)

            # Every active row has the same indexed value, so only one can exist.
            connection.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS one_active_session
                ON sessions ((1))
                WHERE ended_at IS NULL
            """)
    finally:
        connection.close()

def get_active_session():
    """Return the active session, or None when no session is running."""
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    try:
        return connection.execute("""
        SELECT id, project_id, started_at
        FROM sessions
        WHERE ended_at IS NULL
    """).fetchone()
    finally:
        connection.close()


def get_completed_sessions():
    """Return the ten most recently started completed sessions."""
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    try:
        return connection.execute("""
            SELECT id, started_at, ended_at, duration_seconds
            FROM sessions
            WHERE ended_at IS NOT NULL
            ORDER BY started_at DESC, id DESC
            LIMIT 10
        """).fetchall()
    finally:
        connection.close()


def start_session():
    """Start a session and return its ID."""
    started_at = datetime.now(timezone.utc).isoformat()
    connection = sqlite3.connect(DATABASE_PATH)

    try:
        with connection:
            cursor = connection.execute(
                "INSERT INTO sessions (started_at) VALUES (?)",
                (started_at,),
            )
            return cursor.lastrowid
    finally:
        connection.close()

def stop_session(session_id):
    """Complete an active session and return its duration in seconds."""
    connection = sqlite3.connect(DATABASE_PATH)

    try:
        with connection:
            # Reserve the write transaction before reading the session.
            connection.execute("BEGIN IMMEDIATE")

            session = connection.execute(
                """
                SELECT started_at
                FROM sessions
                WHERE id = ? AND ended_at IS NULL
                """,
                (session_id,),
            ).fetchone()

            if session is None:
                raise ValueError("This session is no longer active.")

            started_at = datetime.fromisoformat(session[0])
            ended_at = datetime.now(timezone.utc)
            duration_seconds = max(
                0,
                int((ended_at - started_at).total_seconds()),
            )

            connection.execute(
                """
                UPDATE sessions
                SET ended_at = ?, duration_seconds = ?
                WHERE id = ? AND ended_at IS NULL
                """,
                (ended_at.isoformat(), duration_seconds, session_id),
            )

            return duration_seconds
    finally:
        connection.close()

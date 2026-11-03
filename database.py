import sqlite3
from pathlib import Path
from datetime import datetime, timezone

DATABASE_PATH = Path(__file__).resolve().parent / "data" / "arc.db"

def initialize_database():
    """Create session storage without removing existing records."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH)

    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        project_columns = connection.execute(
            "PRAGMA table_info(projects)"
        ).fetchall()

        column_names = [column[1] for column in project_columns]

        if "next_step" not in column_names:
            connection.execute(
                "ALTER TABLE projects ADD COLUMN next_step TEXT NOT NULL DEFAULT ''"
            )

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

            connection.execute("""
                CREATE TABLE IF NOT EXISTS codewars_profiles (
                username TEXT PRIMARY KEY,
                honor INTEGER NOT NULL CHECK (honor >= 0),
                overall_rank TEXT,
                completed_kata INTEGER NOT NULL CHECK (completed_kata >= 0),
                last_synced_at TEXT NOT NULL
                )
            """)

            connection.execute("""
                CREATE TABLE IF NOT EXISTS github_repositories (
                    project_id INTEGER PRIMARY KEY,
                    github_id INTEGER NOT NULL,
                    full_name TEXT NOT NULL,
                    html_url TEXT NOT NULL,
                    description TEXT,
                    language TEXT,
                    pushed_at TEXT,
                    last_synced_at TEXT NOT NULL,
                    FOREIGN KEY (project_id) REFERENCES projects(id)    
                )
            """)

    finally:
        connection.close()

def create_project(name):
    """Save a project and return its ID."""
    name = name.strip()

    if not name:
        raise ValueError("Enter project name.")

    created_at = datetime.now(timezone.utc).isoformat()
    connection = sqlite3.connect(DATABASE_PATH)

    try:
        with connection:
            cursor = connection.execute(
                "INSERT INTO projects (name, created_at) VALUES (?, ?)",
                (name, created_at),
            )
            return cursor.lastrowid
    finally:
        connection.close()

def get_projects():
    """Return all projects, newest first."""
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    try:
        return connection.execute("""
            SELECT id, name, created_at, next_step
            FROM projects
            ORDER BY created_at DESC, id DESC
        """).fetchall()
    finally:
        connection.close()

def update_project_next_step(project_id, next_step):
    """Save a project's next step; empty text clears the note."""
    next_step = next_step.strip()
    connection = sqlite3.connect(DATABASE_PATH)

    try:
        with connection:
            cursor = connection.execute(
                "UPDATE projects SET next_step = ? WHERE id = ?",
                (next_step, project_id)
            )

            if cursor.rowcount == 0:
                raise ValueError("Choose an existing project.")
    finally:
        connection.close()

def get_active_session():
    """Return the active session, or None when no session is running."""
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    try:
        return connection.execute("""
        SELECT
            sessions.id,
            sessions.project_id,
            sessions.started_at,
            projects.name AS project_name,
            projects.next_step
        FROM sessions
        LEFT JOIN projects ON sessions.project_id = projects.id
        WHERE sessions.ended_at IS NULL
    """).fetchone()
    finally:
        connection.close()


def get_completed_sessions():
    """Return the ten most recently started completed sessions with project names."""
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    try:
        return connection.execute("""
            SELECT
                sessions.id,
                sessions.started_at,
                sessions.ended_at,
                sessions.duration_seconds,
                projects.name AS project_name
            FROM sessions
            LEFT JOIN projects ON sessions.project_id = projects.id
            WHERE sessions.ended_at IS NOT NULL
            ORDER BY sessions.started_at DESC, sessions.id DESC
            LIMIT 10
        """).fetchall()
    finally:
        connection.close()

def start_session(project_id):
    """Start a session for an existing project and return its session ID."""
    started_at = datetime.now(timezone.utc).isoformat()
    connection = sqlite3.connect(DATABASE_PATH)

    try:
        with connection:
            # Keep project validation and session creation in one transaction.
            connection.execute("BEGIN IMMEDIATE")

            project = connection.execute(
                "SELECT id FROM projects WHERE id = ?",
                (project_id,),
            ).fetchone()

            if project is None:
                raise ValueError("Choose an existing project.")

            cursor = connection.execute(
                """
                INSERT INTO sessions (project_id, started_at)
                VALUES (?, ?)
                """,
                (project_id, started_at),
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

def save_codewars_profile(username, honor, overall_rank, completed_kata):
    """Save as sucessfully fetched profile using a UTC sync timestamp."""
    username = username.strip()

    if not username:
        raise ValueError("Enter a Codewars username.")

    if type(honor) is not int or honor < 0:
        raise ValueError("Honor must be a non-negative integer.")

    if type(completed_kata) is not int or completed_kata < 0:
        raise ValueError("Completed kata must be a non-negative integer.")

    last_synced_at = datetime.now(timezone.utc).isoformat()
    connection = sqlite3.connect(DATABASE_PATH)

    try:
        with connection:
            connection.execute(
                """
                INSERT INTO codewars_profiles (
                username, honor, overall_rank,
                completed_kata, last_synced_at
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(username) DO UPDATE SET
                    honor = excluded.honor,
                    overall_rank = excluded.overall_rank,
                    completed_kata = excluded.completed_kata,
                    last_synced_at = excluded.last_synced_at
                """,
                (username, honor, overall_rank, completed_kata, last_synced_at),
            )
    finally:
        connection.close()

def get_codewars_profile(username):
    """Return a saved Codewars profile, or None if it has not been synced."""
    username = username.strip()
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    try:
        return connection.execute(
            """
            SELECT username, honor, overall_rank,
                completed_kata, last_synced_at
            FROM codewars_profiles
            WHERE username = ?
            """,
            (username,),
        ).fetchone()
    finally:
        connection.close()

def get_last_codewars_username():
    """Return the most recently synced username, or an empty string."""
    connection = sqlite3.connect(DATABASE_PATH)

    try:
        profile = connection.execute(
            """
            SELECT username
            FROM codewars_profiles
            ORDER BY last_synced_at DESC, username ASC
            LIMIT 1
            """
        ).fetchone()

        if profile is None:
            return ""

        return profile[0]
    finally:
        connection.close()

def save_github_repository(project_id, repository):
    """Save fetched repository data with a UTC sync timestamp."""
    if not isinstance(repository, dict):
        raise ValueError("Expected GitHub repository data.")

    github_id = repository.get("id")
    full_name = repository.get("full_name")
    html_url = repository.get("html_url")

    if type(github_id) is not int or github_id <= 0:
        raise ValueError("GitHub returned an invalid repository ID.")

    if not isinstance(full_name, str) or not full_name.strip():
        raise ValueError("GitHub returned an invalid repository name.")

    if not isinstance(html_url, str) or not html_url.startswith("https://github.com/"):
        raise ValueError("GitHub returned an invalid repository URL.")

    optional_fields = ("description", "language", "pushed_at")
    for field in optional_fields:
        value = repository.get(field)
        if value is not None and not isinstance(value, str):
            raise ValueError(f"GitHub returned an unexpected {field}.")

    last_synced_at = datetime.now(timezone.utc).isoformat()
    connection = sqlite3.connect(DATABASE_PATH)

    try:
        connection.execute("PRAGMA foreign_keys = ON")

        with connection:
            connection.execute("BEGIN IMMEDIATE")

            project = connection.execute(
                "SELECT id FROM projects WHERE id = ?",
                (project_id,),
            ).fetchone()

            if project is None:
                raise ValueError("Choose an existing project.")

            connection.execute(
                """
                INSERT INTO github_repositories (
                    project_id, github_id, full_name, html_url,
                    description, language, pushed_at, last_synced_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_id) DO UPDATE SET
                    github_id = excluded.github_id,
                    full_name = excluded.full_name,
                    html_url = excluded.html_url,
                    description = excluded.description,
                    language = excluded.language,
                    pushed_at = excluded.pushed_at,
                    last_synced_at = excluded.last_synced_at
                """,
                (
                    project_id,
                    github_id,
                    full_name.strip(),
                    html_url,
                    repository.get("description"),
                    repository.get("language"),
                    repository.get("pushed_at"),
                    last_synced_at,
                ),
            )
    finally:
        connection.close()


def get_github_repository(project_id):
    """Return a project's saved repository, or None if none is saved."""
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    try:
        return connection.execute(
            """
            SELECT project_id, github_id, full_name, html_url,
                   description, language, pushed_at, last_synced_at
            FROM github_repositories
            WHERE project_id = ?
            """,
            (project_id,),
        ).fetchone()
    finally:
        connection.close()


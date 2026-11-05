import sqlite3
from datetime import datetime, timezone

from database import DATABASE_PATH


def main():
    if not DATABASE_PATH.exists():
        print("Arc's database does not exist yet.")
        return

    print("Stop Arc before continuing.")
    print("1. Clear all coding sessions, including active sessions.")
    print("2. Clear all app data.")
    print("Any other input cancels.")

    choice = input("Choose an option: ").strip()

    if choice == "1":
        confirmation_text = "CLEAR SESSIONS"
        tables = ("sessions",)
    elif choice == "2":
        confirmation_text = "CLEAR ALL DATA"
        # Delete dependent records before deleting projects.
        tables = (
            "sessions",
            "github_repositories",
            "codewars_profiles",
            "projects",
        )
    else:
        print("Cancelled.")
        return

    confirmation = input(
        f"Type {confirmation_text} to confirm: "
    ).strip()

    if confirmation != confirmation_text:
        print("Cancelled. No records were deleted.")
        return

    backup_directory = DATABASE_PATH.parent / "backups"
    backup_directory.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%S%fZ"
    )
    backup_path = backup_directory / f"arc-before-reset-{timestamp}.db"

    database_uri = DATABASE_PATH.resolve().as_uri() + "?mode=rw"
    connection = sqlite3.connect(database_uri, uri=True)

    try:
        connection.execute("PRAGMA foreign_keys = ON")

        backup_connection = sqlite3.connect(backup_path)
        try:
            connection.backup(backup_connection)
        finally:
            backup_connection.close()

        print(f"Backup saved: {backup_path}")

        with connection:
            for table_name in tables:
                # These table names come only from the fixed options above.
                cursor = connection.execute(
                    f'DELETE FROM "{table_name}"'
                )
                print(f"{table_name}: deleted {cursor.rowcount} records.")

        print("Reset complete. You can restart Arc.")

    finally:
        connection.close()

if __name__ == "__main__":
    main()

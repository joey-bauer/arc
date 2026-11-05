import sqlite3

from database import DATABASE_PATH


def main():
    if not DATABASE_PATH.exists():
        print("Arc's database does not exist yet.")
        return

    database_uri = DATABASE_PATH.resolve().as_uri() + "?mode=ro"
    connection = sqlite3.connect(database_uri, uri=True)
    connection.row_factory = sqlite3.Row

    try:
        tables = [
            row["name"]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                    AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            )
        ]

        print(f"Database: {DATABASE_PATH}")

        while True:
            print("\nTables:", ", ".join(tables))
            table_name = input(
                "Enter a table name, or q to quit: "
            ).strip()

            if table_name.lower() == "q":
                break

            if table_name not in tables:
                print("Choose a table from the list.")
                continue

            # SQL placeholders work for values, not table names.
            # Validate against discovered tables and quote the identifier.
            quoted_table = '"' + table_name.replace('"','""') + '"'

            columns = connection.execute(
                f"PRAGMA table_info({quoted_table})"
            ).fetchall()

            print("\nColumns:")
            for column in columns:
                print(f"  {column['name']}: {column['type']}")

            total = connection.execute(
                f"SELECT COUNT(*) FROM {quoted_table}"
            ).fetchone()[0]

            rows = connection.execute(
                f"SELECT * FROM {quoted_table} LIMIT ?",
                (20,),
            ).fetchall()

            print(f"\nShowing {len(rows)} of {total} records:")

            if not rows:
                print("No records.")

            for row in rows:
                print(dict(row))

    finally:
        connection.close()


if __name__ == "__main__":
    main()

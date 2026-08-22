import argparse
import sqlite3
from pathlib import Path

import psycopg2
from psycopg2 import sql


TABLES = [
    "users",
    "tickets",
    "login_events",
    "ticket_notes",
    "audit_logs",
    "password_reset_tokens",
    "ticket_attachments",
    "mfa_codes",
    "security_rate_limits",
    "article_feedback",
    "article_views",
]


def sqlite_columns(connection, table):
    rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    return [row[1] for row in rows]


def sqlite_table_exists(connection, table):
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def postgres_count(connection, table):
    with connection.cursor() as cursor:
        cursor.execute(
            sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table))
        )
        return cursor.fetchone()[0]


def copy_table(sqlite_connection, pg_connection, table):
    if not sqlite_table_exists(sqlite_connection, table):
        print(f"SKIP {table}: source table does not exist.")
        return 0

    columns = sqlite_columns(sqlite_connection, table)
    if not columns:
        return 0

    rows = sqlite_connection.execute(
        f"SELECT {', '.join(columns)} FROM {table}"
    ).fetchall()

    if not rows:
        print(f"{table}: 0 rows")
        return 0

    query = sql.SQL("INSERT INTO {} ({}) VALUES ({}) ON CONFLICT DO NOTHING").format(
        sql.Identifier(table),
        sql.SQL(", ").join(map(sql.Identifier, columns)),
        sql.SQL(", ").join(sql.Placeholder() for _ in columns),
    )

    with pg_connection.cursor() as cursor:
        for row in rows:
            cursor.execute(query, tuple(row))

    print(f"{table}: copied {len(rows)} rows")
    return len(rows)


def reset_sequence(pg_connection, table):
    with pg_connection.cursor() as cursor:
        cursor.execute(
            "SELECT pg_get_serial_sequence(%s, 'id')",
            (f"public.{table}",),
        )
        seq_row = cursor.fetchone()
        if not seq_row or not seq_row[0]:
            return

        sequence_name = seq_row[0]
        cursor.execute(
            sql.SQL("SELECT MAX(id) FROM {}").format(sql.Identifier(table))
        )
        max_id = cursor.fetchone()[0]

        if max_id is None:
            return

        cursor.execute(
            "SELECT setval(%s, %s, true)",
            (sequence_name, max_id),
        )


def main():
    parser = argparse.ArgumentParser(
        description="Safely migrate a fresh NexusDesk SQLite database into PostgreSQL."
    )
    parser.add_argument("--sqlite", default="helpdesk.db")
    parser.add_argument("--postgres-url", required=True)
    args = parser.parse_args()

    sqlite_path = Path(args.sqlite)
    if not sqlite_path.exists():
        raise SystemExit(f"SQLite database not found: {sqlite_path}")

    sqlite_connection = sqlite3.connect(sqlite_path)
    sqlite_connection.row_factory = sqlite3.Row
    pg_connection = psycopg2.connect(args.postgres_url)

    try:
        nonempty = {}
        for table in TABLES:
            try:
                count = postgres_count(pg_connection, table)
            except Exception as exc:
                pg_connection.rollback()
                raise SystemExit(
                    f"Target PostgreSQL schema is not ready for table {table}: {exc}"
                )
            if count:
                nonempty[table] = count

        if nonempty:
            raise SystemExit(
                "Migration aborted: target PostgreSQL database is not empty. "
                f"Existing rows: {nonempty}. Use a fresh target database."
            )

        total = 0
        for table in TABLES:
            total += copy_table(sqlite_connection, pg_connection, table)

        for table in TABLES:
            reset_sequence(pg_connection, table)

        pg_connection.commit()
        print(f"MIGRATION COMPLETE: {total} total rows copied.")
    except Exception:
        pg_connection.rollback()
        raise
    finally:
        sqlite_connection.close()
        pg_connection.close()


if __name__ == "__main__":
    main()

import argparse
import sqlite3

import psycopg2
import psycopg2.extras


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


def sqlite_table_exists(connection, table):
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def sqlite_count(connection, table):
    if not sqlite_table_exists(connection, table):
        return 0
    return connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def pg_count(connection, table):
    with connection.cursor() as cursor:
        cursor.execute(f'SELECT COUNT(*) AS count FROM "{table}"')
        return cursor.fetchone()["count"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sqlite", default="helpdesk.db")
    parser.add_argument("--postgres-url", required=True)
    args = parser.parse_args()

    sqlite_connection = sqlite3.connect(args.sqlite)
    pg_connection = psycopg2.connect(
        args.postgres_url,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )

    mismatches = []
    print("TABLE COUNT COMPARISON")
    print("-" * 64)

    try:
        for table in TABLES:
            source = sqlite_count(sqlite_connection, table)
            target = pg_count(pg_connection, table)
            status = "PASS" if source == target else "MISMATCH"
            print(f"{table:24} SQLite={source:<6} PostgreSQL={target:<6} {status}")
            if source != target:
                mismatches.append((table, source, target))

        # Validate several important relational invariants after migration.
        with pg_connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) AS count
                FROM ticket_notes n
                LEFT JOIN tickets t ON t.id = n.ticket_id
                WHERE t.id IS NULL
            """)
            orphan_notes = cursor.fetchone()["count"]

            cursor.execute("""
                SELECT COUNT(*) AS count
                FROM ticket_attachments a
                LEFT JOIN tickets t ON t.id = a.ticket_id
                WHERE t.id IS NULL
            """)
            orphan_attachments = cursor.fetchone()["count"]

            cursor.execute("""
                SELECT COUNT(*) AS count
                FROM password_reset_tokens p
                LEFT JOIN users u ON u.id = p.user_id
                WHERE u.id IS NULL
            """)
            orphan_tokens = cursor.fetchone()["count"]

        print("-" * 64)
        print("Orphan ticket notes:", orphan_notes)
        print("Orphan attachments:", orphan_attachments)
        print("Orphan password tokens:", orphan_tokens)

        if mismatches:
            raise SystemExit(f"FAIL: row-count mismatches: {mismatches}")

        if any([orphan_notes, orphan_attachments, orphan_tokens]):
            raise SystemExit("FAIL: relational integrity check found orphan records.")

        print("POSTGRESQL MIGRATION VERIFICATION: PASS")
    finally:
        sqlite_connection.close()
        pg_connection.close()


if __name__ == "__main__":
    main()

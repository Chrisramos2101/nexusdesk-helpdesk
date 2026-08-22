import sqlite3
import psycopg2
import psycopg2.extras
from database.config import DATABASE_URL


SQLITE_DB = "helpdesk.db"


def migrate_users():
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cursor = sqlite_conn.cursor()

    pg_conn = psycopg2.connect(
        DATABASE_URL,
        cursor_factory=psycopg2.extras.RealDictCursor
    )
    pg_cursor = pg_conn.cursor()

    sqlite_cursor.execute("""
        SELECT
            full_name,
            username,
            email,
            department,
            password_hash,
            role,
            failed_attempts,
            locked_until,
            last_login,
            last_logout
        FROM users
    """)

    users = sqlite_cursor.fetchall()

    for user in users:
        pg_cursor.execute("""
            INSERT INTO users
            (
                full_name,
                username,
                email,
                department,
                password_hash,
                role,
                failed_attempts,
                locked_until,
                last_login,
                last_logout
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (username)
            DO UPDATE SET
                full_name = EXCLUDED.full_name,
                email = EXCLUDED.email,
                department = EXCLUDED.department,
                password_hash = EXCLUDED.password_hash,
                role = EXCLUDED.role,
                failed_attempts = 0,
                locked_until = '',
                last_login = EXCLUDED.last_login,
                last_logout = EXCLUDED.last_logout
        """, (
            user["full_name"],
            user["username"],
            user["email"],
            user["department"],
            user["password_hash"],
            user["role"],
            user["failed_attempts"],
            user["locked_until"],
            user["last_login"],
            user["last_logout"]
        ))

    pg_conn.commit()

    sqlite_conn.close()
    pg_conn.close()

    print(f"Migrated {len(users)} users from SQLite to PostgreSQL.")


if __name__ == "__main__":
    migrate_users()
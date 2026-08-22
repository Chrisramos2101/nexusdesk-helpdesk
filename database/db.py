import sqlite3

from database.config import DATABASE_URL


def get_db_connection():
    if DATABASE_URL.startswith("postgresql://"):
        import psycopg2
        import psycopg2.extras

        return psycopg2.connect(
            DATABASE_URL,
            cursor_factory=psycopg2.extras.RealDictCursor,
        )

    connection = sqlite3.connect(DATABASE_URL)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection

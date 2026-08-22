import sqlite3

from database.db import get_db_connection


def init_db():
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            issue TEXT NOT NULL,
            priority TEXT NOT NULL,
            status TEXT NOT NULL,
            submitted_at TEXT NOT NULL,
            closed_at TEXT,
            assigned_to TEXT,
            completed_by TEXT,
            notes TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    for column in [
        "full_name TEXT DEFAULT ''",
        "department TEXT DEFAULT ''",
        "email TEXT DEFAULT ''",
        "failed_attempts INTEGER DEFAULT 0",
        "locked_until TEXT DEFAULT ''",
        "last_login TEXT DEFAULT ''",
        "last_logout TEXT DEFAULT ''",
        "mfa_enabled INTEGER DEFAULT 0",
        "mfa_secret TEXT DEFAULT ''"
    ]:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {column}")
        except sqlite3.OperationalError:
            pass

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS login_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            event_type TEXT NOT NULL,
            event_time TEXT NOT NULL
        )
    """)

    for column in [
        "assigned_to TEXT DEFAULT 'Unassigned'",
        "completed_by TEXT DEFAULT ''",
        "category TEXT DEFAULT 'Other'",
        "sla_due_at TEXT DEFAULT ''",
        "submitted_by TEXT DEFAULT ''",
        "resolution_time TEXT DEFAULT ''",
        "sla_met TEXT DEFAULT ''"
    ]:
        try:
            cursor.execute(f"ALTER TABLE tickets ADD COLUMN {column}")
        except sqlite3.OperationalError:
            pass

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ticket_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER NOT NULL,
            note TEXT NOT NULL,
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor TEXT NOT NULL,
            action TEXT NOT NULL,
            target_type TEXT NOT NULL,
            target_id TEXT,
            details TEXT,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            expires_at TEXT NOT NULL,
            used INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ticket_attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER NOT NULL,
            original_filename TEXT NOT NULL,
            stored_filename TEXT NOT NULL,
            uploaded_by TEXT NOT NULL,
            uploaded_at TEXT NOT NULL,
            FOREIGN KEY(ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mfa_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            code TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            used INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            attempts INTEGER DEFAULT 0
        )
    """)

    try:
        cursor.execute("ALTER TABLE mfa_codes ADD COLUMN attempts INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS security_rate_limits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bucket_key TEXT NOT NULL,
            action TEXT NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            window_start TEXT NOT NULL,
            UNIQUE(bucket_key, action)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS article_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_slug TEXT NOT NULL,
            username TEXT NOT NULL,
            was_helpful TEXT NOT NULL,
            feedback TEXT,
            created_at TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS article_views (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_slug TEXT NOT NULL,
            username TEXT NOT NULL,
            viewed_at TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()
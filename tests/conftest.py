import os
import sqlite3
import tempfile
from pathlib import Path

import pytest
from werkzeug.security import generate_password_hash


TEST_DB = Path(tempfile.gettempdir()) / "nexusdesk_pytest.db"
if TEST_DB.exists():
    TEST_DB.unlink()

# These must be set before importing app/database modules because the database
# configuration is resolved at module import time.
os.environ["DATABASE_URL"] = str(TEST_DB)
os.environ["SECRET_KEY"] = "nexusdesk-test-secret-key"
os.environ["FLASK_ENV"] = "testing"
os.environ["MAIL_SERVER"] = "localhost"
os.environ["MAIL_PORT"] = "25"
os.environ["MAIL_USERNAME"] = "test@example.com"
os.environ["MAIL_PASSWORD"] = "test-password"
os.environ["MAIL_DEFAULT_SENDER"] = "test@example.com"

from app import app as flask_app  # noqa: E402
from database.schema import init_db  # noqa: E402


TABLES_TO_CLEAR = [
    "security_rate_limits",
    "mfa_codes",
    "article_feedback",
    "article_views",
    "ticket_attachments",
    "ticket_notes",
    "password_reset_tokens",
    "audit_logs",
    "login_events",
    "tickets",
    "users",
]


def _seed_user(connection, username, role, email):
    connection.execute(
        """
        INSERT INTO users
        (full_name, username, email, department, password_hash, role,
         failed_attempts, locked_until, last_login, last_logout)
        VALUES (?, ?, ?, ?, ?, ?, 0, '', '', '')
        """,
        (
            username.title(),
            username,
            email,
            "IT" if role == "admin" else "Finance",
            generate_password_hash("Password1!"),
            role,
        ),
    )


@pytest.fixture(autouse=True)
def clean_database(tmp_path):
    flask_app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        MAIL_SUPPRESS_SEND=True,
        UPLOAD_FOLDER=str(tmp_path / "uploads"),
    )

    with flask_app.app_context():
        init_db()

    connection = sqlite3.connect(TEST_DB)
    connection.execute("PRAGMA foreign_keys = ON")
    for table in TABLES_TO_CLEAR:
        connection.execute(f"DELETE FROM {table}")
    _seed_user(connection, "employee", "employee", "employee@example.com")
    _seed_user(connection, "other", "employee", "other@example.com")
    _seed_user(connection, "admin", "admin", "admin@example.com")
    connection.commit()
    connection.close()
    yield


@pytest.fixture
def app():
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db():
    connection = sqlite3.connect(TEST_DB)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture
def login_as():
    def _login(client, username="employee", role="employee"):
        with client.session_transaction() as session:
            session["username"] = username
            session["role"] = role
            session.permanent = True
    return _login


@pytest.fixture
def create_ticket(db):
    def _create(submitted_by="employee", issue="Test issue"):
        cursor = db.execute(
            """
            INSERT INTO tickets
            (name, department, issue, priority, category, status,
             submitted_at, closed_at, assigned_to, completed_by, notes,
             sla_due_at, submitted_by, resolution_time, sla_met)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "Test User",
                "Finance",
                issue,
                "Medium",
                "Software",
                "Open",
                "08/22/2026 10:00 AM",
                "",
                "Unassigned",
                "",
                "",
                "08/22/2026 06:00 PM",
                submitted_by,
                "",
                "",
            ),
        )
        db.commit()
        return cursor.lastrowid
    return _create

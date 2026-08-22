import sqlite3

from services import password_reset_service


def test_get_user_by_email_is_case_insensitive(monkeypatch):
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            email TEXT NOT NULL
        )
    """)
    connection.execute(
        "INSERT INTO users (username, email) VALUES (?, ?)",
        ("portfolio_admin", "Christian.Example@iCloud.com"),
    )
    connection.commit()

    monkeypatch.setattr(
        password_reset_service,
        "get_db_connection",
        lambda: connection,
    )
    monkeypatch.setattr(
        password_reset_service,
        "db_placeholder",
        lambda: "?",
    )

    user = password_reset_service.get_user_by_email(
        "christian.example@icloud.com"
    )

    assert user is not None
    assert user["username"] == "portfolio_admin"


def test_get_user_by_email_ignores_surrounding_whitespace(monkeypatch):
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            email TEXT NOT NULL
        )
    """)
    connection.execute(
        "INSERT INTO users (username, email) VALUES (?, ?)",
        ("portfolio_admin", "  MixedCase@Example.com  "),
    )
    connection.commit()

    monkeypatch.setattr(
        password_reset_service,
        "get_db_connection",
        lambda: connection,
    )
    monkeypatch.setattr(
        password_reset_service,
        "db_placeholder",
        lambda: "?",
    )

    user = password_reset_service.get_user_by_email(
        "mixedcase@example.com"
    )

    assert user is not None
    assert user["username"] == "portfolio_admin"

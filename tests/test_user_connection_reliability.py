
import sqlite3

import pytest
from unittest.mock import patch
from werkzeug.security import generate_password_hash

from services.user_service import create_user_account


def create_test_user(username):
    create_user_account(
        full_name="Reliability Test",
        username=username,
        email=f"{username}@example.com",
        department="IT",
        password_hash=generate_password_hash(
            "SecurePassword123!"
        ),
        role="employee",
    )


def test_successful_user_creation_is_committed(db):
    create_test_user("reliable_user")

    user = db.execute(
        """
        SELECT username
        FROM users
        WHERE username = ?
        """,
        ("reliable_user",),
    ).fetchone()

    assert user is not None
    assert user["username"] == "reliable_user"


def test_duplicate_username_does_not_lock_database(db):
    create_test_user("duplicate_test")

    with pytest.raises(sqlite3.IntegrityError):
        create_test_user("duplicate_test")

    # This must succeed after the failed insert.
    create_test_user("after_duplicate")

    users = db.execute(
        """
        SELECT username
        FROM users
        WHERE username IN (?, ?)
        ORDER BY username
        """,
        ("duplicate_test", "after_duplicate"),
    ).fetchall()

    assert len(users) == 2


def test_connection_closes_after_failed_insert():
    class FakeCursor:
        def execute(self, query, params):
            raise sqlite3.IntegrityError(
                "Simulated duplicate username"
            )

    class FakeConnection:
        def __init__(self):
            self.rolled_back = False
            self.closed = False
            self.committed = False

        def cursor(self):
            return FakeCursor()

        def commit(self):
            self.committed = True

        def rollback(self):
            self.rolled_back = True

        def close(self):
            self.closed = True

    fake_connection = FakeConnection()

    with patch(
        "services.user_service.get_db_connection",
        return_value=fake_connection,
    ):
        with pytest.raises(sqlite3.IntegrityError):
            create_test_user("failing_user")

    assert fake_connection.rolled_back is True
    assert fake_connection.closed is True
    assert fake_connection.committed is False


def test_connection_closes_after_success():
    class FakeCursor:
        def execute(self, query, params):
            pass

    class FakeConnection:
        def __init__(self):
            self.committed = False
            self.closed = False
            self.rolled_back = False

        def cursor(self):
            return FakeCursor()

        def commit(self):
            self.committed = True

        def rollback(self):
            self.rolled_back = True

        def close(self):
            self.closed = True

    fake_connection = FakeConnection()

    with patch(
        "services.user_service.get_db_connection",
        return_value=fake_connection,
    ):
        create_test_user("successful_user")

    assert fake_connection.committed is True
    assert fake_connection.closed is True
    assert fake_connection.rolled_back is False


def test_duplicate_account_route_recovers(
    client, login_as, db
):
    login_as(client, "admin", "admin")

    response = client.post(
        "/create_user",
        data={
            "full_name": "Duplicate Employee",
            "username": "employee",
            "email": "duplicate@example.com",
            "department": "IT",
            "password": "SecurePassword123!",
            "role": "employee",
        },
    )

    assert response.status_code == 200
    assert b"Username already exists." in response.data

    # Verify that a later account creation still works.
    response = client.post(
        "/create_user",
        data={
            "full_name": "Recovery Employee",
            "username": "recovered_user",
            "email": "recovered@example.com",
            "department": "IT",
            "password": "SecurePassword123!",
            "role": "employee",
        },
    )

    assert response.status_code == 200

    user = db.execute(
        """
        SELECT username
        FROM users
        WHERE username = ?
        """,
        ("recovered_user",),
    ).fetchone()

    assert user is not None

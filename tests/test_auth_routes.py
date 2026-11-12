
import pytest
from werkzeug.security import check_password_hash

from routes.auth import mask_email


@pytest.mark.parametrize(
    "path, method",
    [
        ("/profile", "GET"),
        ("/change_password", "GET"),
        ("/update_profile", "POST"),
    ],
)
def test_anonymous_user_cannot_access_account_routes(
    client, path, method
):
    response = client.open(path, method=method)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


@pytest.mark.parametrize(
    "path",
    ["/mfa_verify", "/mfa_resend"],
)
def test_mfa_requires_pending_login(client, path):
    if path == "/mfa_resend":
        response = client.post(path)
    else:
        response = client.get(path)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_logout_clears_authenticated_session(
    client, login_as, db
):
    login_as(client, "employee", "employee")

    response = client.get("/logout")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")

    with client.session_transaction() as session:
        assert "username" not in session
        assert "role" not in session

    event = db.execute(
        """
        SELECT event_type
        FROM login_events
        WHERE username = ?
        ORDER BY id DESC LIMIT 1
        """,
        ("employee",),
    ).fetchone()

    assert event is not None
    assert event["event_type"] == "logout"


def test_password_mismatch_does_not_change_password(
    client, login_as, db
):
    login_as(client, "employee", "employee")

    response = client.post(
        "/change_password",
        data={
            "current_password": "Password1!",
            "new_password": "NewPassword123!",
            "confirm_password": "DifferentPassword123!",
        },
    )

    assert response.status_code == 200

    user = db.execute(
        """
        SELECT password_hash
        FROM users
        WHERE username = ?
        """,
        ("employee",),
    ).fetchone()

    assert check_password_hash(
        user["password_hash"], "Password1!"
    )


def test_incorrect_current_password_is_rejected(
    client, login_as, db
):
    login_as(client, "employee", "employee")

    response = client.post(
        "/change_password",
        data={
            "current_password": "IncorrectPassword1!",
            "new_password": "NewPassword123!",
            "confirm_password": "NewPassword123!",
        },
    )

    assert response.status_code == 200

    user = db.execute(
        "SELECT password_hash FROM users WHERE username = ?",
        ("employee",),
    ).fetchone()

    assert check_password_hash(
        user["password_hash"], "Password1!"
    )


def test_valid_password_change_updates_hash(
    client, login_as, db
):
    login_as(client, "employee", "employee")

    response = client.post(
        "/change_password",
        data={
            "current_password": "Password1!",
            "new_password": "NewPassword123!",
            "confirm_password": "NewPassword123!",
        },
    )

    assert response.status_code == 200

    user = db.execute(
        "SELECT password_hash FROM users WHERE username = ?",
        ("employee",),
    ).fetchone()

    assert check_password_hash(
        user["password_hash"], "NewPassword123!"
    )

    assert not check_password_hash(
        user["password_hash"], "Password1!"
    )


def test_profile_update_saves_user_information(
    client, login_as, db
):
    login_as(client, "employee", "employee")

    response = client.post(
        "/update_profile",
        data={
            "full_name": "Updated Employee",
            "email": "employee@example.com",
            "department": "IT",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith(
        "/profile?updated=1"
    )

    user = db.execute(
        """
        SELECT full_name, email, department
        FROM users
        WHERE username = ?
        """,
        ("employee",),
    ).fetchone()

    assert user["full_name"] == "Updated Employee"
    assert user["email"] == "employee@example.com"
    assert user["department"] == "IT"


from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from flask import session

from routes.auth import (
    has_valid_mfa_trust,
    mask_email,
)


@pytest.mark.parametrize(
    "email, expected",
    [
        ("", "your account email"),
        ("invalid", "your account email"),
        ("a@example.com", "•@example.com"),
    ],
)
def test_email_masking(email, expected):
    assert mask_email(email) == expected


def test_valid_mfa_trust_is_accepted(app):
    with app.test_request_context("/"):
        session["mfa_trusted_username"] = "employee"
        session["mfa_trusted_until"] = (
            datetime.now() + timedelta(minutes=10)
        ).isoformat()

        assert has_valid_mfa_trust("employee") is True


def test_expired_mfa_trust_is_rejected(app):
    with app.test_request_context("/"):
        session["mfa_trusted_username"] = "employee"
        session["mfa_trusted_until"] = (
            datetime.now() - timedelta(minutes=1)
        ).isoformat()

        assert has_valid_mfa_trust("employee") is False


def test_mfa_trust_for_different_user_is_rejected(app):
    with app.test_request_context("/"):
        session["mfa_trusted_username"] = "other"
        session["mfa_trusted_until"] = (
            datetime.now() + timedelta(minutes=10)
        ).isoformat()

        assert has_valid_mfa_trust("employee") is False


def test_invalid_mfa_trust_timestamp_is_rejected(app):
    with app.test_request_context("/"):
        session["mfa_trusted_username"] = "employee"
        session["mfa_trusted_until"] = "invalid-date"

        assert has_valid_mfa_trust("employee") is False


def test_logout_clears_authenticated_session(
    client, login_as, db
):
    login_as(client, "employee", "employee")

    response = client.get("/logout")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")

    with client.session_transaction() as current_session:
        assert "username" not in current_session
        assert "role" not in current_session

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


def test_anonymous_user_cannot_view_profile(client):
    response = client.get("/profile")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_employee_can_view_profile(
    client, login_as
):
    login_as(client, "employee", "employee")

    with patch(
        "routes.auth.render_template",
        return_value="Profile rendered",
    ) as mock_render:
        response = client.get("/profile")

    assert response.status_code == 200
    assert mock_render.call_args.kwargs["user"][
        "username"
    ] == "employee"

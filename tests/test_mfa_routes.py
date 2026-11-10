
from unittest.mock import patch

from services.mfa_service import (
    generate_mfa_code,
    verify_mfa_code,
)


def start_pending_login(client):
    """Complete password step, but not MFA verification."""
    with patch("routes.auth.send_email", return_value=True):
        response = client.post(
            "/login",
            data={
                "username": "employee",
                "password": "Password1!",
            },
        )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/mfa_verify")


def latest_code(db):
    return db.execute(
        """
        SELECT *
        FROM mfa_codes
        WHERE username = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        ("employee",),
    ).fetchone()


def test_mfa_resend_invalidates_old_code(client, db):
    start_pending_login(client)

    original = latest_code(db)

    with patch("routes.auth.send_email", return_value=True):
        response = client.post("/mfa_resend")

    assert response.status_code == 200

    old_record = db.execute(
        "SELECT used FROM mfa_codes WHERE id = ?",
        (original["id"],),
    ).fetchone()

    new_record = latest_code(db)

    assert old_record["used"] == 1
    assert new_record["id"] != original["id"]
    assert new_record["used"] == 0


def test_mfa_resend_email_failure_invalidates_codes(
    client, db
):
    start_pending_login(client)

    with patch("routes.auth.send_email", return_value=False):
        response = client.post("/mfa_resend")

    assert response.status_code == 503

    active_codes = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM mfa_codes
        WHERE username = ? AND used = 0
        """,
        ("employee",),
    ).fetchone()["count"]

    assert active_codes == 0


def test_mfa_resend_is_rate_limited(client, db):
    start_pending_login(client)

    with patch(
        "routes.auth.send_email", return_value=True
    ) as mock_email:
        responses = [
            client.post("/mfa_resend")
            for _ in range(4)
        ]

    assert [r.status_code for r in responses] == [
        200, 200, 200, 429
    ]

    assert mock_email.call_count == 3


def test_mfa_resend_rejects_missing_user(client):
    with client.session_transaction() as session:
        session["pending_mfa_username"] = "missing_user"
        session["pending_mfa_role"] = "employee"

    response = client.post("/mfa_resend")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")

    with client.session_transaction() as session:
        assert "pending_mfa_username" not in session
        assert "username" not in session


def test_invalid_mfa_code_does_not_authenticate(client, db):
    start_pending_login(client)

    response = client.post(
        "/mfa_verify",
        data={"mfa_code": "not-a-valid-code"},
    )

    assert response.status_code == 200

    with client.session_transaction() as session:
        assert "username" not in session
        assert session["pending_mfa_username"] == "employee"

    event = db.execute(
        """
        SELECT action
        FROM audit_logs
        WHERE actor = ? AND action = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        ("employee", "MFA_FAILED"),
    ).fetchone()

    assert event is not None


def test_expired_mfa_code_cannot_authenticate(client, db):
    start_pending_login(client)

    record = latest_code(db)

    db.execute(
        """
        UPDATE mfa_codes
        SET expires_at = ?
        WHERE id = ?
        """,
        ("2020-01-01 00:00:00", record["id"]),
    )
    db.commit()

    response = client.post(
        "/mfa_verify",
        data={"mfa_code": record["code"]},
    )

    assert response.status_code == 200

    with client.session_transaction() as session:
        assert "username" not in session

    updated = db.execute(
        "SELECT used FROM mfa_codes WHERE id = ?",
        (record["id"],),
    ).fetchone()

    assert updated["used"] == 1


def test_successful_mfa_creates_trusted_session(
    client, db
):
    start_pending_login(client)

    record = latest_code(db)

    response = client.post(
        "/mfa_verify",
        data={"mfa_code": record["code"]},
    )

    assert response.status_code == 302

    with client.session_transaction() as session:
        assert session["username"] == "employee"
        assert session["role"] == "employee"
        assert session["mfa_trusted_username"] == "employee"
        assert session.get("mfa_trusted_until")
        assert "pending_mfa_username" not in session

    assert verify_mfa_code(
        "employee", record["code"]
    ) is False

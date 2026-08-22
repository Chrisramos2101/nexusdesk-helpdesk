from unittest.mock import patch


def test_login_page_loads(client):
    assert client.get("/login").status_code == 200


def test_valid_password_starts_mfa(client, db):
    with patch("routes.auth.send_email", return_value=True):
        response = client.post(
            "/login",
            data={"username": "employee", "password": "Password1!"},
        )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/mfa_verify")

    record = db.execute(
        "SELECT * FROM mfa_codes WHERE username = ? ORDER BY id DESC LIMIT 1",
        ("employee",),
    ).fetchone()
    assert record is not None
    assert len(record["code"]) == 6


def test_mfa_completion_creates_authenticated_session(client, db):
    with patch("routes.auth.send_email", return_value=True):
        client.post(
            "/login",
            data={"username": "employee", "password": "Password1!"},
        )

    code = db.execute(
        "SELECT code FROM mfa_codes WHERE username = ? ORDER BY id DESC LIMIT 1",
        ("employee",),
    ).fetchone()["code"]

    response = client.post("/mfa_verify", data={"mfa_code": code})
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")

    with client.session_transaction() as session:
        assert session["username"] == "employee"
        assert session["role"] == "employee"
        assert "pending_mfa_username" not in session


def test_invalid_password_increments_failed_attempts(client, db):
    response = client.post(
        "/login",
        data={"username": "employee", "password": "wrong"},
    )
    assert response.status_code == 200

    user = db.execute(
        "SELECT failed_attempts FROM users WHERE username = ?",
        ("employee",),
    ).fetchone()
    assert user["failed_attempts"] == 1


def test_five_invalid_passwords_lock_account(client, db):
    for number in range(5):
        response = client.post(
            "/login",
            data={"username": "employee", "password": "wrong"},
            environ_overrides={"REMOTE_ADDR": f"10.0.0.{number + 1}"},
        )
        assert response.status_code == 200

    user = db.execute(
        "SELECT failed_attempts, locked_until FROM users WHERE username = ?",
        ("employee",),
    ).fetchone()
    assert user["failed_attempts"] == 5
    assert user["locked_until"]


def test_email_failure_does_not_return_500(client, db):
    with patch("routes.auth.send_email", return_value=False):
        response = client.post(
            "/login",
            data={"username": "employee", "password": "Password1!"},
        )

    assert response.status_code == 503
    active_codes = db.execute(
        "SELECT COUNT(*) AS count FROM mfa_codes WHERE username = ? AND used = 0",
        ("employee",),
    ).fetchone()["count"]
    assert active_codes == 0

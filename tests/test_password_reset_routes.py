
from unittest.mock import patch

import pytest
from werkzeug.security import check_password_hash

from services.password_reset_service import (
    create_password_reset_token,
)


def make_reset_token(db):
    user = db.execute(
        "SELECT id FROM users WHERE username = ?",
        ("employee",),
    ).fetchone()
    return create_password_reset_token(user["id"])


@pytest.mark.parametrize(
    "path",
    ["/forgot_password", "/reset_password/invalid-token"],
)
def test_password_reset_pages_load(client, path):
    response = client.get(path)
    assert response.status_code == 200


def test_unknown_email_does_not_generate_token(client, db):
    with patch("routes.auth.send_email") as mock_email:
        response = client.post(
            "/forgot_password",
            data={"email": "unknown@example.com"},
        )

    assert response.status_code == 200
    mock_email.assert_not_called()

    count = db.execute(
        "SELECT COUNT(*) FROM password_reset_tokens"
    ).fetchone()[0]

    assert count == 0


def test_existing_user_receives_reset_request(client, db):
    with patch(
        "routes.auth.send_email", return_value=True
    ) as mock_email:
        response = client.post(
            "/forgot_password",
            data={"email": "employee@example.com"},
        )

    assert response.status_code == 200
    mock_email.assert_called_once()

    token = db.execute(
        "SELECT token FROM password_reset_tokens"
    ).fetchone()

    assert token is not None

    message = mock_email.call_args
    assert token["token"] in message.args[2]


def test_invalid_reset_token_cannot_change_password(
    client, db
):
    response = client.post(
        "/reset_password/invalid-token",
        data={
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


def test_mismatched_reset_passwords_are_rejected(
    client, db
):
    token = make_reset_token(db)

    response = client.post(
        f"/reset_password/{token}",
        data={
            "new_password": "NewPassword123!",
            "confirm_password": "DifferentPassword123!",
        },
    )

    assert response.status_code == 200

    record = db.execute(
        "SELECT used FROM password_reset_tokens WHERE token = ?",
        (token,),
    ).fetchone()

    assert record["used"] == 0


def test_weak_reset_password_is_rejected(client, db):
    token = make_reset_token(db)

    response = client.post(
        f"/reset_password/{token}",
        data={
            "new_password": "weak",
            "confirm_password": "weak",
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


def test_valid_reset_changes_password_and_uses_token(
    client, db
):
    token = make_reset_token(db)

    response = client.post(
        f"/reset_password/{token}",
        data={
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

    record = db.execute(
        "SELECT used FROM password_reset_tokens WHERE token = ?",
        (token,),
    ).fetchone()

    assert record["used"] == 1


def test_used_reset_token_cannot_be_reused(client, db):
    token = make_reset_token(db)

    client.post(
        f"/reset_password/{token}",
        data={
            "new_password": "NewPassword123!",
            "confirm_password": "NewPassword123!",
        },
    )

    response = client.post(
        f"/reset_password/{token}",
        data={
            "new_password": "AnotherPassword123!",
            "confirm_password": "AnotherPassword123!",
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
        user["password_hash"], "AnotherPassword123!"
    )

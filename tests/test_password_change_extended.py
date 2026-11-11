
from unittest.mock import patch

import pytest
from werkzeug.security import check_password_hash


def submit_change(client, data):
    with patch(
        "routes.auth.render_template",
        return_value="Password form rendered",
    ) as mock_render:
        response = client.post(
            "/change_password",
            data=data,
        )

    return response, mock_render.call_args.kwargs


def get_password_hash(db):
    return db.execute(
        """
        SELECT password_hash
        FROM users
        WHERE username = 'employee'
        """
    ).fetchone()["password_hash"]


def test_anonymous_password_change_is_rejected(client):
    response = client.post(
        "/change_password",
        data={
            "current_password": "Password1!",
            "new_password": "NewPassword123!",
            "confirm_password": "NewPassword123!",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


@pytest.mark.parametrize(
    "new_password, confirmation, expected_error",
    [
        (
            "NewPassword123!",
            "DifferentPassword123!",
            "do not match",
        ),
        (
            "short",
            "short",
            "at least 8 characters",
        ),
        (
            "lowercase123!",
            "lowercase123!",
            "uppercase",
        ),
        (
            "NoNumbersHere!",
            "NoNumbersHere!",
            "number",
        ),
    ],
)
def test_invalid_new_password_does_not_change_hash(
    client, login_as, db,
    new_password, confirmation, expected_error
):
    login_as(client, "employee", "employee")

    original_hash = get_password_hash(db)

    response, context = submit_change(
        client,
        {
            "current_password": "Password1!",
            "new_password": new_password,
            "confirm_password": confirmation,
        },
    )

    assert response.status_code == 200
    assert expected_error in context["error"]
    assert get_password_hash(db) == original_hash


def test_wrong_current_password_is_rejected(
    client, login_as, db
):
    login_as(client, "employee", "employee")

    original_hash = get_password_hash(db)

    response, context = submit_change(
        client,
        {
            "current_password": "WrongPassword123!",
            "new_password": "NewPassword123!",
            "confirm_password": "NewPassword123!",
        },
    )

    assert response.status_code == 200
    assert context["error"] == (
        "Current password is incorrect."
    )
    assert get_password_hash(db) == original_hash


def test_valid_password_change_updates_hash(
    client, login_as, db
):
    login_as(client, "employee", "employee")

    original_hash = get_password_hash(db)

    response, context = submit_change(
        client,
        {
            "current_password": "Password1!",
            "new_password": "NewPassword123!",
            "confirm_password": "NewPassword123!",
        },
    )

    assert response.status_code == 200
    assert context["error"] == ""
    assert context["message"] == (
        "Password changed successfully."
    )

    updated_hash = get_password_hash(db)

    assert updated_hash != original_hash
    assert check_password_hash(
        updated_hash, "NewPassword123!"
    )
    assert not check_password_hash(
        updated_hash, "Password1!"
    )

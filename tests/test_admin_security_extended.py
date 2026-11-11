
from unittest.mock import patch

import pytest


def user_form(**overrides):
    data = {
        "full_name": "Test Employee",
        "email": "test@example.com",
        "department": "Finance",
        "role": "employee",
    }
    data.update(overrides)
    return data


def create_form(**overrides):
    data = user_form(
        username="new_test_user",
        password="SecurePassword1!",
    )
    data.update(overrides)
    return data


def test_admin_cannot_delete_own_account(
    client, login_as, db
):
    admin_id = db.execute(
        "SELECT id FROM users WHERE username = 'admin'"
    ).fetchone()["id"]

    login_as(client, "admin", "admin")

    response = client.post(
        f"/delete_user/{admin_id}"
    )

    assert response.status_code == 302

    user = db.execute(
        "SELECT id FROM users WHERE id = ?",
        (admin_id,),
    ).fetchone()

    assert user is not None


@pytest.mark.parametrize(
    "field, invalid_value",
    [
        ("full_name", "   "),
        ("email", "   "),
        ("department", "Unknown"),
        ("role", "superadmin"),
    ],
)
def test_invalid_admin_user_updates_are_rejected(
    client, login_as, db, field, invalid_value
):
    user_id = db.execute(
        "SELECT id FROM users WHERE username = 'employee'"
    ).fetchone()["id"]

    login_as(client, "admin", "admin")

    response = client.post(
        f"/edit_user/{user_id}",
        data=user_form(**{field: invalid_value}),
    )

    assert response.status_code == 302

    user = db.execute(
        """
        SELECT full_name, email, department, role
        FROM users WHERE id = ?
        """,
        (user_id,),
    ).fetchone()

    assert user["full_name"] == "Employee"
    assert user["email"] == "employee@example.com"
    assert user["department"] == "Finance"
    assert user["role"] == "employee"


@pytest.mark.parametrize(
    "field, invalid_value, expected_message",
    [
        ("full_name", "", "All fields are required"),
        ("department", "Unknown", "Invalid department"),
        ("role", "superadmin", "Invalid role"),
        ("password", "weak", "at least 8 characters"),
    ],
)
def test_admin_create_user_rejects_invalid_values(
    client, login_as, db,
    field, invalid_value, expected_message
):
    login_as(client, "admin", "admin")

    with patch(
        "routes.admin.render_template",
        return_value="Form rendered",
    ) as mock_render:
        response = client.post(
            "/create_user",
            data=create_form(**{field: invalid_value}),
        )

    assert response.status_code == 200

    message = mock_render.call_args.kwargs["message"]
    assert expected_message in message

    count = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM users WHERE username = 'new_test_user'
        """
    ).fetchone()["count"]

    assert count == 0


def test_duplicate_username_is_rejected(
    client, login_as, db
):
    import sqlite3
    from unittest.mock import patch

    login_as(client, "admin", "admin")

    # Simulate a duplicate-username database error.
    # This tests the route's error handling without
    # leaving a failed database transaction open.
    with (
        patch(
            "routes.admin.create_user_account",
            side_effect=sqlite3.IntegrityError(
                "UNIQUE constraint failed: users.username"
            ),
        ),
        patch(
            "routes.admin.render_template",
            return_value="Form rendered",
        ) as mock_render,
    ):
        response = client.post(
            "/create_user",
            data=create_form(
                username="employee",
                email="duplicate@example.com",
            ),
        )

    assert response.status_code == 200

    assert mock_render.call_args.kwargs["message"] == (
        "Username already exists."
    )

    count = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM users
        WHERE username = 'employee'
        """
    ).fetchone()["count"]

    assert count == 1

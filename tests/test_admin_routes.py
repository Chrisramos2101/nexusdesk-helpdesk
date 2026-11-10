
from unittest.mock import patch

import pytest
from werkzeug.security import check_password_hash


@pytest.mark.parametrize(
    "path, method",
    [
        ("/users", "GET"),
        ("/create_user", "GET"),
        ("/system_dashboard", "GET"),
        ("/run_security_cleanup", "POST"),
    ],
)
def test_employee_cannot_access_admin_operations(
    client, login_as, path, method
):
    login_as(client, "employee", "employee")

    response = client.open(path, method=method)

    assert response.status_code in (302, 403)


def test_admin_can_create_user(client, login_as, db):
    login_as(client, "admin", "admin")

    response = client.post(
        "/create_user",
        data={
            "full_name": "New Employee",
            "username": "new_employee",
            "email": "new@example.com",
            "department": "IT",
            "password": "SecurePass123!",
            "role": "employee",
        },
    )

    assert response.status_code == 200

    user = db.execute(
        "SELECT * FROM users WHERE username = ?",
        ("new_employee",),
    ).fetchone()

    assert user is not None
    assert user["role"] == "employee"
    assert check_password_hash(
        user["password_hash"], "SecurePass123!"
    )


def test_admin_can_edit_user(client, login_as, db):
    login_as(client, "admin", "admin")

    user_id = db.execute(
        "SELECT id FROM users WHERE username = ?",
        ("employee",),
    ).fetchone()["id"]

    response = client.post(
        f"/edit_user/{user_id}",
        data={
            "full_name": "Updated Employee",
            "email": "updated@example.com",
            "department": "IT",
            "role": "employee",
        },
    )

    assert response.status_code == 302

    user = db.execute(
        "SELECT full_name, email FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()

    assert user["full_name"] == "Updated Employee"
    assert user["email"] == "updated@example.com"


def test_invalid_role_does_not_update_user(
    client, login_as, db
):
    login_as(client, "admin", "admin")

    user_id = db.execute(
        "SELECT id FROM users WHERE username = ?",
        ("employee",),
    ).fetchone()["id"]

    response = client.post(
        f"/edit_user/{user_id}",
        data={
            "full_name": "Unauthorized Change",
            "email": "change@example.com",
            "department": "IT",
            "role": "superadmin",
        },
    )

    assert response.status_code == 302

    user = db.execute(
        "SELECT full_name, role FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()

    assert user["role"] == "employee"
    assert user["full_name"] == "Employee"


def test_admin_can_delete_another_user(
    client, login_as, db
):
    login_as(client, "admin", "admin")

    user_id = db.execute(
        "SELECT id FROM users WHERE username = ?",
        ("other",),
    ).fetchone()["id"]

    response = client.post(f"/delete_user/{user_id}")

    assert response.status_code == 302

    user = db.execute(
        "SELECT id FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()

    assert user is None


def test_admin_system_dashboard_counts_users(
    client, login_as
):
    login_as(client, "admin", "admin")

    with patch(
        "routes.admin.render_template",
        return_value="System dashboard rendered",
    ) as mock_render:
        response = client.get("/system_dashboard")

    assert response.status_code == 200

    context = mock_render.call_args.kwargs

    # conftest.py seeds three users.
    assert context["total_users"] == 3
    assert context["total_tickets"] == 0
    assert context["database_status"] == "Connected"


def test_admin_can_run_security_cleanup(
    client, login_as
):
    login_as(client, "admin", "admin")

    with patch(
        "routes.admin.cleanup_expired_security_records"
    ) as mock_cleanup:
        response = client.post("/run_security_cleanup")

    assert response.status_code == 302
    assert response.headers["Location"].endswith(
        "/system_dashboard?cleanup=success"
    )
    mock_cleanup.assert_called_once()

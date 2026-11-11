
import pytest


def test_active_admin_can_access_admin_page(
    client, login_as
):
    login_as(client, "admin", "admin")

    response = client.get("/users")

    assert response.status_code == 200


def test_demoted_admin_loses_access_immediately(
    client, login_as, db
):
    login_as(client, "admin", "admin")

    # Confirm access before demotion.
    assert client.get("/users").status_code == 200

    # Simulate an administrator being demoted
    # while their original session remains active.
    db.execute(
        """
        UPDATE users
        SET role = 'employee'
        WHERE username = 'admin'
        """
    )
    db.commit()

    response = client.get("/users")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")

    with client.session_transaction() as session:
        assert session["role"] == "employee"


@pytest.mark.parametrize(
    "path",
    [
        "/users",
        "/system_dashboard",
        "/create_user",
        "/dashboard",
    ],
)
def test_demoted_admin_cannot_access_protected_pages(
    client, login_as, db, path
):
    login_as(client, "admin", "admin")

    db.execute(
        """
        UPDATE users
        SET role = 'employee'
        WHERE username = 'admin'
        """
    )
    db.commit()

    response = client.get(path)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")


def test_demoted_admin_cannot_modify_users(
    client, login_as, db
):
    login_as(client, "admin", "admin")

    employee = db.execute(
        """
        SELECT id, full_name
        FROM users
        WHERE username = 'employee'
        """
    ).fetchone()

    original_name = employee["full_name"]

    db.execute(
        """
        UPDATE users
        SET role = 'employee'
        WHERE username = 'admin'
        """
    )
    db.commit()

    response = client.post(
        f"/edit_user/{employee['id']}",
        data={
            "full_name": "Unauthorized Change",
            "email": "changed@example.com",
            "department": "IT",
            "role": "admin",
        },
    )

    assert response.status_code == 302

    updated = db.execute(
        """
        SELECT full_name, role
        FROM users
        WHERE id = ?
        """,
        (employee["id"],),
    ).fetchone()

    assert updated["full_name"] == original_name
    assert updated["role"] == "employee"


def test_deleted_admin_session_is_invalidated(
    client, login_as, db
):
    login_as(client, "admin", "admin")

    db.execute(
        """
        DELETE FROM users
        WHERE username = 'admin'
        """
    )
    db.commit()

    response = client.get("/users")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")

    with client.session_transaction() as session:
        assert "username" not in session
        assert "role" not in session


def test_session_role_cannot_override_database_role(
    client, login_as
):
    # Simulate an outdated or inconsistent
    # session claiming administrator privileges.
    login_as(client, "employee", "admin")

    response = client.get("/users")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")

    with client.session_transaction() as session:
        assert session["role"] == "employee"

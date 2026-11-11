
import pytest


def delete_employee(db):
    db.execute(
        """
        DELETE FROM users
        WHERE username = 'employee'
        """
    )
    db.commit()


def test_active_employee_can_access_own_tickets(
    client, login_as
):
    login_as(client, "employee", "employee")

    response = client.get("/my_tickets")

    assert response.status_code == 200


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/my_tickets",
        "/profile",
        "/knowledge_base",
        "/api/users/search",
    ],
)
def test_deleted_employee_cannot_access_protected_pages(
    client, login_as, db, path
):
    login_as(client, "employee", "employee")

    delete_employee(db)

    response = client.get(path)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")

    with client.session_transaction() as session:
        assert "username" not in session
        assert "role" not in session


def test_deleted_employee_cannot_submit_ticket(
    client, login_as, db
):
    login_as(client, "employee", "employee")

    delete_employee(db)

    response = client.post(
        "/submit",
        data={
            "name": "Deleted Employee",
            "department": "IT",
            "issue": "Unauthorized ticket",
            "priority": "Medium",
            "category": "Software",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")

    count = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM tickets
        """
    ).fetchone()["count"]

    assert count == 0


def test_employee_session_cannot_claim_admin_role(
    client, login_as
):
    # Simulate an outdated session role.
    login_as(client, "employee", "admin")

    response = client.get("/my_tickets")

    assert response.status_code == 200

    with client.session_transaction() as session:
        assert session["role"] == "employee"


def test_role_change_refreshes_existing_session(
    client, login_as, db
):
    login_as(client, "employee", "employee")

    db.execute(
        """
        UPDATE users
        SET role = 'admin'
        WHERE username = 'employee'
        """
    )
    db.commit()

    response = client.get("/my_tickets")

    assert response.status_code == 200

    with client.session_transaction() as session:
        assert session["role"] == "admin"


def test_deleted_user_session_cannot_be_reused(
    client, login_as, db
):
    login_as(client, "employee", "employee")

    delete_employee(db)

    first_response = client.get("/profile")
    assert first_response.status_code == 302

    second_response = client.get("/my_tickets")
    assert second_response.status_code == 302
    assert second_response.headers["Location"].endswith(
        "/login"
    )

    with client.session_transaction() as session:
        assert "username" not in session

def test_anonymous_user_is_redirected_from_admin(client):
    response = client.get("/users")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_employee_cannot_open_admin_users(client, login_as):
    login_as(client, "employee", "employee")
    response = client.get("/users")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")


def test_employee_can_open_own_ticket(client, login_as, create_ticket):
    ticket_id = create_ticket("employee")
    login_as(client, "employee", "employee")
    response = client.get(f"/my_tickets/{ticket_id}")
    assert response.status_code == 200


def test_employee_cannot_open_another_users_ticket(client, login_as, create_ticket):
    ticket_id = create_ticket("other")
    login_as(client, "employee", "employee")
    response = client.get(f"/my_tickets/{ticket_id}")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/my_tickets")



def test_employee_cannot_assign_ticket_to_self(
    client, login_as, create_ticket, db
):
    # Create an unassigned ticket.
    ticket_id = create_ticket("employee")

    # Log in as an employee, not an administrator.
    login_as(client, "employee", "employee")

    # Attempt an administrator-only assignment.
    response = client.post(f"/assign_me/{ticket_id}")

    # Access should be rejected or redirected.
    assert response.status_code in (302, 403)

    # Verify the database was not modified.
    ticket = db.execute(
        "SELECT assigned_to FROM tickets WHERE id = ?",
        (ticket_id,),
    ).fetchone()

    assert ticket is not None
    assert ticket["assigned_to"] == "Unassigned"



def test_employee_cannot_quick_close_ticket(
    client, login_as, create_ticket, db
):
    # Create an open ticket.
    ticket_id = create_ticket("employee")

    # Log in as an employee.
    login_as(client, "employee", "employee")

    # Attempt to use the admin-only quick-close endpoint.
    response = client.post(f"/quick_close/{ticket_id}")

    # The request should be rejected or redirected.
    assert response.status_code in (302, 403)

    # Verify the ticket remains open and unchanged.
    ticket = db.execute(
        """
        SELECT status, closed_at, completed_by
        FROM tickets
        WHERE id = ?
        """,
        (ticket_id,),
    ).fetchone()

    assert ticket is not None
    assert ticket["status"] == "Open"
    assert ticket["closed_at"] == ""
    assert ticket["completed_by"] == ""

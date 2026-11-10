from unittest.mock import patch


def test_employee_can_create_ticket(client, login_as, db):
    login_as(client, "employee", "employee")
    with patch("routes.tickets.send_ticket_created_email", return_value=True):
        response = client.post(
            "/submit",
            data={
                "name": "Employee",
                "department": "Finance",
                "issue": "Laptop will not boot",
                "priority": "High",
                "category": "Hardware",
            },
        )

    assert response.status_code == 302
    ticket = db.execute(
        "SELECT * FROM tickets WHERE submitted_by = ? ORDER BY id DESC LIMIT 1",
        ("employee",),
    ).fetchone()
    assert ticket is not None
    assert ticket["status"] == "Open"
    assert ticket["priority"] == "High"


def test_employee_can_add_comment_to_own_ticket(client, login_as, create_ticket, db):
    ticket_id = create_ticket("employee")
    login_as(client, "employee", "employee")
    response = client.post(
        f"/my_tickets/{ticket_id}/comment",
        data={"comment": "Additional troubleshooting detail"},
    )
    assert response.status_code == 302

    note = db.execute(
        "SELECT * FROM ticket_notes WHERE ticket_id = ?",
        (ticket_id,),
    ).fetchone()
    assert note["created_by"] == "employee"


def test_employee_cannot_comment_on_other_users_ticket(client, login_as, create_ticket, db):
    ticket_id = create_ticket("other")
    login_as(client, "employee", "employee")
    response = client.post(
        f"/my_tickets/{ticket_id}/comment",
        data={"comment": "Should not be written"},
    )
    assert response.status_code == 302
    count = db.execute(
        "SELECT COUNT(*) AS count FROM ticket_notes WHERE ticket_id = ?",
        (ticket_id,),
    ).fetchone()["count"]
    assert count == 0



def test_ticket_assignment_updates_database(create_ticket, db):
    from services.ticket_service import assign_ticket_to_user

    # Create a ticket in the isolated test database.
    ticket_id = create_ticket("employee")

    # Assign the ticket to an administrator.
    assign_ticket_to_user(ticket_id, "admin")

    # Verify the assignment was saved.
    ticket = db.execute(
        "SELECT assigned_to FROM tickets WHERE id = ?",
        (ticket_id,),
    ).fetchone()

    assert ticket is not None
    assert ticket["assigned_to"] == "admin"



def test_ticket_closure_updates_database(create_ticket, db):
    from services.ticket_service import close_ticket

    ticket_id = create_ticket("employee")

    close_ticket(
        ticket_id=ticket_id,
        closed_at="11/09/2026 06:30 PM",
        completed_by="admin",
        resolution_time="2 hours",
        sla_met="Yes",
    )

    ticket = db.execute(
        """
        SELECT status, closed_at, completed_by,
               resolution_time, sla_met
        FROM tickets
        WHERE id = ?
        """,
        (ticket_id,),
    ).fetchone()

    assert ticket is not None
    assert ticket["status"] == "Closed"
    assert ticket["closed_at"] == "11/09/2026 06:30 PM"
    assert ticket["completed_by"] == "admin"
    assert ticket["resolution_time"] == "2 hours"
    assert ticket["sla_met"] == "Yes"



def test_admin_can_assign_ticket_to_self(
    client, login_as, create_ticket, db
):
    from unittest.mock import patch

    # Create an unassigned ticket.
    ticket_id = create_ticket("employee")

    # Log in as an administrator.
    login_as(client, "admin", "admin")

    # Prevent real email delivery during the test.
    with patch(
        "routes.tickets.send_ticket_assigned_email",
        return_value=True
    ):
        response = client.post(
            f"/assign_me/{ticket_id}"
        )

    # The application should redirect after assignment.
    assert response.status_code == 302

    # Verify the ticket was assigned to the administrator.
    ticket = db.execute(
        "SELECT assigned_to FROM tickets WHERE id = ?",
        (ticket_id,),
    ).fetchone()

    assert ticket is not None
    assert ticket["assigned_to"] == "admin"



def test_admin_can_quick_close_ticket(
    client, login_as, create_ticket, db
):
    from unittest.mock import patch

    # Create an open, unassigned ticket.
    ticket_id = create_ticket("employee")

    # Log in as an administrator.
    login_as(client, "admin", "admin")

    # Prevent real email delivery.
    with patch(
        "routes.tickets.send_ticket_closed_email",
        return_value=True
    ):
        response = client.post(
            f"/quick_close/{ticket_id}"
        )

    # The application redirects after closing the ticket.
    assert response.status_code == 302

    # Verify the ticket was closed and assigned correctly.
    ticket = db.execute(
        """
        SELECT status, assigned_to, closed_at,
               completed_by, resolution_time, sla_met
        FROM tickets
        WHERE id = ?
        """,
        (ticket_id,),
    ).fetchone()

    assert ticket is not None
    assert ticket["status"] == "Closed"
    assert ticket["assigned_to"] == "admin"
    assert ticket["completed_by"] == "admin"
    assert ticket["closed_at"] != ""
    assert ticket["resolution_time"] != ""
    assert ticket["sla_met"] in ("Yes", "No")

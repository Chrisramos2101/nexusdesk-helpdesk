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

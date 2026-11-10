
import pytest


def ticket_form(**overrides):
    """Return valid ticket-editing form data."""
    data = {
        "name": "Updated Employee",
        "department": "IT",
        "issue": "Updated laptop issue",
        "priority": "High",
        "category": "Hardware",
        "status": "In Progress",
        "assigned_to": "admin",
        "notes": "",
    }
    data.update(overrides)
    return data


def test_admin_can_edit_ticket(
    client, login_as, create_ticket, db
):
    ticket_id = create_ticket("employee")
    login_as(client, "admin", "admin")

    response = client.post(
        f"/update_ticket/{ticket_id}",
        data=ticket_form(),
    )

    assert response.status_code == 302

    ticket = db.execute(
        """
        SELECT name, department, issue,
               priority, category, status, assigned_to
        FROM tickets WHERE id = ?
        """,
        (ticket_id,),
    ).fetchone()

    assert ticket["name"] == "Updated Employee"
    assert ticket["department"] == "IT"
    assert ticket["issue"] == "Updated laptop issue"
    assert ticket["priority"] == "High"
    assert ticket["category"] == "Hardware"
    assert ticket["status"] == "In Progress"
    assert ticket["assigned_to"] == "admin"


@pytest.mark.parametrize(
    "invalid_field, invalid_value",
    [
        ("department", "Invalid Department"),
        ("priority", "Critical"),
        ("category", "Invalid Category"),
        ("status", "Invalid Status"),
    ],
)
def test_invalid_ticket_values_are_rejected(
    client, login_as, create_ticket, db,
    invalid_field, invalid_value
):
    ticket_id = create_ticket("employee")
    login_as(client, "admin", "admin")

    response = client.post(
        f"/update_ticket/{ticket_id}",
        data=ticket_form(
            **{invalid_field: invalid_value}
        ),
    )

    assert response.status_code == 302

    ticket = db.execute(
        """
        SELECT status, priority, department, category
        FROM tickets WHERE id = ?
        """,
        (ticket_id,),
    ).fetchone()

    # The original ticket must remain unchanged.
    assert ticket["status"] == "Open"
    assert ticket["priority"] == "Medium"
    assert ticket["department"] == "Finance"
    assert ticket["category"] == "Software"


def test_admin_can_reopen_closed_ticket(
    client, login_as, create_ticket, db
):
    ticket_id = create_ticket("employee")

    db.execute(
        """
        UPDATE tickets
        SET status = 'Closed',
            closed_at = '11/09/2026 02:00 PM',
            completed_by = 'admin',
            resolution_time = '2 hr 0 min',
            sla_met = 'Yes'
        WHERE id = ?
        """,
        (ticket_id,),
    )
    db.commit()

    login_as(client, "admin", "admin")

    response = client.post(
        f"/update_ticket/{ticket_id}",
        data=ticket_form(status="Open"),
    )

    assert response.status_code == 302

    ticket = db.execute(
        """
        SELECT status, closed_at, completed_by,
               resolution_time, sla_met
        FROM tickets WHERE id = ?
        """,
        (ticket_id,),
    ).fetchone()

    assert ticket["status"] == "Open"
    assert ticket["closed_at"] == ""
    assert ticket["completed_by"] == ""
    assert ticket["resolution_time"] == ""
    assert ticket["sla_met"] == ""


def test_employee_cannot_delete_ticket(
    client, login_as, create_ticket, db
):
    ticket_id = create_ticket("employee")
    login_as(client, "employee", "employee")

    response = client.post(
        f"/delete_ticket/{ticket_id}"
    )

    assert response.status_code in (302, 403)

    ticket = db.execute(
        "SELECT id FROM tickets WHERE id = ?",
        (ticket_id,),
    ).fetchone()

    assert ticket is not None


def test_admin_can_delete_ticket(
    client, login_as, create_ticket, db
):
    ticket_id = create_ticket("employee")
    login_as(client, "admin", "admin")

    response = client.post(
        f"/delete_ticket/{ticket_id}"
    )

    assert response.status_code == 302

    ticket = db.execute(
        "SELECT id FROM tickets WHERE id = ?",
        (ticket_id,),
    ).fetchone()

    assert ticket is None


from datetime import datetime

import pytest
from unittest.mock import patch

from routes import tickets


def ticket_form(**overrides):
    data = {
        "name": "Employee",
        "department": "IT",
        "issue": "Updated issue",
        "priority": "High",
        "category": "Hardware",
        "status": "In Progress",
        "assigned_to": "admin",
        "notes": "",
    }
    data.update(overrides)
    return data


def test_resolution_time_calculation():
    result = tickets.calculate_resolution_time(
        "11/09/2026 10:00 AM",
        "11/09/2026 12:45 PM",
    )

    assert result == "2 hr 45 min"


def test_invalid_resolution_dates_are_handled():
    result = tickets.calculate_resolution_time(
        "invalid",
        "11/09/2026 12:45 PM",
    )

    assert result == ""


@pytest.mark.parametrize(
    "closed, due, expected",
    [
        (
            "11/09/2026 10:00 AM",
            "11/09/2026 11:00 AM",
            "Yes",
        ),
        (
            "11/09/2026 12:00 PM",
            "11/09/2026 11:00 AM",
            "No",
        ),
        (
            "",
            "11/09/2026 11:00 AM",
            "",
        ),
        (
            "invalid",
            "11/09/2026 11:00 AM",
            "",
        ),
    ],
)
def test_sla_met_calculation(closed, due, expected):
    assert tickets.calculate_sla_met(
        closed, due
    ) == expected


def test_invalid_ticket_age_is_handled():
    assert tickets.calculate_ticket_age(
        "not-a-date"
    ) == "Recently submitted"


def test_closed_ticket_has_full_sla_progress():
    result = tickets.calculate_sla_progress(
        "11/09/2026 09:00 AM",
        "11/09/2026 05:00 PM",
        "Closed",
    )

    assert result == 100


def test_missing_sla_deadline_has_zero_progress():
    result = tickets.calculate_sla_progress(
        "11/09/2026 09:00 AM",
        "",
        "Open",
    )

    assert result == 0


def test_invalid_sla_progress_dates_are_handled():
    result = tickets.calculate_sla_progress(
        "invalid-date",
        "11/09/2026 05:00 PM",
        "Open",
    )

    assert result == 0


def test_high_priority_sla_crosses_business_days():
    # Monday, 3 PM: only two business hours remain.
    start = datetime(2026, 11, 9, 15, 0)

    result = tickets.calculate_sla_due_at(
        "High",
        start,
    )

    assert result == "11/10/2026 10:00 AM"


def test_high_priority_sla_skips_weekend():
    # Friday, 4 PM: one hour Friday,
    # then three hours Monday.
    start = datetime(2026, 11, 13, 16, 0)

    result = tickets.calculate_sla_due_at(
        "High",
        start,
    )

    assert result == "11/16/2026 11:00 AM"


def test_admin_update_closes_ticket_with_resolution(
    client, login_as, create_ticket, db
):
    ticket_id = create_ticket("employee")
    login_as(client, "admin", "admin")

    response = client.post(
        f"/update_ticket/{ticket_id}",
        data=ticket_form(status="Closed"),
    )

    assert response.status_code == 302

    ticket = db.execute(
        """
        SELECT status, completed_by,
               closed_at, resolution_time, sla_met
        FROM tickets
        WHERE id = ?
        """,
        (ticket_id,),
    ).fetchone()

    assert ticket["status"] == "Closed"
    assert ticket["completed_by"] == "admin"
    assert ticket["closed_at"]
    assert ticket["resolution_time"]
    assert ticket["sla_met"] in ("Yes", "No")


def test_admin_comment_records_mention(
    client, login_as, create_ticket, db
):
    ticket_id = create_ticket("employee")
    login_as(client, "admin", "admin")

    with patch(
        "routes.tickets.send_mention_email",
        return_value=True,
    ) as send_mention:
        response = client.post(
            f"/update_ticket/{ticket_id}",
            data=ticket_form(
                notes="Please review @employee"
            ),
        )

    assert response.status_code == 302

    note = db.execute(
        """
        SELECT note, created_by
        FROM ticket_notes
        WHERE ticket_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (ticket_id,),
    ).fetchone()

    assert note is not None
    assert note["created_by"] == "admin"
    assert "@employee" in note["note"]

    send_mention.assert_called_once()

    args = send_mention.call_args.args
    assert args[0] == "employee@example.com"
    assert args[1] == "employee"
    assert args[2] == ticket_id


def test_unknown_mention_does_not_send_email(
    client, login_as, create_ticket
):
    ticket_id = create_ticket("employee")
    login_as(client, "admin", "admin")

    with patch(
        "routes.tickets.send_mention_email",
        return_value=True,
    ) as send_mention:
        response = client.post(
            f"/update_ticket/{ticket_id}",
            data=ticket_form(
                notes="Check with @nonexistent_user"
            ),
        )

    assert response.status_code == 302
    send_mention.assert_not_called()


def test_external_return_url_is_rejected(
    client, login_as, create_ticket
):
    ticket_id = create_ticket("employee")
    login_as(client, "admin", "admin")

    response = client.post(
        f"/assign_me/{ticket_id}",
        data={
            "return_to": "https://evil.example.com"
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/dashboard"

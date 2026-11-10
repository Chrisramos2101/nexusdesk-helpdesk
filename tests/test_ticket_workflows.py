
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest


def valid_submission(**overrides):
    data = {
        "name": "Test Employee",
        "department": "Finance",
        "issue": "Laptop will not connect",
        "priority": "Medium",
        "category": "Software",
    }
    data.update(overrides)
    return data


@pytest.mark.parametrize(
    "field, invalid_value",
    [
        ("name", "   "),
        ("issue", "   "),
        ("department", "Invalid Department"),
        ("priority", "Critical"),
        ("category", "Invalid Category"),
    ],
)
def test_invalid_submissions_do_not_create_tickets(
    client, login_as, db, field, invalid_value
):
    login_as(client, "employee", "employee")

    response = client.post(
        "/submit",
        data=valid_submission(**{field: invalid_value}),
    )

    assert response.status_code == 302

    count = db.execute(
        "SELECT COUNT(*) FROM tickets"
    ).fetchone()[0]

    assert count == 0


def test_blank_comment_is_not_saved(
    client, login_as, create_ticket, db
):
    ticket_id = create_ticket("employee")
    login_as(client, "employee", "employee")

    response = client.post(
        f"/my_tickets/{ticket_id}/comment",
        data={"comment": "   "},
    )

    assert response.status_code == 302

    count = db.execute(
        "SELECT COUNT(*) FROM ticket_notes WHERE ticket_id = ?",
        (ticket_id,),
    ).fetchone()[0]

    assert count == 0


def test_employee_cannot_view_other_users_ticket(
    client, login_as, create_ticket
):
    ticket_id = create_ticket("other")
    login_as(client, "employee", "employee")

    response = client.get(
        f"/my_tickets/{ticket_id}"
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith(
        "/my_tickets"
    )


def test_user_search_returns_matching_accounts(
    client, login_as
):
    login_as(client, "employee", "employee")

    response = client.get(
        "/api/users/search?q=admin"
    )

    assert response.status_code == 200

    users = response.get_json()

    assert any(
        user["username"] == "admin"
        for user in users
    )


def test_admin_submitted_ticket_is_auto_assigned(
    client, login_as, db
):
    login_as(client, "admin", "admin")

    with patch(
        "routes.tickets.send_ticket_created_email",
        return_value=True,
    ):
        response = client.post(
            "/submit",
            data=valid_submission(),
        )

    assert response.status_code == 302

    ticket = db.execute(
        """
        SELECT submitted_by, assigned_to
        FROM tickets
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()

    assert ticket is not None
    assert ticket["submitted_by"] == "admin"
    assert ticket["assigned_to"] == "admin"


def test_valid_attachment_is_saved(
    client, login_as, db, app
):
    login_as(client, "employee", "employee")

    data = valid_submission()
    data["attachment"] = (
        BytesIO(b"Test attachment content"),
        "troubleshooting.txt",
    )

    with patch(
        "routes.tickets.send_ticket_created_email",
        return_value=True,
    ):
        response = client.post(
            "/submit",
            data=data,
            content_type="multipart/form-data",
        )

    assert response.status_code == 302

    attachment = db.execute(
        """
        SELECT original_filename, stored_filename
        FROM ticket_attachments
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()

    assert attachment is not None
    assert attachment["original_filename"] == (
        "troubleshooting.txt"
    )

    stored_file = (
        Path(app.config["UPLOAD_FOLDER"])
        / attachment["stored_filename"]
    )

    assert stored_file.exists()
    assert stored_file.read_bytes() == (
        b"Test attachment content"
    )


def test_disallowed_attachment_is_not_saved(
    client, login_as, db
):
    login_as(client, "employee", "employee")

    data = valid_submission()
    data["attachment"] = (
        BytesIO(b"Not an allowed attachment"),
        "script.exe",
    )

    with patch(
        "routes.tickets.send_ticket_created_email",
        return_value=True,
    ):
        response = client.post(
            "/submit",
            data=data,
            content_type="multipart/form-data",
        )

    assert response.status_code == 302

    count = db.execute(
        "SELECT COUNT(*) FROM ticket_attachments"
    ).fetchone()[0]

    assert count == 0


def test_missing_attachment_returns_404(
    client, login_as
):
    login_as(client, "employee", "employee")

    response = client.get(
        "/attachment/nonexistent-file.txt"
    )

    assert response.status_code == 404


from pathlib import Path


def create_test_attachment(db, app, ticket_id):
    filename = "security-check.txt"

    folder = Path(app.config["UPLOAD_FOLDER"])
    folder.mkdir(parents=True, exist_ok=True)

    (folder / filename).write_text(
        "private attachment",
        encoding="utf-8",
    )

    db.execute(
        """
        INSERT INTO ticket_attachments (
            ticket_id,
            original_filename,
            stored_filename,
            uploaded_by,
            uploaded_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            ticket_id,
            filename,
            filename,
            "other",
            "11/11/2026 10:00 AM",
        ),
    )
    db.commit()

    return filename


def test_deleted_employee_cannot_download_attachment(
    client, app, login_as, create_ticket, db
):
    ticket_id = create_ticket("employee")
    filename = create_test_attachment(db, app, ticket_id)

    login_as(client, "employee", "employee")

    db.execute(
        "DELETE FROM users WHERE username = 'employee'"
    )
    db.commit()

    response = client.get(f"/attachment/{filename}")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_demoted_admin_cannot_download_others_attachment(
    client, app, login_as, create_ticket, db
):
    ticket_id = create_ticket("other")
    filename = create_test_attachment(db, app, ticket_id)

    login_as(client, "admin", "admin")

    db.execute(
        "UPDATE users SET role = 'employee' "
        "WHERE username = 'admin'"
    )
    db.commit()

    response = client.get(f"/attachment/{filename}")

    assert response.status_code == 403


def test_ticket_owner_can_still_download_attachment(
    client, app, login_as, create_ticket, db
):
    ticket_id = create_ticket("other")
    filename = create_test_attachment(db, app, ticket_id)

    login_as(client, "other", "employee")

    response = client.get(f"/attachment/{filename}")

    assert response.status_code == 200
    assert response.data == b"private attachment"

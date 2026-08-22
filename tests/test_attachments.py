from pathlib import Path


def _create_attachment(db, app, ticket_id, submitted_by):
    stored = f"{submitted_by}-attachment.txt"
    upload_dir = Path(app.config["UPLOAD_FOLDER"])
    upload_dir.mkdir(parents=True, exist_ok=True)
    (upload_dir / stored).write_text("safe test attachment", encoding="utf-8")
    db.execute(
        """
        INSERT INTO ticket_attachments
        (ticket_id, original_filename, stored_filename, uploaded_by, uploaded_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (ticket_id, "notes.txt", stored, submitted_by, "08/22/2026 10:00 AM"),
    )
    db.commit()
    return stored


def test_ticket_owner_can_download_attachment(client, app, login_as, create_ticket, db):
    ticket_id = create_ticket("employee")
    stored = _create_attachment(db, app, ticket_id, "employee")
    login_as(client, "employee", "employee")
    response = client.get(f"/attachment/{stored}")
    assert response.status_code == 200
    assert response.data == b"safe test attachment"


def test_other_employee_is_forbidden_from_attachment(client, app, login_as, create_ticket, db):
    ticket_id = create_ticket("other")
    stored = _create_attachment(db, app, ticket_id, "other")
    login_as(client, "employee", "employee")
    response = client.get(f"/attachment/{stored}")
    assert response.status_code == 403


def test_admin_can_download_attachment(client, app, login_as, create_ticket, db):
    ticket_id = create_ticket("other")
    stored = _create_attachment(db, app, ticket_id, "other")
    login_as(client, "admin", "admin")
    response = client.get(f"/attachment/{stored}")
    assert response.status_code == 200


import pytest


@pytest.mark.parametrize(
    "path, data",
    [
        (
            "/update_profile",
            {
                "full_name": "Unauthorized",
                "email": "unauthorized@example.com",
                "department": "IT",
            },
        ),
        (
            "/knowledge_base/password-reset/feedback",
            {
                "was_helpful": "yes",
                "feedback": "Deleted user feedback",
            },
        ),
    ],
)
def test_deleted_employee_cannot_write(
    client, login_as, db, path, data
):
    login_as(client, "employee", "employee")

    db.execute(
        "DELETE FROM users WHERE username = ?",
        ("employee",),
    )
    db.commit()

    response = client.post(path, data=data)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")

    with client.session_transaction() as session:
        assert "username" not in session


def test_deleted_employee_cannot_comment(
    client, login_as, create_ticket, db
):
    ticket_id = create_ticket("employee")

    login_as(client, "employee", "employee")

    db.execute(
        "DELETE FROM users WHERE username = ?",
        ("employee",),
    )
    db.commit()

    response = client.post(
        f"/my_tickets/{ticket_id}/comment",
        data={"comment": "Unauthorized comment"},
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")

    count = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM ticket_notes
        WHERE ticket_id = ?
        """,
        (ticket_id,),
    ).fetchone()["count"]

    assert count == 0

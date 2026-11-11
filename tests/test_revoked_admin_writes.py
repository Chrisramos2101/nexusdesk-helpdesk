
import pytest


@pytest.mark.parametrize(
    "endpoint",
    [
        "/assign_me/{ticket_id}",
        "/quick_close/{ticket_id}",
        "/delete_ticket/{ticket_id}",
    ],
)
def test_demoted_admin_cannot_modify_ticket(
    client, login_as, create_ticket, db, endpoint
):
    ticket_id = create_ticket("employee")

    login_as(client, "admin", "admin")

    db.execute(
        "UPDATE users SET role = 'employee' "
        "WHERE username = 'admin'"
    )
    db.commit()

    response = client.post(
        endpoint.format(ticket_id=ticket_id)
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")

    ticket = db.execute(
        """
        SELECT status, assigned_to
        FROM tickets
        WHERE id = ?
        """,
        (ticket_id,),
    ).fetchone()

    assert ticket is not None
    assert ticket["status"] == "Open"
    assert ticket["assigned_to"] == "Unassigned"


def test_demoted_admin_cannot_run_security_cleanup(
    client, login_as, db
):
    login_as(client, "admin", "admin")

    db.execute(
        "UPDATE users SET role = 'employee' "
        "WHERE username = 'admin'"
    )
    db.commit()

    response = client.post("/run_security_cleanup")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")

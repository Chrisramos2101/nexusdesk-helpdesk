
from datetime import datetime, timedelta
from unittest.mock import patch


def capture_page(client, url):
    with patch(
        "routes.tickets.render_template",
        return_value="Page rendered",
    ) as mock_render:
        response = client.get(url)

    assert response.status_code == 200
    assert mock_render.call_count == 1

    return mock_render.call_args.kwargs


def formatted_time(delta):
    return (
        datetime.now() + delta
    ).strftime("%m/%d/%Y %I:%M %p")


def test_anonymous_user_cannot_open_ticket_home(client):
    response = client.get("/")

    assert response.status_code == 302
    assert response.headers["Location"].endswith(
        "/login"
    )


def test_my_tickets_shows_only_current_users_tickets(
    client, login_as, create_ticket
):
    first = create_ticket("employee")
    second = create_ticket("employee")
    create_ticket("other")

    login_as(client, "employee", "employee")

    context = capture_page(client, "/my_tickets")

    ids = {
        ticket["id"]
        for ticket in context["tickets"]
    }

    assert ids == {first, second}


def test_employee_ticket_detail_includes_own_notes(
    client, login_as, create_ticket, db
):
    ticket_id = create_ticket("employee")

    db.execute(
        """
        INSERT INTO ticket_notes
        (ticket_id, note, created_by, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            ticket_id,
            "Diagnostic note",
            "employee",
            "11/09/2026 10:00 AM",
        ),
    )
    db.commit()

    login_as(client, "employee", "employee")

    context = capture_page(
        client,
        f"/my_tickets/{ticket_id}",
    )

    assert context["ticket"]["id"] == ticket_id
    assert len(context["notes"]) == 1
    assert context["notes"][0]["note"] == (
        "Diagnostic note"
    )


def test_employee_home_metrics_exclude_other_users(
    client, login_as, create_ticket, db
):
    own_open = create_ticket("employee")
    own_progress = create_ticket("employee")
    other_open = create_ticket("other")

    future = formatted_time(timedelta(days=30))
    past = formatted_time(timedelta(days=-30))

    db.execute(
        """
        UPDATE tickets SET sla_due_at = ?
        WHERE id = ?
        """,
        (future, own_open),
    )
    db.execute(
        """
        UPDATE tickets
        SET status = 'In Progress', sla_due_at = ?
        WHERE id = ?
        """,
        (past, own_progress),
    )
    db.execute(
        """
        UPDATE tickets SET sla_due_at = ?
        WHERE id = ?
        """,
        (past, other_open),
    )
    db.commit()

    login_as(client, "employee", "employee")

    context = capture_page(client, "/")

    assert context["my_open_tickets"] == 1
    assert context["my_in_progress_tickets"] == 1
    assert context["my_active_tickets"] == 2
    assert context["my_overdue_tickets"] == 1

    assert context["open_tickets"] == 2
    assert context["overdue_tickets"] == 2
    assert context["unassigned_tickets"] == 3


def test_admin_home_counts_only_assigned_active_work(
    client, login_as, create_ticket, db
):
    assigned = create_ticket("employee")
    closed = create_ticket("employee")
    create_ticket("other")

    db.execute(
        """
        UPDATE tickets
        SET assigned_to = 'admin'
        WHERE id = ?
        """,
        (assigned,),
    )

    db.execute(
        """
        UPDATE tickets
        SET assigned_to = 'admin',
            status = 'Closed'
        WHERE id = ?
        """,
        (closed,),
    )
    db.commit()

    login_as(client, "admin", "admin")

    context = capture_page(client, "/")

    assert context["my_open_tickets"] == 1
    assert context["my_active_tickets"] == 0
    assert context["my_in_progress_tickets"] == 0
    assert context["my_overdue_tickets"] == 0


def test_invalid_sla_date_does_not_break_home(
    client, login_as, create_ticket, db
):
    ticket_id = create_ticket("employee")

    db.execute(
        """
        UPDATE tickets
        SET sla_due_at = 'not-a-date'
        WHERE id = ?
        """,
        (ticket_id,),
    )
    db.commit()

    login_as(client, "employee", "employee")

    context = capture_page(client, "/")

    assert context["overdue_tickets"] == 0
    assert context["my_overdue_tickets"] == 0


def test_knowledge_prefill_parameters_reach_home(
    client, login_as
):
    login_as(client, "employee", "employee")

    context = capture_page(
        client,
        "/?priority=High"
        "&category=Hardware"
        "&issue=Monitor%20not%20working",
    )

    assert context["prefill_priority"] == "High"
    assert context["prefill_category"] == "Hardware"
    assert context["prefill_issue"] == (
        "Monitor not working"
    )

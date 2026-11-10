
from services.dashboard_service import get_ticket_count_by_status


def test_dashboard_counts_open_tickets(db, create_ticket):
    # Create three open tickets.
    create_ticket("employee")
    create_ticket("employee")
    create_ticket("other")

    # Close one ticket in the test database.
    db.execute(
        """
        UPDATE tickets
        SET status = 'Closed'
        WHERE id = (
            SELECT MAX(id) FROM tickets
        )
        """
    )
    db.commit()

    # Verify that only the two open tickets are counted.
    result = get_ticket_count_by_status("Open")

    assert result == 2



from services.dashboard_service import get_high_priority_ticket_count


def test_dashboard_counts_high_priority_tickets(
    db, create_ticket
):
    # Create three tickets.
    first_id = create_ticket("employee")
    second_id = create_ticket("employee")
    third_id = create_ticket("other")

    # Assign different priorities.
    db.execute(
        "UPDATE tickets SET priority = ? WHERE id = ?",
        ("High", first_id),
    )
    db.execute(
        "UPDATE tickets SET priority = ? WHERE id = ?",
        ("High", second_id),
    )
    db.execute(
        "UPDATE tickets SET priority = ? WHERE id = ?",
        ("Low", third_id),
    )
    db.commit()

    # Only the two High-priority tickets should count.
    result = get_high_priority_ticket_count()

    assert result == 2



from datetime import datetime, timedelta

import pytest

from services.dashboard_service import (
    count_overdue_tickets,
    get_ticket_count_by_status,
    get_high_priority_ticket_count,
)


@pytest.mark.parametrize(
    "status, expected",
    [
        ("Open", 2),
        ("In Progress", 1),
        ("Closed", 1),
    ],
)
def test_dashboard_counts_each_ticket_status(
    db, create_ticket, status, expected
):
    ids = [create_ticket("employee") for _ in range(4)]

    db.execute(
        "UPDATE tickets SET status = 'In Progress' WHERE id = ?",
        (ids[2],),
    )
    db.execute(
        "UPDATE tickets SET status = 'Closed' WHERE id = ?",
        (ids[3],),
    )
    db.commit()

    assert get_ticket_count_by_status(status) == expected


def test_dashboard_counts_only_active_overdue_tickets(
    db, create_ticket
):
    now = datetime.now()

    past = (now - timedelta(days=2)).strftime(
        "%m/%d/%Y %I:%M %p"
    )
    future = (now + timedelta(days=2)).strftime(
        "%m/%d/%Y %I:%M %p"
    )

    overdue_id = create_ticket("employee")
    future_id = create_ticket("employee")
    closed_id = create_ticket("employee")
    invalid_id = create_ticket("employee")

    db.execute(
        "UPDATE tickets SET sla_due_at = ? WHERE id = ?",
        (past, overdue_id),
    )
    db.execute(
        "UPDATE tickets SET sla_due_at = ? WHERE id = ?",
        (future, future_id),
    )
    db.execute(
        """
        UPDATE tickets
        SET status = 'Closed', sla_due_at = ?
        WHERE id = ?
        """,
        (past, closed_id),
    )
    db.execute(
        "UPDATE tickets SET sla_due_at = ? WHERE id = ?",
        ("invalid-date", invalid_id),
    )
    db.commit()

    assert count_overdue_tickets() == 1


def test_dashboard_no_overdue_tickets(
    db, create_ticket
):
    ticket_id = create_ticket("employee")

    future = (
        datetime.now() + timedelta(days=7)
    ).strftime("%m/%d/%Y %I:%M %p")

    db.execute(
        "UPDATE tickets SET sla_due_at = ? WHERE id = ?",
        (future, ticket_id),
    )
    db.commit()

    assert count_overdue_tickets() == 0


def test_high_priority_count_includes_closed_tickets(
    db, create_ticket
):
    ticket_id = create_ticket("employee")

    db.execute(
        """
        UPDATE tickets
        SET priority = 'High', status = 'Closed'
        WHERE id = ?
        """,
        (ticket_id,),
    )
    db.commit()

    # This service counts all High-priority tickets,
    # regardless of status.
    assert get_high_priority_ticket_count() == 1


def test_employee_cannot_access_admin_dashboard(
    client, login_as
):
    login_as(client, "employee", "employee")

    response = client.get("/dashboard")

    assert response.status_code in (302, 403)

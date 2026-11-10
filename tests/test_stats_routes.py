
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest


def get_stats_context(client):
    """Capture stats calculated by the real Flask route."""
    with patch(
        "routes.dashboard.render_template",
        return_value="Statistics rendered",
    ) as mock_render:
        response = client.get("/stats")

    assert response.status_code == 200
    mock_render.assert_called_once_with(
        "stats.html",
        **mock_render.call_args.kwargs
    )
    return mock_render.call_args.kwargs


@pytest.mark.parametrize(
    "username, role",
    [
        ("employee", "employee"),
        ("other", "employee"),
    ],
)
def test_employee_cannot_access_statistics(
    client, login_as, username, role
):
    login_as(client, username, role)

    response = client.get("/stats")

    assert response.status_code in (302, 403)


def test_anonymous_user_cannot_access_statistics(client):
    response = client.get("/stats")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_empty_statistics_have_zero_counts(
    client, login_as
):
    login_as(client, "admin", "admin")

    stats = get_stats_context(client)

    assert stats["total_tickets"] == 0
    assert stats["open_tickets"] == 0
    assert stats["in_progress_tickets"] == 0
    assert stats["closed_tickets"] == 0
    assert stats["high_priority_tickets"] == 0
    assert stats["sla_met_count"] == 0
    assert stats["sla_missed_count"] == 0
    assert stats["overdue_tickets"] == 0

    assert len(stats["daily_stats"]) == 7
    assert all(
        day["total"] == 0
        for day in stats["daily_stats"]
    )


def test_stats_calculate_ticket_and_priority_counts(
    client, login_as, create_ticket, db
):
    first = create_ticket("employee")
    second = create_ticket("employee")
    third = create_ticket("other")

    db.execute(
        """
        UPDATE tickets
        SET priority = 'High'
        WHERE id = ?
        """,
        (first,),
    )

    db.execute(
        """
        UPDATE tickets
        SET status = 'In Progress', priority = 'Low'
        WHERE id = ?
        """,
        (second,),
    )

    db.execute(
        """
        UPDATE tickets
        SET status = 'Closed', sla_met = 'Yes'
        WHERE id = ?
        """,
        (third,),
    )
    db.commit()

    login_as(client, "admin", "admin")

    stats = get_stats_context(client)

    assert stats["total_tickets"] == 3
    assert stats["open_tickets"] == 1
    assert stats["in_progress_tickets"] == 1
    assert stats["closed_tickets"] == 1

    assert stats["high_priority_tickets"] == 1
    assert stats["medium_priority_tickets"] == 1
    assert stats["low_priority_tickets"] == 1

    assert stats["sla_met_count"] == 1

    priority_stats = {
        row["priority"]: row
        for row in stats["priority_stats"]
    }

    assert priority_stats["High"]["total"] == 1
    assert priority_stats["Medium"]["total"] == 1
    assert priority_stats["Low"]["total"] == 1

    assert priority_stats["High"]["percent"] == 33.3


def test_stats_exclude_closed_tickets_from_workload(
    client, login_as, create_ticket, db
):
    active = create_ticket("employee")
    closed = create_ticket("employee")

    db.execute(
        """
        UPDATE tickets
        SET status = 'In Progress',
            assigned_to = 'admin'
        WHERE id = ?
        """,
        (active,),
    )

    db.execute(
        """
        UPDATE tickets
        SET status = 'Closed',
            assigned_to = 'admin',
            completed_by = 'admin',
            sla_met = 'No'
        WHERE id = ?
        """,
        (closed,),
    )
    db.commit()

    login_as(client, "admin", "admin")

    stats = get_stats_context(client)

    workload = {
        row["assigned_to"]: row["total"]
        for row in stats["assigned_stats"]
    }

    completed = {
        row["completed_by"]: row["total"]
        for row in stats["completed_by_stats"]
    }

    misses = {
        row["assigned_to"]: row["total"]
        for row in stats["sla_missed_by_tech"]
    }

    assert workload["admin"] == 1
    assert completed["admin"] == 1
    assert misses["admin"] == 1
    assert stats["sla_missed_count"] == 1


def test_stats_group_technician_names_case_insensitively(
    client, login_as, create_ticket, db
):
    first = create_ticket("employee")
    second = create_ticket("employee")

    db.execute(
        """
        UPDATE tickets
        SET assigned_to = 'admin',
            status = 'In Progress'
        WHERE id = ?
        """,
        (first,),
    )

    db.execute(
        """
        UPDATE tickets
        SET assigned_to = 'ADMIN',
            status = 'In Progress'
        WHERE id = ?
        """,
        (second,),
    )
    db.commit()

    login_as(client, "admin", "admin")

    stats = get_stats_context(client)

    assert stats["assigned_stats"] == [
        {"assigned_to": "admin", "total": 2}
    ]


def test_stats_daily_trend_ignores_invalid_dates(
    client, login_as, create_ticket, db
):
    valid = create_ticket("employee")
    invalid = create_ticket("employee")

    today = datetime.now().strftime(
        "%m/%d/%Y %I:%M %p"
    )

    db.execute(
        """
        UPDATE tickets
        SET submitted_at = ?
        WHERE id = ?
        """,
        (today, valid),
    )

    db.execute(
        """
        UPDATE tickets
        SET submitted_at = 'invalid-date'
        WHERE id = ?
        """,
        (invalid,),
    )
    db.commit()

    login_as(client, "admin", "admin")

    stats = get_stats_context(client)

    assert stats["total_tickets"] == 2
    assert len(stats["daily_stats"]) == 7
    assert sum(
        day["total"]
        for day in stats["daily_stats"]
    ) == 1


def test_stats_calculate_department_percentages(
    client, login_as, create_ticket, db
):
    first = create_ticket("employee")
    second = create_ticket("employee")
    third = create_ticket("employee")

    db.execute(
        """
        UPDATE tickets
        SET department = 'IT'
        WHERE id = ?
        """,
        (third,),
    )
    db.commit()

    login_as(client, "admin", "admin")

    stats = get_stats_context(client)

    departments = {
        row["department"]: row
        for row in stats["department_stats"]
    }

    assert departments["Finance"]["total"] == 2
    assert departments["Finance"]["percent"] == 66.7

    assert departments["IT"]["total"] == 1
    assert departments["IT"]["percent"] == 33.3

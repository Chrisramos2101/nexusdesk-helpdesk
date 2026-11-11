
from unittest.mock import patch

import pytest


def setup_tickets(create_ticket, db):
    hardware = create_ticket(
        "employee", "Broken monitor"
    )
    network = create_ticket(
        "other", "Network connection failure"
    )
    software = create_ticket(
        "employee", "Software installation"
    )

    db.execute(
        """
        UPDATE tickets
        SET category = 'Hardware',
            priority = 'High',
            assigned_to = 'admin'
        WHERE id = ?
        """,
        (hardware,),
    )

    db.execute(
        """
        UPDATE tickets
        SET category = 'Network',
            priority = 'Low',
            status = 'In Progress',
            assigned_to = 'admin'
        WHERE id = ?
        """,
        (network,),
    )

    db.execute(
        """
        UPDATE tickets
        SET category = 'Software',
            priority = 'Medium',
            assigned_to = 'Unassigned'
        WHERE id = ?
        """,
        (software,),
    )

    db.commit()

    return hardware, network, software


@pytest.mark.parametrize(
    "query, expected_indexes",
    [
        ("status=Open&category=Hardware", {0}),
        ("status=Open&category=Software", {2}),
        ("status=In%20Progress", {1}),
        (
            "status=In%20Progress&assigned_to=admin",
            {1},
        ),
        ("status=Open&assigned_to=ADMIN", {0}),
        ("status=Open&priority=High", {0}),
        ("status=Open&priority=Medium", {2}),
        ("status=Open&search=monitor", {0}),
        ("status=Open&category=Invalid", {0, 2}),
    ],
)
def test_admin_dashboard_extended_filters(
    client, login_as, create_ticket, db,
    query, expected_indexes
):
    ids = setup_tickets(create_ticket, db)

    login_as(client, "admin", "admin")

    with patch(
        "routes.dashboard.render_template",
        return_value="Dashboard rendered",
    ) as mock_render:
        response = client.get(
            f"/dashboard?{query}"
        )

    assert response.status_code == 200

    context = mock_render.call_args.kwargs

    actual_ids = {
        ticket["id"]
        for ticket in context["tickets"]
    }

    expected_ids = {
        ids[index] for index in expected_indexes
    }

    assert actual_ids == expected_ids


def test_employee_cannot_view_admin_dashboard(
    client, login_as
):
    login_as(client, "employee", "employee")

    response = client.get("/dashboard")

    assert response.status_code in (302, 403)

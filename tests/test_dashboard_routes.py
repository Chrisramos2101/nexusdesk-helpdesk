
from unittest.mock import patch

import pytest


@pytest.mark.parametrize(
    "query, expected_indexes",
    [
        ("status=Open", {0, 1}),
        ("status=Closed", {2}),
        ("status=Open&priority=High", {0}),
        ("status=Open&assigned_to=Unassigned", {1}),
        ("status=Open&search=Network", {0}),
        ("status=Invalid", {0, 1}),
    ],
)
def test_admin_dashboard_filters_tickets(
    client, login_as, create_ticket, db,
    query, expected_indexes
):
    # Build three distinct test tickets.
    ids = [
        create_ticket("employee", "Network outage"),
        create_ticket("employee", "Printer issue"),
        create_ticket("other", "Laptop replacement"),
    ]

    db.execute(
        """
        UPDATE tickets
        SET priority = 'High',
            assigned_to = 'admin'
        WHERE id = ?
        """,
        (ids[0],),
    )

    db.execute(
        """
        UPDATE tickets
        SET status = 'Closed'
        WHERE id = ?
        """,
        (ids[2],),
    )
    db.commit()

    login_as(client, "admin", "admin")

    # Capture the dashboard's prepared data without
    # depending on the HTML template.
    with patch(
        "routes.dashboard.render_template",
        return_value="Dashboard rendered",
    ) as mock_render:
        response = client.get(f"/dashboard?{query}")

    assert response.status_code == 200
    mock_render.assert_called_once()

    context = mock_render.call_args.kwargs
    actual_ids = {
        ticket["id"] for ticket in context["tickets"]
    }
    expected_ids = {ids[i] for i in expected_indexes}

    assert actual_ids == expected_ids

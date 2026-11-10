
import pytest

from routes.tickets import calculate_sla_met


@pytest.mark.parametrize(
    "closed_at, sla_due_at, expected",
    [
        # Closed before deadline
        (
            "11/09/2026 02:00 PM",
            "11/09/2026 04:00 PM",
            "Yes",
        ),

        # Closed after deadline
        (
            "11/09/2026 05:00 PM",
            "11/09/2026 04:00 PM",
            "No",
        ),

        # Closed exactly at deadline
        (
            "11/09/2026 04:00 PM",
            "11/09/2026 04:00 PM",
            "Yes",
        ),
    ],
)
def test_sla_met_calculation(
    closed_at, sla_due_at, expected
):
    assert calculate_sla_met(
        closed_at, sla_due_at
    ) == expected



from datetime import datetime

from routes.tickets import calculate_sla_due_at


def test_high_priority_sla_skips_weekend():
    # Friday, November 6, 2026, at 3:00 PM.
    submitted_at = datetime(2026, 11, 6, 15, 0)

    # Four business hours:
    # Friday: 3 PM to 5 PM = 2 hours
    # Monday: 8 AM to 10 AM = 2 hours
    expected = "11/09/2026 10:00 AM"

    actual = calculate_sla_due_at(
        "High",
        submitted_at
    )

    assert actual == expected


@pytest.mark.parametrize(
    "priority, submitted_at, expected",
    [
        # Medium: 1 business day.
        # Friday -> Monday at the same time.
        (
            "Medium",
            datetime(2026, 11, 6, 10, 0),
            "11/09/2026 10:00 AM",
        ),

        # Low: 3 business days.
        # Friday -> Wednesday at the same time.
        (
            "Low",
            datetime(2026, 11, 6, 10, 0),
            "11/11/2026 10:00 AM",
        ),
    ],
)
def test_business_day_sla_deadlines(
    priority, submitted_at, expected
):
    actual = calculate_sla_due_at(
        priority,
        submitted_at
    )

    assert actual == expected

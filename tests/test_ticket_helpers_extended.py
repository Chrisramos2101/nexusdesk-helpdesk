
from datetime import datetime, timedelta

import pytest

from routes import tickets


@pytest.mark.parametrize(
    "filename, expected",
    [
        ("report.pdf", True),
        ("notes.TXT", True),
        ("picture.png", True),
        ("script.exe", False),
        ("no_extension", False),
    ],
)
def test_allowed_attachment_extensions(
    filename, expected
):
    assert tickets.allowed_file(filename) is expected


def test_closed_ticket_has_completed_status():
    assert tickets.get_sla_status({
        "status": "Closed",
        "sla_due_at": "",
    }) == "Completed"


def test_ticket_without_sla_has_no_sla_status():
    assert tickets.get_sla_status({
        "status": "Open",
        "sla_due_at": "",
    }) == "No SLA"


def test_overdue_ticket_status():
    past = datetime.now() - timedelta(days=2)

    result = tickets.get_sla_status({
        "status": "Open",
        "sla_due_at": past.strftime(
            "%m/%d/%Y %I:%M %p"
        ),
    })

    assert result == "Overdue"


def test_ticket_due_soon_status():
    due = datetime.now() + timedelta(minutes=30)

    result = tickets.get_sla_status({
        "status": "Open",
        "sla_due_at": due.strftime(
            "%m/%d/%Y %I:%M %p"
        ),
    })

    assert result == "Due Soon"


def test_ticket_on_track_status():
    due = datetime.now() + timedelta(hours=5)

    result = tickets.get_sla_status({
        "status": "Open",
        "sla_due_at": due.strftime(
            "%m/%d/%Y %I:%M %p"
        ),
    })

    assert result == "On Track"


def test_business_hours_before_opening():
    monday = datetime(2026, 11, 9, 6, 30)

    result = tickets.next_business_start(monday)

    assert result == datetime(2026, 11, 9, 8, 0)


def test_business_hours_after_closing():
    monday = datetime(2026, 11, 9, 18, 0)

    result = tickets.next_business_start(monday)

    assert result == datetime(2026, 11, 10, 8, 0)


def test_business_hours_skip_weekend():
    saturday = datetime(2026, 11, 14, 10, 0)

    result = tickets.next_business_start(saturday)

    assert result == datetime(2026, 11, 16, 8, 0)


def test_medium_priority_skips_weekend():
    friday = datetime(2026, 11, 13, 11, 0)

    result = tickets.calculate_sla_due_at(
        "Medium", friday
    )

    assert result == "11/16/2026 11:00 AM"


def test_low_priority_adds_three_business_days():
    monday = datetime(2026, 11, 9, 9, 0)

    result = tickets.calculate_sla_due_at(
        "Low", monday
    )

    assert result == "11/12/2026 09:00 AM"

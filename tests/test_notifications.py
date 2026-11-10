
from unittest.mock import patch

import pytest

from services import notification_service as notifications


@pytest.mark.parametrize(
    "priority, expected",
    [
        ("High", "4 business hours"),
        ("Medium", "1 business day"),
        ("Low", "3 business days"),
    ],
)
def test_priority_response_times(priority, expected):
    assert notifications.get_priority_response_time(
        priority
    ) == expected


def test_ticket_reference_format():
    assert notifications._ticket_reference(
        42
    ) == "NEX-2026-000042"


def test_notification_url_uses_configured_base(
    monkeypatch,
):
    monkeypatch.setenv(
        "APP_BASE_URL",
        "https://support.example.com/",
    )

    assert notifications._app_url(
        "/dashboard"
    ) == "https://support.example.com/dashboard"


def test_notification_url_missing_base_is_empty(
    monkeypatch,
):
    monkeypatch.delenv("APP_BASE_URL", raising=False)

    assert notifications._app_url(
        "/dashboard"
    ) == ""


def test_created_email_contains_correct_details():
    with patch(
        "services.notification_service.send_email",
        return_value=True,
    ) as mock_email:
        result = notifications.send_ticket_created_email(
            "employee@example.com",
            "employee",
            42,
            "High",
            "Hardware",
        )

    assert result is True
    mock_email.assert_called_once()

    subject, recipient, body, html_body = (
        mock_email.call_args.args
    )

    assert recipient == "employee@example.com"
    assert "NEX-2026-000042" in subject
    assert "4 business hours" in body
    assert "Hardware" in body
    assert "NEX-2026-000042" in html_body


def test_assignment_email_contains_ticket_reference():
    with patch(
        "services.notification_service.send_email",
        return_value=True,
    ) as mock_email:
        notifications.send_ticket_assigned_email(
            "admin@example.com",
            "admin",
            25,
        )

    subject, recipient, body, html_body = (
        mock_email.call_args.args
    )

    assert recipient == "admin@example.com"
    assert "NEX-2026-000025" in subject
    assert "Assigned to you" in body
    assert "Technician checklist" in html_body


@pytest.mark.parametrize(
    "sla_value, expected",
    [
        ("Yes", "Met"),
        ("No", "Missed"),
        (None, "Not Available"),
    ],
)
def test_closed_email_reports_sla_correctly(
    sla_value, expected
):
    with patch(
        "services.notification_service.send_email",
        return_value=True,
    ) as mock_email:
        notifications.send_ticket_closed_email(
            "employee@example.com",
            "employee",
            19,
            "2 hr 15 min",
            sla_value,
        )

    _, _, body, html_body = (
        mock_email.call_args.args
    )

    assert f"SLA: {expected}" in body
    assert expected in html_body
    assert "2 hr 15 min" in body


def test_mention_email_escapes_html_in_comment():
    unsafe_note = "<script>alert('test')</script>\nCheck"

    with patch(
        "services.notification_service.send_email",
        return_value=True,
    ) as mock_email:
        notifications.send_mention_email(
            "admin@example.com",
            "admin",
            17,
            unsafe_note,
        )

    _, recipient, body, html_body = (
        mock_email.call_args.args
    )

    assert recipient == "admin@example.com"
    assert unsafe_note in body

    # User-controlled markup must not become HTML.
    assert "<script>" not in html_body
    assert "&lt;script&gt;" in html_body
    assert "<br>" in html_body


def test_email_button_escapes_url_and_label():
    result = notifications._email_button(
        "<Open Ticket>",
        'https://example.com/?a=1&b="test"',
    )

    assert "&lt;Open Ticket&gt;" in result
    assert "&amp;" in result
    assert "&quot;" in result
    assert "<Open Ticket>" not in result


def test_email_button_omits_missing_url():
    assert notifications._email_button(
        "Open Ticket", ""
    ) == ""


from unittest.mock import patch

import pytest

from services import notification_service as notifications


@pytest.mark.parametrize(
    "value, expected",
    [
        (None, "NEX-2026-None"),
        ("invalid", "NEX-2026-invalid"),
        ("7", "NEX-2026-000007"),
    ],
)
def test_ticket_reference_edge_cases(value, expected):
    assert notifications._ticket_reference(value) == expected


def test_app_url_adds_missing_slash(monkeypatch):
    monkeypatch.setenv(
        "APP_BASE_URL",
        "https://support.example.com/",
    )

    assert notifications._app_url(
        "dashboard"
    ) == "https://support.example.com/dashboard"


def test_missing_app_url_returns_empty(monkeypatch):
    monkeypatch.delenv("APP_BASE_URL", raising=False)

    assert notifications._app_url("dashboard") == ""


def test_html_escaping_handles_none():
    assert notifications._safe(None) == ""


@pytest.mark.parametrize(
    "value, expected",
    [
        ("true", "Met"),
        ("MET", "Met"),
        ("false", "Missed"),
        ("missed", "Missed"),
        ("Pending", "Pending"),
        ("", "Not Available"),
    ],
)
def test_closed_notification_normalizes_sla(
    value, expected
):
    with patch.object(
        notifications,
        "send_email",
        return_value=True,
    ) as mock_email:
        result = notifications.send_ticket_closed_email(
            "employee@example.com",
            "employee",
            10,
            "",
            value,
        )

    assert result is True

    _, _, body, html_body = mock_email.call_args.args

    assert f"SLA: {expected}" in body
    assert "Not Available" in body
    assert expected in html_body


def test_mention_email_escapes_html_username():
    with patch.object(
        notifications,
        "send_email",
        return_value=True,
    ) as mock_email:
        notifications.send_mention_email(
            "employee@example.com",
            "<script>alert(1)</script>",
            15,
            "Review this ticket",
        )

    _, _, _, html_body = mock_email.call_args.args

    assert "<script>" not in html_body
    assert "&lt;script&gt;" in html_body

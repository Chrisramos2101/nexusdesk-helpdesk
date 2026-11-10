
import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from services import email_service


@pytest.mark.parametrize(
    "subject, recipient, body",
    [
        ("", "employee@example.com", "Hello"),
        ("Update", "", "Hello"),
        ("Update", "employee@example.com", ""),
    ],
)
def test_email_rejects_missing_required_fields(
    subject, recipient, body
):
    with (
        patch.object(email_service, "log_system_event") as log,
        patch.object(email_service, "_send_via_brevo") as brevo,
        patch.object(email_service, "_send_via_smtp") as smtp,
    ):
        result = email_service.send_email(
            subject, recipient, body
        )

    assert result is False
    log.assert_called_once()
    brevo.assert_not_called()
    smtp.assert_not_called()


def test_send_email_selects_brevo_when_configured(
    monkeypatch,
):
    monkeypatch.setenv("BREVO_API_KEY", "test-key")
    monkeypatch.setenv(
        "BREVO_SENDER_EMAIL",
        "support@example.com",
    )

    with (
        patch.object(
            email_service,
            "_send_via_brevo",
            return_value=True,
        ) as brevo,
        patch.object(email_service, "_send_via_smtp") as smtp,
    ):
        result = email_service.send_email(
            "  Ticket Update  ",
            " employee@example.com ",
            "  Ticket received  ",
            "<p>Received</p>",
        )

    assert result is True
    brevo.assert_called_once_with(
        "Ticket Update",
        "employee@example.com",
        "Ticket received",
        "<p>Received</p>",
    )
    smtp.assert_not_called()


def test_send_email_uses_smtp_without_brevo(
    monkeypatch,
):
    monkeypatch.delenv("BREVO_API_KEY", raising=False)
    monkeypatch.delenv(
        "BREVO_SENDER_EMAIL", raising=False
    )

    with (
        patch.object(
            email_service,
            "_send_via_smtp",
            return_value=True,
        ) as smtp,
        patch.object(email_service, "_send_via_brevo") as brevo,
    ):
        result = email_service.send_email(
            "Test", "employee@example.com", "Hello"
        )

    assert result is True
    smtp.assert_called_once()
    brevo.assert_not_called()


@pytest.mark.parametrize(
    "status, expected",
    [
        (201, True),
        (503, False),
    ],
)
def test_brevo_checks_response_status(
    monkeypatch, status, expected
):
    monkeypatch.setenv("BREVO_API_KEY", "test-api-key")
    monkeypatch.setenv(
        "BREVO_SENDER_EMAIL",
        "support@example.com",
    )

    response = MagicMock()
    response.__enter__.return_value.status = status

    with patch.object(
        email_service.urllib.request,
        "urlopen",
        return_value=response,
    ) as urlopen:
        result = email_service._send_via_brevo(
            "Ticket created",
            "employee@example.com",
            "Your ticket was created.",
            "<p>Your ticket was created.</p>",
        )

    assert result is expected
    urlopen.assert_called_once()

    request = urlopen.call_args.args[0]
    payload = json.loads(
        request.data.decode("utf-8")
    )

    assert payload["to"][0]["email"] == (
        "employee@example.com"
    )
    assert payload["subject"] == "Ticket created"
    assert payload["htmlContent"] == (
        "<p>Your ticket was created.</p>"
    )
    assert request.get_method() == "POST"


def test_brevo_http_error_is_logged(
    monkeypatch,
):
    monkeypatch.setenv("BREVO_API_KEY", "test-api-key")
    monkeypatch.setenv(
        "BREVO_SENDER_EMAIL",
        "support@example.com",
    )

    error = urllib.error.HTTPError(
        "https://api.brevo.com/v3/smtp/email",
        429,
        "Too Many Requests",
        {},
        None,
    )

    with (
        patch.object(
            email_service.urllib.request,
            "urlopen",
            side_effect=error,
        ),
        patch.object(
            email_service,
            "log_system_event",
        ) as log,
    ):
        result = email_service._send_via_brevo(
            "Test",
            "employee@example.com",
            "Hello",
        )

    assert result is False
    log.assert_called_once()

    assert "429" in log.call_args.args[1]


def test_brevo_network_error_is_logged(
    monkeypatch,
):
    monkeypatch.setenv("BREVO_API_KEY", "test-api-key")
    monkeypatch.setenv(
        "BREVO_SENDER_EMAIL",
        "support@example.com",
    )

    with (
        patch.object(
            email_service.urllib.request,
            "urlopen",
            side_effect=urllib.error.URLError(
                "Connection refused"
            ),
        ),
        patch.object(
            email_service,
            "log_system_event",
        ) as log,
    ):
        result = email_service._send_via_brevo(
            "Test",
            "employee@example.com",
            "Hello",
        )

    assert result is False
    assert "network error" in (
        log.call_args.args[1].lower()
    )


def test_smtp_message_contains_text_and_html():
    with (
        patch.object(email_service, "Message") as message,
        patch.object(email_service.mail, "send") as send,
    ):
        result = email_service._send_via_smtp(
            "Ticket update",
            "employee@example.com",
            "Plain text body",
            "<p>HTML body</p>",
        )

    assert result is True
    message.assert_called_once_with(
        subject="Ticket update",
        recipients=["employee@example.com"],
    )

    msg = message.return_value
    assert msg.body == "Plain text body"
    assert msg.html == "<p>HTML body</p>"
    send.assert_called_once_with(msg)


def test_smtp_failure_is_logged():
    with (
        patch.object(email_service, "Message"),
        patch.object(
            email_service.mail,
            "send",
            side_effect=RuntimeError("SMTP unavailable"),
        ),
        patch.object(
            email_service,
            "log_system_event",
        ) as log,
    ):
        result = email_service._send_via_smtp(
            "Test",
            "employee@example.com",
            "Hello",
        )

    assert result is False
    log.assert_called_once()
    assert "SMTP" in log.call_args.args[1]

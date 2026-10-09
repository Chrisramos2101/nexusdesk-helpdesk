import json
import os
import urllib.error
import urllib.request

from flask_mail import Mail, Message

from services.monitoring_service import log_system_event


mail = Mail()


BREVO_ENDPOINT = "https://api.brevo.com/v3/smtp/email"
EMAIL_TIMEOUT_SECONDS = 12


def _brevo_is_configured() -> bool:
    """
    Return True when the minimum Brevo configuration
    required for transactional email is available.
    """

    return bool(
        os.getenv("BREVO_API_KEY", "").strip()
        and os.getenv("BREVO_SENDER_EMAIL", "").strip()
    )


def _normalize_email_value(value: str | None) -> str:
    """
    Normalize email-related text values without altering
    the actual contents of valid addresses or messages.
    """

    if value is None:
        return ""

    return str(value).strip()


def _send_via_brevo(
    subject: str,
    recipient: str,
    body: str,
    html_body: str | None = None
) -> bool:
    """
    Send a transactional email through the Brevo HTTPS API.

    Returns True when Brevo accepts the message and False
    when the request fails.
    """

    api_key = os.getenv(
        "BREVO_API_KEY",
        ""
    ).strip()

    sender_email = os.getenv(
        "BREVO_SENDER_EMAIL",
        ""
    ).strip()

    sender_name = (
        os.getenv(
            "BREVO_SENDER_NAME",
            "NexusDesk"
        ).strip()
        or "NexusDesk"
    )

    payload = {
        "sender": {
            "email": sender_email,
            "name": sender_name,
        },
        "to": [
            {
                "email": recipient
            }
        ],
        "subject": subject,
        "textContent": body,
    }

    if html_body:
        payload["htmlContent"] = html_body

    request = urllib.request.Request(
        BREVO_ENDPOINT,
        data=json.dumps(
            payload
        ).encode("utf-8"),
        headers={
            "accept": "application/json",
            "api-key": api_key,
            "content-type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=EMAIL_TIMEOUT_SECONDS
        ) as response:

            status = getattr(
                response,
                "status",
                200
            )

            return 200 <= status < 300

    except urllib.error.HTTPError as exc:
        detail = ""

        try:
            detail = (
                exc.read()
                .decode(
                    "utf-8",
                    errors="replace"
                )[:500]
            )

        except Exception:
            pass

        log_system_event(
            "EMAIL_ERROR",
            (
                f"Brevo HTTP {exc.code}: "
                f"{detail or exc.reason}"
            ),
        )

        return False

    except urllib.error.URLError as exc:
        log_system_event(
            "EMAIL_ERROR",
            (
                "Brevo network error: "
                f"{exc.reason}"
            ),
        )

        return False

    except Exception as exc:
        log_system_event(
            "EMAIL_ERROR",
            (
                "Brevo "
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        )

        return False


def _send_via_smtp(
    subject: str,
    recipient: str,
    body: str,
    html_body: str | None = None
) -> bool:
    """
    Send email using Flask-Mail.

    This acts as the local/development transport when
    Brevo is not configured.
    """

    try:
        msg = Message(
            subject=subject,
            recipients=[
                recipient
            ]
        )

        msg.body = body

        if html_body:
            msg.html = html_body

        mail.send(msg)

        return True

    except Exception as exc:
        log_system_event(
            "EMAIL_ERROR",
            (
                "SMTP "
                f"{type(exc).__name__}: "
                f"{exc}"
            )
        )

        return False


def send_email(
    subject: str,
    recipient: str,
    body: str,
    html_body: str | None = None
) -> bool:
    """
    Send a NexusDesk transactional email.

    Production/cloud:
        Brevo HTTPS API

    Local/development:
        Flask-Mail / SMTP

    Both plain-text and HTML content are supported.
    """

    subject = _normalize_email_value(
        subject
    )

    recipient = _normalize_email_value(
        recipient
    )

    body = (
        ""
        if body is None
        else str(body).strip()
    )

    html_body = (
        None
        if html_body is None
        else str(html_body).strip()
    )

    if not subject:
        log_system_event(
            "EMAIL_ERROR",
            "Email was not sent because the subject was empty."
        )

        return False

    if not recipient:
        log_system_event(
            "EMAIL_ERROR",
            "Email was not sent because the recipient was empty."
        )

        return False

    if not body and not html_body:
        log_system_event(
            "EMAIL_ERROR",
            "Email was not sent because the message body was empty."
        )

        return False

    if _brevo_is_configured():
        return _send_via_brevo(
            subject,
            recipient,
            body,
            html_body
        )

    return _send_via_smtp(
        subject,
        recipient,
        body,
        html_body
    )
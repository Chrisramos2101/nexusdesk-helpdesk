import json
import os
import urllib.error
import urllib.request

from flask_mail import Mail, Message

from services.monitoring_service import log_system_event

mail = Mail()

BREVO_ENDPOINT = "https://api.brevo.com/v3/smtp/email"


def _brevo_is_configured() -> bool:
    return bool(
        os.getenv("BREVO_API_KEY", "").strip()
        and os.getenv("BREVO_SENDER_EMAIL", "").strip()
    )


def _send_via_brevo(subject: str, recipient: str, body: str) -> bool:
    api_key = os.getenv("BREVO_API_KEY", "").strip()
    sender_email = os.getenv("BREVO_SENDER_EMAIL", "").strip()
    sender_name = os.getenv("BREVO_SENDER_NAME", "NexusDesk").strip() or "NexusDesk"

    payload = {
        "sender": {
            "email": sender_email,
            "name": sender_name,
        },
        "to": [{"email": recipient}],
        "subject": subject,
        "textContent": body,
    }

    request = urllib.request.Request(
        BREVO_ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "accept": "application/json",
            "api-key": api_key,
            "content-type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            status = getattr(response, "status", 200)
            return 200 <= status < 300
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            pass
        log_system_event(
            "EMAIL_ERROR",
            f"Brevo HTTP {exc.code}: {detail or exc.reason}",
        )
        return False
    except Exception as exc:
        log_system_event(
            "EMAIL_ERROR",
            f"Brevo {type(exc).__name__}: {exc}",
        )
        return False


def _send_via_smtp(subject: str, recipient: str, body: str) -> bool:
    try:
        msg = Message(subject=subject, recipients=[recipient])
        msg.body = body
        mail.send(msg)
        return True
    except Exception as exc:
        log_system_event("EMAIL_ERROR", f"SMTP {type(exc).__name__}: {exc}")
        return False


def send_email(subject: str, recipient: str, body: str) -> bool:
    """Send transactional email using HTTPS in cloud, SMTP as local fallback."""
    if _brevo_is_configured():
        return _send_via_brevo(subject, recipient, body)

    return _send_via_smtp(subject, recipient, body)

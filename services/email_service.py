from flask_mail import Mail, Message

from services.monitoring_service import log_system_event

mail = Mail()


def send_email(subject: str, recipient: str, body: str) -> bool:
    """Send email without allowing an SMTP outage to crash the web request."""
    try:
        msg = Message(subject=subject, recipients=[recipient])
        msg.body = body
        mail.send(msg)
        return True
    except Exception as exc:
        log_system_event("EMAIL_ERROR", f"{type(exc).__name__}: {exc}")
        return False

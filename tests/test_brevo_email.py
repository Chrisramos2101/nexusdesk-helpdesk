import json
from io import BytesIO

from services import email_service


class FakeResponse:
    status = 201

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_brevo_email_uses_https_api(monkeypatch):
    monkeypatch.setenv("BREVO_API_KEY", "test-api-key")
    monkeypatch.setenv("BREVO_SENDER_EMAIL", "verified@example.com")
    monkeypatch.setenv("BREVO_SENDER_NAME", "NexusDesk")

    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(email_service.urllib.request, "urlopen", fake_urlopen)

    assert email_service.send_email(
        "Test subject",
        "recipient@example.com",
        "Hello",
    )

    assert captured["url"] == email_service.BREVO_ENDPOINT
    assert captured["body"]["sender"]["email"] == "verified@example.com"
    assert captured["body"]["to"][0]["email"] == "recipient@example.com"
    assert captured["body"]["subject"] == "Test subject"
    assert captured["body"]["textContent"] == "Hello"
    assert captured["headers"]["Api-key"] == "test-api-key"


def test_email_falls_back_to_smtp_when_brevo_missing(monkeypatch):
    monkeypatch.delenv("BREVO_API_KEY", raising=False)
    monkeypatch.delenv("BREVO_SENDER_EMAIL", raising=False)

    called = {}

    def fake_smtp(subject, recipient, body):
        called["values"] = (subject, recipient, body)
        return True

    monkeypatch.setattr(email_service, "_send_via_smtp", fake_smtp)

    assert email_service.send_email("Subject", "user@example.com", "Body")
    assert called["values"] == ("Subject", "user@example.com", "Body")

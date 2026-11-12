"""Batch 2 security checks. Real PostgreSQL integration is a separate runner."""
import pytest
from flask import Flask
from services.recruiter_demo_guard import register_recruiter_demo_guard


def make_client(monkeypatch, db_url="postgresql://recruiter_demo_app:dummy@localhost:5432/nexusdesk_recruiter_demo"):
    monkeypatch.setenv("RECRUITER_DEMO_MODE", "true")
    monkeypatch.setenv("DATABASE_URL", db_url)
    app = Flask(__name__)
    app.secret_key = "test-only"
    app.config["RECRUITER_STRICT_ENDPOINTS"] = True
    @app.get("/", endpoint="tickets.home")
    def home():
        return "home"
    @app.get("/dashboard", endpoint="dashboard.dashboard")
    def dashboard():
        return "dashboard"
    @app.get("/profile", endpoint="auth.profile")
    def profile():
        return "profile"
    @app.get("/unknown", endpoint="unknown.read")
    def unknown():
        return "unknown"
    register_recruiter_demo_guard(app)
    return app.test_client()


def test_strict_demo_allows_known_read_endpoints(monkeypatch):
    client = make_client(monkeypatch)
    assert client.get("/").status_code == 200
    assert client.get("/dashboard").status_code == 200


def test_strict_demo_rejects_unknown_get_and_sensitive_profile(monkeypatch):
    client = make_client(monkeypatch)
    assert client.get("/unknown").status_code == 404
    assert client.get("/profile").status_code == 403


def test_demo_refuses_non_reader_login_on_full_app(monkeypatch):
    with pytest.raises(RuntimeError, match="SAFETY STOP"):
        make_client(monkeypatch, "postgresql://restore_admin:dummy@localhost:5432/nexusdesk_recruiter_demo")


def test_demo_refuses_empty_password_on_full_app(monkeypatch):
    with pytest.raises(RuntimeError, match="SAFETY STOP"):
        make_client(monkeypatch, "postgresql://recruiter_demo_app@localhost:5432/nexusdesk_recruiter_demo")

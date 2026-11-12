
import pytest
from flask import Flask

from routes import recruiter_demo
from routes.recruiter_demo import recruiter_demo_bp
from services.recruiter_demo_guard import (
    register_recruiter_demo_guard,
)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("RECRUITER_DEMO_MODE", "true")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://test:test@localhost:5432/nexusdesk_recruiter_demo",
    )

    app = Flask(__name__)
    app.secret_key = "recruiter-test-secret"

    app.register_blueprint(recruiter_demo_bp)
    register_recruiter_demo_guard(app)

    def fake_get_user(username):
        accounts = {
            "Demo_Admin": {
                "username": "Demo_Admin",
                "role": "admin",
            },
            "Demo_Employee": {
                "username": "Demo_Employee",
                "role": "employee",
            },
        }
        return accounts.get(username)

    monkeypatch.setattr(
        recruiter_demo,
        "get_user_by_username",
        fake_get_user,
    )

    return app.test_client()


def test_admin_demo_entry(client):
    response = client.post(
        "/recruiter-demo/enter",
        data={"role": "admin"},
    )

    assert response.status_code == 302
    assert response.location.endswith("/dashboard")

    with client.session_transaction() as session:
        assert session["username"] == "Demo_Admin"
        assert session["role"] == "admin"
        assert session["recruiter_demo"] is True


def test_employee_demo_entry(client):
    response = client.post(
        "/recruiter-demo/enter",
        data={"role": "employee"},
    )

    assert response.status_code == 302
    assert response.location.endswith("/")

    with client.session_transaction() as session:
        assert session["username"] == "Demo_Employee"
        assert session["role"] == "employee"
        assert session["recruiter_demo"] is True


def test_invalid_demo_role_rejected(client):
    response = client.post(
        "/recruiter-demo/enter",
        data={"role": "superadmin"},
    )

    assert response.status_code == 400


def test_missing_demo_role_rejected(client):
    response = client.post(
        "/recruiter-demo/enter",
        data={},
    )

    assert response.status_code == 400


def test_demo_entry_unavailable_outside_demo_mode(
    client, monkeypatch
):
    monkeypatch.setenv("RECRUITER_DEMO_MODE", "false")

    response = client.post(
        "/recruiter-demo/enter",
        data={"role": "admin"},
    )

    assert response.status_code == 404


def test_demo_accounts_must_exist(client, monkeypatch):
    monkeypatch.setattr(
        recruiter_demo,
        "get_user_by_username",
        lambda username: None,
    )

    response = client.post(
        "/recruiter-demo/enter",
        data={"role": "admin"},
    )

    assert response.status_code == 503


def test_other_post_requests_remain_blocked(client):
    response = client.post("/login")

    assert response.status_code == 403


def test_demo_entry_rejects_get(client):
    response = client.get("/recruiter-demo/enter")

    assert response.status_code == 405

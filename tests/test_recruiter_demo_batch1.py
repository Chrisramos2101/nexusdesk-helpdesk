"""Additional demo guard + GET-side-effect regression tests."""
import pytest
from flask import Flask

from services.recruiter_demo_guard import register_recruiter_demo_guard


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("RECRUITER_DEMO_MODE", "true")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://test:test@localhost:5432/nexusdesk_recruiter_demo",
    )
    app = Flask(__name__)
    app.secret_key = "test-only-secret"
    register_recruiter_demo_guard(app)
    @app.get("/login", endpoint="auth.login")
    def login():
        return "should not appear"
    @app.get("/reset/123", endpoint="auth.reset_password")
    def reset_password():
        return "should not appear"
    @app.get("/attachment/abc", endpoint="tickets.download_attachment")
    def attachment():
        return "should not appear"
    @app.get("/dashboard", endpoint="dashboard.dashboard")
    def dashboard():
        return "dashboard"
    @app.get("/logout", endpoint="auth.logout")
    def logout():
        return "logout"
    return app.test_client()


def test_normal_login_redirects_to_demo(client):
    response = client.get("/login")
    assert response.status_code == 302
    assert response.location.endswith("/recruiter-demo/")


@pytest.mark.parametrize("path", ["/reset/123", "/attachment/abc"])
def test_sensitive_get_routes_are_blocked(client, path):
    assert client.get(path).status_code == 403


def test_read_only_get_is_available_and_not_cached(client):
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store, private"
    assert response.headers["X-Robots-Tag"] == "noindex, nofollow"


def test_logout_get_remains_available(client):
    assert client.get("/logout").status_code == 200


def test_demo_logout_does_not_open_database(monkeypatch):
    from routes import auth
    monkeypatch.setenv("RECRUITER_DEMO_MODE", "true")
    def forbidden_database():
        raise AssertionError("Demo logout accessed database")
    monkeypatch.setattr(auth, "get_db_connection", forbidden_database)
    app = Flask(__name__)
    app.secret_key = "test-only-secret"
    app.register_blueprint(auth.auth_bp)
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["username"] = "Demo_Employee"
            sess["recruiter_demo"] = True
        response = client.get("/logout")
        assert response.status_code == 302
        assert response.location.endswith("/recruiter-demo/")
        with client.session_transaction() as sess:
            assert "username" not in sess


def test_demo_article_view_does_not_open_database(monkeypatch):
    from routes import knowledge
    monkeypatch.setenv("RECRUITER_DEMO_MODE", "true")
    def forbidden_database():
        raise AssertionError("Demo article view accessed database")
    monkeypatch.setattr(knowledge, "get_db_connection", forbidden_database)
    app = Flask(__name__)
    with app.test_request_context("/knowledge_base/password-reset"):
        knowledge.track_article_view("password-reset")

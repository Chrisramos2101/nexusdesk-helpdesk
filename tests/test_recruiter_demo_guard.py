
import pytest
from flask import Flask

from services.recruiter_demo_guard import (
    register_recruiter_demo_guard,
    validate_recruiter_demo_database,
)


# ============================================================
# TEST 1: Normal NexusDesk mode allows POST requests
# ============================================================

def test_normal_mode_allows_post(monkeypatch):
    monkeypatch.delenv("RECRUITER_DEMO_MODE", raising=False)

    app = Flask(__name__)
    register_recruiter_demo_guard(app)

    @app.route("/test", methods=["GET", "POST"])
    def test_route():
        return "OK"

    response = app.test_client().post("/test")

    assert response.status_code == 200


# ============================================================
# TEST 2: Recruiter mode blocks POST requests
# ============================================================

def test_recruiter_mode_blocks_post(monkeypatch):
    monkeypatch.setenv("RECRUITER_DEMO_MODE", "true")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://test:test@localhost:5432/nexusdesk_recruiter_demo",
    )

    app = Flask(__name__)
    register_recruiter_demo_guard(app)

    @app.route("/test", methods=["GET", "POST"])
    def test_route():
        return "OK"

    response = app.test_client().post("/test")

    assert response.status_code == 403


# ============================================================
# TEST 3: Recruiter mode allows GET requests
# ============================================================

def test_recruiter_mode_allows_get(monkeypatch):
    monkeypatch.setenv("RECRUITER_DEMO_MODE", "true")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://test:test@localhost:5432/nexusdesk_recruiter_demo",
    )

    app = Flask(__name__)
    register_recruiter_demo_guard(app)

    @app.route("/test", methods=["GET", "POST"])
    def test_route():
        return "OK"

    response = app.test_client().get("/test")

    assert response.status_code == 200


# ============================================================
# TEST 4: Recruiter mode blocks PUT, PATCH, and DELETE
# ============================================================

def test_recruiter_mode_blocks_put_patch_delete(monkeypatch):
    monkeypatch.setenv("RECRUITER_DEMO_MODE", "true")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://test:test@localhost:5432/nexusdesk_recruiter_demo",
    )

    app = Flask(__name__)
    register_recruiter_demo_guard(app)

    @app.route(
        "/test",
        methods=["GET", "PUT", "PATCH", "DELETE"],
    )
    def test_route():
        return "OK"

    client = app.test_client()

    for method in ("PUT", "PATCH", "DELETE"):
        response = client.open("/test", method=method)

        assert response.status_code == 403


# ============================================================
# TEST 5: Recruiter mode rejects the original database
# ============================================================

def test_demo_rejects_original_database(monkeypatch):
    monkeypatch.setenv("RECRUITER_DEMO_MODE", "true")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://test:test@localhost:5432/nexusdesk_original",
    )

    with pytest.raises(RuntimeError, match="SAFETY STOP"):
        validate_recruiter_demo_database()


# ============================================================
# TEST 6: Recruiter mode accepts the isolated database
# ============================================================

def test_demo_accepts_isolated_database(monkeypatch):
    monkeypatch.setenv("RECRUITER_DEMO_MODE", "true")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://test:test@localhost:5432/nexusdesk_recruiter_demo",
    )

    validate_recruiter_demo_database()


# ============================================================
# TEST 7: Recruiter mode rejects SQLite databases
# ============================================================

def test_demo_rejects_sqlite(monkeypatch):
    monkeypatch.setenv("RECRUITER_DEMO_MODE", "true")
    monkeypatch.setenv(
        "DATABASE_URL",
        "helpdesk.db",
    )

    with pytest.raises(RuntimeError, match="SAFETY STOP"):
        validate_recruiter_demo_database()

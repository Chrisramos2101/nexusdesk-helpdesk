def test_health_endpoint_reports_healthy_sqlite(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.get_json() == {
        "application": "NexusDesk",
        "database": "sqlite",
        "status": "healthy",
    }


def test_security_headers_are_present(client):
    response = client.get("/login")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]


def test_csrf_rejects_unprotected_post_when_enabled(client, app):
    app.config["WTF_CSRF_ENABLED"] = True
    try:
        response = client.post(
            "/login",
            data={"username": "employee", "password": "Password1!"},
        )
        assert response.status_code == 400
    finally:
        app.config["WTF_CSRF_ENABLED"] = False

from services.production_config import (
    get_app_base_url,
    validate_production_environment,
)


def _cloud_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "x" * 64)
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://user:password@postgres.internal/nexusdesk",
    )
    monkeypatch.setenv("UPLOAD_FOLDER", str(tmp_path / "uploads"))
    monkeypatch.setenv("TRUST_PROXY_HEADERS", "True")


def test_render_hostname_becomes_https_base_url(monkeypatch):
    monkeypatch.delenv("APP_BASE_URL", raising=False)
    monkeypatch.setenv(
        "RENDER_EXTERNAL_HOSTNAME",
        "nexusdesk-helpdesk-example.onrender.com",
    )

    assert (
        get_app_base_url()
        == "https://nexusdesk-helpdesk-example.onrender.com"
    )


def test_explicit_app_base_url_wins(monkeypatch):
    monkeypatch.setenv("APP_BASE_URL", "https://support.example.com/")
    monkeypatch.setenv(
        "RENDER_EXTERNAL_HOSTNAME",
        "nexusdesk-helpdesk-example.onrender.com",
    )

    assert get_app_base_url() == "https://support.example.com"


def test_render_production_validation_without_manual_app_base_url(
    monkeypatch,
    tmp_path,
):
    _cloud_environment(monkeypatch, tmp_path)
    monkeypatch.delenv("APP_BASE_URL", raising=False)
    monkeypatch.setenv(
        "RENDER_EXTERNAL_HOSTNAME",
        "nexusdesk-helpdesk-example.onrender.com",
    )

    validate_production_environment()

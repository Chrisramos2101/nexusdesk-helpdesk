
from pathlib import Path

import pytest

from services import production_config as config


def configure_safe_production(monkeypatch, tmp_path):
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "S" * 40)
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://user:pass@localhost/test",
    )
    monkeypatch.setenv(
        "APP_BASE_URL",
        "https://nexusdesk.example.com",
    )
    monkeypatch.setenv(
        "UPLOAD_FOLDER",
        str(tmp_path / "uploads"),
    )
    monkeypatch.setenv("TRUST_PROXY_HEADERS", "true")


def test_production_mode_detection(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", " production ")

    assert config.is_production() is True

    monkeypatch.setenv("FLASK_ENV", "testing")

    assert config.is_production() is False


def test_legacy_postgres_url_is_normalized(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgres://user:pass@localhost/test",
    )

    assert config._database_url().startswith(
        "postgresql://"
    )


def test_render_hostname_builds_https_url(monkeypatch):
    monkeypatch.delenv("APP_BASE_URL", raising=False)
    monkeypatch.setenv(
        "RENDER_EXTERNAL_HOSTNAME",
        "nexusdesk.example.com",
    )

    assert config.get_app_base_url() == (
        "https://nexusdesk.example.com"
    )


def test_valid_production_configuration(
    monkeypatch, tmp_path
):
    configure_safe_production(monkeypatch, tmp_path)

    config.validate_production_environment()


@pytest.mark.parametrize(
    "variable, value, expected_error",
    [
        ("SECRET_KEY", "short", "SECRET_KEY"),
        (
            "DATABASE_URL",
            "sqlite:///test.db",
            "PostgreSQL",
        ),
        (
            "APP_BASE_URL",
            "http://localhost:5000",
            "HTTPS",
        ),
        (
            "UPLOAD_FOLDER",
            "relative/uploads",
            "absolute path",
        ),
        (
            "TRUST_PROXY_HEADERS",
            "false",
            "TRUST_PROXY_HEADERS",
        ),
    ],
)
def test_unsafe_production_settings_are_rejected(
    monkeypatch, tmp_path,
    variable, value, expected_error
):
    configure_safe_production(monkeypatch, tmp_path)

    monkeypatch.setenv(variable, value)

    with pytest.raises(
        RuntimeError, match=expected_error
    ):
        config.validate_production_environment()


def test_nonproduction_skips_production_validation(
    monkeypatch
):
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.setenv("SECRET_KEY", "")

    config.validate_production_environment()


def test_runtime_upload_directory_is_created(
    monkeypatch, tmp_path
):
    upload_path = tmp_path / "new_uploads"

    monkeypatch.setenv(
        "UPLOAD_FOLDER",
        str(upload_path),
    )

    config.prepare_runtime_directories()

    assert upload_path.is_dir()

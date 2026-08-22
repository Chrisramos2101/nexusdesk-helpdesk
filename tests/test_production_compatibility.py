import importlib.util
import os
from pathlib import Path

import pytest

from database.config import _normalize_database_url
from services.production_config import (
    prepare_runtime_directories,
    validate_production_environment,
)


def test_normalizes_legacy_postgres_scheme():
    assert (
        _normalize_database_url("postgres://user:pass@db/example")
        == "postgresql://user:pass@db/example"
    )


def test_production_validation_accepts_cloud_shape(monkeypatch, tmp_path):
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "x" * 64)
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://user:password@postgres.internal/nexusdesk",
    )
    monkeypatch.setenv("APP_BASE_URL", "https://nexusdesk.example.com")
    monkeypatch.setenv("UPLOAD_FOLDER", str(tmp_path / "uploads"))
    monkeypatch.setenv("TRUST_PROXY_HEADERS", "True")

    validate_production_environment()


def test_production_validation_rejects_sqlite(monkeypatch, tmp_path):
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "x" * 64)
    monkeypatch.setenv("DATABASE_URL", "helpdesk.db")
    monkeypatch.setenv("APP_BASE_URL", "https://nexusdesk.example.com")
    monkeypatch.setenv("UPLOAD_FOLDER", str(tmp_path / "uploads"))
    monkeypatch.setenv("TRUST_PROXY_HEADERS", "True")

    with pytest.raises(RuntimeError, match="PostgreSQL"):
        validate_production_environment()


def test_production_validation_rejects_non_https_base_url(monkeypatch, tmp_path):
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "x" * 64)
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://user:password@postgres.internal/nexusdesk",
    )
    monkeypatch.setenv("APP_BASE_URL", "http://nexusdesk.example.com")
    monkeypatch.setenv("UPLOAD_FOLDER", str(tmp_path / "uploads"))
    monkeypatch.setenv("TRUST_PROXY_HEADERS", "True")

    with pytest.raises(RuntimeError, match="HTTPS"):
        validate_production_environment()


def test_prepare_runtime_directories(monkeypatch, tmp_path):
    destination = tmp_path / "persistent" / "uploads"
    monkeypatch.setenv("UPLOAD_FOLDER", str(destination))

    prepare_runtime_directories()

    assert destination.is_dir()


def test_gunicorn_honors_platform_port(monkeypatch):
    monkeypatch.setenv("PORT", "10000")

    config_path = Path(__file__).resolve().parents[1] / "gunicorn.conf.py"
    spec = importlib.util.spec_from_file_location("phase3c_gunicorn_config", config_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.bind == "0.0.0.0:10000"

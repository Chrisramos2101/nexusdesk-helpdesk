import os
from pathlib import Path
from urllib.parse import urlparse


def is_production() -> bool:
    return os.getenv("FLASK_ENV", "").strip().lower() == "production"


def _database_url() -> str:
    value = os.getenv("DATABASE_URL", "").strip()
    if value.startswith("postgres://"):
        value = "postgresql://" + value[len("postgres://"):]
    return value


def get_app_base_url() -> str:
    """Return the externally reachable application base URL.

    Render automatically provides RENDER_EXTERNAL_HOSTNAME. APP_BASE_URL remains
    supported for custom domains and non-Render deployments.
    """
    explicit = os.getenv("APP_BASE_URL", "").strip().rstrip("/")
    if explicit:
        return explicit

    render_hostname = os.getenv("RENDER_EXTERNAL_HOSTNAME", "").strip()
    if render_hostname:
        return f"https://{render_hostname}"

    return "http://127.0.0.1:5000"


def validate_production_environment() -> None:
    """Fail fast if production starts with unsafe/incomplete core settings."""
    if not is_production():
        return

    errors = []

    secret_key = os.getenv("SECRET_KEY", "")
    if len(secret_key) < 32:
        errors.append("SECRET_KEY must contain at least 32 characters in production.")

    database_url = _database_url()
    if not database_url.startswith("postgresql://"):
        errors.append("DATABASE_URL must point to PostgreSQL in production.")

    base_url = get_app_base_url()
    parsed = urlparse(base_url)
    if parsed.scheme != "https" or not parsed.netloc:
        errors.append(
            "Production requires APP_BASE_URL or RENDER_EXTERNAL_HOSTNAME "
            "to resolve to an absolute HTTPS URL."
        )

    upload_folder = os.getenv("UPLOAD_FOLDER", "").strip()
    if not upload_folder:
        errors.append("UPLOAD_FOLDER is required in production.")
    elif not Path(upload_folder).is_absolute():
        errors.append("UPLOAD_FOLDER must be an absolute path in production.")

    if os.getenv("TRUST_PROXY_HEADERS", "").lower() != "true":
        errors.append(
            "TRUST_PROXY_HEADERS must be True in production behind the Render proxy."
        )

    if errors:
        raise RuntimeError(
            "Invalid production configuration:\n- " + "\n- ".join(errors)
        )


def prepare_runtime_directories() -> None:
    upload_folder = os.getenv("UPLOAD_FOLDER", "uploads").strip() or "uploads"
    Path(upload_folder).mkdir(parents=True, exist_ok=True)

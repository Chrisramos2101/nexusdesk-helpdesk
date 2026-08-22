import os

from dotenv import load_dotenv

# Make database modules safe to import directly (tests, scripts, CLI), not only
# through app.py.
load_dotenv()


def _normalize_database_url(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return "helpdesk.db"

    # sqlite3.connect expects a filesystem path rather than a SQLAlchemy URL.
    if value.startswith("sqlite:///"):
        return value[len("sqlite:///"):]

    # Some platforms/tools still emit the legacy postgres:// scheme.
    if value.startswith("postgres://"):
        return "postgresql://" + value[len("postgres://"):]

    return value


DATABASE_URL = _normalize_database_url(
    os.getenv("DATABASE_URL", "helpdesk.db")
)

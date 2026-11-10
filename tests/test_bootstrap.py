
import pytest
from werkzeug.security import check_password_hash

from services.bootstrap_service import bootstrap_portfolio_admin


def configure_admin(monkeypatch):
    monkeypatch.setenv("BOOTSTRAP_ADMIN_USERNAME", "portfolio_admin")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "SecurePass123!")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAIL", "portfolio@example.com")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_NAME", "Portfolio Administrator")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_DEPARTMENT", "IT")


@pytest.mark.parametrize(
    "missing_variable",
    [
        "BOOTSTRAP_ADMIN_USERNAME",
        "BOOTSTRAP_ADMIN_PASSWORD",
        "BOOTSTRAP_ADMIN_EMAIL",
        "BOOTSTRAP_ADMIN_NAME",
    ],
)
def test_bootstrap_skips_missing_credentials(
    monkeypatch, db, missing_variable
):
    configure_admin(monkeypatch)
    monkeypatch.delenv(missing_variable)

    assert bootstrap_portfolio_admin() is False

    user = db.execute(
        "SELECT id FROM users WHERE username = ?",
        ("portfolio_admin",),
    ).fetchone()

    assert user is None


def test_bootstrap_rejects_weak_password(monkeypatch, db):
    configure_admin(monkeypatch)
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "weak")

    with pytest.raises(RuntimeError):
        bootstrap_portfolio_admin()

    user = db.execute(
        "SELECT id FROM users WHERE username = ?",
        ("portfolio_admin",),
    ).fetchone()

    assert user is None


def test_bootstrap_creates_secure_admin(monkeypatch, db):
    configure_admin(monkeypatch)

    assert bootstrap_portfolio_admin() is True

    user = db.execute(
        "SELECT * FROM users WHERE username = ?",
        ("portfolio_admin",),
    ).fetchone()

    assert user is not None
    assert user["role"] == "admin"
    assert user["email"] == "portfolio@example.com"
    assert user["department"] == "IT"
    assert user["password_hash"] != "SecurePass123!"
    assert check_password_hash(
        user["password_hash"], "SecurePass123!"
    )


def test_bootstrap_does_not_overwrite_existing_admin(
    monkeypatch, db
):
    configure_admin(monkeypatch)
    monkeypatch.setenv("BOOTSTRAP_ADMIN_USERNAME", "admin")

    before = db.execute(
        "SELECT password_hash FROM users WHERE username = ?",
        ("admin",),
    ).fetchone()["password_hash"]

    assert bootstrap_portfolio_admin() is False

    after = db.execute(
        "SELECT password_hash FROM users WHERE username = ?",
        ("admin",),
    ).fetchone()["password_hash"]

    assert after == before


def test_bootstrap_is_idempotent(monkeypatch, db):
    configure_admin(monkeypatch)

    assert bootstrap_portfolio_admin() is True
    assert bootstrap_portfolio_admin() is False

    count = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM users
        WHERE username = ?
        """,
        ("portfolio_admin",),
    ).fetchone()["count"]

    assert count == 1

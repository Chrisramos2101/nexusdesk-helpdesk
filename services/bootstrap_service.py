import os

from werkzeug.security import generate_password_hash

from database.db import get_db_connection
from database.sql_helpers import db_placeholder
from services.validation_service import validate_password_strength


def bootstrap_portfolio_admin() -> bool:
    """Create one real portfolio admin from private environment variables.

    This never embeds credentials in source control and never overwrites an
    existing account or password.
    """
    username = os.getenv("BOOTSTRAP_ADMIN_USERNAME", "").strip()
    password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "")
    email = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "").strip()
    full_name = os.getenv("BOOTSTRAP_ADMIN_NAME", "").strip()
    department = os.getenv("BOOTSTRAP_ADMIN_DEPARTMENT", "IT").strip() or "IT"

    values = [username, password, email, full_name]
    if not all(values):
        print(
            "Portfolio admin bootstrap skipped: required BOOTSTRAP_ADMIN_* "
            "variables are not all configured.",
            flush=True,
        )
        return False

    valid, reason = validate_password_strength(password)
    if not valid:
        raise RuntimeError(f"BOOTSTRAP_ADMIN_PASSWORD is not strong enough: {reason}")

    connection = get_db_connection()
    cursor = connection.cursor()
    placeholder = db_placeholder()

    try:
        cursor.execute(
            f"SELECT id FROM users WHERE username = {placeholder}",
            (username,),
        )
        existing = cursor.fetchone()

        if existing:
            print(
                f"Portfolio admin already exists: {username}; leaving credentials unchanged.",
                flush=True,
            )
            return False

        cursor.execute(
            f"""
            INSERT INTO users (
                username,
                password_hash,
                role,
                full_name,
                department,
                email,
                failed_attempts,
                locked_until,
                last_login,
                last_logout,
                mfa_enabled,
                mfa_secret
            )
            VALUES (
                {placeholder}, {placeholder}, 'admin',
                {placeholder}, {placeholder}, {placeholder},
                0, '', '', '', 0, ''
            )
            """,
            (
                username,
                generate_password_hash(password),
                full_name,
                department,
                email,
            ),
        )
        connection.commit()

        print(f"Portfolio admin created: {username}", flush=True)
        return True
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

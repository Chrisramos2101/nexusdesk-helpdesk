"""Verified, one-time account email changes; compatible with SQLite and PostgreSQL."""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from database.db import get_db_connection
from database.sql_helpers import db_placeholder, is_postgres


TTL_MINUTES = 30


def _now():
    return datetime.now(timezone.utc)


def _digest(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def email_in_use(email, user_id):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        p = db_placeholder()
        cursor.execute(
            f"SELECT id FROM users WHERE LOWER(TRIM(email)) = LOWER(TRIM({p})) "
            f"AND id <> {p} LIMIT 1", (email, user_id)
        )
        return cursor.fetchone() is not None
    finally:
        connection.close()


def issue_email_change(user_id, email):
    """Create pending request; return raw token to caller once, never persist it."""
    token = secrets.token_urlsafe(32)
    created = _now()
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        p = db_placeholder()
        cursor.execute(
            f"UPDATE email_change_tokens SET used = 1 WHERE user_id = {p} AND used = 0",
            (user_id,),
        )
        cursor.execute(
            f"INSERT INTO email_change_tokens "
            "(user_id, new_email, token_hash, expires_at, used, created_at) "
            f"VALUES ({p}, {p}, {p}, {p}, 0, {p})",
            (user_id, email, _digest(token),
             (created + timedelta(minutes=TTL_MINUTES)).isoformat(),
             created.isoformat()),
        )
        connection.commit()
        return token
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def cancel_email_change(token):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        p = db_placeholder()
        cursor.execute(
            f"UPDATE email_change_tokens SET used = 1 WHERE token_hash = {p}",
            (_digest(token),),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def confirm_email_change(username, token):
    """Return (success, old_email, new_email), consuming valid tokens atomically."""
    if not token or len(token) > 256:
        return False, None, None
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        p = db_placeholder()
        lock = " FOR UPDATE" if is_postgres() else ""
        cursor.execute(
            "SELECT t.id, t.user_id, t.new_email, t.expires_at, "
            "u.email AS old_email "
            "FROM email_change_tokens t "
            "JOIN users u ON u.id = t.user_id "
            f"WHERE t.token_hash = {p} AND t.used = 0 AND u.username = {p}" + lock,
            (_digest(token), username),
        )
        row = cursor.fetchone()
        if not row:
            connection.rollback()
            return False, None, None
        expires = datetime.fromisoformat(row["expires_at"])
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if _now() > expires:
            connection.rollback()
            return False, None, None
        cursor.execute(
            f"SELECT id FROM users WHERE LOWER(TRIM(email)) = LOWER(TRIM({p})) "
            f"AND id <> {p} LIMIT 1", (row["new_email"], row["user_id"]),
        )
        if cursor.fetchone():
            connection.rollback()
            return False, None, None
        cursor.execute(
            f"UPDATE users SET email = {p} WHERE id = {p}",
            (row["new_email"], row["user_id"]),
        )
        cursor.execute(
            f"UPDATE email_change_tokens SET used = 1 WHERE user_id = {p}",
            (row["user_id"],),
        )
        # Old-mailbox password-reset links must not survive a successful change.
        cursor.execute(
            f"UPDATE password_reset_tokens SET used = 1 WHERE user_id = {p}",
            (row["user_id"],),
        )
        connection.commit()
        return True, row["old_email"], row["new_email"]
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

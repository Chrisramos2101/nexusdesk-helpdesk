import secrets
from datetime import datetime, timedelta

from database.db import get_db_connection
from database.sql_helpers import db_placeholder


def get_user_by_email(email):
    """Find a user by email without treating email casing as significant.

    PostgreSQL text equality is case-sensitive. Authentication/account-recovery
    email addresses should be matched case-insensitively so an address stored as
    Example@icloud.com is found when the reset form submits example@icloud.com.
    """
    connection = get_db_connection()
    cursor = connection.cursor()
    placeholder = db_placeholder()

    cursor.execute(f"""
        SELECT *
        FROM users
        WHERE LOWER(TRIM(email)) = LOWER(TRIM({placeholder}))
        LIMIT 1
    """, (email,))

    user = cursor.fetchone()
    connection.close()

    return user


def create_password_reset_token(user_id):
    token = secrets.token_urlsafe(32)
    created_at = datetime.now()
    expires_at = created_at + timedelta(minutes=30)

    connection = get_db_connection()
    cursor = connection.cursor()
    placeholder = db_placeholder()

    cursor.execute(f"""
        INSERT INTO password_reset_tokens
        (user_id, token, expires_at, used, created_at)
        VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
    """, (
        user_id,
        token,
        expires_at.strftime("%m/%d/%Y %I:%M %p"),
        0,
        created_at.strftime("%m/%d/%Y %I:%M %p")
    ))

    connection.commit()
    connection.close()

    return token


def get_valid_reset_token(token):
    connection = get_db_connection()
    cursor = connection.cursor()
    placeholder = db_placeholder()

    cursor.execute(f"""
        SELECT password_reset_tokens.*, users.username
        FROM password_reset_tokens
        JOIN users ON password_reset_tokens.user_id = users.id
        WHERE password_reset_tokens.token = {placeholder}
        AND password_reset_tokens.used = 0
    """, (token,))

    reset_token = cursor.fetchone()
    connection.close()

    if not reset_token:
        return None

    expires_at = datetime.strptime(reset_token["expires_at"], "%m/%d/%Y %I:%M %p")

    if datetime.now() > expires_at:
        return None

    return reset_token


def mark_token_used(token):
    connection = get_db_connection()
    cursor = connection.cursor()
    placeholder = db_placeholder()

    cursor.execute(f"""
        UPDATE password_reset_tokens
        SET used = 1
        WHERE token = {placeholder}
    """, (token,))

    connection.commit()
    connection.close()

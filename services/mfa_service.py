import hmac
import secrets
from datetime import datetime, timedelta

from database.db import get_db_connection
from database.sql_helpers import db_placeholder

MAX_MFA_ATTEMPTS = 5


def invalidate_mfa_codes(username: str) -> None:
    connection = get_db_connection()
    cursor = connection.cursor()
    placeholder = db_placeholder()
    cursor.execute(
        f"UPDATE mfa_codes SET used = 1 WHERE username = {placeholder} AND used = 0",
        (username,),
    )
    connection.commit()
    connection.close()


def generate_mfa_code(username: str) -> str:
    code = f"{secrets.randbelow(1_000_000):06d}"
    connection = get_db_connection()
    cursor = connection.cursor()
    placeholder = db_placeholder()

    # Only the newest challenge should remain valid.
    cursor.execute(
        f"UPDATE mfa_codes SET used = 1 WHERE username = {placeholder} AND used = 0",
        (username,),
    )

    now = datetime.now()
    expires_at = (now + timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
    created_at = now.strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        f"""
        INSERT INTO mfa_codes (username, code, expires_at, used, created_at, attempts)
        VALUES ({placeholder}, {placeholder}, {placeholder}, 0, {placeholder}, 0)
        """,
        (username, code, expires_at, created_at),
    )
    connection.commit()
    connection.close()
    return code


def verify_mfa_code(username: str, submitted_code: str) -> bool:
    connection = get_db_connection()
    cursor = connection.cursor()
    placeholder = db_placeholder()

    cursor.execute(
        f"""
        SELECT *
        FROM mfa_codes
        WHERE username = {placeholder}
          AND used = 0
        ORDER BY id DESC
        LIMIT 1
        """,
        (username,),
    )
    record = cursor.fetchone()

    if not record:
        connection.close()
        return False

    attempts = int(record["attempts"] or 0) if "attempts" in record.keys() else 0
    expires_at = datetime.strptime(record["expires_at"], "%Y-%m-%d %H:%M:%S")

    if datetime.now() > expires_at or attempts >= MAX_MFA_ATTEMPTS:
        cursor.execute(
            f"UPDATE mfa_codes SET used = 1 WHERE id = {placeholder}",
            (record["id"],),
        )
        connection.commit()
        connection.close()
        return False

    matches = hmac.compare_digest(str(record["code"]), str(submitted_code).strip())

    if not matches:
        next_attempts = attempts + 1
        cursor.execute(
            f"""
            UPDATE mfa_codes
            SET attempts = {placeholder}, used = {placeholder}
            WHERE id = {placeholder}
            """,
            (next_attempts, 1 if next_attempts >= MAX_MFA_ATTEMPTS else 0, record["id"]),
        )
        connection.commit()
        connection.close()
        return False

    cursor.execute(
        f"UPDATE mfa_codes SET used = 1 WHERE id = {placeholder}",
        (record["id"],),
    )
    connection.commit()
    connection.close()
    return True

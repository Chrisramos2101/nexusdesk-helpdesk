from datetime import datetime, timedelta, timezone

from database.db import get_db_connection
from database.sql_helpers import db_placeholder


_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def check_rate_limit(bucket_key: str, action: str, limit: int, window_seconds: int) -> tuple[bool, int]:
    """Record one attempt and return (allowed, retry_after_seconds).

    Storage is database-backed, so the limiter works consistently across normal
    Flask requests and does not rely on a single Python process's memory.
    """
    now = _utc_now_naive()
    connection = get_db_connection()
    cursor = connection.cursor()
    placeholder = db_placeholder()

    cursor.execute(
        f"""
        SELECT id, attempts, window_start
        FROM security_rate_limits
        WHERE bucket_key = {placeholder}
          AND action = {placeholder}
        """,
        (bucket_key, action),
    )
    record = cursor.fetchone()

    if not record:
        cursor.execute(
            f"""
            INSERT INTO security_rate_limits (bucket_key, action, attempts, window_start)
            VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})
            """,
            (bucket_key, action, 1, now.strftime(_TIMESTAMP_FORMAT)),
        )
        connection.commit()
        connection.close()
        return True, 0

    try:
        window_start = datetime.strptime(record["window_start"], _TIMESTAMP_FORMAT)
    except (TypeError, ValueError):
        window_start = now - timedelta(seconds=window_seconds + 1)

    window_end = window_start + timedelta(seconds=window_seconds)

    if now >= window_end:
        cursor.execute(
            f"""
            UPDATE security_rate_limits
            SET attempts = {placeholder}, window_start = {placeholder}
            WHERE id = {placeholder}
            """,
            (1, now.strftime(_TIMESTAMP_FORMAT), record["id"]),
        )
        connection.commit()
        connection.close()
        return True, 0

    attempts = int(record["attempts"] or 0)
    if attempts >= limit:
        retry_after = max(1, int((window_end - now).total_seconds()))
        connection.close()
        return False, retry_after

    cursor.execute(
        f"""
        UPDATE security_rate_limits
        SET attempts = attempts + 1
        WHERE id = {placeholder}
        """,
        (record["id"],),
    )
    connection.commit()
    connection.close()
    return True, 0


def reset_rate_limit(bucket_key: str, action: str) -> None:
    connection = get_db_connection()
    cursor = connection.cursor()
    placeholder = db_placeholder()
    cursor.execute(
        f"DELETE FROM security_rate_limits WHERE bucket_key = {placeholder} AND action = {placeholder}",
        (bucket_key, action),
    )
    connection.commit()
    connection.close()

from datetime import datetime, timedelta

from database.db import get_db_connection
from database.sql_helpers import db_placeholder


def cleanup_expired_security_records():
    connection = get_db_connection()
    cursor = connection.cursor()
    placeholder = db_placeholder()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    thirty_days_ago = (
        datetime.now() - timedelta(days=30)
    ).strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(f"""
        DELETE FROM mfa_codes
        WHERE expires_at < {placeholder}
    """, (now,))

    cursor.execute(f"""
        DELETE FROM mfa_codes
        WHERE used = 1
        AND created_at < {placeholder}
    """, (thirty_days_ago,))

    cursor.execute("""
        DELETE FROM password_reset_tokens
        WHERE used = 1
    """)

    cursor.execute(f"""
        DELETE FROM security_rate_limits
        WHERE window_start < {placeholder}
    """, (thirty_days_ago,))

    connection.commit()
    connection.close()
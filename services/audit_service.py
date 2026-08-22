from datetime import datetime

from database.db import get_db_connection
from database.sql_helpers import db_placeholder


def log_audit_event(actor, action, target_type, target_id="", details=""):
    connection = get_db_connection()
    cursor = connection.cursor()
    placeholder = db_placeholder()

    created_at = datetime.now().strftime("%m/%d/%Y %I:%M %p")

    cursor.execute(f"""
        INSERT INTO audit_logs
        (actor, action, target_type, target_id, details, created_at)
        VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
    """, (
        actor,
        action,
        target_type,
        str(target_id),
        details,
        created_at
    ))

    connection.commit()
    connection.close()
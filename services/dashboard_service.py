from datetime import datetime

from database.db import get_db_connection
from database.sql_helpers import db_placeholder


def count_overdue_tickets():
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT sla_due_at
        FROM tickets
        WHERE status != 'Closed' AND sla_due_at != ''
    """)

    rows = cursor.fetchall()
    connection.close()

    overdue_tickets = 0

    for row in rows:
        try:
            due_time = datetime.strptime(row["sla_due_at"], "%m/%d/%Y %I:%M %p")
            if datetime.now() > due_time:
                overdue_tickets += 1
        except Exception:
            pass

    return overdue_tickets


def get_ticket_count_by_status(status):
    connection = get_db_connection()
    cursor = connection.cursor()
    placeholder = db_placeholder()

    cursor.execute(f"""
        SELECT COUNT(*) AS total
        FROM tickets
        WHERE status = {placeholder}
    """, (status,))

    total = cursor.fetchone()["total"]

    connection.close()

    return total


def get_high_priority_ticket_count():
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM tickets
        WHERE priority = 'High'
    """)

    total = cursor.fetchone()["total"]

    connection.close()

    return total
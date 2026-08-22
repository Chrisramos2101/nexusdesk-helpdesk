from datetime import datetime

from database.db import get_db_connection
from database.sql_helpers import db_placeholder


def save_attachment_record(ticket_id, original_filename, stored_filename, uploaded_by):
    connection = get_db_connection()
    cursor = connection.cursor()
    placeholder = db_placeholder()

    uploaded_at = datetime.now().strftime("%m/%d/%Y %I:%M %p")

    cursor.execute(f"""
        INSERT INTO ticket_attachments
        (ticket_id, original_filename, stored_filename, uploaded_by, uploaded_at)
        VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
    """, (
        ticket_id,
        original_filename,
        stored_filename,
        uploaded_by,
        uploaded_at
    ))

    connection.commit()
    connection.close()


def get_attachments_for_ticket(ticket_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    placeholder = db_placeholder()

    cursor.execute(f"""
        SELECT *
        FROM ticket_attachments
        WHERE ticket_id = {placeholder}
        ORDER BY uploaded_at DESC
    """, (ticket_id,))

    attachments = cursor.fetchall()

    connection.close()

    return attachments

def get_attachment_with_ticket(stored_filename):
    connection = get_db_connection()
    cursor = connection.cursor()
    placeholder = db_placeholder()

    cursor.execute(f"""
        SELECT a.*, t.submitted_by
        FROM ticket_attachments AS a
        JOIN tickets AS t ON t.id = a.ticket_id
        WHERE a.stored_filename = {placeholder}
    """, (stored_filename,))

    attachment = cursor.fetchone()
    connection.close()
    return attachment

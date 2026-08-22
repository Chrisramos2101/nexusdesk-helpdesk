from database.db import get_db_connection
from database.sql_helpers import db_placeholder, is_postgres


def get_ticket_by_id(ticket_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    placeholder = db_placeholder()

    cursor.execute(f"""
        SELECT *
        FROM tickets
        WHERE id = {placeholder}
    """, (ticket_id,))

    ticket = cursor.fetchone()

    connection.close()

    return ticket


def create_ticket(name, department, issue, priority, category, submitted_at, submitted_by, sla_due_at):
    connection = get_db_connection()
    cursor = connection.cursor()
    placeholder = db_placeholder()

    insert_sql = f"""
        INSERT INTO tickets
        (name, department, issue, priority, category, status, submitted_at, closed_at, assigned_to, completed_by, notes, sla_due_at, submitted_by)
        VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
    """

    params = (
        name, department, issue, priority, category, "Open", submitted_at, "",
        "Unassigned", "", "", sla_due_at, submitted_by
    )

    if is_postgres():
        cursor.execute(insert_sql + " RETURNING id", params)
        new_ticket_id = cursor.fetchone()["id"]
    else:
        cursor.execute(insert_sql, params)
        new_ticket_id = cursor.lastrowid

    connection.commit()
    connection.close()
    return new_ticket_id


def assign_ticket_to_user(ticket_id, assigned_to):
    connection = get_db_connection()
    cursor = connection.cursor()
    placeholder = db_placeholder()

    cursor.execute(f"""
        UPDATE tickets
        SET assigned_to = {placeholder}
        WHERE id = {placeholder}
    """, (assigned_to, ticket_id))

    connection.commit()
    connection.close()


def close_ticket(ticket_id, closed_at, completed_by, resolution_time, sla_met):
    connection = get_db_connection()
    cursor = connection.cursor()
    placeholder = db_placeholder()

    cursor.execute(f"""
        UPDATE tickets
        SET status = 'Closed',
            closed_at = {placeholder},
            completed_by = {placeholder},
            resolution_time = {placeholder},
            sla_met = {placeholder}
        WHERE id = {placeholder}
    """, (
        closed_at,
        completed_by,
        resolution_time,
        sla_met,
        ticket_id
    ))

    connection.commit()
    connection.close()


def delete_ticket_by_id(ticket_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    placeholder = db_placeholder()

    cursor.execute(f"""
        SELECT stored_filename
        FROM ticket_attachments
        WHERE ticket_id = {placeholder}
    """, (ticket_id,))
    stored_filenames = [row["stored_filename"] for row in cursor.fetchall()]

    cursor.execute(f"DELETE FROM ticket_notes WHERE ticket_id = {placeholder}", (ticket_id,))
    cursor.execute(f"DELETE FROM ticket_attachments WHERE ticket_id = {placeholder}", (ticket_id,))
    cursor.execute(f"DELETE FROM tickets WHERE id = {placeholder}", (ticket_id,))

    connection.commit()
    connection.close()
    return stored_filenames


def update_ticket_by_id(
    ticket_id,
    name,
    department,
    issue,
    priority,
    category,
    status,
    assigned_to,
    closed_at,
    completed_by,
    resolution_time,
    sla_met
):
    connection = get_db_connection()
    cursor = connection.cursor()
    placeholder = db_placeholder()

    cursor.execute(f"""
        UPDATE tickets
        SET name = {placeholder},
            department = {placeholder},
            issue = {placeholder},
            priority = {placeholder},
            category = {placeholder},
            status = {placeholder},
            assigned_to = {placeholder},
            closed_at = {placeholder},
            completed_by = {placeholder},
            resolution_time = {placeholder},
            sla_met = {placeholder}
        WHERE id = {placeholder}
    """, (
        name,
        department,
        issue,
        priority,
        category,
        status,
        assigned_to,
        closed_at,
        completed_by,
        resolution_time,
        sla_met,
        ticket_id
    ))

    connection.commit()
    connection.close()


def add_ticket_note(ticket_id, note, created_by, created_at):
    connection = get_db_connection()
    cursor = connection.cursor()
    placeholder = db_placeholder()

    cursor.execute(f"""
        INSERT INTO ticket_notes (ticket_id, note, created_by, created_at)
        VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})
    """, (ticket_id, note, created_by, created_at))

    connection.commit()
    connection.close()


def get_ticket_submitter_username(ticket_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    placeholder = db_placeholder()

    cursor.execute(f"""
        SELECT submitted_by
        FROM tickets
        WHERE id = {placeholder}
    """, (ticket_id,))

    ticket = cursor.fetchone()

    connection.close()

    if ticket:
        return ticket["submitted_by"]

    return None
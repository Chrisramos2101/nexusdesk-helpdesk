from flask import Blueprint, render_template, request, session
from datetime import datetime
from services.dashboard_service import count_overdue_tickets, get_ticket_count_by_status, get_high_priority_ticket_count
from database.db import get_db_connection
from database.sql_helpers import db_placeholder
from routes.auth_helpers import admin_required
from routes.tickets import get_sla_status
from services.user_service import get_technicians
from services.attachment_service import get_attachments_for_ticket

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@admin_required
def dashboard():
    selected_status = request.args.get("status", "Open")
    search_query = request.args.get("search", "")
    selected_priority = request.args.get("priority", "")
    selected_category = request.args.get("category", "")
    selected_assigned = request.args.get("assigned_to", "")

    priority_order = {
        "High": 1,
        "Medium": 2,
        "Low": 3
    }

    connection = get_db_connection()
    cursor = connection.cursor()

    placeholder = db_placeholder()

    query = f"""
        SELECT * FROM tickets
        WHERE status = {placeholder}
    """

    params = [selected_status]

    if search_query:
        query += f"""
            AND (
                name LIKE {placeholder}
                OR department LIKE {placeholder}
                OR issue LIKE {placeholder}
                OR category LIKE {placeholder}
                OR priority LIKE {placeholder}
                OR assigned_to LIKE {placeholder}
                OR submitted_by LIKE {placeholder}
                OR status LIKE {placeholder}
            )
        """
        search_pattern = f"%{search_query}%"
        params.extend([
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern
        ])

    if selected_priority:
        query += f" AND priority = {placeholder}"
        params.append(selected_priority)

    if selected_category:
        query += f" AND category = {placeholder}"
        params.append(selected_category)

    if selected_assigned:
        query += f" AND assigned_to LIKE {placeholder}"
        params.append(f"%{selected_assigned}%")

    cursor.execute(query, params)
    tickets_from_db = cursor.fetchall()

    cursor.execute("""
        SELECT * FROM ticket_notes
        ORDER BY created_at DESC
    """)
    notes_from_db = cursor.fetchall()

    tickets_with_sla = []

    for ticket in tickets_from_db:
        ticket_dict = dict(ticket)
        ticket_dict["sla_status"] = get_sla_status(ticket)
        tickets_with_sla.append(ticket_dict)

    notes_by_ticket = {}

    for note in notes_from_db:
        ticket_id = note["ticket_id"]

        if ticket_id not in notes_by_ticket:
            notes_by_ticket[ticket_id] = []

        notes_by_ticket[ticket_id].append(note)

    open_tickets = get_ticket_count_by_status("Open")
    in_progress_tickets = get_ticket_count_by_status("In Progress")
    closed_tickets = get_ticket_count_by_status("Closed")

    cursor.execute("SELECT COUNT(*) AS total FROM tickets WHERE sla_met = 'Yes'")
    sla_met_count = cursor.fetchone()["total"]

    overdue_tickets = count_overdue_tickets()

    cursor.execute("""
        SELECT assigned_to, COUNT(*) AS total
        FROM tickets
        WHERE status != 'Closed'
        GROUP BY assigned_to
    """)
    tech_load = cursor.fetchall()

    connection.close()

    sla_order = {
        "Overdue": 1,
        "Due Soon": 2,
        "On Track": 3,
        "No SLA": 4,
        "Completed": 5
    }

    sorted_tickets = sorted(
        tickets_with_sla,
        key=lambda ticket: (
            sla_order[ticket["sla_status"]],
            priority_order[ticket["priority"]]
        )
    )

    attachments_by_ticket = {}

    for ticket in sorted_tickets:
        attachments_by_ticket[ticket["id"]] = get_attachments_for_ticket(ticket["id"])

    return render_template(
        "dashboard.html",
        tickets=sorted_tickets,
        selected_status=selected_status,
        notes_by_ticket=notes_by_ticket,
        admin_name=session["username"],
        search_query=search_query,
        selected_priority=selected_priority,
        selected_category=selected_category,
        selected_assigned=selected_assigned,
        open_tickets=open_tickets,
        in_progress_tickets=in_progress_tickets,
        closed_tickets=closed_tickets,
        overdue_tickets=overdue_tickets,
        sla_met_count=sla_met_count,
        tech_load=tech_load,
        technicians=get_technicians(),
        attachments_by_ticket=attachments_by_ticket,
    )


@dashboard_bp.route("/stats")
@admin_required
def stats():
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) AS total FROM tickets")
    total_tickets = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM tickets WHERE status = 'Open'")
    open_tickets = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM tickets WHERE status = 'In Progress'")
    in_progress_tickets = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM tickets WHERE status = 'Closed'")
    closed_tickets = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM tickets WHERE sla_met = 'Yes'")
    sla_met_count = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM tickets WHERE sla_met = 'No'")
    sla_missed_count = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT assigned_to, COUNT(*) AS total
        FROM tickets
        WHERE sla_met = 'No'
        GROUP BY assigned_to
    """)
    sla_missed_by_tech = cursor.fetchall()

    high_priority_tickets = get_high_priority_ticket_count()

    cursor.execute("SELECT department, COUNT(*) AS total FROM tickets GROUP BY department")
    department_stats = cursor.fetchall()

    cursor.execute("SELECT priority, COUNT(*) AS total FROM tickets GROUP BY priority")
    priority_stats = cursor.fetchall()

    cursor.execute("SELECT category, COUNT(*) AS total FROM tickets GROUP BY category")
    category_stats = cursor.fetchall()

    cursor.execute("""
        SELECT assigned_to, COUNT(*) AS total
        FROM tickets
        WHERE assigned_to IS NOT NULL AND assigned_to != ''
        GROUP BY assigned_to
    """)
    assigned_stats = cursor.fetchall()

    cursor.execute("""
        SELECT completed_by, COUNT(*) AS total
        FROM tickets
        WHERE status = 'Closed' AND completed_by != ''
        GROUP BY completed_by
    """)
    completed_by_stats = cursor.fetchall()

    cursor.execute("""
        SELECT submitted_at, COUNT(*) AS total
        FROM tickets
        GROUP BY submitted_at
        ORDER BY submitted_at DESC
        LIMIT 7
    """)
    daily_stats = cursor.fetchall()

    open_percent = round((open_tickets / total_tickets) * 100, 1) if total_tickets else 0
    progress_percent = round((in_progress_tickets / total_tickets) * 100, 1) if total_tickets else 0
    closed_percent = round((closed_tickets / total_tickets) * 100, 1) if total_tickets else 0

    priority_stats = [
        {
            "priority": row["priority"],
            "total": row["total"],
            "percent": round((row["total"] / total_tickets) * 100, 1) if total_tickets else 0
        }
        for row in priority_stats
    ]

    department_stats = [
        {
            "department": row["department"],
            "total": row["total"],
            "percent": round((row["total"] / total_tickets) * 100, 1) if total_tickets else 0
        }
        for row in department_stats
    ]

    category_stats = [
        {
            "category": row["category"],
            "total": row["total"],
            "percent": round((row["total"] / total_tickets) * 100, 1) if total_tickets else 0
        }
        for row in category_stats
    ]

    assigned_stats = [
        {
            "assigned_to": row["assigned_to"],
            "total": row["total"],
            "percent": round((row["total"] / total_tickets) * 100, 1) if total_tickets else 0
        }
        for row in assigned_stats
    ]

    overdue_tickets = count_overdue_tickets()

    connection.close()

    return render_template(
        "stats.html",
        total_tickets=total_tickets,
        open_tickets=open_tickets,
        in_progress_tickets=in_progress_tickets,
        closed_tickets=closed_tickets,
        high_priority_tickets=high_priority_tickets,
        open_percent=open_percent,
        progress_percent=progress_percent,
        closed_percent=closed_percent,
        priority_stats=priority_stats,
        department_stats=department_stats,
        category_stats=category_stats,
        assigned_stats=assigned_stats,
        completed_by_stats=completed_by_stats,
        daily_stats=daily_stats,
        sla_met_count=sla_met_count,
        sla_missed_count=sla_missed_count,
        sla_missed_by_tech=sla_missed_by_tech,
        overdue_tickets=overdue_tickets,
    )
from flask import Blueprint, render_template, request, session
from datetime import datetime, timedelta
from services.dashboard_service import count_overdue_tickets, get_ticket_count_by_status
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
    selected_status = request.args.get("status", "Open").strip()
    search_query = request.args.get("search", "").strip()
    selected_priority = request.args.get("priority", "").strip()
    selected_category = request.args.get("category", "").strip()
    selected_assigned = request.args.get("assigned_to", "").strip()

    # =========================================================
    # VALIDATE FILTER VALUES
    # =========================================================

    valid_statuses = {"Open", "In Progress", "Closed"}
    valid_priorities = {"", "Low", "Medium", "High"}
    valid_categories = {
        "",
        "Hardware",
        "Software",
        "Network",
        "Account Access",
        "Security",
        "Other",
    }

    if selected_status not in valid_statuses:
        selected_status = "Open"

    if selected_priority not in valid_priorities:
        selected_priority = ""

    if selected_category not in valid_categories:
        selected_category = ""

    admin_name = session["username"]
    admin_key = admin_name.lower()

    priority_order = {
        "High": 1,
        "Medium": 2,
        "Low": 3,
    }

    sla_order = {
        "Overdue": 1,
        "Due Soon": 2,
        "On Track": 3,
        "No SLA": 4,
        "Completed": 5,
    }

    connection = get_db_connection()
    cursor = connection.cursor()

    placeholder = db_placeholder()

    # =========================================================
    # CANONICAL USERNAMES
    #
    # Historical tickets may contain casing differences such as
    # Cristian_Admin / Cristian_admin.
    # =========================================================

    cursor.execute("""
        SELECT username
        FROM users
    """)

    canonical_usernames = {
        row["username"].lower(): row["username"]
        for row in cursor.fetchall()
        if row["username"]
    }

    def display_username(value):
        if not value:
            return "Unassigned"

        value = str(value).strip()

        if not value or value.lower() == "unassigned":
            return "Unassigned"

        return canonical_usernames.get(
            value.lower(),
            value
        )

    # =========================================================
    # BUILD TICKET QUERY
    # =========================================================

    query = f"""
        SELECT *
        FROM tickets
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
            search_pattern,
        ])

    if selected_priority:
        query += f"""
            AND priority = {placeholder}
        """
        params.append(selected_priority)

    if selected_category:
        query += f"""
            AND category = {placeholder}
        """
        params.append(selected_category)

    if selected_assigned:
        if selected_assigned == "Unassigned":
            query += """
                AND (
                    assigned_to IS NULL
                    OR TRIM(assigned_to) = ''
                    OR LOWER(assigned_to) = 'unassigned'
                )
            """
        else:
            query += f"""
                AND LOWER(assigned_to) = LOWER({placeholder})
            """
            params.append(selected_assigned)

    cursor.execute(query, params)
    tickets_from_db = cursor.fetchall()

    # =========================================================
    # NOTES
    # =========================================================

    cursor.execute("""
        SELECT *
        FROM ticket_notes
        ORDER BY created_at DESC
    """)

    notes_from_db = cursor.fetchall()

    notes_by_ticket = {}

    for note in notes_from_db:
        ticket_id = note["ticket_id"]

        if ticket_id not in notes_by_ticket:
            notes_by_ticket[ticket_id] = []

        notes_by_ticket[ticket_id].append(note)

    # =========================================================
    # SLA + DISPLAY DATA
    # =========================================================

    tickets_with_sla = []

    for ticket in tickets_from_db:
        ticket_dict = dict(ticket)

        ticket_dict["sla_status"] = get_sla_status(ticket)

        ticket_dict["assigned_to_display"] = display_username(
            ticket_dict.get("assigned_to")
        )

        assigned_value = (
            ticket_dict.get("assigned_to") or ""
        ).strip().lower()

        ticket_dict["assigned_to_me"] = (
            assigned_value == admin_key
        )

        tickets_with_sla.append(ticket_dict)

    # =========================================================
    # GLOBAL STATUS COUNTS
    # =========================================================

    open_tickets = get_ticket_count_by_status("Open")
    in_progress_tickets = get_ticket_count_by_status("In Progress")
    closed_tickets = get_ticket_count_by_status("Closed")

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM tickets
        WHERE status = 'Open'
          AND priority = 'High'
    """)

    open_high_priority_count = cursor.fetchone()["total"]

    # =========================================================
    # ACTIVE TECHNICIAN WORKLOAD
    # =========================================================

    cursor.execute("""
        SELECT
            LOWER(assigned_to) AS assigned_key,
            COUNT(*) AS total
        FROM tickets
        WHERE status != 'Closed'
          AND assigned_to IS NOT NULL
          AND TRIM(assigned_to) != ''
          AND LOWER(assigned_to) != 'unassigned'
        GROUP BY LOWER(assigned_to)
        ORDER BY total DESC
    """)

    tech_load = [
        {
            "assigned_to": display_username(row["assigned_key"]),
            "total": row["total"],
        }
        for row in cursor.fetchall()
    ]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM tickets
        WHERE status != 'Closed'
          AND (
              assigned_to IS NULL
              OR TRIM(assigned_to) = ''
              OR LOWER(assigned_to) = 'unassigned'
          )
    """)

    unassigned_active_count = cursor.fetchone()["total"]

    connection.close()

    # =========================================================
    # SORT TICKETS
    # =========================================================

    if selected_status == "Closed":
        sorted_tickets = sorted(
            tickets_with_sla,
            key=lambda ticket: ticket["id"],
            reverse=True,
        )
    else:
        sorted_tickets = sorted(
            tickets_with_sla,
            key=lambda ticket: (
                sla_order.get(ticket["sla_status"], 99),
                priority_order.get(ticket["priority"], 99),
                -ticket["id"],
            ),
        )

    # =========================================================
    # ATTACHMENTS
    # =========================================================

    attachments_by_ticket = {}

    for ticket in sorted_tickets:
        attachments_by_ticket[ticket["id"]] = (
            get_attachments_for_ticket(ticket["id"])
        )

    # =========================================================
    # CURRENT VIEW METRICS
    # =========================================================

    visible_ticket_count = len(sorted_tickets)

    visible_overdue_count = sum(
        1
        for ticket in sorted_tickets
        if ticket["sla_status"] == "Overdue"
    )

    visible_due_soon_count = sum(
        1
        for ticket in sorted_tickets
        if ticket["sla_status"] == "Due Soon"
    )

    visible_unassigned_count = sum(
        1
        for ticket in sorted_tickets
        if ticket["assigned_to_display"] == "Unassigned"
    )

    visible_assigned_to_me_count = sum(
        1
        for ticket in sorted_tickets
        if ticket["assigned_to_me"]
    )

    high_priority_view = (
        selected_status == "Open"
        and selected_priority == "High"
    )

    # =========================================================
    # DYNAMIC PAGE CONTEXT
    # =========================================================

    if selected_status == "Closed":

        view_badge = "TICKET HISTORY"
        view_icon = "✅"
        view_title = "Closed Tickets"
        view_description = (
            "Review completed support requests, resolution history, "
            "attachments, and ticket notes."
        )
        view_tone = "success"

        visible_sla_met = sum(
            1
            for ticket in sorted_tickets
            if ticket.get("sla_met") == "Yes"
        )

        visible_sla_missed = sum(
            1
            for ticket in sorted_tickets
            if ticket.get("sla_met") == "No"
        )

        completed_by_me = sum(
            1
            for ticket in sorted_tickets
            if (
                ticket.get("completed_by")
                and ticket["completed_by"].lower() == admin_key
            )
        )

        view_metrics = [
            {
                "icon": "✅",
                "value": visible_ticket_count,
                "label": "Closed in View",
                "tone": "success",
            },
            {
                "icon": "🟢",
                "value": visible_sla_met,
                "label": "SLA Met",
                "tone": "success",
            },
            {
                "icon": "🔴",
                "value": visible_sla_missed,
                "label": "SLA Missed",
                "tone": "danger",
            },
            {
                "icon": "👤",
                "value": completed_by_me,
                "label": "Completed by Me",
                "tone": "info",
            },
        ]

        empty_title = "No closed tickets found."
        empty_text = (
            "Completed tickets matching these filters will appear here."
        )

    elif selected_status == "In Progress":

        view_badge = "ACTIVE WORK"
        view_icon = "🛠️"
        view_title = "In-Progress Tickets"
        view_description = (
            "Track active support requests, technician ownership, "
            "SLA status, and ongoing work."
        )
        view_tone = "info"

        view_metrics = [
            {
                "icon": "🛠️",
                "value": visible_ticket_count,
                "label": "In Progress",
                "tone": "info",
            },
            {
                "icon": "⏰",
                "value": visible_overdue_count,
                "label": "Overdue",
                "tone": "danger",
            },
            {
                "icon": "⚠️",
                "value": visible_due_soon_count,
                "label": "Due Soon",
                "tone": "warning",
            },
            {
                "icon": "📥",
                "value": visible_unassigned_count,
                "label": "Unassigned",
                "tone": "warning",
            },
            {
                "icon": "👤",
                "value": visible_assigned_to_me_count,
                "label": "Assigned to Me",
                "tone": "info",
            },
        ]

        empty_title = "No tickets are currently in progress."
        empty_text = (
            "Tickets being actively worked will appear here."
        )

    elif high_priority_view:

        view_badge = "PRIORITY QUEUE"
        view_icon = "🚨"
        view_title = "High-Priority Tickets"
        view_description = (
            "Review open support requests requiring elevated attention."
        )
        view_tone = "danger"

        view_metrics = [
            {
                "icon": "🚨",
                "value": visible_ticket_count,
                "label": "High-Priority Open",
                "tone": "danger",
            },
            {
                "icon": "⏰",
                "value": visible_overdue_count,
                "label": "Overdue",
                "tone": "danger",
            },
            {
                "icon": "⚠️",
                "value": visible_due_soon_count,
                "label": "Due Soon",
                "tone": "warning",
            },
            {
                "icon": "📥",
                "value": visible_unassigned_count,
                "label": "Unassigned",
                "tone": "warning",
            },
            {
                "icon": "👤",
                "value": visible_assigned_to_me_count,
                "label": "Assigned to Me",
                "tone": "info",
            },
        ]

        empty_title = "No open high-priority tickets."
        empty_text = (
            "High-priority requests will appear here when attention is needed."
        )

    else:

        view_badge = "TICKET OPERATIONS"
        view_icon = "📋"
        view_title = "Open Ticket Queue"
        view_description = (
            "Review, assign, prioritize, and resolve active support requests."
        )
        view_tone = "default"

        view_metrics = [
            {
                "icon": "📥",
                "value": visible_ticket_count,
                "label": "Open in View",
                "tone": "info",
            },
            {
                "icon": "⏰",
                "value": visible_overdue_count,
                "label": "Overdue",
                "tone": "danger",
            },
            {
                "icon": "⚠️",
                "value": visible_due_soon_count,
                "label": "Due Soon",
                "tone": "warning",
            },
            {
                "icon": "📭",
                "value": visible_unassigned_count,
                "label": "Unassigned",
                "tone": "warning",
            },
            {
                "icon": "👤",
                "value": visible_assigned_to_me_count,
                "label": "Assigned to Me",
                "tone": "info",
            },
        ]

        empty_title = "No open tickets found."
        empty_text = (
            "New support requests matching these filters will appear here."
        )

    # =========================================================
    # FILTER / RETURN STATE
    # =========================================================

    filters_expanded = bool(
        search_query
        or selected_category
        or selected_assigned
        or (
            selected_priority
            and not high_priority_view
        )
    )

    encoded_status = selected_status.replace(" ", "%20")

    if high_priority_view:
        clear_filters_url = (
            "/dashboard?status=Open&priority=High"
        )
    else:
        clear_filters_url = (
            f"/dashboard?status={encoded_status}"
        )

    return_to = request.full_path.rstrip("?")

    technicians = get_technicians()

    return render_template(
        "dashboard.html",

        tickets=sorted_tickets,

        selected_status=selected_status,
        selected_priority=selected_priority,
        selected_category=selected_category,
        selected_assigned=selected_assigned,
        search_query=search_query,

        admin_name=admin_name,

        open_tickets=open_tickets,
        in_progress_tickets=in_progress_tickets,
        closed_tickets=closed_tickets,
        open_high_priority_count=open_high_priority_count,

        tech_load=tech_load,
        unassigned_active_count=unassigned_active_count,

        technicians=technicians,

        notes_by_ticket=notes_by_ticket,
        attachments_by_ticket=attachments_by_ticket,

        view_badge=view_badge,
        view_icon=view_icon,
        view_title=view_title,
        view_description=view_description,
        view_tone=view_tone,
        view_metrics=view_metrics,

        high_priority_view=high_priority_view,

        empty_title=empty_title,
        empty_text=empty_text,

        filters_expanded=filters_expanded,
        clear_filters_url=clear_filters_url,
        return_to=return_to,
    )


@dashboard_bp.route("/stats")
@admin_required
def stats():
    connection = get_db_connection()
    cursor = connection.cursor()

    # =========================================================
    # CANONICAL USERNAMES
    # Prevents historical casing differences such as
    # Cristian_Admin vs Cristian_admin from appearing separately.
    # =========================================================

    cursor.execute("""
        SELECT username
        FROM users
    """)

    canonical_usernames = {
        row["username"].lower(): row["username"]
        for row in cursor.fetchall()
        if row["username"]
    }

    def display_username(value):
        if not value:
            return "Unknown"

        return canonical_usernames.get(
            str(value).lower(),
            value
        )


    # =========================================================
    # TICKET OVERVIEW
    # =========================================================

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM tickets
    """)
    total_tickets = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM tickets
        WHERE status = 'Open'
    """)
    open_tickets = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM tickets
        WHERE status = 'In Progress'
    """)
    in_progress_tickets = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM tickets
        WHERE status = 'Closed'
    """)
    closed_tickets = cursor.fetchone()["total"]


    # =========================================================
    # PRIORITY BREAKDOWN
    # =========================================================

    cursor.execute("""
        SELECT priority, COUNT(*) AS total
        FROM tickets
        GROUP BY priority
    """)

    priority_rows = cursor.fetchall()

    priority_lookup = {
        row["priority"]: row["total"]
        for row in priority_rows
    }

    low_priority_tickets = priority_lookup.get("Low", 0)
    medium_priority_tickets = priority_lookup.get("Medium", 0)
    high_priority_tickets = priority_lookup.get("High", 0)

    priority_stats = []

    for priority in ["Low", "Medium", "High"]:
        total = priority_lookup.get(priority, 0)

        priority_stats.append({
            "priority": priority,
            "total": total,
            "percent": (
                round((total / total_tickets) * 100, 1)
                if total_tickets
                else 0
            )
        })


    # =========================================================
    # SLA PERFORMANCE
    #
    # SLA Met / Missed = completed-ticket history.
    # Overdue = ticket is still active after its SLA deadline.
    # =========================================================

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM tickets
        WHERE sla_met = 'Yes'
    """)
    sla_met_count = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM tickets
        WHERE sla_met = 'No'
    """)
    sla_missed_count = cursor.fetchone()["total"]


    # =========================================================
    # SLA MISSES BY TECHNICIAN
    # Case-insensitive grouping avoids duplicate technician names.
    # =========================================================

    cursor.execute("""
        SELECT
            LOWER(assigned_to) AS assigned_key,
            COUNT(*) AS total
        FROM tickets
        WHERE sla_met = 'No'
          AND assigned_to IS NOT NULL
          AND TRIM(assigned_to) != ''
          AND LOWER(assigned_to) != 'unassigned'
        GROUP BY LOWER(assigned_to)
        ORDER BY total DESC
    """)

    sla_missed_by_tech = [
        {
            "assigned_to": display_username(row["assigned_key"]),
            "total": row["total"]
        }
        for row in cursor.fetchall()
    ]


    # =========================================================
    # DEPARTMENT ANALYTICS
    # =========================================================

    cursor.execute("""
        SELECT department, COUNT(*) AS total
        FROM tickets
        GROUP BY department
        ORDER BY total DESC
    """)

    department_stats = [
        {
            "department": row["department"],
            "total": row["total"],
            "percent": (
                round((row["total"] / total_tickets) * 100, 1)
                if total_tickets
                else 0
            )
        }
        for row in cursor.fetchall()
    ]


    # =========================================================
    # CATEGORY ANALYTICS
    # =========================================================

    cursor.execute("""
        SELECT category, COUNT(*) AS total
        FROM tickets
        GROUP BY category
        ORDER BY total DESC
    """)

    category_stats = [
        {
            "category": row["category"],
            "total": row["total"],
            "percent": (
                round((row["total"] / total_tickets) * 100, 1)
                if total_tickets
                else 0
            )
        }
        for row in cursor.fetchall()
    ]


    # =========================================================
    # ACTIVE TECHNICIAN WORKLOAD
    #
    # Only active tickets count as current workload.
    # Closed tickets are intentionally excluded.
    # =========================================================

    cursor.execute("""
        SELECT
            LOWER(assigned_to) AS assigned_key,
            COUNT(*) AS total
        FROM tickets
        WHERE status != 'Closed'
          AND assigned_to IS NOT NULL
          AND TRIM(assigned_to) != ''
          AND LOWER(assigned_to) != 'unassigned'
        GROUP BY LOWER(assigned_to)
        ORDER BY total DESC
    """)

    assigned_stats = [
        {
            "assigned_to": display_username(row["assigned_key"]),
            "total": row["total"]
        }
        for row in cursor.fetchall()
    ]


    # =========================================================
    # COMPLETED TICKETS BY TECHNICIAN
    # =========================================================

    cursor.execute("""
        SELECT
            LOWER(completed_by) AS completed_key,
            COUNT(*) AS total
        FROM tickets
        WHERE status = 'Closed'
          AND completed_by IS NOT NULL
          AND TRIM(completed_by) != ''
          AND LOWER(completed_by) != 'unassigned'
        GROUP BY LOWER(completed_by)
        ORDER BY total DESC
    """)

    completed_by_stats = [
        {
            "completed_by": display_username(row["completed_key"]),
            "total": row["total"]
        }
        for row in cursor.fetchall()
    ]


    # =========================================================
    # 7-DAY TICKET VOLUME TREND
    #
    # Dates are parsed in Python so this remains portable
    # between SQLite and PostgreSQL.
    # =========================================================

    cursor.execute("""
        SELECT submitted_at
        FROM tickets
        WHERE submitted_at IS NOT NULL
          AND submitted_at != ''
    """)

    submitted_rows = cursor.fetchall()

    daily_counts = {}

    for row in submitted_rows:
        try:
            submitted_date = datetime.strptime(
                row["submitted_at"],
                "%m/%d/%Y %I:%M %p"
            ).date()

            daily_counts[submitted_date] = (
                daily_counts.get(submitted_date, 0) + 1
            )

        except (ValueError, TypeError):
            continue

    today = datetime.now().date()

    daily_stats = []

    for days_ago in range(6, -1, -1):
        day = today - timedelta(days=days_ago)

        daily_stats.append({
            "label": day.strftime("%a %m/%d"),
            "total": daily_counts.get(day, 0)
        })


    connection.close()


    # Current active tickets that have passed their SLA deadline.
    overdue_tickets = count_overdue_tickets()


    return render_template(
        "stats.html",

        # Ticket overview
        total_tickets=total_tickets,
        open_tickets=open_tickets,
        in_progress_tickets=in_progress_tickets,
        closed_tickets=closed_tickets,

        # Priority
        low_priority_tickets=low_priority_tickets,
        medium_priority_tickets=medium_priority_tickets,
        high_priority_tickets=high_priority_tickets,
        priority_stats=priority_stats,

        # SLA
        sla_met_count=sla_met_count,
        sla_missed_count=sla_missed_count,
        overdue_tickets=overdue_tickets,
        sla_missed_by_tech=sla_missed_by_tech,

        # Analytics
        department_stats=department_stats,
        category_stats=category_stats,
        assigned_stats=assigned_stats,
        completed_by_stats=completed_by_stats,
        daily_stats=daily_stats,
    )
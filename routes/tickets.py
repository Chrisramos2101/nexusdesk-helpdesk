from flask import Blueprint, current_app, jsonify, redirect, render_template, request, send_from_directory, session
from datetime import datetime, timedelta
from services.ticket_service import get_ticket_by_id, create_ticket, assign_ticket_to_user, close_ticket, delete_ticket_by_id, update_ticket_by_id, add_ticket_note, get_ticket_submitter_username
from database.db import get_db_connection
from routes.auth_helpers import login_required, admin_required
from services.audit_service import log_audit_event
from services.validation_service import (
    VALID_DEPARTMENTS,
    VALID_PRIORITIES,
    VALID_CATEGORIES,
    VALID_STATUSES,
    is_valid_choice,
    is_not_empty
)
import os
from uuid import uuid4
from werkzeug.utils import secure_filename
from services.attachment_service import save_attachment_record, get_attachment_with_ticket
from services.notification_service import send_ticket_created_email, send_ticket_assigned_email, send_ticket_closed_email, send_mention_email
from services.user_service import get_user_email_by_username, get_user_by_username
from database.sql_helpers import db_placeholder

tickets_bp = Blueprint("tickets", __name__)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf", "txt", "doc", "docx"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_sla_status(ticket):
    if ticket["status"] == "Closed":
        return "Completed"

    if not ticket["sla_due_at"]:
        return "No SLA"

    due_time = datetime.strptime(ticket["sla_due_at"], "%m/%d/%Y %I:%M %p")
    now = datetime.now()

    if now > due_time:
        return "Overdue"

    minutes_left = (due_time - now).total_seconds() / 60

    if minutes_left <= 60:
        return "Due Soon"

    return "On Track"


def calculate_resolution_time(submitted_at, closed_at):
    try:
        submitted_time = datetime.strptime(submitted_at, "%m/%d/%Y %I:%M %p")
        closed_time = datetime.strptime(closed_at, "%m/%d/%Y %I:%M %p")

        difference = closed_time - submitted_time
        total_minutes = int(difference.total_seconds() / 60)

        hours = total_minutes // 60
        minutes = total_minutes % 60

        return f"{hours} hr {minutes} min"

    except Exception:
        return ""


def calculate_sla_met(closed_at, sla_due_at):
    try:
        if not closed_at or not sla_due_at:
            return ""

        closed_time = datetime.strptime(closed_at, "%m/%d/%Y %I:%M %p")
        due_time = datetime.strptime(sla_due_at, "%m/%d/%Y %I:%M %p")

        return "Yes" if closed_time <= due_time else "No"

    except Exception:
        return ""
    

def calculate_ticket_age(submitted_at):
    try:
        submitted_time = datetime.strptime(submitted_at, "%m/%d/%Y %I:%M %p")
        difference = datetime.now() - submitted_time

        if difference.days > 0:
            return f"{difference.days} day(s) old"

        hours = difference.seconds // 3600
        minutes = (difference.seconds % 3600) // 60

        if hours > 0:
            return f"{hours} hour(s) old"

        return f"{minutes} minute(s) old"
    except Exception:
        return "Recently submitted"


def calculate_sla_progress(submitted_at, sla_due_at, status):
    try:
        if status == "Closed":
            return 100

        if not sla_due_at:
            return 0

        submitted_time = datetime.strptime(submitted_at, "%m/%d/%Y %I:%M %p")
        due_time = datetime.strptime(sla_due_at, "%m/%d/%Y %I:%M %p")
        now = datetime.now()

        total = (due_time - submitted_time).total_seconds()
        used = (now - submitted_time).total_seconds()

        if total <= 0:
            return 100

        progress = int((used / total) * 100)

        return max(0, min(progress, 100))
    except Exception:
        return 0


@tickets_bp.route("/")
@login_required
def home():
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) AS total FROM tickets WHERE status = 'Open'")
    open_tickets = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM tickets WHERE priority = 'High'")
    high_priority_tickets = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT sla_due_at
        FROM tickets
        WHERE status != 'Closed' AND sla_due_at != ''
    """)
    rows = cursor.fetchall()

    overdue_tickets = 0

    for row in rows:
        try:
            due_time = datetime.strptime(row["sla_due_at"], "%m/%d/%Y %I:%M %p")
            if datetime.now() > due_time:
                overdue_tickets += 1
        except Exception:
            pass

    submitted = request.args.get("submitted")
    ticket_id = request.args.get("ticket_id")
    prefill_priority = request.args.get("priority", "")
    prefill_category = request.args.get("category", "")
    prefill_issue = request.args.get("issue", "")

    placeholder = db_placeholder()

    cursor.execute(f"""
        SELECT COUNT(*) AS total
        FROM tickets
        WHERE submitted_by = {placeholder} AND status != 'Closed'
    """, (session["username"],))
    my_open_tickets = cursor.fetchone()["total"]

    connection.close()

    return render_template(
        "index.html",
        role=session["role"],
        open_tickets=open_tickets,
        overdue_tickets=overdue_tickets,
        high_priority_tickets=high_priority_tickets,
        submitted=submitted,
        ticket_id=ticket_id,
        username=session["username"],
        my_open_tickets=my_open_tickets,
        prefill_priority=prefill_priority,
        prefill_category=prefill_category,
        prefill_issue=prefill_issue,
    )


@tickets_bp.route("/my_tickets")
@login_required
def my_tickets():
    connection = get_db_connection()
    cursor = connection.cursor()

    placeholder = db_placeholder()

    cursor.execute(f"""
        SELECT *
        FROM tickets
        WHERE submitted_by = {placeholder}
        ORDER BY id DESC
    """, (session["username"],))

    tickets = cursor.fetchall()
    connection.close()

    return render_template("my_tickets.html", tickets=tickets)


@tickets_bp.route("/my_tickets/<int:ticket_id>")
@login_required
def ticket_detail(ticket_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    placeholder = db_placeholder()

    cursor.execute(f"""
        SELECT *
        FROM tickets
        WHERE id = {placeholder}
        AND submitted_by = {placeholder}
    """, (ticket_id, session["username"]))

    ticket = cursor.fetchone()

    if not ticket:
        connection.close()
        return redirect("/my_tickets")

    cursor.execute(f"""
        SELECT *
        FROM ticket_notes
        WHERE ticket_id = {placeholder}
        ORDER BY id DESC
    """, (ticket_id,))

    notes = cursor.fetchall()

    cursor.execute(f"""
        SELECT *
        FROM ticket_attachments
        WHERE ticket_id = {placeholder}
        ORDER BY id DESC
    """, (ticket_id,))

    attachments = cursor.fetchall()

    ticket_age = calculate_ticket_age(ticket["submitted_at"])
    sla_progress = calculate_sla_progress(
        ticket["submitted_at"],
        ticket["sla_due_at"],
        ticket["status"]
    )

    connection.close()

    return render_template(
        "ticket_detail.html",
        ticket=ticket,
        notes=notes,
        attachments=attachments,
        ticket_age=ticket_age,
        sla_progress=sla_progress
    )


@tickets_bp.route("/api/users/search")
@login_required
def search_users():
    query = request.args.get("q", "").lower()
    placeholder = db_placeholder()

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(f"""
        SELECT username, role, full_name
        FROM users
        WHERE LOWER(username) LIKE {placeholder}
        OR LOWER(full_name) LIKE {placeholder}
        ORDER BY username
        LIMIT 8
    """, (f"%{query}%", f"%{query}%"))

    users = cursor.fetchall()
    connection.close()

    return jsonify([
        {
            "username": user["username"],
            "role": user["role"],
            "full_name": user["full_name"]
        }
        for user in users
    ])


@tickets_bp.route("/my_tickets/<int:ticket_id>/comment", methods=["POST"])
@login_required
def employee_add_ticket_comment(ticket_id):
    comment = request.form["comment"]

    if not comment.strip():
        return redirect(f"/my_tickets/{ticket_id}")

    connection = get_db_connection()
    cursor = connection.cursor()

    placeholder = db_placeholder()

    cursor.execute(f"""
        SELECT id
        FROM tickets
        WHERE id = {placeholder}
        AND submitted_by = {placeholder}
    """, (ticket_id, session["username"]))

    ticket = cursor.fetchone()
    connection.close()

    if not ticket:
        return redirect("/my_tickets")

    add_ticket_note(
        ticket_id,
        comment,
        session["username"],
        datetime.now().strftime("%m/%d/%Y %I:%M %p")
    )

    log_audit_event(
        session["username"],
        "ADD_EMPLOYEE_COMMENT",
        "ticket",
        ticket_id,
        "Employee added comment to ticket"
    )

    return redirect(f"/my_tickets/{ticket_id}")


@tickets_bp.route("/submit", methods=["POST"])
@login_required
def submit():
    name = request.form["name"]
    department = request.form["department"]
    issue = request.form["issue"]
    priority = request.form["priority"]
    category = request.form["category"]
    if not is_not_empty(name) or not is_not_empty(issue):
        return redirect("/")

    if not is_valid_choice(department, VALID_DEPARTMENTS):
        return redirect("/")

    if not is_valid_choice(priority, VALID_PRIORITIES):
        return redirect("/")

    if not is_valid_choice(category, VALID_CATEGORIES):
        return redirect("/")
    submitted_at = datetime.now().strftime("%m/%d/%Y %I:%M %p")
    submitted_by = session["username"]

    now = datetime.now()

    if priority == "High":
        sla_due_at = (now + timedelta(hours=1)).strftime("%m/%d/%Y %I:%M %p")
    elif priority == "Medium":
        sla_due_at = (now + timedelta(hours=8)).strftime("%m/%d/%Y %I:%M %p")
    else:
        sla_due_at = (now + timedelta(hours=24)).strftime("%m/%d/%Y %I:%M %p")

    new_ticket_id = create_ticket(
        name,
        department,
        issue,
        priority,
        category,
        submitted_at,
        submitted_by,
        sla_due_at
    )

    uploaded_file = request.files.get("attachment")

    if uploaded_file and uploaded_file.filename != "":
        if allowed_file(uploaded_file.filename):
            original_filename = secure_filename(uploaded_file.filename)
            file_extension = original_filename.rsplit(".", 1)[1].lower()
            stored_filename = f"{uuid4().hex}.{file_extension}"

            upload_folder = current_app.config["UPLOAD_FOLDER"]
            os.makedirs(upload_folder, exist_ok=True)

            file_path = os.path.join(upload_folder, stored_filename)
            uploaded_file.save(file_path)

            save_attachment_record(
                new_ticket_id,
                original_filename,
                stored_filename,
                session["username"]
            )

    log_audit_event(
        session["username"],
        "CREATE_TICKET",
        "ticket",
        new_ticket_id,
        f"Created {priority} priority ticket"
    )

    recipient_email = get_user_email_by_username(session["username"])

    if recipient_email:
        send_ticket_created_email(
            recipient_email,
            session["username"],
            new_ticket_id,
            priority,
            category
        )

    return redirect(f"/?submitted=success&ticket_id={new_ticket_id}")


@tickets_bp.route("/update_ticket/<int:ticket_id>", methods=["POST"])
@admin_required
def update_ticket(ticket_id):
    name = request.form["name"]
    department = request.form["department"]
    issue = request.form["issue"]
    priority = request.form["priority"]
    category = request.form["category"]
    status = request.form["status"]
    if not is_valid_choice(department, VALID_DEPARTMENTS):
        return redirect("/dashboard")

    if not is_valid_choice(priority, VALID_PRIORITIES):
        return redirect("/dashboard")

    if not is_valid_choice(category, VALID_CATEGORIES):
        return redirect("/dashboard")

    if not is_valid_choice(status, VALID_STATUSES):
        return redirect("/dashboard")
    assigned_to = request.form["assigned_to"]
    new_note = request.form["notes"]

    connection = get_db_connection()
    cursor = connection.cursor()

    placeholder = db_placeholder()

    cursor.execute(f"SELECT * FROM tickets WHERE id = {placeholder}", (ticket_id,))
    ticket = cursor.fetchone()

    closed_at = ticket["closed_at"] if ticket["closed_at"] else ""
    completed_by = ticket["completed_by"] if ticket["completed_by"] else ""
    resolution_time = ticket["resolution_time"] if "resolution_time" in ticket.keys() else ""
    sla_met = ticket["sla_met"] if "sla_met" in ticket.keys() else ""

    if status == "Closed" and not closed_at:
        closed_at = datetime.now().strftime("%m/%d/%Y %I:%M %p")
        completed_by = assigned_to if assigned_to != "Unassigned" else session["username"]
        resolution_time = calculate_resolution_time(ticket["submitted_at"], closed_at)
        sla_met = calculate_sla_met(closed_at, ticket["sla_due_at"])

    if status != "Closed":
        closed_at = ""
        completed_by = ""
        resolution_time = ""
        sla_met = ""

    update_ticket_by_id(
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
    )

    log_audit_event(
        session["username"],
        "UPDATE_TICKET",
        "ticket",
        ticket_id,
        f"Updated ticket status to {status}"
    )

    if new_note.strip() != "":
        note_time = datetime.now().strftime("%m/%d/%Y %I:%M %p")

        add_ticket_note(
            ticket_id,
            new_note,
            session["username"],
            note_time
        )

        words = new_note.split()

        for word in words:

            if word.startswith("@"):

                mentioned_username = word.replace("@", "").strip()

                mentioned_user = get_user_by_username(
                    mentioned_username
                )

                if mentioned_user:

                    send_mention_email(
                        mentioned_user["email"],
                        mentioned_username,
                        ticket_id,
                        new_note
                    )

                    log_audit_event(
                        session["username"],
                        "MENTION_USER",
                        "ticket",
                        ticket_id,
                        f"Mentioned {mentioned_username}"
                    )

    return redirect(f"/dashboard?status={status}")


@tickets_bp.route("/assign_me/<int:ticket_id>", methods=["POST"])
@admin_required
def assign_me(ticket_id):
    assign_ticket_to_user(
        ticket_id,
        session["username"].capitalize()
    )

    log_audit_event(
        session["username"],
        "ASSIGN_TICKET",
        "ticket",
        ticket_id,
        "Assigned ticket to self"
    )

    recipient_email = get_user_email_by_username(session["username"])

    if recipient_email:
        send_ticket_assigned_email(
            recipient_email,
            session["username"],
            ticket_id
        )

    return redirect("/dashboard")


@tickets_bp.route("/quick_close/<int:ticket_id>", methods=["POST"])
@admin_required
def quick_close(ticket_id):
    closed_at = datetime.now().strftime("%m/%d/%Y %I:%M %p")

    ticket = get_ticket_by_id(ticket_id)

    resolution_time = calculate_resolution_time(
        ticket["submitted_at"],
        closed_at
    )

    sla_met = calculate_sla_met(
        closed_at,
        ticket["sla_due_at"]
    )

    close_ticket(
        ticket_id,
        closed_at,
        ticket["assigned_to"] if ticket["assigned_to"] else session["username"],
        resolution_time,
        sla_met
    )

    log_audit_event(
        session["username"],
        "CLOSE_TICKET",
        "ticket",
        ticket_id,
        "Quick closed ticket"
    )

    submitter_username = get_ticket_submitter_username(ticket_id)
    submitter_email = get_user_email_by_username(submitter_username)

    if submitter_email:
        send_ticket_closed_email(
            submitter_email,
            submitter_username,
            ticket_id,
            resolution_time,
            sla_met
        )

    return redirect("/dashboard?status=Closed")


@tickets_bp.route("/delete_ticket/<int:ticket_id>", methods=["POST"])
@admin_required
def delete_ticket(ticket_id):
    stored_filenames = delete_ticket_by_id(ticket_id)

    for stored_filename in stored_filenames:
        file_path = os.path.join(current_app.config["UPLOAD_FOLDER"], stored_filename)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
        except OSError:
            pass

    log_audit_event(
        session["username"],
        "DELETE_TICKET",
        "ticket",
        ticket_id,
        "Deleted ticket"
    )

    return redirect("/dashboard")


@tickets_bp.route("/attachment/<filename>")
@login_required
def download_attachment(filename):
    attachment = get_attachment_with_ticket(filename)

    if not attachment:
        return "Attachment not found", 404

    is_admin = session.get("role") == "admin"
    owns_ticket = attachment["submitted_by"] == session.get("username")

    if not is_admin and not owns_ticket:
        return "Forbidden", 403

    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        attachment["stored_filename"],
        as_attachment=True,
        download_name=attachment["original_filename"]
    )

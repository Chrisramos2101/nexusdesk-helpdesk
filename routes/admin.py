import os
import sqlite3

try:
    import psycopg2
    INTEGRITY_ERRORS = (sqlite3.IntegrityError, psycopg2.IntegrityError)
except ImportError:
    INTEGRITY_ERRORS = (sqlite3.IntegrityError,)
from flask import Blueprint, render_template, request, redirect, session
from werkzeug.security import generate_password_hash
from services.user_service import get_all_users, update_user, delete_user_by_id, create_user_account
from database.db import get_db_connection
from database.sql_helpers import db_placeholder
from routes.auth_helpers import admin_required
from services.audit_service import log_audit_event
from services.cleanup_service import cleanup_expired_security_records
from services.validation_service import (
    VALID_DEPARTMENTS,
    VALID_ROLES,
    is_valid_choice,
    is_not_empty,
    validate_password_strength
)

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/users")
@admin_required
def users():
    users = get_all_users()

    return render_template(
        "users.html",
        users=users
    )


@admin_bp.route("/edit_user/<int:user_id>", methods=["POST"])
@admin_required
def edit_user(user_id):
    full_name = request.form["full_name"]
    email = request.form["email"]
    department = request.form["department"]
    role = request.form["role"]
    if (
        not is_not_empty(full_name)
        or not is_not_empty(email)
    ):
        return redirect("/users")

    if not is_valid_choice(department, VALID_DEPARTMENTS):
        return redirect("/users")

    if not is_valid_choice(role, VALID_ROLES):
        return redirect("/users")

    update_user(user_id, full_name, email, department, role)

    log_audit_event(
        session["username"],
        "UPDATE_USER",
        "user",
        user_id,
        f"Updated user {full_name}"
    )

    return redirect("/users")


@admin_bp.route("/delete_user/<int:user_id>", methods=["POST"])
@admin_required
def delete_user(user_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    placeholder = db_placeholder()
    cursor.execute(f"""
        SELECT username
        FROM users
        WHERE id = {placeholder}
    """, (user_id,))

    user = cursor.fetchone()

    if user and user["username"] == session["username"]:
        connection.close()
        return redirect("/users")

    connection.close()

    delete_user_by_id(user_id)

    log_audit_event(
        session["username"],
        "DELETE_USER",
        "user",
        user_id,
        "Deleted user account"
    )

    return redirect("/users")


@admin_bp.route("/create_user", methods=["GET", "POST"])
@admin_required
def create_user():
    message = ""

    if request.method == "POST":
        full_name = request.form["full_name"]
        username = request.form["username"]
        email = request.form["email"]
        department = request.form["department"]
        password = request.form["password"]
        role = request.form["role"]
        if (
            not is_not_empty(full_name)
            or not is_not_empty(username)
            or not is_not_empty(email)
            or not is_not_empty(password)
        ):
            message = "All fields are required."
            return render_template("create_user.html", message=message)

        if not is_valid_choice(department, VALID_DEPARTMENTS):
            message = "Invalid department selected."
            return render_template("create_user.html", message=message)

        if not is_valid_choice(role, VALID_ROLES):
            message = "Invalid role selected."
            return render_template("create_user.html", message=message)

        is_valid_password, password_error = validate_password_strength(password)

        if not is_valid_password:
            message = password_error
            return render_template("create_user.html", message=message)

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            create_user_account(
                full_name,
                username,
                email,
                department,
                generate_password_hash(password),
                role
            )

            message = "User created successfully."

            log_audit_event(
                session["username"],
                "CREATE_USER",
                "user",
                username,
                f"Created user account with role {role}"
            )

        except INTEGRITY_ERRORS:
            message = "Username already exists."

        connection.close()

    return render_template("create_user.html", message=message)


@admin_bp.route("/run_security_cleanup", methods=["POST"])
@admin_required
def run_security_cleanup():
    cleanup_expired_security_records()

    log_audit_event(
        session["username"],
        "RUN_SECURITY_CLEANUP",
        "system",
        "",
        "Cleaned expired MFA codes and used reset tokens"
    )

    return redirect("/system_dashboard")



@admin_bp.route("/system_dashboard")
@admin_required
def system_dashboard():

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) AS count FROM users")
    total_users = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) AS count FROM tickets")
    total_tickets = cursor.fetchone()["count"]

    cursor.execute("""
        SELECT COUNT(*) AS count
        FROM tickets
        WHERE status != 'Closed'
    """)
    open_tickets = cursor.fetchone()["count"]

    cursor.execute("""
        SELECT COUNT(*) AS count
        FROM login_events
    """)
    total_logins = cursor.fetchone()["count"]

    cursor.execute("""
        SELECT *
        FROM audit_logs
        ORDER BY id DESC
        LIMIT 10
    """)

    recent_activity = cursor.fetchall()

    cursor.execute("""
        SELECT COUNT(*) AS count
        FROM users
        WHERE failed_attempts > 0
    """)
    at_risk_accounts = cursor.fetchone()["count"]

    cursor.execute("""
        SELECT username,
            failed_attempts,
            locked_until
        FROM users
        WHERE failed_attempts > 0
        ORDER BY failed_attempts DESC
    """)
    failed_login_users = cursor.fetchall()

    cursor.execute("""
        SELECT COUNT(*) AS count
        FROM audit_logs
        WHERE action LIKE '%EMAIL%'
        OR action LIKE '%PASSWORD_RESET%'
        OR action LIKE '%MENTION%'
    """)
    email_events = cursor.fetchone()["count"]

    cursor.execute("""
        SELECT *
        FROM audit_logs
        WHERE action LIKE '%EMAIL%'
        OR action LIKE '%PASSWORD_RESET%'
        OR action LIKE '%MENTION%'
        ORDER BY id DESC
        LIMIT 5
    """)
    recent_email_events = cursor.fetchall()

    system_status = "Healthy"
    database_status = "Connected"
    app_environment = os.getenv("FLASK_ENV", "development")

    cursor.execute("""
        SELECT COUNT(*) AS count
        FROM audit_logs
        WHERE action = 'MFA_SUCCESS'
    """)
    mfa_success_count = cursor.fetchone()["count"]

    cursor.execute("""
        SELECT COUNT(*) AS count
        FROM audit_logs
        WHERE action = 'MFA_FAILED'
    """)
    mfa_failed_count = cursor.fetchone()["count"]

    connection.close()

    return render_template(
        "system_dashboard.html",
        total_users=total_users,
        total_tickets=total_tickets,
        open_tickets=open_tickets,
        total_logins=total_logins,
        recent_activity=recent_activity,
        at_risk_accounts=at_risk_accounts,
        failed_login_users=failed_login_users,
        email_events=email_events,
        recent_email_events=recent_email_events,
        system_status=system_status,
        database_status=database_status,
        app_environment=app_environment,
        mfa_success_count=mfa_success_count,
        mfa_failed_count=mfa_failed_count
    )
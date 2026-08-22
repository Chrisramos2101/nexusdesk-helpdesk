from flask import Blueprint, render_template, request, redirect, session
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta
from routes.auth_helpers import login_required
from database.db import get_db_connection
from database.sql_helpers import db_placeholder
from services.user_service import get_user_by_username
from services.validation_service import validate_password_strength
from services.email_service import send_email
from services.password_reset_service import (
    get_user_by_email,
    create_password_reset_token,
    get_valid_reset_token,
    mark_token_used
)
from services.audit_service import log_audit_event
from services.mfa_service import generate_mfa_code, invalidate_mfa_codes, verify_mfa_code
from services.security_service import check_rate_limit, reset_rate_limit
from services.production_config import get_app_base_url
import os

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    error = ""

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        rate_key = f"{request.remote_addr or 'unknown'}:{username.lower()}"
        allowed, retry_after = check_rate_limit(rate_key, "login", limit=10, window_seconds=300)
        if not allowed:
            error = f"Too many login attempts. Try again in {retry_after} seconds."
            return render_template("login.html", error=error), 429

        user = get_user_by_username(username)
        now = datetime.now()

        if user:
            locked_until = user["locked_until"]

            if locked_until:
                try:
                    lock_time = datetime.strptime(locked_until, "%m/%d/%Y %I:%M %p")
                    if now < lock_time:
                        error = f"Account locked until {locked_until}."
                        return render_template("login.html", error=error)
                except Exception:
                    pass

        if user and check_password_hash(user["password_hash"], password):
            connection = get_db_connection()
            cursor = connection.cursor()
            placeholder = db_placeholder()

            login_time = now.strftime("%m/%d/%Y %I:%M %p")

            cursor.execute(f"""
                UPDATE users
                SET failed_attempts = 0,
                    locked_until = '',
                    last_login = {placeholder}
                WHERE username = {placeholder}
            """, (login_time, username))

            cursor.execute(f"""
                INSERT INTO login_events (username, event_type, event_time)
                VALUES ({placeholder}, {placeholder}, {placeholder})
            """, (username, "login", login_time))

            connection.commit()
            connection.close()

            reset_rate_limit(rate_key, "login")
            mfa_code = generate_mfa_code(user["username"])

            email_sent = send_email(
                "NexusDesk MFA Verification Code",
                user["email"],
                f"""
            Hello {user["username"]},

            Your NexusDesk verification code is:

            {mfa_code}

            This code expires in 10 minutes.

            If this was not you, contact IT immediately.
            """
            )

            if not email_sent:
                invalidate_mfa_codes(user["username"])
                error = "Unable to send a verification code right now. Please contact IT."
                return render_template("login.html", error=error), 503

            session.clear()
            session["pending_mfa_username"] = user["username"]
            session["pending_mfa_role"] = user["role"]

            return redirect("/mfa_verify")

        if user:
            failed_attempts = user["failed_attempts"] + 1
            locked_until = ""

            if failed_attempts >= 5:
                locked_until = (now + timedelta(minutes=15)).strftime("%m/%d/%Y %I:%M %p")

            connection = get_db_connection()
            cursor = connection.cursor()
            placeholder = db_placeholder()

            cursor.execute(f"""
                UPDATE users
                SET failed_attempts = {placeholder},
                    locked_until = {placeholder}
                WHERE username = {placeholder}
            """, (failed_attempts, locked_until, username))

            connection.commit()
            connection.close()

        error = "Invalid username or password"

    return render_template("login.html", error=error)


@auth_bp.route("/mfa_verify", methods=["GET", "POST"])
def mfa_verify():
    error = ""

    if "pending_mfa_username" not in session:
        return redirect("/login")

    if request.method == "POST":
        submitted_code = request.form.get("mfa_code", "").strip()
        username = session["pending_mfa_username"]
        role = session["pending_mfa_role"]

        rate_key = f"{request.remote_addr or 'unknown'}:{username.lower()}"
        allowed, retry_after = check_rate_limit(rate_key, "mfa", limit=10, window_seconds=600)
        if not allowed:
            error = f"Too many verification attempts. Try again in {retry_after} seconds."
            return render_template("mfa_verify.html", error=error), 429

        if verify_mfa_code(username, submitted_code):
            reset_rate_limit(rate_key, "mfa")
            log_audit_event(
                username,
                "MFA_SUCCESS",
                "user",
                "",
                "User completed MFA verification"
            )

            session.clear()
            session.permanent = True
            session["username"] = username
            session["role"] = role

            return redirect("/")
        
        error = "Invalid or expired verification code."

        log_audit_event(
            session["pending_mfa_username"],
            "MFA_FAILED",
            "user",
            "",
            "Invalid or expired MFA code"
        )

    return render_template("mfa_verify.html", error=error)


@auth_bp.route("/logout")
def logout():
    if "username" in session:
        logout_time = datetime.now().strftime("%m/%d/%Y %I:%M %p")

        connection = get_db_connection()
        cursor = connection.cursor()
        placeholder = db_placeholder()

        cursor.execute(f"""
            UPDATE users
            SET last_logout = {placeholder}
            WHERE username = {placeholder}
        """, (logout_time, session["username"]))

        cursor.execute(f"""
            INSERT INTO login_events (username, event_type, event_time)
            VALUES ({placeholder}, {placeholder}, {placeholder})
        """, (session["username"], "logout", logout_time))

        connection.commit()
        connection.close()

    session.clear()
    return redirect("/login")


@auth_bp.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    message = ""

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        rate_key = f"{request.remote_addr or 'unknown'}:{email}"
        allowed, retry_after = check_rate_limit(rate_key, "password_reset", limit=5, window_seconds=900)
        if not allowed:
            message = f"Too many reset requests. Try again in {retry_after} seconds."
            return render_template("forgot_password.html", message=message), 429

        user = get_user_by_email(email)

        if user:
            token = create_password_reset_token(user["id"])
            base_url = get_app_base_url()
            reset_link = f"{base_url}/reset_password/{token}"

            email_body = f"""
Hello {user["username"]},

A password reset was requested for your NexusDesk account.

Click the link below to reset your password:

{reset_link}

This link expires in 30 minutes.

If you did not request this, you can ignore this email.
"""

            email_sent = send_email(
                "NexusDesk Password Reset",
                user["email"],
                email_body
            )

            log_audit_event(
                user["username"],
                "REQUEST_PASSWORD_RESET",
                "user",
                user["id"],
                "Password reset email sent" if email_sent else "Password reset email delivery failed"
            )

        message = "If this email exists, a password reset link has been sent."

    return render_template("forgot_password.html", message=message)


@auth_bp.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    reset_token = get_valid_reset_token(token)

    if not reset_token:
        return render_template(
            "reset_password.html",
            error="This password reset link is invalid or expired.",
            message=""
        )

    message = ""
    error = ""

    if request.method == "POST":
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if new_password != confirm_password:
            error = "Passwords do not match."
        else:
            is_valid_password, password_error = validate_password_strength(new_password)

            if not is_valid_password:
                error = password_error
            else:
                connection = get_db_connection()
                cursor = connection.cursor()
                placeholder = db_placeholder()

                cursor.execute(f"""
                    UPDATE users
                    SET password_hash = {placeholder}
                    WHERE id = {placeholder}
                """, (
                    generate_password_hash(new_password),
                    reset_token["user_id"]
                ))

                connection.commit()
                connection.close()

                mark_token_used(token)

                log_audit_event(
                    reset_token["username"],
                    "RESET_PASSWORD",
                    "user",
                    reset_token["user_id"],
                    "Password reset completed"
                )

                message = "Password reset successfully. You may now log in."

    return render_template(
        "reset_password.html",
        error=error,
        message=message
    )


@auth_bp.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    message = ""
    error = ""

    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if new_password != confirm_password:
            error = "New passwords do not match."
        else:
            is_valid_password, password_error = validate_password_strength(new_password)

            if not is_valid_password:
                error = password_error
            else:
                connection = get_db_connection()
                cursor = connection.cursor()
                placeholder = db_placeholder()

                cursor.execute(f"""
                    SELECT *
                    FROM users
                    WHERE username = {placeholder}
                """, (session["username"],))

                user = cursor.fetchone()

                if user and check_password_hash(user["password_hash"], current_password):
                    cursor.execute(f"""
                        UPDATE users
                        SET password_hash = {placeholder}
                        WHERE username = {placeholder}
                    """, (generate_password_hash(new_password), session["username"]))

                    connection.commit()
                    message = "Password changed successfully."
                else:
                    error = "Current password is incorrect."

                connection.close()

    return render_template("change_password.html", message=message, error=error)


@auth_bp.route("/profile")
@login_required
def profile():
    user = get_user_by_username(session["username"])

    return render_template(
        "profile.html",
        user=user
    )


@auth_bp.route("/update_profile", methods=["POST"])
@login_required
def update_profile():

    full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip()
    department = request.form.get("department", "").strip()

    connection = get_db_connection()
    cursor = connection.cursor()
    placeholder = db_placeholder()

    cursor.execute(f"""
        UPDATE users
        SET
            full_name = {placeholder},
            email = {placeholder},
            department = {placeholder}
        WHERE username = {placeholder}
    """, (
        full_name,
        email,
        department,
        session["username"]
    ))

    connection.commit()
    connection.close()

    return redirect("/profile")

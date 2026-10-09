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
from html import escape
import os

auth_bp = Blueprint("auth", __name__)

MFA_TRUST_MINUTES = 30


def has_valid_mfa_trust(username):
    trusted_username = session.get("mfa_trusted_username")
    trusted_until = session.get("mfa_trusted_until")

    if trusted_username != username or not trusted_until:
        return False

    try:
        expires_at = datetime.fromisoformat(trusted_until)
        return datetime.now() < expires_at
    except (TypeError, ValueError):
        return False

def mask_email(email: str) -> str:
    if not email or "@" not in email:
        return "your account email"

    local_part, domain = email.rsplit("@", 1)

    if len(local_part) <= 1:
        masked_local = "•"
    else:
        visible_first = local_part[0]
        mask_length = min(max(len(local_part) - 1, 4), 10)
        masked_local = visible_first + ("•" * mask_length)

    return f"{masked_local}@{domain}"


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

            if has_valid_mfa_trust(user["username"]):
                trusted_until = session["mfa_trusted_until"]

                session.clear()
                session.permanent = True

                session["username"] = user["username"]
                session["role"] = user["role"]

                session["mfa_trusted_username"] = user["username"]
                session["mfa_trusted_until"] = trusted_until

                log_audit_event(
                    user["username"],
                    "MFA_TRUST_REUSED",
                    "user",
                    "",
                    "Login completed within active 30-minute MFA trust window"
                )

                return redirect("/")

            reset_rate_limit(rate_key, "login")
            mfa_code = generate_mfa_code(user["username"])

            display_name = (
                user["full_name"]
                or user["username"]
            ).strip()

            safe_display_name = escape(display_name)

            email_body = f"""
            Hello {display_name},

            Your NexusDesk verification code is:

            {mfa_code}

            This code expires in 10 minutes.

            If you did not attempt to sign in to NexusDesk, you can safely ignore this email.

            Security reminder:
            Never share your verification code with anyone.
            NexusDesk will never ask you to send your password or verification code by email.

            — NexusDesk
            IT Support & Ticket Management
            """

            email_html = f"""
            <!DOCTYPE html>
            <html lang="en">
            <body style="
                margin:0;
                padding:0;
                background-color:#0f172a;
                font-family:Arial, Helvetica, sans-serif;
                color:#e5e7eb;
            ">

            <table width="100%" cellpadding="0" cellspacing="0"
                style="padding:40px 20px; background-color:#0f172a;">
                <tr>
                    <td align="center">

                        <table width="100%" cellpadding="0" cellspacing="0"
                            style="
                                max-width:600px;
                                background-color:#111827;
                                border:1px solid #263449;
                                border-radius:16px;
                                padding:36px;
                            ">
                            <tr>
                                <td>

                                    <div style="
                                        font-size:24px;
                                        font-weight:bold;
                                        color:#ffffff;
                                        margin-bottom:6px;
                                    ">
                                        🎧 NexusDesk
                                    </div>

                                    <div style="
                                        color:#94a3b8;
                                        font-size:14px;
                                        margin-bottom:32px;
                                    ">
                                        IT Support & Ticket Management
                                    </div>

                                    <h1 style="
                                        color:#ffffff;
                                        font-size:26px;
                                        margin:0 0 16px 0;
                                    ">
                                        Verify Your Sign-In
                                    </h1>

                                    <p style="
                                        color:#e5e7eb;
                                        line-height:1.6;
                                    ">
                                        Hello <strong>{safe_display_name}</strong>,
                                    </p>

                                    <p style="
                                        color:#cbd5e1;
                                        line-height:1.6;
                                    ">
                                        Use the verification code below to finish
                                        signing in to your NexusDesk account.
                                    </p>

                                    <div style="
                                        margin:30px 0;
                                        text-align:center;
                                    ">
                                        <div style="
                                            display:inline-block;
                                            min-width:220px;
                                            padding:22px 28px;
                                            background-color:#1e293b;
                                            border:1px solid #334155;
                                            border-radius:12px;
                                            color:#ffffff;
                                            font-size:34px;
                                            font-weight:bold;
                                            letter-spacing:10px;
                                            text-align:center;
                                        ">
                                            {mfa_code}
                                        </div>
                                    </div>

                                    <div style="
                                        background-color:#1e293b;
                                        border-radius:10px;
                                        padding:16px;
                                        margin:24px 0;
                                        color:#cbd5e1;
                                        font-size:14px;
                                        line-height:1.5;
                                    ">
                                        ⏱ <strong>
                                            This verification code expires in 10 minutes.
                                        </strong>
                                    </div>

                                    <p style="
                                        color:#94a3b8;
                                        font-size:14px;
                                        line-height:1.6;
                                    ">
                                        If you did not attempt to sign in to NexusDesk,
                                        you can safely ignore this email.
                                    </p>

                                    <hr style="
                                        border:none;
                                        border-top:1px solid #263449;
                                        margin:28px 0;
                                    ">

                                    <p style="
                                        color:#94a3b8;
                                        font-size:13px;
                                        line-height:1.6;
                                    ">
                                        🔒 <strong>Security reminder:</strong>
                                        Never share your verification code with anyone.
                                        NexusDesk will never ask you to send your password
                                        or verification code by email.
                                    </p>

                                </td>
                            </tr>
                        </table>

                    </td>
                </tr>
            </table>

            </body>
            </html>
            """

            email_sent = send_email(
                "NexusDesk Sign-In Verification Code",
                user["email"],
                email_body,
                html_body=email_html
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
    message = ""

    if "pending_mfa_username" not in session:
        return redirect("/login")

    username = session["pending_mfa_username"]

    user = get_user_by_username(username)

    masked_email = (
        mask_email(user["email"])
        if user and user["email"]
        else "your account email"
    )

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

            trusted_until = (
                datetime.now() + timedelta(minutes=MFA_TRUST_MINUTES)
            ).isoformat()

            session.clear()
            session.permanent = True

            session["username"] = username
            session["role"] = role

            session["mfa_trusted_username"] = username
            session["mfa_trusted_until"] = trusted_until

            return redirect("/")
        
        error = "Invalid or expired verification code."

        log_audit_event(
            session["pending_mfa_username"],
            "MFA_FAILED",
            "user",
            "",
            "Invalid or expired MFA code"
        )

    return render_template("mfa_verify.html", error=error, message=message, masked_email=masked_email)


@auth_bp.route("/mfa_resend", methods=["POST"])
def mfa_resend():

    if "pending_mfa_username" not in session:
        return redirect("/login")

    username = session["pending_mfa_username"]

    user = get_user_by_username(username)

    if not user:
        session.clear()
        return redirect("/login")

    masked_email = mask_email(user["email"])

    rate_key = (
        f"{request.remote_addr or 'unknown'}:"
        f"{username.lower()}"
    )

    allowed, retry_after = check_rate_limit(
        rate_key,
        "mfa_resend",
        limit=3,
        window_seconds=600
    )

    if not allowed:
        error = (
            "Too many verification-code requests. "
            f"Try again in {retry_after} seconds."
        )

        return render_template(
            "mfa_verify.html",
            error=error,
            message="",
            masked_email=masked_email
        ), 429

    mfa_code = generate_mfa_code(username)

    display_name = (
        user["full_name"]
        or user["username"]
    ).strip()

    email_body = f"""
    Hello {display_name},

    Your new NexusDesk verification code is:

    {mfa_code}

    This code expires in 10 minutes.

    Your previous verification code is no longer valid.

    If you did not attempt to sign in to NexusDesk, you can safely ignore this email.

    Security reminder:
    Never share your verification code with anyone.
    NexusDesk will never ask you to send your password or verification code by email.

    — NexusDesk
    IT Support & Ticket Management
    """

    safe_display_name = escape(display_name)

    email_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <body style="
        margin:0;
        padding:0;
        background-color:#0f172a;
        font-family:Arial, Helvetica, sans-serif;
        color:#e5e7eb;
    ">

    <table width="100%" cellpadding="0" cellspacing="0"
        style="padding:40px 20px; background-color:#0f172a;">
        <tr>
            <td align="center">

                <table width="100%" cellpadding="0" cellspacing="0"
                    style="
                        max-width:600px;
                        background-color:#111827;
                        border:1px solid #263449;
                        border-radius:16px;
                        padding:36px;
                    ">
                    <tr>
                        <td>

                            <div style="
                                font-size:24px;
                                font-weight:bold;
                                color:#ffffff;
                                margin-bottom:6px;
                            ">
                                🎧 NexusDesk
                            </div>

                            <div style="
                                color:#94a3b8;
                                font-size:14px;
                                margin-bottom:32px;
                            ">
                                IT Support & Ticket Management
                            </div>

                            <h1 style="
                                color:#ffffff;
                                font-size:26px;
                                margin:0 0 16px 0;
                            ">
                                Verify Your Sign-In
                            </h1>

                            <p style="
                                color:#e5e7eb;
                                line-height:1.6;
                            ">
                                Hello <strong>{safe_display_name}</strong>,
                            </p>

                            <p style="
                                color:#cbd5e1;
                                line-height:1.6;
                            ">
                                Use the verification code below to finish
                                signing in to your NexusDesk account.
                            </p>

                            <div style="
                                margin:30px 0;
                                text-align:center;
                            ">
                                <div style="
                                    display:inline-block;
                                    min-width:220px;
                                    padding:22px 28px;
                                    background-color:#1e293b;
                                    border:1px solid #334155;
                                    border-radius:12px;
                                    color:#ffffff;
                                    font-size:34px;
                                    font-weight:bold;
                                    letter-spacing:10px;
                                    text-align:center;
                                ">
                                    {mfa_code}
                                </div>
                            </div>

                            <div style="
                                background-color:#1e293b;
                                border-radius:10px;
                                padding:16px;
                                margin:24px 0;
                                color:#cbd5e1;
                                font-size:14px;
                                line-height:1.5;
                            ">
                                ⏱ <strong>
                                    This verification code expires in 10 minutes.
                                </strong>
                            </div>

                            <p style="
                                color:#94a3b8;
                                font-size:14px;
                                line-height:1.6;
                            ">
                                Because you requested a new code,
                                your previous verification code is no longer valid.
                            </p>

                            <p style="
                                color:#94a3b8;
                                font-size:14px;
                                line-height:1.6;
                            ">
                                If you did not attempt to sign in to NexusDesk,
                                you can safely ignore this email.
                            </p>

                            <hr style="
                                border:none;
                                border-top:1px solid #263449;
                                margin:28px 0;
                            ">

                            <p style="
                                color:#94a3b8;
                                font-size:13px;
                                line-height:1.6;
                            ">
                                🔒 <strong>Security reminder:</strong>
                                Never share your verification code with anyone.
                                NexusDesk will never ask you to send your password
                                or verification code by email.
                            </p>

                        </td>
                    </tr>
                </table>

            </td>
        </tr>
    </table>

    </body>
    </html>
    """

    email_sent = send_email(
        "Your New NexusDesk Verification Code",
        user["email"],
        email_body,
        html_body=email_html
    )

    if not email_sent:
        invalidate_mfa_codes(username)

        return render_template(
            "mfa_verify.html",
            error=(
                "Unable to send a new verification code right now. "
                "Please try again later."
            ),
            message="",
            masked_email=masked_email
        ), 503

    log_audit_event(
        username,
        "MFA_CODE_RESENT",
        "user",
        "",
        "User requested a new MFA verification code"
    )

    return render_template(
        "mfa_verify.html",
        error="",
        message="A new verification code has been sent.",
        masked_email=masked_email
    )


@auth_bp.route("/logout")
def logout():
    trusted_username = session.get("mfa_trusted_username")
    trusted_until = session.get("mfa_trusted_until")

    if "username" in session:
        logout_time = datetime.now().strftime("%m/%d/%Y %I:%M %p")

        connection = get_db_connection()
        cursor = connection.cursor()
        placeholder = db_placeholder()

        cursor.execute(f"""
            UPDATE users
            SET last_logout = {placeholder}
            WHERE username = {placeholder}
        """, (
            logout_time,
            session["username"]
        ))

        cursor.execute(f"""
            INSERT INTO login_events (
                username,
                event_type,
                event_time
            )
            VALUES (
                {placeholder},
                {placeholder},
                {placeholder}
            )
        """, (
            session["username"],
            "logout",
            logout_time
        ))

        connection.commit()
        connection.close()

    # Log the user out completely.
    session.clear()

    # Preserve only the temporary MFA trust window.
    if trusted_username and trusted_until:
        try:
            expires_at = datetime.fromisoformat(
                trusted_until
            )

            if datetime.now() < expires_at:
                session.permanent = True

                session["mfa_trusted_username"] = (
                    trusted_username
                )

                session["mfa_trusted_until"] = (
                    trusted_until
                )

        except (TypeError, ValueError):
            pass

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

            display_name = (user["full_name"] or user["username"]).strip()

            email_body = f"""
            Hello {display_name},

            We received a request to reset the password for your NexusDesk account.

            Reset your password using the secure link below:

            {reset_link}

            This link expires in 30 minutes.

            If you did not request a password reset, you can safely ignore this email.
            Your password will remain unchanged.

            Security reminder:
            NexusDesk will never ask you to send your password or verification code by email.

            — NexusDesk
            IT Support & Ticket Management
            """

            email_html = f"""
            <!DOCTYPE html>
            <html>
            <body style="
                margin:0;
                padding:0;
                background-color:#0f172a;
                font-family:Arial, Helvetica, sans-serif;
                color:#e5e7eb;
            ">
                <table width="100%" cellpadding="0" cellspacing="0" style="padding:40px 20px;">
                    <tr>
                        <td align="center">

                            <table width="100%" cellpadding="0" cellspacing="0"
                                style="
                                    max-width:600px;
                                    background-color:#111827;
                                    border:1px solid #263449;
                                    border-radius:16px;
                                    padding:36px;
                                ">

                                <tr>
                                    <td>
                                        <div style="
                                            font-size:24px;
                                            font-weight:bold;
                                            color:#ffffff;
                                            margin-bottom:6px;
                                        ">
                                            🎧 NexusDesk
                                        </div>

                                        <div style="
                                            color:#94a3b8;
                                            font-size:14px;
                                            margin-bottom:32px;
                                        ">
                                            IT Support & Ticket Management
                                        </div>

                                        <h1 style="
                                            color:#ffffff;
                                            font-size:26px;
                                            margin:0 0 16px 0;
                                        ">
                                            Reset Your Password
                                        </h1>

                                        <p style="line-height:1.6;">
                                            Hello <strong>{display_name}</strong>,
                                        </p>

                                        <p style="line-height:1.6; color:#cbd5e1;">
                                            We received a request to reset the password
                                            for your NexusDesk account.
                                        </p>

                                        <p style="line-height:1.6; color:#cbd5e1;">
                                            Click the button below to create a new password.
                                        </p>

                                        <div style="text-align:center; margin:32px 0;">
                                            <a href="{reset_link}"
                                            style="
                                                display:inline-block;
                                                background-color:#3b82f6;
                                                color:#ffffff;
                                                text-decoration:none;
                                                padding:14px 28px;
                                                border-radius:8px;
                                                font-weight:bold;
                                                font-size:15px;
                                            ">
                                                Reset My Password
                                            </a>
                                        </div>

                                        <div style="
                                            background-color:#1e293b;
                                            border-radius:10px;
                                            padding:16px;
                                            margin:24px 0;
                                            color:#cbd5e1;
                                            font-size:14px;
                                            line-height:1.5;
                                        ">
                                            ⏱ <strong>This reset link expires in 30 minutes.</strong>
                                        </div>

                                        <p style="
                                            color:#94a3b8;
                                            font-size:14px;
                                            line-height:1.6;
                                        ">
                                            If you did not request a password reset,
                                            you can safely ignore this email.
                                            Your password will remain unchanged.
                                        </p>

                                        <hr style="
                                            border:none;
                                            border-top:1px solid #263449;
                                            margin:28px 0;
                                        ">

                                        <p style="
                                            color:#94a3b8;
                                            font-size:13px;
                                            line-height:1.6;
                                        ">
                                            🔒 <strong>Security reminder:</strong>
                                            NexusDesk will never ask you to send your
                                            password or verification code by email.
                                        </p>

                                        <p style="
                                            color:#64748b;
                                            font-size:12px;
                                            margin-top:28px;
                                        ">
                                            If the button does not work, copy and paste
                                            this link into your browser:
                                        </p>

                                        <p style="
                                            color:#60a5fa;
                                            font-size:12px;
                                            word-break:break-all;
                                        ">
                                            {reset_link}
                                        </p>

                                    </td>
                                </tr>
                            </table>

                        </td>
                    </tr>
                </table>
            </body>
            </html>
            """

            email_sent = send_email(
                "NexusDesk Password Reset",
                user["email"],
                email_body,
                html_body=email_html
            )

            log_audit_event(
                user["username"],
                "REQUEST_PASSWORD_RESET",
                "user",
                user["id"],
                "Password reset email sent" if email_sent else "Password reset email delivery failed"
            )

        message = True

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

    return redirect("/profile?updated=1")

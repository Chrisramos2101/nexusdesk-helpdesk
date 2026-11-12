import os
from urllib.parse import urlparse

from flask import abort, redirect, request

# ND-RECRUITER-FINAL-POLISH-2026
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
DEMO_DATABASE_NAME = "nexusdesk_recruiter_demo"
DEMO_DATABASE_USER = "recruiter_demo_app"

# Explicit GET-only navigation permitted on the real recruiter site.
# Admin/employee access within these routes still uses existing DB-backed decorators.
DEMO_READ_ENDPOINTS = {
    "recruiter_demo.landing",
    "recruiter_demo.preview",
    "auth.logout",
    "tickets.home",
    "tickets.my_tickets",
    "tickets.ticket_detail",
    "dashboard.dashboard",
    "dashboard.stats",
    "admin.users",
    "admin.system_dashboard",
    "knowledge.knowledge_base",
    "knowledge.knowledge_article",
    "knowledge.contact_it",
    "knowledge.admin_article_feedback",
    "static",
    "health_check",
    "favicon",
}

BLOCKED_DEMO_GET_ENDPOINTS = {
    "auth.mfa_verify", "auth.forgot_password", "auth.reset_password",
    "auth.change_password", "auth.confirm_email_change", "auth.profile",
    "admin.create_user", "tickets.admin_submit_ticket",
    "tickets.download_attachment", "tickets.search_users",
}


def recruiter_mode_enabled():
    return os.getenv("RECRUITER_DEMO_MODE", "false").strip().lower() == "true"


def validate_recruiter_demo_database():
    """Refuse non-demo database names while demo mode is enabled."""
    if not recruiter_mode_enabled():
        return
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url.startswith("postgres://"):
        database_url = "postgresql://" + database_url[len("postgres://"):]
    parsed = urlparse(database_url)
    if parsed.scheme != "postgresql" or parsed.path.lstrip("/") != DEMO_DATABASE_NAME:
        raise RuntimeError("SAFETY STOP: Recruiter demo must use its isolated database.")


def register_recruiter_demo_guard(app):
    validate_recruiter_demo_database()

    # These checks are enforced on the actual application, not isolated toy test apps.
    if recruiter_mode_enabled() and app.config.get("RECRUITER_STRICT_ENDPOINTS", False):
        raw_url = os.getenv("DATABASE_URL", "").strip()
        if raw_url.startswith("postgres://"):
            raw_url = "postgresql://" + raw_url[len("postgres://"):]
        parsed = urlparse(raw_url)
        if parsed.username != DEMO_DATABASE_USER or not parsed.password or not parsed.hostname:
            raise RuntimeError("SAFETY STOP: Recruiter site requires dedicated read-only DB login.")

    @app.before_request
    def protect_recruiter_demo():
        if not recruiter_mode_enabled():
            return None

        # Block password/MFA authentication on the demo website.
        if request.endpoint == "auth.login" and request.method in SAFE_METHODS:
            return redirect("/recruiter-demo/")

        if request.method in SAFE_METHODS:
            if request.endpoint in BLOCKED_DEMO_GET_ENDPOINTS:
                abort(403)
            if app.config.get("RECRUITER_STRICT_ENDPOINTS", False):
                if request.endpoint not in DEMO_READ_ENDPOINTS:
                    abort(404)
            return None

        # CSRFProtect must validate this before it establishes a session.
        if request.method == "POST" and request.endpoint == "recruiter_demo.enter":
            return None

        abort(403)

    @app.after_request
    def mark_demo_response(response):
        if recruiter_mode_enabled():
            response.headers["Cache-Control"] = "no-store, private"
            response.headers["X-Robots-Tag"] = "noindex, nofollow"
            response.headers["X-NexusDesk-Demo"] = "read-only"
        return response

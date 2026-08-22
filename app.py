import os
from datetime import timedelta

from dotenv import load_dotenv

# Environment must be loaded before importing routes/services/database modules.
# Several of those modules read DATABASE_URL at import time.
load_dotenv()

from flask import Flask, request, send_from_directory
from flask_wtf.csrf import CSRFProtect
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

from database.config import DATABASE_URL
from database.schema import init_db
from health import register_health_route
from routes.admin import admin_bp
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.knowledge import knowledge_bp
from routes.tickets import tickets_bp
from services.email_service import mail
from services.monitoring_service import log_system_event
from services.production_config import (
    prepare_runtime_directories,
    validate_production_environment,
)


# Fail fast on invalid production configuration before accepting traffic.
validate_production_environment()
prepare_runtime_directories()

app = Flask(__name__)

# Render and similar platforms terminate HTTPS at a trusted reverse proxy.
# Only enable this when deployment explicitly opts in.
if os.getenv("TRUST_PROXY_HEADERS", "False").lower() == "true":
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=1,
        x_proto=1,
        x_host=1,
        x_port=1,
    )


@app.errorhandler(Exception)
def handle_exception(error):
    if isinstance(error, HTTPException):
        return error

    log_system_event(
        "ERROR",
        str(error)
    )

    raise error


register_health_route(app)


@app.after_request
def apply_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; "
        "img-src 'self' data:; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
    )

    if os.environ.get("FLASK_ENV") == "production" and request.is_secure:
        response.headers.setdefault(
            "Strict-Transport-Security",
            "max-age=31536000; includeSubDomains",
        )

    return response


app.config["TEMPLATES_AUTO_RELOAD"] = os.getenv("FLASK_ENV") != "production"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=60)
app.config["MAIL_SERVER"] = os.getenv("MAIL_SERVER")
app.config["MAIL_PORT"] = int(os.getenv("MAIL_PORT", 587))
app.config["MAIL_USE_TLS"] = os.getenv("MAIL_USE_TLS", "True") == "True"
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.getenv("MAIL_DEFAULT_SENDER")
app.config["UPLOAD_FOLDER"] = os.getenv("UPLOAD_FOLDER", "uploads")
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_UPLOAD_MB", 10)) * 1024 * 1024

mail.init_app(app)

if os.environ.get("FLASK_ENV") == "production":
    app.config["SESSION_COOKIE_SECURE"] = True
else:
    app.config["SESSION_COOKIE_SECURE"] = False

app.secret_key = os.environ.get("SECRET_KEY")

if not app.secret_key:
    raise RuntimeError(
        "SECRET_KEY environment variable is required."
    )

csrf = CSRFProtect(app)
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(knowledge_bp)
app.register_blueprint(tickets_bp)
app.register_blueprint(dashboard_bp)


@app.context_processor
def inject_csrf_token():
    from flask_wtf.csrf import generate_csrf
    return dict(csrf_token=generate_csrf)


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, "static"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon"
    )


# For direct/local SQLite development, run the idempotent schema initializer on
# every startup. This upgrades older helpdesk.db files without deleting data.
if not DATABASE_URL.startswith("postgresql://"):
    with app.app_context():
        init_db()


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "False").lower() == "true")

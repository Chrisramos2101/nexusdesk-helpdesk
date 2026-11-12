
from flask import (
    Blueprint,
    abort,
    redirect,
    render_template,
    request,
    session,
)

from services.recruiter_demo_guard import recruiter_mode_enabled
from services.user_service import get_user_by_username


recruiter_demo_bp = Blueprint(
    "recruiter_demo",
    __name__,
    url_prefix="/recruiter-demo",
)


DEMO_ACCOUNTS = {
    "admin": ("Demo_Admin", "admin"),
    "employee": ("Demo_Employee", "employee"),
}


@recruiter_demo_bp.route("/", methods=["GET"])
def landing():
    if not recruiter_mode_enabled():
        abort(404)

    return render_template("recruiter_demo.html")


@recruiter_demo_bp.route("/enter", methods=["POST"])
def enter():
    if not recruiter_mode_enabled():
        abort(404)

    selected_role = request.form.get("role", "").strip()

    if selected_role not in DEMO_ACCOUNTS:
        abort(400)

    username, expected_role = DEMO_ACCOUNTS[selected_role]

    # Verify the account exists in the isolated database.
    user = get_user_by_username(username)

    if not user:
        abort(503)

    if user["role"] != expected_role:
        abort(503)

    # Clear any previous authentication state.
    session.clear()
    session.permanent = True

    session["username"] = user["username"]
    session["role"] = user["role"]
    session["recruiter_demo"] = True

    if expected_role == "admin":
        return redirect("/dashboard")

    return redirect("/")

# ND-RECRUITER-FINAL-POLISH-2026
# Read-only UI previews never call the production write endpoints.
@recruiter_demo_bp.route("/preview/<feature>", methods=["GET"])
def preview(feature):
    if not recruiter_mode_enabled():
        abort(404)
    username = session.get("username")
    role = session.get("role")
    if not session.get("recruiter_demo"):
        abort(403)
    if (role, username) not in {("admin", "Demo_Admin"), ("employee", "Demo_Employee")}:
        abort(403)
    features = {
        "create-user": ("admin", "Create User", "Administrator account setup"),
        "submit-support-request": ("admin", "Submit Support Request", "Administrator support request"),
        "edit-ticket": ("admin", "Update Ticket", "Ticket lifecycle and technician assignment"),
        "profile": ("both", "My Profile", "Fictional profile details"),
        "change-password": ("employee", "Change Password", "Account security workflow"),
    }
    if feature not in features:
        abort(404)
    allowed_role, title, subtitle = features[feature]
    if allowed_role not in ("both", role):
        abort(403)
    return render_template(
        "recruiter_feature_preview.html",
        feature=feature,
        title=title,
        subtitle=subtitle,
        role=role,
        demo_name="Demo Administrator" if role == "admin" else "Demo Employee",
        demo_department="IT" if role == "admin" else "Operations",
        demo_email="demo-admin@example.com" if role == "admin" else "demo-employee@example.com",
    )

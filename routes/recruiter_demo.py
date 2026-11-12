
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

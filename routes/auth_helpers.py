
from functools import wraps

from flask import redirect, session

from services.user_service import get_user_by_username


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):

        username = session.get("username")

        if not username:
            return redirect("/login")

        # Verify that the authenticated account
        # still exists in the database.
        user = get_user_by_username(username)

        if not user:
            session.clear()
            return redirect("/login")

        # Keep the session role synchronized with
        # the authoritative database record.
        session["role"] = user["role"]

        return view(*args, **kwargs)

    return wrapped_view


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):

        username = session.get("username")

        if not username:
            return redirect("/login")

        # Never trust the session role alone.
        user = get_user_by_username(username)

        if not user:
            session.clear()
            return redirect("/login")

        current_role = user["role"]
        session["role"] = current_role

        if current_role != "admin":
            return redirect("/")

        return view(*args, **kwargs)

    return wrapped_view

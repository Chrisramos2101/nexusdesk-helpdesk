
from functools import wraps

from flask import redirect, session

from services.user_service import get_user_by_username


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "username" not in session:
            return redirect("/login")

        return view(*args, **kwargs)

    return wrapped_view


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):

        username = session.get("username")

        if not username:
            return redirect("/login")

        # Always check the current database role.
        # Do not trust a potentially outdated session role.
        user = get_user_by_username(username)

        if not user:
            session.clear()
            return redirect("/login")

        current_role = user["role"]

        # Synchronize the session with the database.
        session["role"] = current_role

        if current_role != "admin":
            return redirect("/")

        return view(*args, **kwargs)

    return wrapped_view

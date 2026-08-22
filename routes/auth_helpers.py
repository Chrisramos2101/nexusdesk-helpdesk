from functools import wraps
from flask import redirect, session


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
        if "username" not in session:
            return redirect("/login")

        if session.get("role") != "admin":
            return redirect("/")

        return view(*args, **kwargs)

    return wrapped_view
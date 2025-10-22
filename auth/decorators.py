# auth/decorators.py
"""
Decorators to protect Dash page layouts and callbacks.

- require_login_view: for page layouts (returns dcc.Location redirect if not authenticated).
- require_role: to restrict page layouts to a specific role.
"""
from dotenv import load_dotenv
load_dotenv() 
import functools
from flask_login import current_user
from dash import dcc, html

def require_login_view(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            # return a client-side redirect to /login (works inside Dash page layout)
            return dcc.Location(href="/login", id="redirect-auth")
        return func(*args, **kwargs)
    return wrapper

def require_role(role_name):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return dcc.Location(href="/login", id="redirect-auth")
            user_role = getattr(current_user, "user_model", None) and current_user.user_model.role
            if user_role and user_role.name == role_name:
                return func(*args, **kwargs)
            # unauthorized: simple message (you can change to a nicer UI)
            return html.Div("Access denied: insufficient permissions", style={"color": "red", "padding": "8px"})
        return wrapper
    return decorator

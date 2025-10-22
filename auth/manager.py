# auth/manager.py
from functools import wraps
from flask import redirect, request, current_app
from flask_login import LoginManager, UserMixin, current_user
from auth.models import get_user_by_id
import os

login_manager = LoginManager()
login_manager.login_view = "/login"  # optional

class AuthUser(UserMixin):
    def __init__(self, user_model):
        self._user = user_model

    def get_id(self):
        return str(self._user.id)

    @property
    def username(self):
        return self._user.username

    @property
    def role(self):
        return self._user.role.name if self._user and self._user.role else None

    @property
    def is_active(self):
        return bool(self._user.is_active)

@login_manager.user_loader
def _load_user(user_id):
    try:
        u = get_user_by_id(int(user_id))
    except Exception:
        return None
    if not u:
        return None
    return AuthUser(u)

def init_auth(flask_app, secret_key: str | None = None, *, cookie_secure: bool = False, cookie_httponly: bool = True, cookie_samesite: str = "Lax"):
    """
    Initialize LoginManager on the Flask app and register before_request guard.

    Args:
        flask_app: Flask app instance (e.g. app.server from Dash).
        secret_key: optional secret key to set on flask_app if not already set.
        cookie_secure: set SESSION_COOKIE_SECURE (set True in production+HTTPS).
        cookie_httponly: set SESSION_COOKIE_HTTPONLY.
        cookie_samesite: 'Lax' or 'Strict' or 'None'.
    """
    # set secret key if provided and not already present
    if secret_key:
        if not getattr(flask_app, "secret_key", None):
            flask_app.secret_key = secret_key
    # fallback to env SECRET_KEY if still missing
    if not getattr(flask_app, "secret_key", None):
        env_key = os.environ.get("SECRET_KEY")
        if env_key:
            flask_app.secret_key = env_key

    # configure session cookie options
    flask_app.config.setdefault("SESSION_COOKIE_SECURE", cookie_secure)
    flask_app.config.setdefault("SESSION_COOKIE_HTTPONLY", cookie_httponly)
    flask_app.config.setdefault("SESSION_COOKIE_SAMESITE", cookie_samesite)

    # init login manager
    login_manager.init_app(flask_app)

    # whitelist path prefixes that don't require auth (dash assets, login routes, api, static)
    WHITELIST = (
        "/login",
        "/auth",
        "/assets",
        "/_dash",
        "/_dash-layout",
        "/_dash-dependencies",
        "/_dash-update-component",
        "/_dash-component-suites",
        "/favicon.ico",
        "/static",
        "/api",
    )

    @flask_app.before_request
    def _require_login_for_pages():
        path = request.path
        # allow whitelisted prefixes
        for p in WHITELIST:
            if path.startswith(p):
                return None
        # if not authenticated, redirect to /login
        if not current_user.is_authenticated:
            return redirect("/login")
        return None

def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect("/login")
        if getattr(current_user, "role", None) != "admin":
            return redirect("/")  # or abort(403)
        return func(*args, **kwargs)
    return wrapper

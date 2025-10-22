# auth/__init__.py
# package marker + top-level exports

from .manager import init_auth, login_manager, AuthUser
from .models import init_db, SessionLocal, User, Role

__all__ = ["init_auth", "login_manager", "AuthUser", "init_db", "SessionLocal", "User", "Role"]

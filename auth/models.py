# auth/models.py
"""
Auth models + DB helpers (SQLAlchemy).

Usage:
- Set env var AUTH_DATABASE_URL to something like:
    mysql+pymysql://user:pass@127.0.0.1:3306/dbname?charset=utf8mb4
  If not set, fallback ke sqlite:///./auth_users.db (dev).
- Call init_db() once (or use Alembic migrations in production).
- Use get_db_session() as a context manager to get a session.
"""
from __future__ import annotations
from dotenv import load_dotenv
load_dotenv() 


import os
import datetime
from contextlib import contextmanager
from typing import Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    create_engine,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session
from werkzeug.security import generate_password_hash, check_password_hash

# ---------------------------------------------------------------------------
# Configuration: change via environment variable
# ---------------------------------------------------------------------------
DATABASE_URL = os.environ.get("AUTH_DATABASE_URL", "sqlite:///./auth_users.db")
# Example MySQL URL:
# mysql+pymysql://username:password@127.0.0.1:3306/prob_forecast_auth?charset=utf8mb4

# ---------------------------------------------------------------------------
# SQLAlchemy setup
# ---------------------------------------------------------------------------
Base = declarative_base()

# engine options
_engine_kwargs = {
    "echo": False,
    # keep-alive for pool to avoid "MySQL server has gone away"
    "pool_pre_ping": True,
}

if DATABASE_URL.startswith("sqlite"):
    # sqlite needs check_same_thread for single-process dev
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        **{k: v for k, v in _engine_kwargs.items() if k != "pool_pre_ping"},
    )
else:
    # MySQL / Postgres / others
    engine = create_engine(DATABASE_URL, **_engine_kwargs)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine,expire_on_commit=False)

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)  # e.g. 'admin' / 'user'
    description = Column(String(255), nullable=True)

    def __repr__(self):
        return f"<Role id={self.id} name={self.name}>"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("username", name="uq_users_username"),)

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String(300), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    telegram_id = Column(String(32), nullable=True)  

    role = relationship("Role", lazy="joined")

    def set_password(self, plain: str) -> None:
        """
        Hash and set password. Uses Werkzeug's generate_password_hash (PBKDF2 by default).
        """
        self.password_hash = generate_password_hash(plain)

    def check_password(self, plain: str) -> bool:
        """
        Verify password against stored hash.
        """
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, plain)

    def __repr__(self):
        return f"<User id={self.id} username={self.username} active={self.is_active} role={self.role.name if self.role else None}>"

# ---------------------------------------------------------------------------
# DB utilities
# ---------------------------------------------------------------------------
def init_db() -> None:
    """
    Create DB schema (development convenience). For production prefer Alembic migrations.
    """
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db_session() -> Session:
    """
    Context manager to yield a SQLAlchemy session and ensure close/rollback on error.
    Usage:
        with get_db_session() as db:
            # use db (Session)
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

# ---------------------------------------------------------------------------
# Convenience helpers for common auth tasks
# ---------------------------------------------------------------------------
def create_role(name: str, description: Optional[str] = None) -> Role:
    """
    Create role if not exists and return it.
    """
    with get_db_session() as db:
        role = db.query(Role).filter(Role.name == name).first()
        if role:
            return role
        role = Role(name=name, description=description)
        db.add(role)
        db.flush()  # ensure id populated
        return role


def get_role_by_name(name: str) -> Optional[Role]:
    with get_db_session() as db:
        return db.query(Role).filter(Role.name == name).first()


def create_user(username: str, password: str, role_name: Optional[str] = None, is_active: bool = True , telegram_id: Optional[str] = None) -> User:
    """
    Create a new user (raises on duplicate username).
    """
    with get_db_session() as db:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            raise ValueError("username already exists")
        role = None
        if role_name:
            role = db.query(Role).filter(Role.name == role_name).first()
            if not role:
                # auto-create role if missing
                role = Role(name=role_name)
                db.add(role)
                db.flush()
        user = User(username=username, role=role, is_active=is_active, telegram_id=telegram_id)
        user.set_password(password)
        db.add(user)
        db.flush()
        return user


def get_user_by_username(username: str) -> Optional[User]:
    with get_db_session() as db:
        return db.query(User).filter(User.username == username).first()


def get_user_by_id(user_id: int) -> Optional[User]:
    with get_db_session() as db:
        return db.query(User).filter(User.id == int(user_id)).first()


def disable_user(username: str) -> bool:
    with get_db_session() as db:
        u = db.query(User).filter(User.username == username).first()
        if not u:
            return False
        u.is_active = False
        db.add(u)
        return True


def enable_user(username: str) -> bool:
    with get_db_session() as db:
        u = db.query(User).filter(User.username == username).first()
        if not u:
            return False
        u.is_active = True
        db.add(u)
        return True

# Tambahkan di auth/models.py (di bagian Helpers)
def list_users():
    with get_db_session() as db:
        lst = db.query(User).all()
        out = []
        for u in lst:
            out.append({
                "id": u.id,
                "username": u.username,
                "is_active": bool(u.is_active),
                "role": u.role.name if u.role else None,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "telegram_id": u.telegram_id,
            })
        return out

def disable_user_by_id(user_id: int) -> bool:
    with get_db_session() as db:
        u = db.query(User).filter(User.id == int(user_id)).first()
        if not u:
            return False
        u.is_active = False
        db.add(u)
        return True

def enable_user_by_id(user_id: int) -> bool:
    with get_db_session() as db:
        u = db.query(User).filter(User.id == int(user_id)).first()
        if not u:
            return False
        u.is_active = True
        db.add(u)
        return True



# ---------------------------------------------------------------------------
# Convenience function: ensure default roles present (call at init time)
# ---------------------------------------------------------------------------
def ensure_default_roles(names=("admin", "user")):
    with get_db_session() as db:
        for n in names:
            if not db.query(Role).filter(Role.name == n).first():
                db.add(Role(name=n, description=f"default role {n}"))


def update_user_by_id(user_id: int, username: str = None, password: str = None, role_name: str = None, is_active: bool = None,telegram_id: str = None):
    """Update user fields."""
    with get_db_session() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")

        if username and username != user.username:
            existing = db.query(User).filter(User.username == username).first()
            if existing:
                raise ValueError("Username already exists")
            user.username = username

        if password:
            user.set_password(password)

        if role_name:
            role = db.query(Role).filter(Role.name == role_name).first()
            if not role:
                role = Role(name=role_name)
                db.add(role)
                db.flush()
            user.role = role

        if telegram_id is not None:
            user.telegram_id = telegram_id

        if is_active is not None:
            user.is_active = bool(is_active)

        db.add(user)
        db.flush()
        return user


def delete_user_by_id(user_id: int) -> bool:
    """Delete a user permanently."""
    with get_db_session() as db:
        u = db.query(User).filter(User.id == user_id).first()
        if not u:
            return False
        db.delete(u)
        db.flush()
        return True

# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------
__all__ = [
    "Base",
    "engine",
    "SessionLocal",
    "init_db",
    "get_db_session",
    "Role",
    "User",
    "create_role",
    "get_role_by_name",
    "create_user",
    "get_user_by_username",
    "get_user_by_id",
    "disable_user",
    "enable_user",
    "ensure_default_roles",
    "update_user_by_id",
    "delete_user_by_id",


]

# auth/routes.py
from flask import Blueprint, request, jsonify, redirect
from flask_login import login_user, logout_user, login_required, current_user
from auth.manager import AuthUser, admin_required
from auth.models import get_user_by_username, create_user, list_users, enable_user, disable_user, create_role, ensure_default_roles

bp = Blueprint("auth", __name__, url_prefix="/auth")

@bp.route("/login", methods=["POST"])
def api_login():
    j = request.get_json(silent=True) or {}
    username = j.get("username") or request.form.get("username")
    password = j.get("password") or request.form.get("password")
    if not username or not password:
        return jsonify({"success": False, "error": "username/password required"}), 400

    user = get_user_by_username(username)
    if not user or not user.check_password(password) or not user.is_active:
        return jsonify({"success": False, "error": "invalid credentials"}), 401

    login_user(AuthUser(user), remember=False)
    return jsonify({"success": True, "username": user.username, "role": user.role.name if user.role else None})

@bp.route("/logout", methods=["GET", "POST"])
@login_required
def api_logout():
    logout_user()
    return jsonify({"success": True})

# Admin endpoints
@bp.route("/users", methods=["GET"])
@login_required
def api_list_users():
    # only admin can list users
    if getattr(current_user, "role", None) != "admin":
        return jsonify({"error": "forbidden"}), 403
    data = list_users()
    return jsonify({"users": data})

@bp.route("/users", methods=["POST"])
@login_required
def api_create_user():
    if getattr(current_user, "role", None) != "admin":
        return jsonify({"error": "forbidden"}), 403
    j = request.get_json()
    username = j.get("username")
    password = j.get("password")
    role = j.get("role", "user")
    if not username or not password:
        return jsonify({"error": "username and password required"}), 400
    # ensure role exists
    create_role(role, f"role {role}")
    try:
        u = create_user(username, password, role_name=role, is_active=True)
        return jsonify({"success": True, "user": {"id": u.id, "username": u.username, "role": u.role.name}}), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@bp.route("/users/<int:user_id>/disable", methods=["POST"])
@login_required
def api_disable_user(user_id):
    if getattr(current_user, "role", None) != "admin":
        return jsonify({"error": "forbidden"}), 403
    ok = disable_user_by_id(user_id) if "disable_user_by_id" in globals() else None
    # fallback to disable_user(username) if you don't have disable by id
    if ok is None:
        return jsonify({"error": "server missing helper"}), 500
    return jsonify({"success": ok})

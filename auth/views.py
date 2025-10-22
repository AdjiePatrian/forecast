# auth/views.py
"""
Flask Blueprint that exposes /login and /logout.
- POST /login accepts JSON {"username":..., "password":...} or form fields.
- GET /login returns a simple HTML form (useful for troubleshooting).
- No /register endpoint here (admin-only user creation).
"""
from dotenv import load_dotenv
load_dotenv() 
from flask import Blueprint, request, jsonify, render_template_string, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from .manager import AuthUser
from .models import SessionLocal, User

auth_bp = Blueprint("auth", __name__)

_SIMPLE_LOGIN_FORM = """
<!doctype html>
<title>Login</title>
<h3>Login</h3>
<form method="post">
  <label>Username</label><br/>
  <input name="username" /><br/>
  <label>Password</label><br/>
  <input name="password" type="password" /><br/>
  <input type="submit" value="Login" />
</form>
"""

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template_string(_SIMPLE_LOGIN_FORM)

    data = request.get_json() if request.is_json else request.form
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"success": False, "error": "username & password required"}), 400

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if user and user.check_password(password):
            if not user.is_active:
                return jsonify({"success": False, "error": "user disabled"}), 403
            login_user(AuthUser(user))
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "invalid credentials"}), 401
    finally:
        db.close()

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    # when called from browser redirect to home or login
    return redirect(url_for("auth.login"))

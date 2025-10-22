# check_users.py
from dotenv import load_dotenv
load_dotenv()

from auth.models import get_user_by_username
import os

u = get_user_by_username(os.getenv("ADMIN_USER", "admin"))
if u:
    print("Found user:", u.username, "id=", u.id, "role=", u.role.name if u.role else None, "active=", u.is_active)
else:
    print("Admin user not found. Coba jalankan create_admin.py lagi.")

import os, getpass
from auth.models import init_db, ensure_default_roles, get_user_by_username, create_user, create_role

def main():
    # 1) pastikan tabel dibuat
    print("Inisialisasi DB (create tables jika belum ada)...")
    init_db()
    print("init_db() selesai. memastikan role default ada...")
    ensure_default_roles(("admin", "user"))

    # 2) ambil kredensial dari env atau prompt
    admin_user = os.environ.get("ADMIN_USER") or input("Username admin (default 'admin'): ").strip() or "admin"
    admin_pass = os.environ.get("ADMIN_PASS")
    if not admin_pass:
        admin_pass = getpass.getpass("Password admin: ").strip()
        if not admin_pass:
            print("Password kosong, batal.")
            return

    # 3) cek apakah user sudah ada
    existing = get_user_by_username(admin_user)
    if existing:
        print(f"User '{admin_user}' sudah ada (id={existing.id}). Tidak membuat ulang.")
        return

    # 4) buat role 'admin' jika belum ada dan buat user
    create_role("admin", "Administrator aplikasi")  # safe-create
    u = create_user(admin_user, admin_pass, role_name="admin", is_active=True)
    print("Admin berhasil dibuat:", u.username, "id=", u.id)

if __name__ == "__main__":
    main()
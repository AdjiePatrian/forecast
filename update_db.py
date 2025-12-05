# update_db_schema.py
from auth.models import init_db

if __name__ == "__main__":
    print("🔄 Memeriksa dan membuat tabel yang belum ada...")
    init_db()
    print("✅ Struktur database sudah diperbarui (tabel baru ditambahkan jika perlu).")

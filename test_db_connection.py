# test_db_connection.py (debug versi lengkap)
from dotenv import load_dotenv, find_dotenv
import os
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text

print("CWD:", os.getcwd())

# cari .env otomatis
found = find_dotenv(usecwd=True)
print("find_dotenv ->", repr(found))
if found:
    print("Loading .env from:", found)
    load_dotenv(found)
else:
    print("No .env found by find_dotenv(usecwd=True). Trying load_dotenv() default.")
    load_dotenv()   # fallback

# show files in cwd (small listing)
print("\nFiles in cwd (first 200 chars of names):")
for fn in os.listdir("."):
    print(" -", fn)

# print relevant env vars (mask password)
def mask(s):
    if not s:
        return None
    if "@" in s and "://" in s:
        # try not to print full password in URL
        try:
            proto, rest = s.split("://", 1)
            creds, host = rest.split("@", 1)
            user, pwd = creds.split(":", 1) if ":" in creds else (creds, "")
            return f"{proto}://{user}:***@{host}"
        except Exception:
            return s[:40] + "..."
    return (s[:10] + "...") if len(s) > 13 else s

print("\nENV VARS (masked):")
print(" AUTH_DATABASE_URL =", mask(os.environ.get("AUTH_DATABASE_URL")))
print(" DB_USER =", os.environ.get("DB_USER"))
print(" DB_PASS =", None if not os.environ.get("DB_PASS") else "<hidden>")
print(" DB_HOST =", os.environ.get("DB_HOST"))
print(" DB_PORT =", os.environ.get("DB_PORT"))
print(" DB_NAME =", os.environ.get("DB_NAME"))

# build URL from components if needed
DATABASE_URL = os.environ.get("AUTH_DATABASE_URL")
if not DATABASE_URL:
    user = os.environ.get("DB_USER", "prob_user")
    pwd = os.environ.get("DB_PASS", "")
    host = os.environ.get("DB_HOST", "127.0.0.1")
    port = os.environ.get("DB_PORT", "3306")
    name = os.environ.get("DB_NAME", "prob_forecast_auth")
    pwd_enc = quote_plus(pwd)
    DATABASE_URL = f"mysql+pymysql://{user}:{pwd_enc}@{host}:{port}/{name}?charset=utf8mb4"
    print("\nBuilt DATABASE_URL from components (masked):", mask(DATABASE_URL))
else:
    print("\nUsing AUTH_DATABASE_URL from env (masked):", mask(DATABASE_URL))

# quick DB test (only if URL present)
try:
    e = create_engine(DATABASE_URL)
    with e.connect() as conn:
        r = conn.execute(text("SELECT 1"))
        print("DB test returned:", r.fetchone())
except Exception as err:
    print("DB connection ERROR:", type(err).__name__, err)

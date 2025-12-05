# telegram_bot.py
import os
import requests
from auth.models import list_users

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"


def _send_message(chat_id: str, text: str) -> bool:
    """Internal helper: kirim pesan ke chat_id tertentu."""
    if not BOT_TOKEN:
        print("[Telegram] ❌ Bot token not found.")
        return False

    try:
        resp = requests.post(
            TELEGRAM_API_URL,
            data={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML"
            },
            timeout=5
        )
        if resp.status_code != 200:
            print("[Telegram] Error response:", resp.text)
        return resp.ok
    except Exception as e:
        print("[Telegram] Error:", e)
        return False


def send_telegram_message(chat_id: str, text: str) -> bool:
    """
    Backward compatible: kirim pesan langsung ke chat_id tertentu.
    """
    return _send_message(chat_id, text)


def send_telegram_message_to_all(text: str) -> dict:
    """
    Kirim pesan ke semua user aktif yang memiliki telegram_id.
    Args:
        text (str): pesan yang akan dikirim.
    Returns:
        dict: hasil per user, {username: True/False}
    """
    if not BOT_TOKEN:
        print("[Telegram] ❌ BOT_TOKEN tidak ditemukan di environment variable.")
        return {}

    users = list_users()
    results = {}

    print(f"[Telegram] 📢 Mengirim pesan ke semua user dengan telegram_id ...")

    for user in users:
        if not user.get("is_active"):
            continue
        telegram_id = user.get("telegram_id")
        if not telegram_id:
            continue

        ok = _send_message(telegram_id, text)
        results[user["username"]] = ok
        status = "✅" if ok else "❌"
        print(f"[Telegram] {status} @{user['username']} ({telegram_id})")

    print(f"[Telegram] Broadcast selesai. {sum(results.values())}/{len(results)} berhasil.")
    return results

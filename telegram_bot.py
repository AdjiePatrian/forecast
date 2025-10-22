import os
import requests

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def send_telegram_message(chat_id: str, text: str) -> bool:
    """Kirim pesan Telegram ke chat_id tertentu."""
    if not BOT_TOKEN:
        print("Telegram Bot token not found.")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }

    try:
        resp = requests.post(url, data=data, timeout=5)
        if resp.status_code != 200:
            print("Telegram Error:", resp.text)
        return resp.ok
    except Exception as e:
        print("Telegram Error:", e)
        return False

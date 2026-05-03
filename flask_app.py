import os
import logging
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
DIFU_API_KEY   = os.environ.get("DIFU_API_KEY", "")
DIFU_API_URL = "https://api.dify.ai/v1/chat-messages"
TELEGRAM_BASE  = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

conversations = {}

def send_message(chat_id, text):
    try:
        requests.post(f"{TELEGRAM_BASE}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}, timeout=15)
    except Exception as e:
        log.error(f"error: {e}")

def ask_difu(user_message, conversation_id=None):
    headers = {"Authorization": f"Bearer {DIFU_API_KEY}", "Content-Type": "application/json"}
    body = {"inputs": {}, "query": user_message, "response_mode": "blocking", "user": "telegram-bot"}
    if conversation_id:
        body["conversation_id"] = conversation_id
    try:
        r = requests.post(DIFU_API_URL, headers=headers, json=body, timeout=30)
        r.raise_for_status()
        data = r.json()
        return data.get("answer", "لم أتمكن من الحصول على رد."), data.get("conversation_id", conversation_id or "")
    except Exception as e:
        log.error(f"difu error: {e}")
        return "حدث خطأ في الاتصال بالذكاء الاصطناعي.", conversation_id or ""

@app.route(f"/webhook/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    try:
        update = request.get_json(force=True)
        if not update:
            return jsonify({"ok": True})
        message = update.get("message") or update.get("edited_message")
        if not message:
            return jsonify({"ok": True})
        chat_id = message["chat"]["id"]
        text = message.get("text", "").strip()
        if not text:
            return jsonify({"ok": True})
        if text == "/start":
            conversations.pop(chat_id, None)
            send_message(chat_id, "مرحباً! 👋\nأنا بوت مدعوم بـ difu.ai\nأرسل أي سؤال وسأجيبك.")
            return jsonify({"ok": True})
        if text == "/reset":
            conversations.pop(chat_id, None)
            send_message(chat_id, "✅ تمت إعادة تعيين المحادثة.")
            return jsonify({"ok": True})
        conv_id = conversations.get(chat_id)
        answer, new_conv_id = ask_difu(text, conv_id)
        if new_conv_id:
            conversations[chat_id] = new_conv_id
        send_message(chat_id, answer)
    except Exception as e:
        log.error(f"webhook error: {e}")
    return jsonify({"ok": True})

@app.route("/")
def index():
    return "Bot is running!"

if __name__ == "__main__":
    app.run(debug=False)

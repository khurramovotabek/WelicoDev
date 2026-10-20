"""Django (sinxron) kodidan Telegram Bot API'ga xabar yuborish uchun kichik klient.

Bot o'zi aiogram bilan ishlaydi; bu modul faqat saytdan bildirishnoma va ommaviy xabar yuborish uchun.
"""

import json
import logging
import urllib.error
import urllib.request

from django.conf import settings

log = logging.getLogger(__name__)


class TelegramError(Exception):
    def __init__(self, description, code=None, retry_after=None):
        super().__init__(description)
        self.code = code
        self.retry_after = retry_after


def call(method, payload=None, files=None, timeout=15):
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        raise TelegramError("TELEGRAM_BOT_TOKEN is not configured")
    url = f"https://api.telegram.org/bot{token}/{method}"
    if files:
        body, content_type = _multipart(payload or {}, files)
    else:
        # Telegram null qiymatli maydonlarni rad etadi ("object expected as reply markup")
        clean = {k: v for k, v in (payload or {}).items() if v is not None}
        body, content_type = json.dumps(clean).encode(), "application/json"
    req = urllib.request.Request(url, data=body, headers={"Content-Type": content_type})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        data = json.loads(e.read() or b"{}")
    if not data.get("ok"):
        params = data.get("parameters") or {}
        raise TelegramError(data.get("description", "unknown error"), data.get("error_code"), params.get("retry_after"))
    return data["result"]


def _multipart(fields, files):
    import uuid

    boundary = uuid.uuid4().hex
    parts = []
    for k, v in fields.items():
        if v is None:
            continue
        if not isinstance(v, str):
            v = json.dumps(v)
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    for k, (filename, content) in files.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"; filename="{filename}"\r\n'
            f"Content-Type: application/octet-stream\r\n\r\n".encode() + content + b"\r\n"
        )
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def send_message(chat_id, text, reply_markup=None, disable_preview=True):
    return call("sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "link_preview_options": {"is_disabled": disable_preview},
        "reply_markup": reply_markup,
    })


def send_photo(chat_id, photo_bytes, filename, caption, reply_markup=None):
    return call(
        "sendPhoto",
        {"chat_id": str(chat_id), "caption": caption, "parse_mode": "HTML", "reply_markup": reply_markup},
        files={"photo": (filename, photo_bytes)},
    )


def url_button(text, url):
    # Telegram faqat ochiq https/http havolalarni qabul qiladi (localhost tugmalari xato beradi)
    if not url or "://localhost" in url or "://127.0.0.1" in url:
        return None
    return {"inline_keyboard": [[{"text": text, "url": url}]]}

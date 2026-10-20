"""Telegram Mini App autentifikatsiyasi: initData imzosini tekshirish.

https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
Mini App Telegram Web'da iframe ichida ochiladi va u yerda cookie ishonchsiz, shuning uchun har bir
so'rov `X-Telegram-Init-Data` sarlavhasi bilan keladi va server uni har safar tekshiradi.
"""

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from django.conf import settings
from django.core import signing

from apps.accounts.models import User

MAX_AGE = 60 * 60 * 24  # initData 24 soatdan eski bo'lmasin
HEADER = "HTTP_X_TELEGRAM_INIT_DATA"


def validate_init_data(init_data, bot_token=None, max_age=MAX_AGE):
    """To'g'ri bo'lsa Telegram foydalanuvchi ma'lumotini (dict) qaytaradi, aks holda None."""
    bot_token = bot_token or settings.TELEGRAM_BOT_TOKEN
    if not init_data or not bot_token:
        return None
    try:
        pairs = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=True))
    except ValueError:
        return None
    received = pairs.pop("hash", "")
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received):
        return None
    try:
        if time.time() - int(pairs.get("auth_date", 0)) > max_age:
            return None
        return json.loads(pairs.get("user", "{}")) or None
    except (ValueError, TypeError):
        return None


def user_from_tg(tg):
    """Telegram foydalanuvchisini topadi yoki (ro'yxatdan o'tmagan holda) yaratadi."""
    user = User.objects.filter(telegram_id=tg["id"]).first()
    if user is None:
        user = User(
            username=f"tg_{tg['id']}", telegram_id=tg["id"],
            first_name=(tg.get("first_name") or "")[:150], last_name=(tg.get("last_name") or "")[:150],
            telegram_username=tg.get("username") or "",
            language=tg.get("language_code", "uz")[:2] if tg.get("language_code", "")[:2] in ("uz", "ru", "en") else "uz",
        )
        user.set_unusable_password()
        user.save()
    elif tg.get("username") and tg["username"] != user.telegram_username:
        User.objects.filter(pk=user.pk).update(telegram_username=tg["username"])
    return user


class TelegramWebAppMiddleware:
    """`/app/` so'rovlarida initData sarlavhasi bo'lsa, request.user shu Telegram foydalanuvchisi bo'ladi."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.tma = False
        if "/app/" in request.path:
            tg = validate_init_data(request.META.get(HEADER, ""))
            if tg is None and settings.DEBUG and request.META.get("HTTP_X_TMA_DEBUG_USER"):
                # Faqat lokal muhitda: Chrome'da Telegram'siz ko'rish uchun
                tg = {"id": int(request.META["HTTP_X_TMA_DEBUG_USER"]), "first_name": "Debug"}
            if tg:
                user = user_from_tg(tg)
                if user.is_active and not user.is_blocked:
                    request.user = user
                    request.tma = True
                    request._dont_enforce_csrf_checks = True  # autentifikatsiya cookie emas, imzolangan sarlavha orqali
        return self.get_response(request)


# ------------------------------------------------------------------ himoyalangan video uchun imzolangan havola

VIDEO_SALT = "wcd.lesson-video"


def sign_video(user_id, lesson_id):
    return signing.TimestampSigner(salt=VIDEO_SALT).sign(f"{user_id}:{lesson_id}")


def unsign_video(token, max_age=60 * 60 * 2):
    try:
        user_id, lesson_id = signing.TimestampSigner(salt=VIDEO_SALT).unsign(token, max_age=max_age).split(":")
        return int(user_id), int(lesson_id)
    except (signing.BadSignature, ValueError):
        return None

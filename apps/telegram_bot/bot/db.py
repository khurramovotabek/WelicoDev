"""Bot handlerlari uchun ORM amallari (sinxron kod async muhitda sync_to_async orqali chaqiriladi)."""

import uuid

from asgiref.sync import sync_to_async
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import LoginCode, LoginRequest, User
from apps.telegram_bot.models import BotEvent, BotMessage, BotSettings


@sync_to_async
def get_settings():
    return BotSettings.load()


@sync_to_async
def touch_user(tg_user):
    """Telegram foydalanuvchisini topadi yoki yaratadi va faollik vaqtini yangilaydi."""
    user = User.objects.filter(telegram_id=tg_user.id).first()
    created = False
    if user is None:
        user = User(
            username=f"tg_{tg_user.id}",
            telegram_id=tg_user.id,
            first_name=(tg_user.first_name or "")[:150],
            last_name=(tg_user.last_name or "")[:150],
            language=(tg_user.language_code or "uz")[:2] if (tg_user.language_code or "")[:2] in ("uz", "ru", "en") else "uz",
        )
        user.set_unusable_password()
        user.save()
        created = True
        BotEvent.objects.create(user=user, kind=BotEvent.Kind.START)
    updates = {"last_bot_activity": timezone.now(), "bot_blocked": False}
    if tg_user.username != user.telegram_username:
        updates["telegram_username"] = tg_user.username or ""
    User.objects.filter(pk=user.pk).update(**updates)
    for k, v in updates.items():
        setattr(user, k, v)
    return user, created


@sync_to_async
def set_language(user_id, lang):
    User.objects.filter(pk=user_id).update(language=lang)


@sync_to_async
def complete_registration(user_id, first_name, last_name, phone):
    phone = phone if phone.startswith("+") else f"+{phone}"
    User.objects.filter(pk=user_id).update(first_name=first_name, last_name=last_name, phone=phone, is_registered=True)
    user = User.objects.get(pk=user_id)
    BotEvent.objects.create(user=user, kind=BotEvent.Kind.REGISTER)
    return user


@sync_to_async
def get_login_request(token_hex):
    try:
        token = uuid.UUID(hex=token_hex)
    except ValueError:
        return None
    return LoginRequest.objects.filter(token=token).first()


@sync_to_async
def resolve_login_request(request_id, user_id, approve):
    """Kirish so'rovini tasdiqlaydi yoki rad etadi. Tasdiqlansa, zaxira kod ham qaytadi."""
    with transaction.atomic():
        req = LoginRequest.objects.select_for_update().filter(pk=request_id).first()
        if req is None or req.is_expired or req.status != LoginRequest.Status.PENDING:
            return None, None
        user = User.objects.get(pk=user_id)
        if not approve:
            req.status = LoginRequest.Status.REJECTED
            req.user = user
            req.save(update_fields=["status", "user"])
            return req, None
        req.status = LoginRequest.Status.CONFIRMED
        req.user = user
        req.save(update_fields=["status", "user"])
        code = LoginCode.issue(user, request=req)
        BotEvent.objects.create(user=user, kind=BotEvent.Kind.LOGIN_CONFIRM)
        return req, code.code


@sync_to_async
def issue_code(user_id):
    user = User.objects.get(pk=user_id)
    code = LoginCode.issue(user)
    BotEvent.objects.create(user=user, kind=BotEvent.Kind.LOGIN_CODE)
    return code.code


@sync_to_async
def profile_stats(user_id):
    from apps.education.models import Enrollment
    from apps.interactions.models import Comment

    user = User.objects.get(pk=user_id)
    return {
        "user": user,
        "courses": Enrollment.objects.filter(user=user, is_active=True).count(),
        "comments": Comment.objects.filter(user=user).count(),
    }


@sync_to_async
def published_courses(lang):
    from django.utils import translation

    from apps.education.models import Course

    with translation.override(lang):
        # i18n_patterns tufayli URL tanlangan til prefiksi bilan qaytadi
        return [(c.title, f"{settings.SITE_URL}{c.get_absolute_url()}") for c in Course.objects.listed()[:10]]


@sync_to_async
def save_incoming(user_id, text, message_id):
    user = User.objects.get(pk=user_id)
    return BotMessage.objects.create(user=user, direction=BotMessage.Direction.IN, text=text, telegram_message_id=message_id)


@sync_to_async
def log_event(user_id, kind, payload=""):
    BotEvent.objects.create(user_id=user_id, kind=kind, payload=payload[:200])


@sync_to_async
def mark_blocked(telegram_id):
    User.objects.filter(telegram_id=telegram_id).update(bot_blocked=True)
    user = User.objects.filter(telegram_id=telegram_id).first()
    if user:
        BotEvent.objects.create(user=user, kind=BotEvent.Kind.BLOCKED)


@sync_to_async
def admin_chat_ids():
    ids = set(settings.TELEGRAM_ADMIN_IDS)
    ids.update(User.objects.filter(is_staff=True, telegram_id__isnull=False).values_list("telegram_id", flat=True))
    return ids


@sync_to_async
def save_avatar(user_id, content):
    from django.core.files.base import ContentFile

    user = User.objects.get(pk=user_id)
    if not user.avatar:
        user.avatar.save(f"tg_{user.telegram_id}.jpg", ContentFile(content), save=True)

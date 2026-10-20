"""Telegram kanal postlari: yuborish, kanalda tahrirlash, o'chirish va sayt kontentidan post tayyorlash."""

import logging

from django.conf import settings
from django.utils import timezone, translation
from django.utils.html import escape

from . import api
from .formatting import html_to_telegram, truncate_telegram
from .models import BotSettings, ChannelPost

log = logging.getLogger(__name__)

CAPTION_LIMIT = 1024
TEXT_LIMIT = 4096


def channel_id():
    return BotSettings.load().channel_id.strip()


def render(post):
    """Post matni Telegram HTML ko'rinishida, rasmli/rasmsiz limitga moslab qisqartirilgan."""
    text = html_to_telegram(post.body)
    return truncate_telegram(text, CAPTION_LIMIT if post.image else TEXT_LIMIT)


def _markup(post):
    return api.url_button(post.button_text, post.button_url) if post.button_text and post.button_url else None


def publish(post):
    """Postni kanalga yuboradi. Muvaffaqiyatli bo'lsa True."""
    chat = channel_id()
    if not chat or not settings.TELEGRAM_BOT_TOKEN:
        post.status, post.error = ChannelPost.Status.FAILED, "Kanal yoki bot tokeni sozlanmagan"
        post.save(update_fields=["status", "error", "updated_at"])
        return False
    text = render(post)
    try:
        if post.image:
            with post.image.open("rb") as f:
                result = api.call(
                    "sendPhoto",
                    {"chat_id": chat, "caption": text, "parse_mode": "HTML", "reply_markup": _markup(post),
                     "disable_notification": post.silent},
                    files={"photo": (post.image.name.rsplit("/", 1)[-1], f.read())},
                )
        else:
            result = api.call("sendMessage", {
                "chat_id": chat, "text": text, "parse_mode": "HTML", "reply_markup": _markup(post),
                "disable_notification": post.silent, "link_preview_options": {"is_disabled": post.disable_preview},
            })
        if post.pin:
            try:
                api.call("pinChatMessage", {"chat_id": chat, "message_id": result["message_id"], "disable_notification": True})
            except api.TelegramError as e:
                log.info("pin failed: %s", e)
    except api.TelegramError as e:
        post.status, post.error = ChannelPost.Status.FAILED, str(e)[:300]
        post.save(update_fields=["status", "error", "updated_at"])
        return False
    post.status, post.error = ChannelPost.Status.SENT, ""
    post.message_id, post.sent_at = result["message_id"], timezone.now()
    post.save(update_fields=["status", "error", "message_id", "sent_at", "updated_at"])
    return True


def edit(post):
    """Kanalda allaqachon turgan postni yangilaydi (matn/izoh va tugma)."""
    if not post.message_id:
        return False
    chat, text = channel_id(), render(post)
    try:
        if post.image:
            api.call("editMessageCaption", {"chat_id": chat, "message_id": post.message_id, "caption": text,
                                            "parse_mode": "HTML", "reply_markup": _markup(post)})
        else:
            api.call("editMessageText", {"chat_id": chat, "message_id": post.message_id, "text": text, "parse_mode": "HTML",
                                         "reply_markup": _markup(post),
                                         "link_preview_options": {"is_disabled": post.disable_preview}})
    except api.TelegramError as e:
        if "message is not modified" in str(e):
            return True
        post.error = str(e)[:300]
        post.save(update_fields=["error", "updated_at"])
        return False
    return True


def delete(post):
    if post.message_id:
        try:
            api.call("deleteMessage", {"chat_id": channel_id(), "message_id": post.message_id})
        except api.TelegramError as e:
            log.info("delete failed: %s", e)


# --------------------------------------------------------------------------- sayt kontentidan post

def _tags(obj):
    if not hasattr(obj, "tags"):
        return ""
    return " ".join(f"#{t.name.replace(' ', '_').replace('-', '_')}" for t in obj.tags.all()[:5])


def build_from(obj):
    """Maqola/dars/kurs/loyihadan rich text post tayyorlaydi (sayt tilida: o'zbekcha)."""
    from apps.blog.models import Article
    from apps.education.models import Course, Lesson
    from apps.portfolio.models import Project

    with translation.override("uz"):
        url = settings.SITE_URL + obj.get_absolute_url()
        if isinstance(obj, Article):
            # Maqola boshidagi 2 ta paragraf: o'quvchini qiziqtirish uchun yetarli, qolgani saytda
            import re

            paras = re.findall(r"<p[^>]*>.*?</p>", obj.content or "", flags=re.S)[:2]
            body = (f"<p>📝 <strong>{escape(obj.title)}</strong></p><p><em>{escape(obj.excerpt)}</em></p>"
                    + "".join(paras) + f"<p>⏱ {obj.reading_minutes} daqiqa · {_tags(obj)}</p>")
            return dict(kind="article", title=obj.title, body=body, image=obj.cover, button_text="📖 Maqolani o'qish", button_url=url)
        if isinstance(obj, Lesson):
            c = obj.course
            body = (f"<p>🎬 <strong>Yangi dars: {obj.order}. {escape(obj.title)}</strong></p>"
                    f"<p>🎓 {escape(c.title)}</p>" + (f"<p>{escape(obj.summary)}</p>" if obj.summary else "")
                    + (f"<p>⏱ {obj.duration_label}</p>" if obj.duration_seconds else "")
                    + ("<p>📝 Uyga vazifa bor</p>" if obj.homework_mode != "none" else ""))
            return dict(kind="lesson", title=f"{c.title}: {obj.title}", body=body, image=obj.thumbnail or c.cover,
                        button_text="▶️ Darsni ko'rish", button_url=url)
        if isinstance(obj, Course):
            body = (f"<p>🎓 <strong>Yangi kurs: {escape(obj.title)}</strong></p><p>{escape(obj.subtitle)}</p>"
                    + (obj.what_you_learn or "") + f"<p>{'🆓 Bepul' if obj.is_free else '💳 Pullik'} · {obj.get_level_display()}</p>")
            return dict(kind="course", title=obj.title, body=body, image=obj.cover, button_text="🚀 Kursni boshlash", button_url=url)
        if isinstance(obj, Project):
            stack = ", ".join(s.name for s in obj.tech_stack.all()[:6])
            body = (f"<p>🚀 <strong>{escape(obj.title)}</strong> — {escape(obj.subtitle)}</p><p>{escape(obj.short_description)}</p>"
                    + (f"<p>🛠 {escape(stack)}</p>" if stack else ""))
            return dict(kind="project", title=obj.title, body=body, image=obj.cover, button_text="👀 Loyihani ko'rish", button_url=url)
    raise ValueError(f"Unsupported object: {obj!r}")


def post_object(obj, publish_now=True, user=None):
    data = build_from(obj)
    image = data.pop("image")
    post = ChannelPost(object_id=obj.pk, created_by=user, **data)
    if image:
        post.image.name = image.name  # mavjud faylga havola (nusxalanmaydi)
    post.save()
    if publish_now:
        publish(post)
    return post

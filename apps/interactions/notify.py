"""Sayt hodisalari haqida adminlarga Telegram orqali xabar berish."""

from django.conf import settings
from django.utils.html import escape

from apps.telegram_bot.models import BotSettings
from apps.telegram_bot.tasks import notify_admins


def _enqueue(text, url=None, button=None, **kwargs):
    if not settings.TELEGRAM_BOT_TOKEN:
        return
    notify_admins.delay(text, button, url, **kwargs)


def notify_admins_contact(msg):
    if not BotSettings.load().notify_contact_message:
        return
    text = (
        f"📩 <b>Yangi xabar</b>\n\n<b>{escape(msg.name)}</b> · {escape(msg.email)}\n"
        f"<i>{escape(msg.subject or '—')}</i>\n\n{escape(msg.message[:1500])}"
    )
    _enqueue(text, f"{settings.SITE_URL}/admin/interactions/contactmessage/{msg.pk}/change/", "Ochish")


def notify_admins_comment(comment, url):
    if not BotSettings.load().notify_new_comment:
        return
    text = f"💬 <b>Yangi izoh</b> — {escape(str(comment.target))}\n\n<b>{escape(comment.user.display_name)}</b>: {escape(comment.body[:800])}"
    _enqueue(text, url, "Ko'rish")


def notify_admins_review(review, url):
    if not BotSettings.load().notify_new_review:
        return
    stars = "⭐" * review.rating
    text = f"{stars} <b>Yangi sharh</b> — {escape(str(review.target))}\n\n<b>{escape(review.user.display_name)}</b>: {escape(review.body[:800])}\n\n<i>Tasdiqlash kutilmoqda</i>"
    _enqueue(text, f"{settings.SITE_URL}/admin/interactions/review/{review.pk}/change/", "Tasdiqlash")


def notify_admins_homework(sub):
    if not BotSettings.load().notify_homework:
        return
    text = (
        f"📝 <b>Uyga vazifa topshirildi</b>\n\n<b>{escape(sub.user.display_name)}</b>\n"
        f"{escape(sub.lesson.course.title)} → {escape(sub.lesson.title)}"
    )
    url = f"{settings.SITE_URL}/admin/education/homeworksubmission/{sub.pk}/change/"
    markup = {"inline_keyboard": [
        [{"text": "✅ Qabul", "callback_data": f"hw:ok:{sub.pk}"}, {"text": "🔁 Qayta ishlash", "callback_data": f"hw:no:{sub.pk}"}],
        [{"text": "🔗 Ochish", "url": url}],
    ]}
    _enqueue(text, url, "Tekshirish", bot="edu", edu_markup=markup)


def notify_reply(parent, reply, url):
    """Foydalanuvchining izohiga javob yozilsa, unga bot orqali xabar (agar sozlamada yoqilgan bo'lsa)."""
    user = parent.user
    if not settings.TELEGRAM_BOT_TOKEN or not user.telegram_id or not user.notify_comments or user.bot_blocked:
        return
    from apps.telegram_bot.tasks import send_to_user

    text = (f"💬 <b>{escape(reply.user.display_name)}</b> izohingizga javob yozdi:\n\n"
            f"<i>{escape(parent.body[:200])}</i>\n\n{escape(reply.body[:800])}")
    send_to_user.delay(user.pk, text, "Javobni ko'rish", url)

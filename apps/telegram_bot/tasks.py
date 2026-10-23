import logging
import time

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from . import api

log = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def notify_admins(self, text, button_text=None, button_url=None):
    """Adminlarga (TELEGRAM_ADMIN_IDS va botdan ro'yxatdan o'tgan staff) xabar yuboradi."""
    from apps.accounts.models import User

    chat_ids = set(settings.TELEGRAM_ADMIN_IDS)
    chat_ids.update(User.objects.filter(is_staff=True, telegram_id__isnull=False).values_list("telegram_id", flat=True))
    markup = api.url_button(button_text, button_url) if button_text and button_url else None
    for chat_id in chat_ids:
        try:
            api.send_message(chat_id, text, reply_markup=markup)
        except api.TelegramError as e:
            log.warning("admin notify failed for %s: %s", chat_id, e)


@shared_task
def send_to_user(user_id, text, button_text=None, button_url=None, sent_by_id=None):
    from apps.accounts.models import User

    from .models import BotMessage

    user = User.objects.filter(pk=user_id, telegram_id__isnull=False).first()
    if not user:
        return
    markup = api.url_button(button_text, button_url) if button_text and button_url else None
    try:
        result = api.send_message(user.telegram_id, text, reply_markup=markup)
        BotMessage.objects.create(
            user=user, direction=BotMessage.Direction.OUT, text=text, telegram_message_id=result.get("message_id"),
            is_read=True, sent_by_id=sent_by_id,
        )
    except api.TelegramError as e:
        if e.code == 403:
            User.objects.filter(pk=user.pk).update(bot_blocked=True)
        log.warning("send_to_user %s failed: %s", user_id, e)


@shared_task
def run_broadcast(broadcast_id):
    """Ommaviy xabarni yuboradi. Telegram limiti: ~25 xabar/soniya."""
    from apps.accounts.models import User

    from .models import Broadcast

    b = Broadcast.objects.select_related("course").get(pk=broadcast_id)
    if b.status not in (Broadcast.Status.DRAFT, Broadcast.Status.SCHEDULED):
        return
    users = User.objects.filter(telegram_id__isnull=False, bot_blocked=False, is_blocked=False)
    if b.audience != Broadcast.Audience.STAFF:
        users = users.filter(notify_news=True)
    if b.audience == Broadcast.Audience.REGISTERED:
        users = users.filter(is_registered=True)
    elif b.audience == Broadcast.Audience.STUDENTS:
        users = users.filter(enrollments__isnull=False).distinct()
    elif b.audience == Broadcast.Audience.COURSE and b.course_id:
        users = users.filter(enrollments__course_id=b.course_id).distinct()
    elif b.audience == Broadcast.Audience.STAFF:
        users = users.filter(is_staff=True)

    ids = list(users.values_list("id", "telegram_id"))
    Broadcast.objects.filter(pk=b.pk).update(status=Broadcast.Status.SENDING, total=len(ids), sent=0, failed=0, started_at=timezone.now())
    markup = api.url_button(b.button_text, b.button_url) if b.button_text and b.button_url else None
    from .formatting import html_to_telegram, truncate_telegram

    text = truncate_telegram(html_to_telegram(b.text), 1024 if b.image else 4096)
    photo = b.image.read() if b.image else None
    sent = failed = 0
    for user_id, chat_id in ids:
        for _attempt in range(2):
            try:
                if photo:
                    api.send_photo(chat_id, photo, b.image.name.rsplit("/", 1)[-1], text, reply_markup=markup)
                else:
                    api.send_message(chat_id, text, reply_markup=markup)
                sent += 1
                break
            except api.TelegramError as e:
                if e.retry_after:
                    time.sleep(e.retry_after + 1)
                    continue
                if e.code == 403:
                    User.objects.filter(pk=user_id).update(bot_blocked=True)
                failed += 1
                break
        if (sent + failed) % 20 == 0:
            Broadcast.objects.filter(pk=b.pk).update(sent=sent, failed=failed)
        time.sleep(0.045)
    Broadcast.objects.filter(pk=b.pk).update(
        status=Broadcast.Status.DONE, sent=sent, failed=failed, finished_at=timezone.now(),
    )


@shared_task
def post_to_channel(model_label, pk):
    """Yangi nashr qilingan kontentni kanalga rich text post sifatida joylaydi (bir marta)."""
    from django.apps import apps as django_apps

    from . import channel

    from .models import ChannelPost

    model = django_apps.get_model(model_label)
    obj = model.objects.filter(pk=pk).first()
    if obj is None or getattr(obj, "posted_to_channel_at", None) or obj.status != "published":
        return
    kind = {"blog.Article": "article", "education.Lesson": "lesson"}.get(model_label, "")
    # Ishonchli dublikat himoyasi: eski obyekt saqlanib posted_to_channel_at None bo'lib qolsa ham qayta yuborilmaydi
    if ChannelPost.objects.filter(kind=kind, object_id=pk, status=ChannelPost.Status.SENT).exists():
        model.objects.filter(pk=pk).update(posted_to_channel_at=timezone.now())
        return
    if not channel.channel_id() or not settings.TELEGRAM_BOT_TOKEN:
        return
    post = channel.post_object(obj)
    if post.status == "sent" and hasattr(obj, "posted_to_channel_at"):
        model.objects.filter(pk=pk).update(posted_to_channel_at=timezone.now())


@shared_task
def send_channel_post(post_id):
    from . import channel
    from .models import ChannelPost

    post = ChannelPost.objects.filter(pk=post_id).first()
    if post and post.status in (ChannelPost.Status.DRAFT, ChannelPost.Status.SCHEDULED, ChannelPost.Status.FAILED):
        channel.publish(post)


@shared_task
def send_due():
    """Vaqti kelgan rejalashtirilgan kanal postlari va ommaviy xabarlarni yuboradi (Celery beat: har daqiqa)."""
    from .models import Broadcast, ChannelPost

    now = timezone.now()
    for pk in ChannelPost.objects.filter(status="scheduled", scheduled_at__lte=now).values_list("pk", flat=True):
        send_channel_post(pk)
    for pk in Broadcast.objects.filter(status="scheduled", scheduled_at__lte=now).values_list("pk", flat=True):
        run_broadcast(pk)


@shared_task
def indexnow_ping(paths):
    """Yangi/yangilangan sahifalarni IndexNow orqali Yandex va Bing'ga yuboradi (barcha tillar)."""
    import json
    import urllib.request
    from urllib.parse import urlparse

    from apps.core.models import SiteSettings

    key = SiteSettings.load().indexnow_key
    if not key or not settings.SITE_URL.startswith("https://"):
        return
    host = urlparse(settings.SITE_URL).netloc
    body = json.dumps({
        "host": host, "key": key, "keyLocation": f"{settings.SITE_URL}/{key}.txt",
        "urlList": [settings.SITE_URL + p for p in paths][:1000],
    }).encode()
    req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body, headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:  # noqa: BLE001 - indekslash xabari muhim emas, sayt ishlashiga ta'sir qilmasin
        log.info("indexnow ping failed: %s", e)


def _nudge(user, text, button_text, url):
    """Eslatmani yuboradi; bot bloklangan bo'lsa belgilab qo'yadi. Muvaffaqiyatli bo'lsa True."""
    try:
        api.send_message(user.telegram_id, text, reply_markup=api.url_button(button_text, settings.SITE_URL + url))
        return True
    except api.TelegramError as e:
        if e.code == 403:
            type(user).objects.filter(pk=user.pk).update(bot_blocked=True)
        log.warning("nudge %s failed: %s", user.pk, e)
        return False


@shared_task
def nudge_learners():
    """Kunlik eslatmalar (Celery beat):

    1) kursga yozilmagan yangi foydalanuvchilarga — 1 va 3 kundan keyin bepul kursni boshlash taklifi;
    2) kursni boshlab, 3 kundan beri davom ettirmaganlarga — keyingi dars (har yozilishga bir marta).
    """
    from datetime import timedelta
    from html import escape

    from django.db.models import Count, Max, Q
    from django.utils import translation

    from apps.accounts.models import User
    from apps.education.models import Course, Enrollment, LessonProgress

    from .bot.texts import t

    now = timezone.now()
    reachable = User.objects.filter(
        telegram_id__isnull=False, is_registered=True, is_staff=False,
        bot_blocked=False, is_blocked=False, notify_news=True,
    )
    course = (
        Course.objects.published().filter(is_free=True, is_private=False)
        .annotate(n=Count("lessons", filter=Q(lessons__status="published")))
        .filter(n__gt=0).order_by("-is_featured", "order", "id").first()
    )
    sent = 0
    if course:
        # (bosqich, ro'yxatdan o'tgandan keyin necha kun) — har biri bir marta
        for stage, days in ((1, 1), (2, 3)):
            users = reachable.filter(
                nudge_stage=stage - 1, enrollments__isnull=True, date_joined__lte=now - timedelta(days=days),
            ).distinct()
            for user in users[:500]:
                lang = user.language or "uz"
                with translation.override(lang):
                    text = t(f"nudge_start_{stage}", lang, name=escape(user.first_name or user.display_name),
                             course=escape(course.title), subtitle=escape(course.subtitle), lessons=course.n)
                    url = course.get_absolute_url()
                if _nudge(user, text, t("btn_start_course", lang), url):
                    sent += 1
                # Yuborilmasa ham bosqich oshadi — bir xil xabar qayta-qayta urinilmasin
                User.objects.filter(pk=user.pk).update(nudge_stage=stage)
                time.sleep(0.05)

    stale = now - timedelta(days=3)
    enrollments = (
        Enrollment.objects.filter(
            user__in=reachable, is_active=True, completed_at__isnull=True, nudged_at__isnull=True,
            created_at__lte=stale, course__status="published",
        )
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
        .select_related("user", "course", "last_lesson")
    )
    for e in enrollments[:500]:
        last = (
            LessonProgress.objects.filter(user=e.user, lesson__course=e.course)
            .aggregate(at=Max("updated_at"))["at"]
        )
        if last and last > stale:
            continue
        lesson = e.last_lesson.next_lesson() if e.last_lesson else e.course.published_lessons().first()
        if lesson is None:
            continue
        lang = e.user.language or "uz"
        with translation.override(lang):
            text = t("nudge_continue", lang, name=escape(e.user.first_name or e.user.display_name),
                     course=escape(e.course.title), lesson=escape(lesson.title))
            url = lesson.get_absolute_url()
        if _nudge(e.user, text, t("btn_continue", lang), url):
            sent += 1
        Enrollment.objects.filter(pk=e.pk).update(nudged_at=now)
        time.sleep(0.05)
    return sent

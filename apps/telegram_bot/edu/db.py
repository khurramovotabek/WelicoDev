"""Ta'lim boti uchun ORM amallari. Hammasi sinxron; handlerlar sync_to_async orqali chaqiradi.

Biznes mantiq (yozilish, ruxsat, vazifa tekshiruvi) apps.education.services'dagi bilan bir xil —
sayt, dashboard va bot bitta yo'ldan o'tadi.
"""

from django.conf import settings
from django.db.models import Q, Sum
from django.utils import timezone, translation

from apps.accounts.models import User
from apps.education import services
from apps.education.models import AccessRequest, Course, Enrollment, HomeworkSubmission

from .texts import LEVELS, t


def touch_user(tg_user):
    """Telegram foydalanuvchisini topadi (yoki yaratadi) va ta'lim botini ochganini belgilaydi."""
    user = User.objects.filter(telegram_id=tg_user.id).first()
    if user is None:
        code = (tg_user.language_code or "")[:2]
        user = User(
            username=f"tg_{tg_user.id}", telegram_id=tg_user.id,
            first_name=(tg_user.first_name or "")[:150], last_name=(tg_user.last_name or "")[:150],
            language=code if code in ("uz", "ru", "en") else "uz",
        )
        user.set_unusable_password()
        user.save()
    updates = {"edu_bot_started": True, "edu_bot_blocked": False}
    if tg_user.username and tg_user.username != user.telegram_username:
        updates["telegram_username"] = tg_user.username
    User.objects.filter(pk=user.pk).update(**updates)
    for k, v in updates.items():
        setattr(user, k, v)
    return user


def mark_blocked(telegram_id):
    User.objects.filter(telegram_id=telegram_id).update(edu_bot_blocked=True)


def set_language(user_id, lang):
    User.objects.filter(pk=user_id).update(language=lang)


def _price(course, lang):
    if course.is_free:
        return t("free", lang)
    return t("som", lang, price=f"{course.price:,.0f}".replace(",", " "))


def _duration(seconds):
    h, m = divmod(seconds // 60, 60)
    return f"{h}h {m:02d}m" if h else f"{m}m"


def course_list(lang):
    with translation.override(lang):
        return [(c.pk, c.title, c.is_free) for c in Course.objects.listed().order_by("-is_featured", "order", "id")[:20]]


def course_card(user, course_id, lang):
    """Kurs kartasi: matn va holatga mos tugmalar ro'yxati (callback yoki url)."""
    from html import escape

    course = Course.objects.for_user(user).filter(pk=course_id).first()
    if course is None:
        return None
    with translation.override(lang):
        lessons = course.published_lessons()
        text = t("course_card", lang, title=escape(course.title), subtitle=escape(course.subtitle),
                 level=LEVELS.get(course.level, {}).get(lang, course.get_level_display()),
                 lessons=lessons.count(), duration=_duration(course.total_seconds), price=_price(course, lang))
        enrollment = services.get_enrollment(user, course)
        buttons = []
        if enrollment:
            text += t("progress_line", lang, p=services.course_progress(user, course))
            nxt = (enrollment.last_lesson.next_lesson() if enrollment.last_lesson else None) or enrollment.last_lesson or lessons.first()
            buttons.append(("url", t("btn_continue", lang), settings.SITE_URL + (nxt or course).get_absolute_url()))
        elif course.is_free and not course.is_private:
            buttons.append(("cb", t("btn_enroll", lang), f"en:{course.pk}"))
        elif AccessRequest.objects.filter(user=user, course=course, status=AccessRequest.Status.PENDING).exists():
            buttons.append(("cb", t("btn_requested", lang), f"c:{course.pk}"))
        else:
            buttons.append(("cb", t("btn_request", lang), f"rq:{course.pk}"))
        buttons.append(("url", t("btn_site", lang), settings.SITE_URL + course.get_absolute_url()))
        buttons.append(("cb", t("btn_back", lang), "cl"))
    return text, buttons


def enroll_free(user, course_id, lang):
    """Bepul ochiq kursga yozadi. Natija: (kurs nomi, birinchi dars URL) yoki None."""
    course = Course.objects.listed().filter(pk=course_id, is_free=True).first()
    if course is None:
        return None
    Enrollment.objects.get_or_create(user=user, course=course)
    with translation.override(lang):
        first = course.published_lessons().first()
        return course.title, settings.SITE_URL + (first or course).get_absolute_url()


def request_access(user, course_id):
    course = Course.objects.for_user(user).filter(pk=course_id).filter(Q(is_free=False) | Q(is_private=True)).first()
    if course is None:
        return None
    req, _created = services.request_access(user, course, note="Telegram: @welicodev_educationbot")
    return req.reference


def my_courses(user, lang):
    rows = []
    qs = (
        Enrollment.objects.filter(user=user, is_active=True)
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))
        .select_related("course", "last_lesson").order_by("-created_at")
    )
    with translation.override(lang):
        for e in qs[:10]:
            nxt = (e.last_lesson.next_lesson() if e.last_lesson else None) or e.last_lesson or e.course.published_lessons().first()
            rows.append({
                "title": e.course.title, "progress": services.course_progress(user, e.course),
                "done": bool(e.completed_at), "url": settings.SITE_URL + (nxt or e.course).get_absolute_url(),
            })
    return rows


def my_homework(user, lang):
    with translation.override(lang):
        return [
            (s.lesson.course.title, s.lesson.title, s.status, s.feedback)
            for s in HomeworkSubmission.objects.filter(user=user).select_related("lesson__course").order_by("-created_at")[:10]
        ]


# --------------------------------------------------------------------------- Admin

def admin_stats():
    return {
        "students": Enrollment.objects.filter(is_active=True).values("user").distinct().count(),
        "enrollments": Enrollment.objects.filter(is_active=True).count(),
        "completed": Enrollment.objects.filter(completed_at__isnull=False).count(),
        "requests": AccessRequest.objects.filter(status=AccessRequest.Status.PENDING).count(),
        "homework": HomeworkSubmission.objects.filter(status=HomeworkSubmission.Status.PENDING).count(),
        "revenue": f"{AccessRequest.objects.filter(status='approved').aggregate(s=Sum('amount'))['s'] or 0:,.0f}".replace(",", " "),
    }


def pending_requests():
    return list(AccessRequest.objects.filter(status=AccessRequest.Status.PENDING).select_related("user", "course").order_by("created_at")[:10])


def pending_homework():
    return list(HomeworkSubmission.objects.filter(status=HomeworkSubmission.Status.PENDING)
                .select_related("user", "lesson__course").order_by("created_at")[:10])


def resolve_request(admin, request_id, approve):
    """So'rovni tasdiqlaydi yoki rad etadi. Natija: AccessRequest yoki None (allaqachon ko'rib chiqilgan)."""
    req = AccessRequest.objects.select_related("user", "course").filter(pk=request_id).first()
    if req is None or req.status != AccessRequest.Status.PENDING:
        return None
    if approve:
        services.grant_access(req.course, req.user, by=admin, access_request=req, amount=req.course.price or None)
    else:
        services.reject_access(req, by=admin)
    req.refresh_from_db()
    return req


def review_homework(admin, sub_id, approve):
    sub = HomeworkSubmission.objects.select_related("user", "lesson__course").filter(pk=sub_id).first()
    if sub is None or sub.status != HomeworkSubmission.Status.PENDING:
        return None
    status = "approved" if approve else "rejected"
    sub.mark_reviewed(status, sub.feedback)
    services.try_complete(sub.user, sub.lesson)
    services.notify_homework_result(sub)
    return sub


# --------------------------------------------------------------------------- Kanal

def edu_channel():
    from apps.telegram_bot import channel

    return channel.channel_id("edu") if channel.edu_ready() else ""


def unannounced(kind):
    """Kanalga hali chiqmagan e'lon qilingan darslar (videosi bor) yoki kurslar."""
    from apps.education.models import Lesson
    from apps.telegram_bot.models import ChannelPost

    if kind == "lesson":
        qs = (Lesson.objects.filter(status="published", course__status="published", posted_to_channel_at__isnull=True)
              .exclude(video="", video_url="").select_related("course").order_by("-created_at")[:8])
        return [(x.pk, f"{x.course.title[:20]} · {x.order}. {x.title}"[:60]) for x in qs]
    sent = ChannelPost.objects.filter(kind="course", status="sent").values_list("object_id", flat=True)
    return [(c.pk, c.title[:60]) for c in Course.objects.listed().exclude(pk__in=list(sent)).order_by("-created_at")[:8]]


def announce(kind, pk, admin):
    """Dars yoki kursni ta'lim kanaliga e'lon qiladi. Natija: ChannelPost yoki None."""
    from apps.education.models import Lesson
    from apps.telegram_bot import channel

    model = Lesson if kind == "lesson" else Course
    obj = model.objects.filter(pk=pk).first()
    if obj is None:
        return None
    post = channel.post_object(obj, user=admin)
    if post.status == "sent" and kind == "lesson":
        Lesson.objects.filter(pk=pk).update(posted_to_channel_at=timezone.now())
    return post


def record_manual_post(admin, html, message_id):
    """Botdan qo'lda joylangan postni dashboard tarixida ko'rinishi uchun saqlaydi."""
    import re

    from apps.telegram_bot.models import ChannelPost

    plain = re.sub(r"<[^>]+>", "", html or "").strip()
    return ChannelPost.objects.create(
        kind="manual", target="edu", title=(plain[:60] or "Bot orqali post"), body=html or "<p>📎</p>",
        status="sent", message_id=message_id, sent_at=timezone.now(), created_by=admin,
    )

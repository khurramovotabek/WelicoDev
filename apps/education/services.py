"""Kurs progressi va darslarni ketma-ket ochish qoidalari.

Dars tugatilgan hisoblanadi, agar:
  * videosi bo'lsa, kamida WATCH_THRESHOLD qismi ko'rilgan bo'lsa, va
  * uyga vazifa talabi bajarilgan bo'lsa (SUBMIT: javob topshirilgan, APPROVAL: javob qabul qilingan).
Ketma-ket kursda dars faqat oldingi dars tugatilganda ochiladi.
"""

import secrets

from django.db import transaction
from django.utils import timezone

from .models import (
    WATCH_THRESHOLD, Certificate, Enrollment, HomeworkSubmission, Lesson, LessonProgress,
)


def get_enrollment(user, course):
    if not user.is_authenticated:
        return None
    from django.db.models import Q

    return (
        Enrollment.objects.filter(user=user, course=course, is_active=True)
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())).first()
    )


def completed_lesson_ids(user, course):
    if not user.is_authenticated:
        return set()
    return set(
        LessonProgress.objects.filter(user=user, lesson__course=course, completed_at__isnull=False)
        .values_list("lesson_id", flat=True)
    )


def lesson_states(user, course):
    """Kurs darslari ro'yxati: har biri uchun (dars, holat). Holat: completed / current / unlocked / locked."""
    lessons = list(course.published_lessons())
    enrolled = get_enrollment(user, course) is not None
    done = completed_lesson_ids(user, course)
    states = []
    previous_done = True
    current_marked = False
    for lesson in lessons:
        if lesson.id in done:
            state = "completed"
        elif user.is_staff:
            state = "unlocked"
        elif lesson.is_preview:
            state = "unlocked"
        elif not enrolled:
            state = "locked"
        elif not course.sequential or previous_done:
            state = "current" if not current_marked else "unlocked"
            current_marked = True
        else:
            state = "locked"
        states.append((lesson, state))
        previous_done = lesson.id in done
    return states


def is_lesson_unlocked(user, lesson):
    if lesson.is_preview or (user.is_authenticated and user.is_staff):
        return True
    if get_enrollment(user, lesson.course) is None:
        return False
    if not lesson.course.sequential:
        return True
    previous = lesson.previous_lesson()
    if previous is None:
        return True
    return LessonProgress.objects.filter(user=user, lesson=previous, completed_at__isnull=False).exists()


def homework_satisfied(user, lesson):
    mode = lesson.homework_mode
    if mode in (Lesson.HomeworkMode.NONE, Lesson.HomeworkMode.OPTIONAL):
        return True
    subs = HomeworkSubmission.objects.filter(user=user, lesson=lesson)
    if mode == Lesson.HomeworkMode.SUBMIT:
        return subs.exclude(status=HomeworkSubmission.Status.REJECTED).exists()
    return subs.filter(status=HomeworkSubmission.Status.APPROVED).exists()


def _video_done(progress, lesson):
    return not lesson.has_video or progress.video_completed


@transaction.atomic
def record_watch(user, lesson, position, delta):
    """Pleyerdan keladigan heartbeat. `delta` haqiqatda ko'rilgan soniyalar (oldinga sakrash hisoblanmaydi)."""
    progress, _created = LessonProgress.objects.select_for_update().get_or_create(user=user, lesson=lesson)
    # Bir heartbeat orasida 30 soniyadan ko'p ko'rib bo'lmaydi: soxta so'rovlardan himoya
    delta = max(0, min(int(delta), 30))
    progress.watched_seconds += delta
    progress.last_position = max(0, int(position))
    duration = lesson.duration_seconds
    if duration and progress.watched_seconds >= duration * WATCH_THRESHOLD:
        progress.video_completed = True
    progress.save()
    try_complete(user, lesson, progress)
    Enrollment.objects.filter(user=user, course=lesson.course).update(last_lesson=lesson)
    return progress


def mark_video_completed(user, lesson):
    """Tashqi video (YouTube) uchun: davomiylik noma'lum, foydalanuvchi o'zi belgilaydi."""
    progress, _created = LessonProgress.objects.get_or_create(user=user, lesson=lesson)
    progress.video_completed = True
    progress.save(update_fields=["video_completed", "updated_at"])
    return try_complete(user, lesson, progress)


def try_complete(user, lesson, progress=None):
    if progress is None:
        progress, _created = LessonProgress.objects.get_or_create(user=user, lesson=lesson)
    if progress.completed_at:
        return progress
    if _video_done(progress, lesson) and homework_satisfied(user, lesson):
        progress.completed_at = timezone.now()
        progress.save(update_fields=["completed_at", "updated_at"])
        _maybe_finish_course(user, lesson.course)
    return progress


def _maybe_finish_course(user, course):
    enrollment = get_enrollment(user, course)
    if not enrollment or enrollment.completed_at:
        return
    total = course.published_lessons().count()
    if total and len(completed_lesson_ids(user, course)) >= total:
        enrollment.completed_at = timezone.now()
        enrollment.save(update_fields=["completed_at"])
        Certificate.objects.get_or_create(
            enrollment=enrollment, defaults={"code": f"WCD-{secrets.token_hex(4).upper()}"},
        )


def course_progress(user, course):
    total = course.published_lessons().count()
    if not total:
        return 0
    return round(len(completed_lesson_ids(user, course)) * 100 / total)


# --------------------------------------------------------------------------- Pullik kurslarga kirish

def _notify(task, *args, **kwargs):
    """Telegram xabarini tranzaksiya tugagach yuboradi (xato bo'lsa sahifa buzilmaydi)."""
    from django.conf import settings

    if not settings.TELEGRAM_BOT_TOKEN:
        return
    transaction.on_commit(lambda: task.delay(*args, **kwargs))


def request_access(user, course, note=""):
    """Foydalanuvchi pullik kursga so'rov qoldiradi; adminlar Telegram'da xabar oladi."""
    from html import escape

    from django.conf import settings
    from django.urls import reverse

    from apps.telegram_bot.tasks import notify_admins

    from .models import AccessRequest

    req = AccessRequest.objects.filter(user=user, course=course, status=AccessRequest.Status.PENDING).first()
    created = req is None
    if created:
        req = AccessRequest.objects.create(user=user, course=course, note=note[:300])
    elif note and note != req.note:
        req.note = note[:300]
        req.save(update_fields=["note", "updated_at"])
    if created:
        price = f"{course.price:,.0f}".replace(",", " ")
        text = (
            f"💳 <b>Yangi kurs so'rovi</b> · <code>{req.reference}</code>\n\n"
            f"📚 {escape(course.title)} — {price} so'm\n"
            f"👤 {escape(user.display_name)}" + (f" · {escape(user.phone)}" if user.phone else "")
            + (f" · @{escape(user.telegram_username)}" if getattr(user, "telegram_username", "") else "")
            + (f"\n📝 {escape(note)}" if note else "")
        )
        url = f"{settings.SITE_URL}{reverse('dashboard:access')}"
        # Ta'lim botida admin to'g'ridan-to'g'ri tasdiqlaydi yoki rad etadi
        markup = {"inline_keyboard": [
            [{"text": "✅ Ruxsat berish", "callback_data": f"ar:ok:{req.pk}"},
             {"text": "❌ Rad etish", "callback_data": f"ar:no:{req.pk}"}],
            [{"text": "📊 Dashboard", "url": url}],
        ]}
        _notify(notify_admins, text, "Dashboard", url, bot="edu", edu_markup=markup)
    return req, created


@transaction.atomic
def grant_access(course, user, by=None, expires_at=None, access_request=None, amount=None, notify=True):
    """Kursga ruxsat beradi (Enrollment yaratadi yoki qayta yoqadi) va foydalanuvchiga Telegram orqali xabar yuboradi."""
    from html import escape

    from django.conf import settings

    from apps.telegram_bot.tasks import send_to_user

    from .models import AccessRequest

    enrollment, _created = Enrollment.objects.get_or_create(user=user, course=course, defaults={"granted_by": by})
    enrollment.is_active = True
    enrollment.expires_at = expires_at
    enrollment.granted_by = by or enrollment.granted_by
    enrollment.save(update_fields=["is_active", "expires_at", "granted_by"])

    pending = AccessRequest.objects.filter(user=user, course=course, status=AccessRequest.Status.PENDING)
    if access_request is not None:
        pending = pending | AccessRequest.objects.filter(pk=access_request.pk)
    pending.update(status=AccessRequest.Status.APPROVED, reviewed_at=timezone.now(), reviewed_by=by,
                   **({"amount": amount} if amount is not None else {}))
    if notify:
        first = course.published_lessons().first()
        url = f"{settings.SITE_URL}{(first or course).get_absolute_url()}"
        _notify(send_to_user, user.pk, f"🎉 <b>{escape(course.title)}</b> kursiga ruxsat berildi!\n\nO'qishni boshlashingiz mumkin.",
                "Kursni ochish", url, by.pk if by else None, bot="edu")
    return enrollment


def reject_access(access_request, by=None, admin_note=""):
    from html import escape

    from apps.telegram_bot.tasks import send_to_user

    access_request.status = access_request.Status.REJECTED
    access_request.admin_note = admin_note[:300]
    access_request.reviewed_at = timezone.now()
    access_request.reviewed_by = by
    access_request.save(update_fields=["status", "admin_note", "reviewed_at", "reviewed_by", "updated_at"])
    text = f"«{escape(access_request.course.title)}» kursi bo'yicha so'rovingiz rad etildi."
    if admin_note:
        text += f"\n\n{escape(admin_note)}"
    _notify(send_to_user, access_request.user_id, text, bot="edu")


def notify_homework_result(sub):
    """O'quvchiga uyga vazifa natijasi (ta'lim botidan, bo'lmasa asosiy botdan)."""
    from html import escape

    from django.conf import settings
    from django.utils import translation

    from apps.telegram_bot.tasks import send_to_user

    with translation.override(sub.user.language or "uz"):
        verdict = "✅ qabul qilindi" if sub.status == "approved" else "🔁 qayta ishlash kerak"
        text = f"📝 <b>{escape(sub.lesson.title)}</b> — uyga vazifangiz {verdict}."
        if sub.feedback:
            text += f"\n\n💬 {escape(sub.feedback)}"
        _notify(send_to_user, sub.user_id, text, "Darsni ochish", settings.SITE_URL + sub.lesson.get_absolute_url(), bot="edu")


def revoke_access(enrollment):
    enrollment.is_active = False
    enrollment.save(update_fields=["is_active"])

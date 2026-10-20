import json
import mimetypes
import os
import re

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import FileResponse, Http404, HttpResponse, HttpResponseForbidden, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.core.utils import get_hero
from apps.interactions.services import annotate_stats, rating_summary

from . import services
from .forms import HomeworkForm
from .models import Certificate, Course, Enrollment, HomeworkSubmission, Lesson, LessonResource


def course_list(request):
    from django.db.models import Sum

    from apps.portfolio.models import Skill

    level, tech, q = request.GET.get("level", ""), request.GET.get("tech", ""), request.GET.get("q", "").strip()
    base = Course.objects.for_user(request.user)
    courses = base.annotate(
        n_lessons=Count("lessons", filter=Q(lessons__status="published"), distinct=True),
        n_students=Count("enrollments", distinct=True),
        n_seconds=Sum("lessons__duration_seconds", filter=Q(lessons__status="published")),
    ).prefetch_related("technologies")
    if level:
        courses = courses.filter(level=level)
    if tech:
        courses = courses.filter(technologies__slug=tech).distinct()
    if q:
        courses = courses.filter(Q(title__icontains=q) | Q(subtitle__icontains=q))
    enrolled = {}
    if request.user.is_authenticated:
        for e in Enrollment.objects.filter(user=request.user, is_active=True).select_related("course"):
            enrolled[e.course_id] = services.course_progress(request.user, e.course)
    lessons = Lesson.objects.filter(course__in=base, status="published")
    featured = None if (level or tech or q) else courses.filter(is_featured=True).first()
    return render(request, "education/courses.html", {
        "hero": get_hero("education"),
        "courses": annotate_stats(courses.exclude(pk=featured.pk) if featured else courses),
        "featured": featured,
        "levels": Course.Level.choices,
        "techs": Skill.objects.filter(courses__status="published").distinct(),
        "active_level": level, "active_tech": tech, "q": q,
        "enrolled": enrolled,
        "stats": {
            "courses": base.count(),
            "lessons": lessons.count(),
            "hours": round((lessons.aggregate(s=Sum("duration_seconds"))["s"] or 0) / 3600, 1),
            "students": Enrollment.objects.filter(course__in=base).values("user").distinct().count(),
        },
    })


def course_detail(request, slug):
    course = get_object_or_404(Course.objects.for_user(request.user).prefetch_related("technologies", "modules"), slug=slug)
    enrollment = services.get_enrollment(request.user, course)
    states = services.lesson_states(request.user, course)
    # Modullar bo'yicha guruhlash (modulsiz darslar oxirida)
    groups, by_module = [], {}
    for lesson, state in states:
        key = lesson.module_id
        if key not in by_module:
            by_module[key] = {"module": lesson.module, "items": []}
            groups.append(by_module[key])
        by_module[key]["items"].append((lesson, state))
    resume = None
    if enrollment:
        resume = enrollment.last_lesson or next((l for l, s in states if s == "current"), None)
    from apps.core import seo
    from apps.core.models import SiteSettings

    rating = rating_summary(course)
    return render(request, "education/course_detail.html", {
        "course": course,
        "jsonld": seo.course(course, [lesson for lesson, _s in states], rating, SiteSettings.load()),
        "enrollment": enrollment,
        "groups": groups,
        "lessons_total": len(states),
        "completed": sum(1 for _l, s in states if s == "completed"),
        "progress": services.course_progress(request.user, course) if enrollment else 0,
        "resume": resume,
        "first_lesson": states[0][0] if states else None,
        "rating": rating,
        "students": course.enrollments.count(),
        "certificate": getattr(enrollment, "certificate", None) if enrollment and enrollment.completed_at else None,
        "access_request": course.access_requests.filter(user=request.user).order_by("-created_at").first()
        if request.user.is_authenticated and not course.is_free else None,
    })


@require_POST
def enroll(request, slug):
    course = get_object_or_404(Course.objects.for_user(request.user), slug=slug)
    if not request.user.is_authenticated:
        return redirect(f"{reverse('accounts:login')}?next={course.get_absolute_url()}")
    if not course.is_free and not request.user.is_staff:
        return redirect("education:buy", slug=course.slug)
    Enrollment.objects.get_or_create(user=request.user, course=course)
    messages.success(request, _("Kursga yozildingiz! Birinchi darsdan boshlang."))
    first = course.published_lessons().first()
    return redirect(first.get_absolute_url() if first else course.get_absolute_url())


def buy(request, slug):
    """Pullik kursni sotib olish: to'lov Telegram orqali kelishiladi, keyin admin dashboarddan ruxsat beradi."""
    from apps.core.models import SiteSettings

    from .models import AccessRequest

    course = get_object_or_404(Course.objects.for_user(request.user), slug=slug)
    if course.is_free:
        return redirect(course)
    if not request.user.is_authenticated:
        return redirect(f"{reverse('accounts:login')}?next={reverse('education:buy', args=[course.slug])}")
    if services.get_enrollment(request.user, course):
        return redirect(course)

    site = SiteSettings.load()
    access_request = AccessRequest.objects.filter(user=request.user, course=course).order_by("-created_at").first()
    if request.method == "POST":
        access_request, _created = services.request_access(request.user, course, request.POST.get("note", "").strip())
        if request.POST.get("go") == "telegram":
            return redirect(_payment_link(site, course, access_request, request.user))
        messages.success(request, _("So'rovingiz qabul qilindi. To'lovdan keyin kurs ochiladi."))
        return redirect("education:buy", slug=course.slug)

    states = services.lesson_states(request.user, course)
    return render(request, "education/buy.html", {
        "course": course,
        "site": site,
        "access_request": access_request,
        "telegram_link": _payment_link(site, course, access_request, request.user) if access_request else site.payment_link,
        "lessons_total": len(states),
        "preview_lessons": [lesson for lesson, _s in states if lesson.is_preview][:3],
        "modules": course.modules.all(),
    })


def _payment_link(site, course, access_request, user):
    from urllib.parse import quote

    price = f"{course.price:,.0f}".replace(",", " ")
    text = _("Assalomu alaykum! «%(course)s» kursini sotib olmoqchiman (%(price)s so'm). So'rov: %(ref)s, ism: %(name)s") % {
        "course": course.title, "price": price, "ref": access_request.reference if access_request else "-", "name": user.display_name,
    }
    return f"{site.payment_link}?text={quote(text)}"


def lesson_detail(request, course_slug, lesson_slug):
    from apps.core import seo

    course = get_object_or_404(Course.objects.for_user(request.user), slug=course_slug)
    lesson = get_object_or_404(course.published_lessons().prefetch_related("resources"), slug=lesson_slug)
    if not services.is_lesson_unlocked(request.user, lesson):
        if not request.user.is_authenticated:
            return redirect(f"{reverse('accounts:login')}?next={lesson.get_absolute_url()}")
        if services.get_enrollment(request.user, course) is None:
            messages.info(request, _("Darslarni ko'rish uchun avval kursga yoziling"))
        else:
            messages.error(request, _("Bu dars hali yopiq. Avval oldingi darsni tugating."))
        return redirect(course)

    progress = None
    submissions = []
    if request.user.is_authenticated:
        progress = lesson.progress.filter(user=request.user).first()
        submissions = HomeworkSubmission.objects.filter(user=request.user, lesson=lesson)
        Enrollment.objects.filter(user=request.user, course=course).update(last_lesson=lesson)
    next_lesson = lesson.next_lesson()
    return render(request, "education/lesson_detail.html", {
        "course": course,
        "lesson": lesson,
        "states": services.lesson_states(request.user, course),
        "progress": progress,
        "submissions": submissions,
        "homework_form": HomeworkForm(),
        "homework_ok": services.homework_satisfied(request.user, lesson) if request.user.is_authenticated else False,
        "prev_lesson": lesson.previous_lesson(),
        "next_lesson": next_lesson,
        "next_unlocked": next_lesson and services.is_lesson_unlocked(request.user, next_lesson),
        "course_progress": services.course_progress(request.user, course),
        "youtube_id": _youtube_id(lesson.video_url),
        "jsonld": seo.lesson_video(lesson, _youtube_id(lesson.video_url)) if lesson.is_preview and lesson.has_video else None,
    })


def _youtube_id(url):
    m = re.search(r"(?:v=|youtu\.be/|embed/|shorts/)([\w-]{11})", url or "")
    return m.group(1) if m else ""


def _lesson_for_media(request, course_slug, lesson_slug):
    lesson = get_object_or_404(Lesson.objects.select_related("course"), course__slug=course_slug, slug=lesson_slug, status="published")
    if lesson.course.status != "published" and not request.user.is_staff:
        raise Http404
    if not services.is_lesson_unlocked(request.user, lesson):
        raise Http404
    return lesson


def _serve_protected(request, fieldfile):
    """Himoyalangan faylni beradi. Prod'da Nginx X-Accel-Redirect, lokalda Range qo'llab-quvvatlanadigan oqim."""
    path = fieldfile.path
    if not os.path.exists(path):
        raise Http404
    content_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
    if getattr(settings, "USE_X_ACCEL_REDIRECT", False):
        resp = HttpResponse(content_type=content_type)
        resp["X-Accel-Redirect"] = "/protected/" + fieldfile.name
        resp["Cache-Control"] = "private, no-store"
        return resp

    size = os.path.getsize(path)
    range_header = request.META.get("HTTP_RANGE", "")
    m = re.match(r"bytes=(\d+)-(\d*)", range_header)
    if m:
        start = int(m.group(1))
        end = int(m.group(2)) if m.group(2) else min(start + 2 * 1024 * 1024, size) - 1
        end = min(end, size - 1)
        length = end - start + 1

        def chunks():
            with open(path, "rb") as f:
                f.seek(start)
                remaining = length
                while remaining > 0:
                    data = f.read(min(64 * 1024, remaining))
                    if not data:
                        break
                    remaining -= len(data)
                    yield data

        resp = StreamingHttpResponse(chunks(), status=206, content_type=content_type)
        resp["Content-Range"] = f"bytes {start}-{end}/{size}"
        resp["Content-Length"] = str(length)
    else:
        resp = FileResponse(open(path, "rb"), content_type=content_type)
        resp["Content-Length"] = str(size)
    resp["Accept-Ranges"] = "bytes"
    resp["Cache-Control"] = "private, no-store"
    return resp


def lesson_video(request, course_slug, lesson_slug):
    token = request.GET.get("t")
    if token:
        # Mini App: <video> sarlavha yubora olmaydi, shuning uchun qisqa muddatli imzolangan havola
        from apps.accounts.models import User
        from apps.miniapp.auth import unsign_video

        signed = unsign_video(token)
        lesson = get_object_or_404(Lesson.objects.select_related("course"), course__slug=course_slug, slug=lesson_slug, status="published")
        user = User.objects.filter(pk=signed[0]).first() if signed and signed[1] == lesson.pk else None
        if user is None or not services.is_lesson_unlocked(user, lesson) or not lesson.video:
            raise Http404
        return _serve_protected(request, lesson.video)
    lesson = _lesson_for_media(request, course_slug, lesson_slug)
    if not lesson.video:
        raise Http404
    return _serve_protected(request, lesson.video)


def resource_download(request, pk):
    res = get_object_or_404(LessonResource.objects.select_related("lesson__course"), pk=pk)
    lesson = _lesson_for_media(request, res.lesson.course.slug, res.lesson.slug)
    if not res.file or res.lesson_id != lesson.pk:
        raise Http404
    resp = _serve_protected(request, res.file)
    resp["Content-Disposition"] = f'attachment; filename="{os.path.basename(res.file.name)}"'
    return resp


@require_POST
def lesson_heartbeat(request, course_slug, lesson_slug):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)
    lesson = _lesson_for_media(request, course_slug, lesson_slug)
    try:
        data = json.loads(request.body or "{}")
        position, delta = float(data.get("position", 0)), float(data.get("delta", 0))
    except (ValueError, TypeError):
        return HttpResponse(status=400)
    progress = services.record_watch(request.user, lesson, position, delta)
    return _progress_json(request.user, lesson, progress)


@require_POST
def lesson_mark_watched(request, course_slug, lesson_slug):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)
    lesson = _lesson_for_media(request, course_slug, lesson_slug)
    if lesson.video:
        # Saytdagi videoni faqat haqiqiy ko'rish orqali tugatish mumkin
        return HttpResponseForbidden()
    progress = services.mark_video_completed(request.user, lesson)
    if request.htmx:
        resp = HttpResponse()
        resp["HX-Refresh"] = "true"
        return resp
    return _progress_json(request.user, lesson, progress)


def _progress_json(user, lesson, progress):
    from django.http import JsonResponse

    return JsonResponse({
        "video_completed": progress.video_completed,
        "completed": progress.is_completed,
        "watched": progress.watched_seconds,
        "course_progress": services.course_progress(user, lesson.course),
    })


@require_POST
def homework_submit(request, course_slug, lesson_slug):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)
    lesson = _lesson_for_media(request, course_slug, lesson_slug)
    if lesson.homework_mode == Lesson.HomeworkMode.NONE:
        raise Http404
    form = HomeworkForm(request.POST, request.FILES)
    if form.is_valid():
        sub = form.save(commit=False)
        sub.user = request.user
        sub.lesson = lesson
        sub.save()
        from apps.interactions.notify import notify_admins_homework

        notify_admins_homework(sub)
        services.try_complete(request.user, lesson)
        messages.success(request, _("Uyga vazifa topshirildi!"))
    else:
        messages.error(request, " ".join(e for errs in form.errors.values() for e in errs))
    return redirect(lesson.get_absolute_url() + "#homework")


@login_required
def my_courses(request):
    enrollments = Enrollment.objects.filter(user=request.user, is_active=True).select_related("course", "last_lesson")
    return render(request, "education/my_courses.html", {
        "items": [(e, services.course_progress(request.user, e.course)) for e in enrollments],
    })


def certificate(request, code):
    cert = get_object_or_404(Certificate.objects.select_related("enrollment__user", "enrollment__course"), code=code)
    return render(request, "education/certificate.html", {"cert": cert})

"""Telegram Mini App: mobil uchun alohida, yengil interfeys.

Sahifa qobig'i (`shell`) bir marta yuklanadi; qolgan barcha ekranlar HTMX orqali `#view` ga
`X-Telegram-Init-Data` sarlavhasi bilan yuklanadi (qarang: auth.TelegramWebAppMiddleware).
"""

import json
from functools import wraps

from django.conf import settings
from django.db.models import Count, Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.http import require_POST

from apps.blog.models import Article, ArticleCategory
from apps.core.models import Role
from apps.core.utils import count_view
from apps.education import services
from apps.education.forms import HomeworkForm
from apps.education.models import Course, Enrollment, HomeworkSubmission, Lesson
from apps.portfolio.models import Project, ProjectCategory

from .auth import sign_video


def tma(view):
    """Faqat Telegram imzosi tekshirilgan so'rovlar uchun."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not getattr(request, "tma", False):
            return HttpResponse(status=401)
        return view(request, *args, **kwargs)

    return wrapper


def registered(view):
    """Ro'yxatdan o'tmagan foydalanuvchiga ro'yxatdan o'tish ekranini ko'rsatadi."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_registered:
            return render(request, "miniapp/register.html")
        return view(request, *args, **kwargs)

    return tma(wrapper)


def _screen(request, template, ctx, title="", back=True):
    resp = render(request, template, ctx)
    resp["HX-Trigger-After-Swap"] = json.dumps({"tma:screen": {"title": str(title), "back": back}})
    return resp


# Telegram Web (web.telegram.org va boshqalar) Mini App'ni iframe ichida ochadi
FRAME_ANCESTORS = "frame-ancestors 'self' https://web.telegram.org https://webk.telegram.org https://webz.telegram.org https://*.telegram.org"


@xframe_options_exempt
def shell(request):
    resp = _shell(request)
    resp["Content-Security-Policy"] = FRAME_ANCESTORS
    return resp


def _shell(request):
    return render(request, "miniapp/shell.html", {
        "bot_username": settings.TELEGRAM_BOT_USERNAME,
        "debug_user": request.GET.get("debug_user", "") if settings.DEBUG else "",
    })


@tma
def me(request):
    u = request.user
    return JsonResponse({"registered": u.is_registered, "name": u.first_name, "language": u.language})


# --------------------------------------------------------------------------- Bosh ekran

@registered
def home(request):
    u = request.user
    enrollments = list(Enrollment.objects.filter(user=u, is_active=True).select_related("course", "last_lesson")[:3])
    learning = [(e, services.course_progress(u, e.course)) for e in enrollments]
    return _screen(request, "miniapp/home.html", {
        "learning": learning,
        "courses": Course.objects.for_user(request.user).annotate(n=Count("lessons", filter=Q(lessons__status="published")))[:6],
        "articles": Article.objects.published()[:4],
        "projects": Project.objects.published().filter(is_featured=True)[:4],
        "roles": Role.objects.filter(is_active=True),
    }, back=False)


# --------------------------------------------------------------------------- Kurslar

@registered
def courses(request):
    items = Course.objects.for_user(request.user).annotate(
        n=Count("lessons", filter=Q(lessons__status="published"), distinct=True),
        students=Count("enrollments", distinct=True),
    )
    enrolled = {e.course_id: e for e in Enrollment.objects.filter(user=request.user, is_active=True)}
    rows = [(c, c.pk in enrolled, services.course_progress(request.user, c) if c.pk in enrolled else 0) for c in items]
    return _screen(request, "miniapp/courses.html", {"rows": rows}, _("Kurslar"), back=False)


@registered
def course(request, slug):
    c = get_object_or_404(Course.objects.for_user(request.user), slug=slug)
    enrollment = services.get_enrollment(request.user, c)
    states = services.lesson_states(request.user, c)
    return _screen(request, "miniapp/course.html", {
        "course": c, "enrollment": enrollment, "states": states,
        "progress": services.course_progress(request.user, c) if enrollment else 0,
        "completed": sum(1 for _l, s in states if s == "completed"),
        "next_lesson": next((l for l, s in states if s in ("current", "unlocked")), None),
        **_purchase_context(request.user, c, enrollment),
    }, c.title)


def _purchase_context(user, c, enrollment):
    """Pullik kurs uchun: narx, so'rov holati va Telegram'ga tayyor xabarli havola."""
    if c.is_free or enrollment:
        return {}
    from apps.core.models import SiteSettings
    from apps.education.models import AccessRequest
    from apps.education.views import _payment_link

    site = SiteSettings.load()
    req = AccessRequest.objects.filter(user=user, course=c).order_by("-created_at").first()
    return {"access_request": req, "payment_link": _payment_link(site, c, req, user), "payment_note": site.payment_note}


@registered
@require_POST
def buy(request, slug):
    c = get_object_or_404(Course.objects.for_user(request.user), slug=slug)
    if not c.is_free:
        services.request_access(request.user, c, request.POST.get("note", "").strip())
    return course(request, slug)


@registered
@require_POST
def enroll(request, slug):
    c = get_object_or_404(Course.objects.for_user(request.user), slug=slug)
    if not c.is_free and not request.user.is_staff:
        return HttpResponse(status=403)
    Enrollment.objects.get_or_create(user=request.user, course=c)
    return course(request, slug)


@registered
def lesson(request, course_slug, lesson_slug):
    c = get_object_or_404(Course.objects.for_user(request.user), slug=course_slug)
    lsn = get_object_or_404(c.published_lessons().prefetch_related("resources"), slug=lesson_slug)
    if not services.is_lesson_unlocked(request.user, lsn):
        return _screen(request, "miniapp/locked.html", {"course": c, "lesson": lsn}, lsn.title)
    from apps.education.views import _youtube_id

    progress = lsn.progress.filter(user=request.user).first()
    Enrollment.objects.filter(user=request.user, course=c).update(last_lesson=lsn)
    nxt = lsn.next_lesson()
    video_src = ""
    if lsn.video:
        video_src = reverse("education:lesson_video", args=[c.slug, lsn.slug]) + "?t=" + sign_video(request.user.pk, lsn.pk)
    return _screen(request, "miniapp/lesson.html", {
        "course": c, "lesson": lsn, "progress": progress, "video_src": video_src,
        "youtube_id": _youtube_id(lsn.video_url),
        "submissions": HomeworkSubmission.objects.filter(user=request.user, lesson=lsn),
        "homework_ok": services.homework_satisfied(request.user, lsn),
        "next_lesson": nxt,
        "next_unlocked": nxt and services.is_lesson_unlocked(request.user, nxt),
        "prev_lesson": lsn.previous_lesson(),
    }, f"{lsn.order}. {lsn.title}")


def _lesson_or_404(request, course_slug, lesson_slug):
    lsn = get_object_or_404(Lesson.objects.select_related("course"), course__slug=course_slug, slug=lesson_slug, status="published")
    if not services.is_lesson_unlocked(request.user, lsn):
        raise Http404
    return lsn


@registered
@require_POST
def heartbeat(request, course_slug, lesson_slug):
    lsn = _lesson_or_404(request, course_slug, lesson_slug)
    try:
        data = json.loads(request.body or "{}")
        p = services.record_watch(request.user, lsn, float(data.get("position", 0)), float(data.get("delta", 0)))
    except (ValueError, TypeError):
        return HttpResponse(status=400)
    return JsonResponse({"video_completed": p.video_completed, "completed": p.is_completed,
                         "course_progress": services.course_progress(request.user, lsn.course)})


@registered
@require_POST
def watched(request, course_slug, lesson_slug):
    lsn = _lesson_or_404(request, course_slug, lesson_slug)
    if not lsn.video:
        services.mark_video_completed(request.user, lsn)
    return lesson(request, course_slug, lesson_slug)


@registered
@require_POST
def homework(request, course_slug, lesson_slug):
    lsn = _lesson_or_404(request, course_slug, lesson_slug)
    form = HomeworkForm(request.POST, request.FILES)
    if lsn.homework_mode != "none" and form.is_valid():
        sub = form.save(commit=False)
        sub.user, sub.lesson = request.user, lsn
        sub.save()
        from apps.interactions.notify import notify_admins_homework

        notify_admins_homework(sub)
        services.try_complete(request.user, lsn)
    resp = lesson(request, course_slug, lesson_slug)
    resp["HX-Trigger"] = json.dumps({"tma:toast": _("Uyga vazifa topshirildi!") if form.is_valid() else " ".join(
        e for errs in form.errors.values() for e in errs)})
    return resp


# --------------------------------------------------------------------------- Journal va loyihalar

@registered
def journal(request):
    cat = request.GET.get("category", "")
    items = Article.objects.published().select_related("category")
    if cat:
        items = items.filter(category__slug=cat)
    return _screen(request, "miniapp/journal.html", {
        "items": items[:30], "categories": ArticleCategory.objects.filter(articles__status="published").distinct(), "active": cat,
    }, "Blog", back=False)


@registered
def article(request, slug):
    a = get_object_or_404(Article.objects.published().prefetch_related("tags"), slug=slug)
    count_view(request, a)
    return _screen(request, "miniapp/article.html", {"article": a, "site_url": settings.SITE_URL + a.get_absolute_url()}, a.title)


@registered
def projects(request):
    cat = request.GET.get("category", "")
    items = Project.objects.published().select_related("category")
    if cat:
        items = items.filter(category__slug=cat)
    return _screen(request, "miniapp/projects.html", {
        "items": items, "categories": ProjectCategory.objects.filter(projects__status="published").distinct(), "active": cat,
    }, _("Loyihalar"), back=False)


@registered
def project(request, slug):
    p = get_object_or_404(Project.objects.published().prefetch_related("tech_stack", "images", "features"), slug=slug)
    count_view(request, p)
    return _screen(request, "miniapp/project.html", {"project": p, "site_url": settings.SITE_URL + p.get_absolute_url()}, p.title)


# --------------------------------------------------------------------------- Profil

@registered
def profile(request):
    u = request.user
    enrollments = Enrollment.objects.filter(user=u, is_active=True).select_related("course", "last_lesson")
    from apps.education.models import AccessRequest

    return _screen(request, "miniapp/profile.html", {
        "items": [(e, services.course_progress(u, e.course)) for e in enrollments],
        "requests": AccessRequest.objects.filter(user=u).select_related("course").order_by("-created_at")[:10],
        "certificates": [e.certificate for e in enrollments if e.completed_at and hasattr(e, "certificate")],
        "languages": settings.LANGUAGES,
    }, _("Profil"), back=False)


@tma
@require_POST
def set_language(request):
    lang = request.POST.get("lang")
    if lang in dict(settings.LANGUAGES):
        type(request.user).objects.filter(pk=request.user.pk).update(language=lang)
    resp = HttpResponse()
    resp["HX-Redirect"] = f"/{lang}/app/"
    return resp


def preview(request):
    """Faqat lokal muhit: Mini App'ni telefon ramkasida ko'rish (Chrome orqali kuzatish uchun)."""
    if not settings.DEBUG:
        raise Http404
    return render(request, "miniapp/preview.html", {
        "lang": request.GET.get("lang", "uz") if request.GET.get("lang") in ("uz", "ru", "en") else "uz",
        "debug_user": request.GET.get("user", "900001"),
        # ?path=/uz/projects/ — saytning istalgan sahifasini telefon o'lchamida tekshirish
        "path": request.GET.get("path", "") if request.GET.get("path", "").startswith("/") else "",
    })

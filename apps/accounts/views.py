import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.core.utils import client_ip

from .forms import ProfileForm
from .models import LoginCode, LoginRequest

BACKEND = "django.contrib.auth.backends.ModelBackend"
RATE_LIMIT = 10  # IP bo'yicha 10 daqiqada kod kiritish urinishlari


def _safe_next(request, default=None):
    nxt = request.POST.get("next") or request.GET.get("next") or request.session.get("login_next")
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return nxt
    return default or reverse("core:home")


def _current_login_request(request):
    token = request.session.get("login_token")
    if not token:
        return None
    return LoginRequest.objects.filter(token=token, session_key=request.session.session_key).first()


def _finish_login(request, user, login_request=None):
    if login_request:
        LoginRequest.objects.filter(pk=login_request.pk).update(status=LoginRequest.Status.USED)
    nxt = _safe_next(request)
    login(request, user, backend=BACKEND)
    request.session.pop("login_token", None)
    request.session.pop("login_next", None)
    return nxt


def login_view(request):
    if request.user.is_authenticated:
        return redirect(_safe_next(request))
    if not request.session.session_key:
        request.session.save()
    if request.GET.get("next"):
        request.session["login_next"] = _safe_next(request)

    login_request = _current_login_request(request)
    if login_request is None or login_request.is_expired or login_request.status != LoginRequest.Status.PENDING:
        login_request = LoginRequest.objects.create(
            session_key=request.session.session_key,
            ip_address=client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:255],
        )
        request.session["login_token"] = str(login_request.token)

    deep_link = f"https://t.me/{settings.TELEGRAM_BOT_USERNAME}?start=login_{login_request.token.hex}"
    return render(request, "accounts/login.html", {
        "deep_link": deep_link,
        "login_request": login_request,
        "next": _safe_next(request),
        "code_ttl": settings.LOGIN_CODE_TTL_SECONDS,
    })


def login_status(request):
    """HTMX har 2 soniyada so'raydi: bot orqali tasdiqlangan bo'lsa, shu brauzer avtomatik kiradi."""
    login_request = _current_login_request(request)
    if login_request is None:
        return HttpResponse(status=204)
    if login_request.status == LoginRequest.Status.CONFIRMED and login_request.user and not login_request.is_expired:
        if login_request.user.is_blocked or not login_request.user.is_active:
            return HttpResponse(status=204)
        nxt = _finish_login(request, login_request.user, login_request)
        resp = HttpResponse()
        resp["HX-Redirect"] = nxt
        return resp
    if login_request.status == LoginRequest.Status.REJECTED:
        # Toast bir marta ko'rinsin: keyingi so'rovlar uchun bu urinish yopiladi
        request.session.pop("login_token", None)
        resp = HttpResponse()
        resp["HX-Trigger"] = json.dumps({"toast": {"value": _("Kirish botda rad etildi"), "kind": "error"}})
        return resp
    return HttpResponse(status=204)


@require_POST
def verify_code(request):
    ip = client_ip(request) or "unknown"
    key = f"login-attempts:{ip}"
    attempts = cache.get(key, 0)
    if attempts >= RATE_LIMIT:
        return _code_error(request, _("Urinishlar soni ko'p. 10 daqiqadan keyin qayta urinib ko'ring."))
    cache.set(key, attempts + 1, 600)

    code = "".join(ch for ch in request.POST.get("code", "") if ch.isdigit())
    if len(code) != 6:
        return _code_error(request, _("6 xonali kodni kiriting"))

    with transaction.atomic():
        login_code = (
            LoginCode.objects.select_for_update().select_related("user")
            .filter(code=code, is_used=False).order_by("-created_at").first()
        )
        if login_code is None or not login_code.is_valid:
            if login_code:
                login_code.attempts += 1
                login_code.save(update_fields=["attempts"])
            return _code_error(request, _("Kod noto'g'ri yoki muddati o'tgan. Botdan yangi kod oling."))
        user = login_code.user
        if user.is_blocked or not user.is_active:
            return _code_error(request, _("Hisobingiz bloklangan. Admin bilan bog'laning."))
        login_code.is_used = True
        login_code.save(update_fields=["is_used"])

    cache.delete(key)
    nxt = _finish_login(request, user, _current_login_request(request))
    if request.htmx:
        resp = HttpResponse()
        resp["HX-Redirect"] = nxt
        return resp
    return redirect(nxt)


def _code_error(request, message):
    if request.htmx:
        return render(request, "accounts/partials/code_error.html", {"error": message})
    messages.error(request, message)
    return redirect("accounts:login")


@require_POST
def logout_view(request):
    logout(request)
    return redirect("core:home")


@login_required
def profile(request):
    from django.contrib.contenttypes.models import ContentType

    from apps.blog.models import Article
    from apps.education.models import Certificate, Enrollment, LessonProgress
    from apps.education.services import course_progress
    from apps.gallery.models import Photo
    from apps.interactions.models import Comment, Reaction
    from apps.portfolio.models import Project

    tab = request.GET.get("tab", "overview")
    u = request.user
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=u)
        if form.is_valid():
            form.save()
            messages.success(request, _("Profil saqlandi"))
            return redirect(f"{request.path}?tab=settings")
        tab = "settings"
    else:
        form = ProfileForm(instance=u)

    enrollments = Enrollment.objects.filter(user=u, is_active=True).select_related("course", "last_lesson")
    courses = [(e, course_progress(u, e.course)) for e in enrollments]

    # Saqlanganlar: turli modellardagi bookmark'lar
    saved = []
    bookmarks = Reaction.objects.filter(user=u, kind=Reaction.Kind.BOOKMARK).select_related("content_type").order_by("-created_at")
    models = {ContentType.objects.get_for_model(m).pk: (m, label, icon) for m, label, icon in (
        (Project, _("Loyiha"), "folder"), (Article, _("Maqola"), "file-text"), (Photo, _("Foto"), "image"))}
    for b in bookmarks:
        model, label, icon = models.get(b.content_type_id, (None, "", ""))
        obj = model.objects.filter(pk=b.object_id).first() if model else None
        if obj:
            saved.append({"obj": obj, "label": label, "icon": icon, "at": b.created_at,
                          "image": getattr(obj, "cover", None) or getattr(obj, "image", None)})

    completed_lessons = LessonProgress.objects.filter(user=u, completed_at__isnull=False)
    from apps.education.models import AccessRequest, Course

    n_lessons = completed_lessons.count()
    n_certs = Certificate.objects.filter(enrollment__user=u).count()
    n_comments = Comment.objects.filter(user=u).count()
    level = _level(n_lessons * 10 + n_certs * 150 + n_comments * 3 + len(saved))
    owned = [e.course_id for e, _p in courses]
    return render(request, "accounts/profile.html", {
        "level": level,
        "achievements": (ach := _achievements(n_lessons, n_certs, n_comments, len(saved), len(courses))),
        "achievements_done": sum(1 for a in ach if a["done"]),
        "access_requests": AccessRequest.objects.filter(user=u).select_related("course").order_by("-created_at")[:20],
        "paid_enrollments": [(e, p) for e, p in courses if not e.course.is_free or e.course.is_private],
        "recommended": Course.objects.for_user(u).exclude(pk__in=owned).order_by("-is_featured", "order")[:3],
        "tab": tab, "form": form, "courses": courses, "saved": saved,
        "certificates": Certificate.objects.filter(enrollment__user=u).select_related("enrollment__course"),
        "comments": Comment.objects.filter(user=u).select_related("content_type")[:20],
        "recent_lessons": completed_lessons.select_related("lesson__course").order_by("-completed_at")[:6],
        "stats": {
            "courses": len(courses),
            "lessons": n_lessons,
            "certificates": n_certs,
            "comments": n_comments,
            "saved": len(saved),
            "likes": Reaction.objects.filter(user=u, kind=Reaction.Kind.LIKE).count(),
        },
    })


LEVELS = [0, 50, 150, 300, 500, 800, 1200, 1700, 2300, 3000]


def _level(xp):
    """XP -> daraja va keyingi darajagacha progress."""
    n = sum(1 for t in LEVELS if xp >= t)
    lo = LEVELS[n - 1]
    hi = LEVELS[n] if n < len(LEVELS) else lo + 1000
    return {"n": n, "xp": xp, "next": hi, "pct": min(100, round((xp - lo) * 100 / (hi - lo)))}


def _achievements(lessons, certs, comments, saved, courses):
    return [
        {"icon": "footprints", "title": _("Birinchi qadam"), "hint": _("Birinchi darsni tugating"), "done": lessons >= 1},
        {"icon": "flame", "title": _("Qizg'in o'quvchi"), "hint": _("10 ta dars tugating"), "done": lessons >= 10},
        {"icon": "rocket", "title": _("Marafonchi"), "hint": _("50 ta dars tugating"), "done": lessons >= 50},
        {"icon": "award", "title": _("Sertifikat"), "hint": _("Birinchi kursni tugating"), "done": certs >= 1},
        {"icon": "layers", "title": _("Ko'p qirrali"), "hint": _("3 ta kursga yoziling"), "done": courses >= 3},
        {"icon": "message-circle", "title": _("Faol a'zo"), "hint": _("5 ta izoh qoldiring"), "done": comments >= 5},
        {"icon": "bookmark", "title": _("Kolleksioner"), "hint": _("5 ta narsani saqlang"), "done": saved >= 5},
    ]

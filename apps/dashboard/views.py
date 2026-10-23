"""WeliCoDev dashboard: dizayn bo'yicha maxsus boshqaruv paneli (faqat staff uchun).

Murakkab bo'lmagan modellarni tahrirlash Unfold admin orqali; asosiy ish oqimlari shu yerda.
"""

import shutil
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db import connection
from django.db.models import Count, Max, Q, Sum
from django.db.models.functions import TruncDate
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.accounts.models import User
from apps.blog.models import Article, ArticleCategory
from apps.core.charts import donut
from apps.core.models import SiteSettings, SocialLink
from apps.education.models import AccessRequest, Course, Enrollment, HomeworkSubmission, LessonProgress
from apps.education import services as edu
from apps.interactions.analytics import series
from apps.interactions.models import Comment, ContactMessage, Reaction, Review
from apps.portfolio.models import Project, ProjectCategory
from apps.telegram_bot.models import BotEvent, BotMessage, BotSettings, Broadcast

from .forms import (
    ArticleForm, BotSettingsForm, BroadcastForm, ProjectForm, ReplyForm, SiteSettingsForm, SocialLinkFormSet,
)

def staff(view):
    """Dashboard faqat staff uchun. Kirmaganlar Telegram login'ga, oddiy foydalanuvchilar 404 ga (panel borligi oshkor qilinmaydi)."""
    from functools import wraps

    from django.contrib.auth.views import redirect_to_login
    from django.http import Http404

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), reverse("accounts:login"))
        if not (request.user.is_active and request.user.is_staff):
            raise Http404
        return view(request, *args, **kwargs)

    return wrapper


def _pct_change(current, previous):
    if not previous:
        return 100 if current else 0
    return round((current - previous) * 100 / previous)


def _kpi(model, date_field="created_at", qs=None):
    qs = qs if qs is not None else model.objects.all()
    now = timezone.now()
    this = qs.filter(**{f"{date_field}__gte": now - timedelta(days=30)}).count()
    prev = qs.filter(**{f"{date_field}__gte": now - timedelta(days=60), f"{date_field}__lt": now - timedelta(days=30)}).count()
    return {"total": qs.count(), "month": this, "change": _pct_change(this, prev)}


def _daily(qs, field, start):
    rows = qs.filter(**{f"{field}__date__gte": start}).annotate(d=TruncDate(field)).values("d").annotate(n=Count("id"))
    return {r["d"]: r["n"] for r in rows}


def badges():
    """Yon menyu va qo'ng'iroqcha uchun kutilayotgan ishlar soni."""
    data = cache.get("dash:badges")
    if data is None:
        data = {
            "messages": ContactMessage.objects.filter(status="new").count()
            + BotMessage.objects.filter(direction="in", is_read=False).count(),
            "reviews": Review.objects.filter(is_approved=False).count(),
            "homework": HomeworkSubmission.objects.filter(status="pending").count(),
            "access": AccessRequest.objects.filter(status="pending").count(),
        }
        data["total"] = sum(data.values())
        cache.set("dash:badges", data, 30)
    return data


def _render(request, template, ctx=None):
    ctx = ctx or {}
    ctx["badges"] = badges()
    ctx["bot_ok"] = bool(settings.TELEGRAM_BOT_TOKEN)
    return render(request, template, ctx)


# --------------------------------------------------------------------------- Bosh sahifa

@staff
def home(request):
    days = int(request.GET.get("days", 30)) if request.GET.get("days") in ("7", "30", "90") else 30
    start = timezone.localdate() - timedelta(days=days - 1)
    visits = series(days)
    new_users = _daily(User.objects.all(), "date_joined", start)
    new_comments = _daily(Comment.objects.all(), "created_at", start)
    chart = {
        "labels": [d.strftime("%b %d") for d, _v in visits],
        "views": [v.views if v else 0 for _d, v in visits],
        "visitors": [v.unique_visitors if v else 0 for _d, v in visits],
        "users": [new_users.get(d, 0) for d, _v in visits],
        "comments": [new_comments.get(d, 0) for d, _v in visits],
    }
    langs = dict(User.objects.filter(is_staff=False).values_list("language").annotate(n=Count("id")))
    lang_donut = donut([("O'zbekcha", langs.get("uz", 0)), ("Русский", langs.get("ru", 0)), ("English", langs.get("en", 0))])

    activity = []
    for u in User.objects.filter(is_staff=False).order_by("-date_joined")[:4]:
        activity.append((u.date_joined, "user-plus", "info", _("Yangi foydalanuvchi"), u.display_name))
    for c in Comment.objects.select_related("user").order_by("-created_at")[:4]:
        activity.append((c.created_at, "message-circle", "violet", _("Yangi izoh"), f"{c.user.display_name}: {c.body[:50]}"))
    for r in Review.objects.select_related("user").order_by("-created_at")[:3]:
        activity.append((r.created_at, "star", "warn", _("Yangi sharh"), f"{'★' * r.rating} {r.user.display_name}"))
    for s in HomeworkSubmission.objects.select_related("user", "lesson").order_by("-created_at")[:3]:
        activity.append((s.created_at, "clipboard-check", "ok", _("Uyga vazifa"), f"{s.user.display_name} · {s.lesson.title}"))
    activity.sort(key=lambda a: a[0], reverse=True)

    disk = shutil.disk_usage(settings.MEDIA_ROOT if settings.MEDIA_ROOT.exists() else settings.BASE_DIR)
    return _render(request, "dashboard/home.html", {
        "days": days,
        "kpi_users": _kpi(User, "date_joined", User.objects.filter(is_staff=False)),
        "kpi_projects": _kpi(Project),
        "kpi_articles": _kpi(Article),
        "kpi_reviews": _kpi(Review),
        "kpi_students": _kpi(Enrollment),
        "chart": chart,
        "lang_donut": lang_donut,
        "lang_total": sum(langs.values()),
        "recent_users": User.objects.filter(is_staff=False).order_by("-date_joined")[:5],
        "activity": activity[:6],
        "system": _system_status(),
        "storage": {"used": disk.used, "total": disk.total, "pct": round(disk.used * 100 / disk.total)},
        "sessions": Session.objects.filter(expire_date__gt=timezone.now()).count(),
        "today_views": visits[-1][1].views if visits and visits[-1][1] else 0,
    })


def _system_status():
    checks = {}
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
        checks["db"] = True
    except Exception:  # noqa: BLE001
        checks["db"] = False
    try:
        cache.set("dash:ping", 1, 5)
        checks["redis"] = cache.get("dash:ping") == 1
    except Exception:  # noqa: BLE001
        checks["redis"] = False
    checks["bot"] = bool(settings.TELEGRAM_BOT_TOKEN)
    checks["ok"] = checks["db"] and checks["redis"]
    return checks


# --------------------------------------------------------------------------- Foydalanuvchilar

@staff
def users(request):
    qs = User.objects.annotate(
        n_courses=Count("enrollments", distinct=True), n_comments=Count("comments", distinct=True),
    ).order_by("-date_joined")
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    if q:
        qs = qs.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(phone__icontains=q) | Q(telegram_username__icontains=q))
    if status == "staff":
        qs = qs.filter(is_staff=True)
    elif status == "blocked":
        qs = qs.filter(is_blocked=True)
    elif status == "incomplete":
        qs = qs.filter(is_registered=False, is_staff=False)
    elif status == "active":
        qs = qs.filter(is_registered=True, is_blocked=False)
    page = Paginator(qs, 20).get_page(request.GET.get("page"))
    selected = None
    if request.GET.get("user"):
        selected = User.objects.filter(pk=request.GET["user"]).first()
    ctx = {
        "page": page, "q": q, "status": status, "selected": selected,
        "stats": {
            "total": User.objects.filter(is_staff=False).count(),
            "registered": User.objects.filter(is_registered=True, is_staff=False).count(),
            "bot_active": User.objects.filter(telegram_id__isnull=False, bot_blocked=False).count(),
            "blocked": User.objects.filter(is_blocked=True).count(),
        },
    }
    if selected:
        ctx["selected_courses"] = [(e, edu.course_progress(selected, e.course)) for e in Enrollment.objects.filter(user=selected).select_related("course")]
        ctx["selected_comments"] = Comment.objects.filter(user=selected)[:5]
        ctx["reply_form"] = ReplyForm()
    if request.htmx and request.htmx.target == "user-panel":
        return _render(request, "dashboard/partials/user_panel.html", ctx)
    return _render(request, "dashboard/users.html", ctx)


@staff
@require_POST
def user_toggle_block(request, pk):
    user = get_object_or_404(User, pk=pk, is_superuser=False)
    user.is_blocked = not user.is_blocked
    user.save(update_fields=["is_blocked"])
    messages.success(request, _("Foydalanuvchi bloklandi") if user.is_blocked else _("Blok olib tashlandi"))
    return redirect(f"{reverse('dashboard:users')}?user={pk}")


@staff
@require_POST
def user_message(request, pk):
    """Foydalanuvchiga bot orqali shaxsiy xabar yuborish."""
    from apps.telegram_bot.tasks import send_to_user

    user = get_object_or_404(User, pk=pk, telegram_id__isnull=False)
    form = ReplyForm(request.POST)
    if not settings.TELEGRAM_BOT_TOKEN:
        messages.error(request, _("Bot tokeni sozlanmagan (.env → TELEGRAM_BOT_TOKEN)"))
    elif form.is_valid():
        send_to_user.delay(user.pk, form.cleaned_data["text"], sent_by_id=request.user.pk)
        BotMessage.objects.filter(user=user, direction="in", is_read=False).update(is_read=True)
        messages.success(request, _("Xabar navbatga qo'yildi"))
    nxt = request.POST.get("next")
    return redirect(nxt if nxt and nxt.startswith("/") else f"{reverse('dashboard:users')}?user={pk}")


# --------------------------------------------------------------------------- Loyihalar

@staff
def projects(request):
    qs = Project.objects.select_related("category").prefetch_related("tags").order_by("-updated_at")
    q, status, cat = request.GET.get("q", "").strip(), request.GET.get("status", ""), request.GET.get("category", "")
    sort = request.GET.get("sort", "new")
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(short_description__icontains=q))
    if status == "featured":
        qs = qs.filter(is_featured=True)
    elif status:
        qs = qs.filter(status=status)
    if cat:
        qs = qs.filter(category__slug=cat)
    qs = qs.order_by({"views": "-views_count", "old": "updated_at", "title": "title"}.get(sort, "-updated_at"))
    from apps.interactions.services import annotate_stats

    page = Paginator(annotate_stats(qs), 9).get_page(request.GET.get("page"))
    selected = Project.objects.filter(pk=request.GET.get("project")).first() if request.GET.get("project") else (page.object_list[0] if page.object_list else None)
    all_p = Project.objects.all()
    total = all_p.count() or 1
    ctx = {
        "page": page, "q": q, "status": status, "category": cat, "sort": sort, "view": request.GET.get("view", "grid"),
        "categories": ProjectCategory.objects.all(), "selected": selected,
        "stats": {
            "total": _kpi(Project),
            "published": all_p.filter(status="published").count(),
            "drafts": all_p.filter(status="draft").count(),
            "featured": all_p.filter(is_featured=True).count(),
            "total_n": total,
        },
    }
    if selected:
        ct_filter = {"content_type__model": "project", "object_id": selected.pk}
        ctx["sel_stats"] = {
            "likes": Reaction.objects.filter(kind="like", **ct_filter).count(),
            "comments": Comment.objects.filter(**ct_filter).count(),
        }
    if request.htmx and request.htmx.target == "project-panel":
        return _render(request, "dashboard/partials/project_panel.html", ctx)
    return _render(request, "dashboard/projects.html", ctx)


@staff
def project_form(request, pk=None):
    project = get_object_or_404(Project, pk=pk) if pk else None
    form = ProjectForm(request.POST or None, request.FILES or None, instance=project)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.status = "draft" if "draft" in request.POST else "published"
        obj.save()
        form.save_m2m()
        for f in request.FILES.getlist("gallery"):
            obj.images.create(image=f, order=obj.images.count())
        for img_id in request.POST.getlist("remove_image"):
            obj.images.filter(pk=img_id).delete()
        messages.success(request, _("Loyiha saqlandi") if pk else _("Loyiha yaratildi"))
        return redirect("dashboard:project_edit", pk=obj.pk)
    return _render(request, "dashboard/project_form.html", {"form": form, "project": project, "langs": settings.LANGUAGES})


@staff
@require_POST
def project_action(request, pk, action):
    p = get_object_or_404(Project, pk=pk)
    if action == "delete":
        p.delete()
        messages.success(request, _("Loyiha o'chirildi"))
        return redirect("dashboard:projects")
    if action == "toggle_publish":
        p.status = "draft" if p.status == "published" else "published"
    elif action == "toggle_featured":
        p.is_featured = not p.is_featured
    p.save()
    return redirect(f"{reverse('dashboard:projects')}?project={pk}")


# --------------------------------------------------------------------------- Maqolalar

@staff
def articles(request):
    qs = Article.objects.select_related("category", "author").order_by("-published_at")
    q, status, cat, author = (request.GET.get(k, "").strip() for k in ("q", "status", "category", "author"))
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(excerpt__icontains=q))
    if status:
        qs = qs.filter(status=status)
    if cat:
        qs = qs.filter(category__slug=cat)
    if author:
        qs = qs.filter(author_id=author)
    page = Paginator(qs, 10).get_page(request.GET.get("page"))
    all_a = Article.objects.all()
    n = all_a.count() or 1
    return _render(request, "dashboard/articles.html", {
        "page": page, "q": q, "status": status, "category": cat, "author": author,
        "categories": ArticleCategory.objects.annotate(n=Count("articles")).order_by("-n"),
        "authors": User.objects.filter(articles__isnull=False).distinct(),
        "stats": {
            "total": _kpi(Article),
            "published": all_a.filter(status="published").count(),
            "drafts": all_a.filter(status="draft").count(),
            "archived": all_a.filter(status="archived").count(),
            "n": n,
        },
    })


@staff
def article_form(request, pk=None):
    article = get_object_or_404(Article, pk=pk) if pk else None
    form = ArticleForm(request.POST or None, request.FILES or None, instance=article)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        if not obj.author_id:
            obj.author = request.user
        if "draft" in request.POST:
            obj.status = "draft"
        obj.save()
        form.save_m2m()
        messages.success(request, _("Maqola saqlandi"))
        return redirect("dashboard:article_edit", pk=obj.pk)
    from apps.core.seo_audit import audit_article

    return _render(request, "dashboard/article_form.html", {
        "form": form, "article": article, "langs": settings.LANGUAGES,
        "seo": audit_article(article) if article else None,
    })


@staff
@require_POST
def article_delete(request, pk):
    get_object_or_404(Article, pk=pk).delete()
    messages.success(request, _("Maqola o'chirildi"))
    return redirect("dashboard:articles")


# --------------------------------------------------------------------------- Kurslar va vazifalar

@staff
def courses(request):
    items = Course.objects.annotate(
        n_lessons=Count("lessons", distinct=True), n_students=Count("enrollments", distinct=True),
        n_done=Count("enrollments", filter=Q(enrollments__completed_at__isnull=False), distinct=True),
    ).order_by("order", "-created_at")
    return _render(request, "dashboard/courses.html", {
        "items": items,
        "pending": HomeworkSubmission.objects.filter(status="pending").count(),
        "students": Enrollment.objects.values("user").distinct().count(),
        "completed_lessons": LessonProgress.objects.filter(completed_at__isnull=False).count(),
    })


@staff
def homework(request):
    status = request.GET.get("status", "pending")
    qs = HomeworkSubmission.objects.select_related("user", "lesson__course").order_by("-created_at")
    if status:
        qs = qs.filter(status=status)
    page = Paginator(qs, 15).get_page(request.GET.get("page"))
    return _render(request, "dashboard/homework.html", {"page": page, "status": status, "statuses": HomeworkSubmission.Status.choices})


@staff
@require_POST
def homework_review(request, pk):
    from apps.telegram_bot.tasks import send_to_user

    sub = get_object_or_404(HomeworkSubmission.objects.select_related("user", "lesson__course"), pk=pk)
    status = request.POST.get("status")
    if status not in ("approved", "rejected"):
        return HttpResponse(status=400)
    sub.mark_reviewed(status, request.POST.get("feedback", "").strip())
    edu.try_complete(sub.user, sub.lesson)
    with translation.override(sub.user.language or "uz"):
        verdict = "✅ qabul qilindi" if status == "approved" else "🔁 qayta ishlash kerak"
        text = f"📝 <b>{sub.lesson.title}</b> — uyga vazifangiz {verdict}."
        if sub.feedback:
            text += f"\n\n💬 {sub.feedback}"
        send_to_user.delay(sub.user_id, text, "Darsni ochish", settings.SITE_URL + sub.lesson.get_absolute_url())
    cache.delete("dash:badges")
    if request.htmx:
        return render(request, "dashboard/partials/homework_row.html", {"s": sub})
    return redirect("dashboard:homework")


# --------------------------------------------------------------------------- Izohlar va sharhlar

@staff
def comments(request):
    tab = request.GET.get("tab", "comments")
    if tab == "reviews":
        qs = Review.objects.select_related("user", "content_type").order_by("is_approved", "-created_at")
    else:
        qs = Comment.objects.select_related("user", "content_type").order_by("-created_at")
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(body__icontains=q)
    page = Paginator(qs, 15).get_page(request.GET.get("page"))
    return _render(request, "dashboard/comments.html", {"page": page, "tab": tab, "q": q})


@staff
@require_POST
def moderate(request, kind, pk, action):
    model = Review if kind == "review" else Comment
    obj = get_object_or_404(model, pk=pk)
    if action == "delete":
        obj.delete()
        cache.delete("dash:badges")
        return HttpResponse("")
    if action == "approve":
        obj.is_approved = True
    elif action == "hide":
        obj.is_approved = False
    elif action == "pin" and kind == "comment":
        obj.is_pinned = not obj.is_pinned
    obj.save()
    cache.delete("dash:badges")
    return render(request, "dashboard/partials/moderation_row.html", {"o": obj, "tab": "reviews" if kind == "review" else "comments"})


# --------------------------------------------------------------------------- Xabarlar (sayt + bot)

@staff
def inbox(request):
    tab = request.GET.get("tab", "bot")
    ctx = {"tab": tab}
    if tab == "site":
        qs = ContactMessage.objects.order_by("-created_at")
        ctx["page"] = Paginator(qs, 15).get_page(request.GET.get("page"))
        if request.GET.get("open"):
            msg = get_object_or_404(ContactMessage, pk=request.GET["open"])
            if msg.status == "new":
                msg.status = "read"
                msg.save(update_fields=["status"])
                cache.delete("dash:badges")
            ctx["opened"] = msg
    else:
        # Har bir foydalanuvchi bo'yicha oxirgi xabar (suhbatlar ro'yxati)
        users = (
            User.objects.filter(bot_messages__isnull=False)
            .annotate(unread=Count("bot_messages", filter=Q(bot_messages__direction="in", bot_messages__is_read=False)),
                      last=Max("bot_messages__created_at"))
            .order_by("-last")
        )
        ctx["threads"] = users[:50]
        chat_user = User.objects.filter(pk=request.GET.get("chat")).first() if request.GET.get("chat") else (users[0] if users else None)
        if chat_user:
            BotMessage.objects.filter(user=chat_user, direction="in", is_read=False).update(is_read=True)
            cache.delete("dash:badges")
            ctx["chat_user"] = chat_user
            ctx["chat"] = BotMessage.objects.filter(user=chat_user).select_related("sent_by").order_by("created_at")[:200]
            ctx["reply_form"] = ReplyForm()
    return _render(request, "dashboard/inbox.html", ctx)


@staff
@require_POST
def contact_status(request, pk):
    msg = get_object_or_404(ContactMessage, pk=pk)
    status = request.POST.get("status")
    if status in ContactMessage.Status.values:
        msg.status = status
        msg.save(update_fields=["status"])
    return redirect(f"{reverse('dashboard:inbox')}?tab=site&open={pk}")


# --------------------------------------------------------------------------- Telegram bot

@staff
def bot(request):
    since = timezone.now() - timedelta(days=30)
    start = timezone.localdate() - timedelta(days=13)
    events = BotEvent.objects.filter(created_at__gte=since)
    by_kind = dict(events.values_list("kind").annotate(n=Count("id")))
    daily_starts = _daily(BotEvent.objects.filter(kind="start"), "created_at", start)
    daily_logins = _daily(BotEvent.objects.filter(kind__in=["login_code", "login_confirm"]), "created_at", start)
    labels = [start + timedelta(days=i) for i in range(14)]
    tg_users = User.objects.filter(telegram_id__isnull=False)
    return _render(request, "dashboard/bot.html", {
        "stats": {
            "users": tg_users.count(),
            "registered": tg_users.filter(is_registered=True).count(),
            "blocked": tg_users.filter(bot_blocked=True).count(),
            "active_7d": tg_users.filter(last_bot_activity__gte=timezone.now() - timedelta(days=7)).count(),
            "logins_30d": by_kind.get("login_code", 0) + by_kind.get("login_confirm", 0),
            "unread": BotMessage.objects.filter(direction="in", is_read=False).count(),
        },
        "chart": {
            "labels": [d.strftime("%b %d") for d in labels],
            "starts": [daily_starts.get(d, 0) for d in labels],
            "logins": [daily_logins.get(d, 0) for d in labels],
        },
        "broadcasts": Broadcast.objects.select_related("created_by")[:6],
        "events": BotEvent.objects.select_related("user")[:10],
        "bot_settings": BotSettings.load(),
        "bot_username": settings.TELEGRAM_BOT_USERNAME,
        "admin_ids": settings.TELEGRAM_ADMIN_IDS,
    })


@staff
def broadcast_form(request, pk=None):
    obj = get_object_or_404(Broadcast, pk=pk) if pk else None
    if obj and obj.status not in ("draft", "scheduled"):
        return redirect("dashboard:bot")
    form = BroadcastForm(request.POST or None, request.FILES or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        b = form.save(commit=False)
        b.created_by = b.created_by or request.user
        b.status = Broadcast.Status.SCHEDULED if b.scheduled_at and b.scheduled_at > timezone.now() else Broadcast.Status.DRAFT
        b.save()
        action = request.POST.get("action")
        if action in ("send", "test"):
            if not settings.TELEGRAM_BOT_TOKEN:
                messages.error(request, _("Bot tokeni sozlanmagan (.env → TELEGRAM_BOT_TOKEN)"))
                return redirect("dashboard:broadcast_edit", pk=b.pk)
            from apps.telegram_bot.tasks import run_broadcast

            if action == "test":
                b.audience = Broadcast.Audience.STAFF
                b.save(update_fields=["audience"])
            run_broadcast.delay(b.pk)
            messages.success(request, _("Yuborish boshlandi"))
            return redirect("dashboard:bot")
        messages.success(request, _("Saqlandi"))
        return redirect("dashboard:broadcast_edit", pk=b.pk)
    audience_counts = {
        "all": User.objects.filter(telegram_id__isnull=False, bot_blocked=False, is_blocked=False).count(),
        "registered": User.objects.filter(telegram_id__isnull=False, bot_blocked=False, is_registered=True).count(),
        "students": User.objects.filter(telegram_id__isnull=False, bot_blocked=False, enrollments__isnull=False).distinct().count(),
        "staff": User.objects.filter(telegram_id__isnull=False, is_staff=True).count(),
    }
    return _render(request, "dashboard/broadcast_form.html", {"form": form, "obj": obj, "audience_counts": audience_counts})


@staff
def bot_settings(request):
    obj = BotSettings.load()
    form = BotSettingsForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Bot sozlamalari saqlandi"))
        return redirect("dashboard:bot_settings")
    return _render(request, "dashboard/bot_settings.html", {"form": form, "langs": settings.LANGUAGES})


@staff
def broadcast_progress(request, pk):
    b = get_object_or_404(Broadcast, pk=pk)
    return JsonResponse({"status": b.status, "sent": b.sent, "failed": b.failed, "total": b.total})


# --------------------------------------------------------------------------- Analitika

@staff
def analytics(request):
    days = 30
    visits = series(days)
    top_projects = Project.objects.published().order_by("-views_count")[:6]
    top_articles = Article.objects.published().order_by("-views_count")[:6]
    totals = {
        "views": sum(v.views for _d, v in visits if v),
        "visitors": sum(v.unique_visitors for _d, v in visits if v),
        "project_views": Project.objects.aggregate(v=Sum("views_count"))["v"] or 0,
        "article_views": Article.objects.aggregate(v=Sum("views_count"))["v"] or 0,
    }
    return _render(request, "dashboard/analytics.html", {
        "chart": {
            "labels": [d.strftime("%b %d") for d, _v in visits],
            "views": [v.views if v else 0 for _d, v in visits],
            "visitors": [v.unique_visitors if v else 0 for _d, v in visits],
        },
        "totals": totals, "top_projects": top_projects, "top_articles": top_articles,
        "progress": [(c, c.enrollments.count(), c.enrollments.filter(completed_at__isnull=False).count()) for c in Course.objects.all()],
    })


# --------------------------------------------------------------------------- Sozlamalar

@staff
def site_settings(request):
    obj = SiteSettings.load()
    form = SiteSettingsForm(request.POST or None, request.FILES or None, instance=obj)
    formset = SocialLinkFormSet(request.POST or None, queryset=SocialLink.objects.all(), prefix="social")
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        form.save()
        formset.save()
        messages.success(request, _("Sozlamalar saqlandi"))
        return redirect("dashboard:settings")
    return _render(request, "dashboard/settings.html", {"form": form, "formset": formset, "langs": settings.LANGUAGES})


@staff
def search(request):
    q = request.GET.get("q", "").strip()
    results = []
    if len(q) >= 2:
        for p in Project.objects.filter(title__icontains=q)[:5]:
            results.append(("folder", p.title, _("Loyiha"), reverse("dashboard:project_edit", args=[p.pk])))
        for a in Article.objects.filter(title__icontains=q)[:5]:
            results.append(("file-text", a.title, _("Maqola"), reverse("dashboard:article_edit", args=[a.pk])))
        for u in User.objects.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(phone__icontains=q))[:5]:
            results.append(("user-round", u.display_name, u.phone or _("Foydalanuvchi"), f"{reverse('dashboard:users')}?user={u.pk}"))
        for c in Course.objects.filter(title__icontains=q)[:3]:
            results.append(("graduation-cap", c.title, _("Kurs"), reverse("admin:education_course_change", args=[c.pk])))
    return render(request, "dashboard/partials/search_results.html", {"results": results, "q": q})

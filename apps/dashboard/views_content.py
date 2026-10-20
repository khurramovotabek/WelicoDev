"""Dashboard: Telegram kanal postlari, musiqa, tajriba/ta'lim va ko'nikmalar."""

from django.conf import settings
from django.core.cache import cache
from django.contrib import messages
from django.db.models import Count, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.blog.models import Article
from apps.accounts.models import User
from apps.education import services as edu
from apps.education.models import AccessRequest, Course, Enrollment, Lesson
from apps.gallery.models import Playlist, Track
from apps.portfolio.models import Experience, Project, Skill, SkillCategory
from apps.telegram_bot import channel
from apps.telegram_bot.formatting import html_to_telegram, truncate_telegram, visible_length
from apps.telegram_bot.models import BotSettings, ChannelPost

from .forms import ChannelPostForm, ExperienceForm, PlaylistForm, SkillForm, TrackForm
from .views import _render, staff

# --------------------------------------------------------------------------- Telegram kanal

CONTENT = {"article": Article, "lesson": Lesson, "course": Course, "project": Project}


@staff
def channel_posts(request):
    status = request.GET.get("status", "")
    qs = ChannelPost.objects.select_related("created_by")
    if status:
        qs = qs.filter(status=status)
    bs = BotSettings.load()
    return _render(request, "dashboard/channel.html", {
        "posts": qs[:50], "status": status, "statuses": ChannelPost.Status.choices, "bot_settings": bs,
        "stats": {
            "sent": ChannelPost.objects.filter(status="sent").count(),
            "scheduled": ChannelPost.objects.filter(status="scheduled").count(),
            "failed": ChannelPost.objects.filter(status="failed").count(),
        },
        # Kanalga hali chiqmagan, lekin nashr qilingan kontent: bir bosishda post qilish uchun
        "suggest_articles": Article.objects.published().filter(posted_to_channel_at__isnull=True)[:5],
        "suggest_courses": Course.objects.published().exclude(pk__in=ChannelPost.objects.filter(kind="course").values("object_id"))[:3],
        "suggest_projects": Project.objects.published().exclude(pk__in=ChannelPost.objects.filter(kind="project").values("object_id"))[:3],
    })


@staff
def channel_post_form(request, pk=None):
    post = get_object_or_404(ChannelPost, pk=pk) if pk else None
    form = ChannelPostForm(request.POST or None, request.FILES or None, instance=post)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.created_by = obj.created_by or request.user
        action = request.POST.get("action", "save")
        was_sent = bool(obj.message_id)
        if not was_sent:
            obj.status = ChannelPost.Status.SCHEDULED if obj.scheduled_at and obj.scheduled_at > timezone.now() else ChannelPost.Status.DRAFT
        obj.save()
        if was_sent:
            # Kanaldagi postni joyida yangilash (rasm almashtirib bo'lmaydi: Telegram cheklovi)
            ok = channel.edit(obj)
            (messages.success if ok else messages.error)(request, _("Kanaldagi post yangilandi") if ok else obj.error)
        elif action == "send":
            ok = channel.publish(obj)
            (messages.success if ok else messages.error)(request, _("Kanalga joylandi") if ok else obj.error)
            if ok:
                return redirect("dashboard:channel")
        elif obj.status == ChannelPost.Status.SCHEDULED:
            messages.success(request, _("Rejalashtirildi: %(t)s") % {"t": timezone.localtime(obj.scheduled_at).strftime("%d.%m.%Y %H:%M")})
        else:
            messages.success(request, _("Saqlandi"))
        return redirect("dashboard:channel_edit", pk=obj.pk)
    return _render(request, "dashboard/channel_form.html", {
        "form": form, "obj": post, "channel_id": BotSettings.load().channel_id,
        "preview": html_to_telegram(post.body) if post else "",
    })


@staff
@require_POST
def channel_preview(request):
    """Muharrirdagi HTML -> Telegram ko'rinishi (jonli preview uchun)."""
    tg = html_to_telegram(request.POST.get("body", ""))
    limit = 1024 if request.POST.get("has_image") == "1" else 4096
    return JsonResponse({"html": truncate_telegram(tg, limit), "length": visible_length(tg), "limit": limit})


@staff
@require_POST
def channel_post_action(request, pk, action):
    post = get_object_or_404(ChannelPost, pk=pk)
    if action == "delete":
        if request.POST.get("from_channel"):
            channel.delete(post)
        post.delete()
        messages.success(request, _("Post o'chirildi"))
    elif action == "retry":
        ok = channel.publish(post)
        (messages.success if ok else messages.error)(request, _("Kanalga joylandi") if ok else post.error)
    return redirect("dashboard:channel")


@staff
@require_POST
def channel_from_content(request, kind, pk):
    """Maqola/kurs/loyiha/darsdan avtomatik post yaratadi; 'draft' bo'lsa tahrirlash uchun ochadi."""
    model = CONTENT.get(kind)
    if not model:
        return HttpResponse(status=404)
    obj = get_object_or_404(model, pk=pk)
    publish_now = request.POST.get("mode") == "send"
    post = channel.post_object(obj, publish_now=publish_now, user=request.user)
    if publish_now:
        if post.status == "sent":
            if hasattr(obj, "posted_to_channel_at"):
                model.objects.filter(pk=pk).update(posted_to_channel_at=timezone.now())
            messages.success(request, _("Kanalga joylandi"))
        else:
            messages.error(request, post.error)
        return redirect(request.POST.get("next") or "dashboard:channel")
    return redirect("dashboard:channel_edit", pk=post.pk)


# --------------------------------------------------------------------------- Musiqa

@staff
def music(request):
    q = request.GET.get("q", "").strip()
    tracks = Track.objects.select_related("category")
    if q:
        tracks = tracks.filter(Q(title__icontains=q) | Q(artist__icontains=q))
    if request.GET.get("fav"):
        tracks = tracks.filter(is_favorite=True)
    return _render(request, "dashboard/music.html", {
        "tracks": tracks, "q": q, "fav": request.GET.get("fav"),
        "playlists": Playlist.objects.annotate(n=Count("tracks")),
        "stats": {"tracks": Track.objects.count(), "favorites": Track.objects.filter(is_favorite=True).count(),
                  "playlists": Playlist.objects.count(), "external": Track.objects.exclude(external_url="").count()},
    })


@staff
def track_form(request, pk=None):
    obj = get_object_or_404(Track, pk=pk) if pk else None
    form = TrackForm(request.POST or None, request.FILES or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        t = form.save()
        messages.success(request, _("Trek saqlandi"))
        return redirect("dashboard:music") if "close" in request.POST else redirect("dashboard:track_edit", pk=t.pk)
    return _render(request, "dashboard/track_form.html", {"form": form, "obj": obj, "langs": settings.LANGUAGES})


@staff
@require_POST
def track_action(request, pk, action):
    t = get_object_or_404(Track, pk=pk)
    if action == "favorite":
        t.is_favorite = not t.is_favorite
        t.save(update_fields=["is_favorite"])
    elif action == "toggle":
        t.is_published = not t.is_published
        t.save(update_fields=["is_published"])
    elif action == "delete":
        t.delete()
        return HttpResponse("") if request.htmx else redirect("dashboard:music")
    if request.htmx:
        from django.shortcuts import render

        return render(request, "dashboard/partials/track_row.html", {"t": t})
    return redirect("dashboard:music")


@staff
def playlist_form(request, pk=None):
    obj = get_object_or_404(Playlist, pk=pk) if pk else None
    form = PlaylistForm(request.POST or None, request.FILES or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Pleylist saqlandi"))
        return redirect("dashboard:music")
    return _render(request, "dashboard/playlist_form.html", {"form": form, "obj": obj, "langs": settings.LANGUAGES})


# --------------------------------------------------------------------------- Tajriba va ta'lim

@staff
def experience(request):
    items = Experience.objects.prefetch_related("technologies").order_by("-is_current", "-start_date")
    return _render(request, "dashboard/experience.html", {
        "work": [e for e in items if e.kind != Experience.Kind.EDUCATION],
        "study": [e for e in items if e.kind == Experience.Kind.EDUCATION],
    })


@staff
def experience_form(request, pk=None):
    obj = get_object_or_404(Experience, pk=pk) if pk else None
    initial = {"kind": request.GET.get("kind")} if not obj and request.GET.get("kind") else None
    form = ExperienceForm(request.POST or None, request.FILES or None, instance=obj, initial=initial)
    if request.method == "POST" and form.is_valid():
        e = form.save()
        messages.success(request, _("Saqlandi"))
        return redirect("dashboard:experience_edit", pk=e.pk)
    return _render(request, "dashboard/experience_form.html", {"form": form, "obj": obj, "langs": settings.LANGUAGES})


@staff
@require_POST
def experience_delete(request, pk):
    get_object_or_404(Experience, pk=pk).delete()
    messages.success(request, _("O'chirildi"))
    return redirect("dashboard:experience")


# --------------------------------------------------------------------------- Ko'nikmalar

@staff
def skills(request):
    cat = request.GET.get("category", "")
    qs = Skill.objects.select_related("category")
    if cat:
        qs = qs.filter(category__slug=cat)
    return _render(request, "dashboard/skills.html", {
        "skills": qs, "categories": SkillCategory.objects.annotate(n=Count("skills")), "active": cat,
        "stats": {"total": Skill.objects.count(), "featured": Skill.objects.filter(is_featured=True).count(),
                  "learning": Skill.objects.filter(is_learning=True).count(), "expert": Skill.objects.filter(level="expert").count()},
    })


@staff
def skill_form(request, pk=None):
    obj = get_object_or_404(Skill, pk=pk) if pk else None
    form = SkillForm(request.POST or None, request.FILES or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Ko'nikma saqlandi"))
        return redirect(reverse("dashboard:skills"))
    return _render(request, "dashboard/skill_form.html", {"form": form, "obj": obj, "langs": settings.LANGUAGES})


@staff
@require_POST
def skill_action(request, pk, action):
    s = get_object_or_404(Skill, pk=pk)
    if action == "featured":
        s.is_featured = not s.is_featured
        s.save(update_fields=["is_featured"])
    elif action == "delete":
        s.delete()
    return redirect(request.POST.get("next") or "dashboard:skills")


# --------------------------------------------------------------------------- Pullik kurslarga ruxsat

def _parse_expiry(value):
    """"30" -> 30 kundan keyin; bo'sh -> muddatsiz."""
    from datetime import timedelta

    try:
        days = int(value)
    except (TypeError, ValueError):
        return None
    return timezone.now() + timedelta(days=days) if days > 0 else None


@staff
def access(request):
    status = request.GET.get("status", "pending")
    course_id = request.GET.get("course", "")
    q = request.GET.get("q", "").strip()
    reqs = AccessRequest.objects.select_related("user", "course", "reviewed_by")
    if status in AccessRequest.Status.values:
        reqs = reqs.filter(status=status)
    enrollments = (
        Enrollment.objects.filter(Q(course__is_free=False) | Q(course__is_private=True))
        .select_related("user", "course", "granted_by").order_by("-created_at")
    )
    if course_id.isdigit():
        reqs = reqs.filter(course_id=course_id)
        enrollments = enrollments.filter(course_id=course_id)
    if q:
        uq = Q(user__first_name__icontains=q) | Q(user__last_name__icontains=q) | Q(user__phone__icontains=q) | Q(user__telegram_username__icontains=q)
        reqs = reqs.filter(uq)
        enrollments = enrollments.filter(uq)
    paid = Course.objects.filter(Q(is_free=False) | Q(is_private=True)).annotate(
        n_access=Count("enrollments", filter=Q(enrollments__is_active=True), distinct=True),
        n_pending=Count("access_requests", filter=Q(access_requests__status="pending"), distinct=True),
    )
    revenue = AccessRequest.objects.filter(status="approved").aggregate(s=Sum("amount"))["s"] or 0
    return _render(request, "dashboard/access.html", {
        "requests": reqs[:100], "enrollments": enrollments[:100], "paid_courses": paid,
        "status": status, "course_id": course_id, "q": q, "statuses": AccessRequest.Status.choices,
        "now": timezone.now(), "revenue": revenue,
        "counts": {s: AccessRequest.objects.filter(status=s).count() for s in AccessRequest.Status.values},
    })


@staff
def access_grant(request):
    """Foydalanuvchi qidirish (HTMX) va qo'lda ruxsat berish."""
    if request.method == "GET":
        q = request.GET.get("user_q", "").strip()
        users = []
        if len(q) >= 2:
            users = User.objects.filter(
                Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(phone__icontains=q)
                | Q(telegram_username__icontains=q) | Q(username__icontains=q)
            ).order_by("-date_joined")[:8]
        return render(request, "dashboard/partials/access_user_results.html", {"users": users, "q": q})
    user = get_object_or_404(User, pk=request.POST.get("user"))
    course = get_object_or_404(Course, pk=request.POST.get("course"))
    amount = request.POST.get("amount") or None
    edu.grant_access(course, user, by=request.user, expires_at=_parse_expiry(request.POST.get("days")),
                     amount=int(amount) if amount and amount.isdigit() else None)
    messages.success(request, _("%(user)s uchun «%(course)s» ochildi") % {"user": user.display_name, "course": course.title})
    return redirect(f"{reverse('dashboard:access')}?status=approved")


@staff
@require_POST
def access_request_action(request, pk, action):
    req = get_object_or_404(AccessRequest.objects.select_related("user", "course"), pk=pk)
    if action == "approve":
        amount = request.POST.get("amount") or ""
        edu.grant_access(req.course, req.user, by=request.user, access_request=req,
                         expires_at=_parse_expiry(request.POST.get("days")),
                         amount=int(amount) if amount.isdigit() else int(req.course.price))
        messages.success(request, _("Ruxsat berildi: %(user)s → %(course)s") % {"user": req.user.display_name, "course": req.course.title})
    elif action == "reject":
        edu.reject_access(req, by=request.user, admin_note=request.POST.get("admin_note", ""))
        messages.info(request, _("So'rov rad etildi"))
    cache.delete("dash:badges")
    return redirect(request.POST.get("next") or reverse("dashboard:access"))


@staff
@require_POST
def access_enrollment_action(request, pk, action):
    enrollment = get_object_or_404(Enrollment.objects.select_related("user", "course"), pk=pk)
    if action == "revoke":
        edu.revoke_access(enrollment)
        messages.info(request, _("Ruxsat bekor qilindi"))
    elif action == "restore":
        edu.grant_access(enrollment.course, enrollment.user, by=request.user, expires_at=enrollment.expires_at, notify=False)
        messages.success(request, _("Ruxsat qayta tiklandi"))
    elif action == "extend":
        edu.grant_access(enrollment.course, enrollment.user, by=request.user,
                         expires_at=_parse_expiry(request.POST.get("days")), notify=False)
        messages.success(request, _("Muddat yangilandi"))
    return redirect(request.POST.get("next") or reverse("dashboard:access"))

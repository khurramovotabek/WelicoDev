"""Butun saytni tekshirish: har bir sahifa (3 til), dashboard, Mini App va Unfold admin.

Bazadagi haqiqiy obyektlar bo'yicha URL'lar yig'iladi va har biri staff hamda oddiy foydalanuvchi
sifatida ochiladi. 500 (server xatosi) bo'lsa traceback chiqariladi. Faqat GET so'rovlar: ma'lumot o'zgarmaydi.

    .venv/bin/python scripts/crawl.py            # to'liq
    .venv/bin/python scripts/crawl.py --quick    # faqat o'zbekcha
"""

import os
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402
from django.contrib import admin  # noqa: E402
from django.test import Client  # noqa: E402
from django.urls import NoReverseMatch, reverse  # noqa: E402
from django.utils import translation  # noqa: E402

from apps.accounts.models import User  # noqa: E402
from apps.blog.models import Article, ArticleCategory  # noqa: E402
from apps.education.models import Certificate, Course, Lesson  # noqa: E402
from apps.gallery.models import MediaCategory, Photo, Playlist, Track, Video  # noqa: E402
from apps.portfolio.models import Experience, Project, ProjectCategory, Skill, SkillCategory  # noqa: E402
from apps.telegram_bot.models import Broadcast, ChannelPost  # noqa: E402

settings.ALLOWED_HOSTS = ["*"]
LANGS = ["uz"] if "--quick" in sys.argv else [code for code, _n in settings.LANGUAGES]


def public_urls(lang):
    with translation.override(lang):
        urls = [reverse(n) for n in (
            "core:home", "core:contact", "core:search", "portfolio:about", "portfolio:skills", "portfolio:project_list",
            "portfolio:experience_list", "blog:article_list", "gallery:index", "gallery:photo_list", "gallery:video_list",
            "gallery:music", "education:course_list", "accounts:login",
        )]
        urls += [f"{reverse('core:search')}?q={q}" for q in ("docker", "django", "x", "o'zbek")]
        urls += [f"{reverse('portfolio:project_list')}?category={c.slug}" for c in ProjectCategory.objects.all()]
        urls += [f"{reverse('portfolio:project_list')}?sort={s}&q=a" for s in ("latest", "popular", "oldest")]
        urls += [f"{reverse('portfolio:skills')}?category={c.slug}" for c in SkillCategory.objects.all()]
        urls += [f"{reverse('portfolio:experience_list')}?kind={k}" for k, _l in Experience.Kind.choices]
        urls += [f"{reverse('blog:article_list')}?category={c.slug}" for c in ArticleCategory.objects.all()]
        urls += [f"{reverse('gallery:index')}?photo={c.slug}&video={c.slug}&music={c.slug}" for c in MediaCategory.objects.all()]
        urls += [f"{reverse('gallery:music')}?category=favorites", *(f"{reverse('gallery:music')}?playlist={p.pk}" for p in Playlist.objects.all())]
        urls += [f"{reverse('education:course_list')}?level={lv}" for lv, _l in Course.Level.choices]
        urls += [f"{reverse('education:course_list')}?tech={s.slug}" for s in Skill.objects.all()[:5]]
        urls += [reverse("education:buy", args=[c.slug]) for c in Course.objects.listed().filter(is_free=False)]
        for qs in (Project.objects.all(), Article.objects.all(), Experience.objects.all(), Course.objects.listed(),
                   Photo.objects.all(), Video.objects.all(), Lesson.objects.filter(course__status="published", course__is_private=False).select_related("course")):
            urls += [o.get_absolute_url() for o in qs]
        urls += [reverse("core:share", args=[k, o.slug]) for k, qs in (("project", Project.objects.published()),
                 ("article", Article.objects.published()), ("course", Course.objects.listed())) for o in qs[:3]]
        urls += [reverse("education:certificate", args=[c.code]) for c in Certificate.objects.all()[:3]]
        urls += [reverse("blog:feed"), "/sitemap.xml", "/robots.txt", f"/{lang}/does-not-exist/"]
    return urls


def user_urls(lang):
    with translation.override(lang):
        base = reverse("accounts:profile")
        return [f"{base}?tab={t}" for t in ("overview", "courses", "saved", "certificates", "activity", "settings")] + [reverse("education:my_courses")]


def dashboard_urls():
    names = ["home", "users", "projects", "project_add", "articles", "article_add", "courses", "homework", "comments",
             "inbox", "access", "bot", "bot_settings", "broadcast_add", "channel", "channel_add", "music", "track_add", "playlist_add",
             "experience", "experience_add", "skills", "skill_add", "analytics", "settings"]
    urls = [reverse(f"dashboard:{n}") for n in names]
    urls += [f"{reverse('dashboard:home')}?days={d}" for d in (7, 30, 90)]
    urls += [f"{reverse('dashboard:comments')}?tab=reviews", f"{reverse('dashboard:inbox')}?tab=site", f"{reverse('dashboard:search')}?q=do"]
    urls += [f"{reverse('dashboard:homework')}?status={s}" for s in ("", "pending", "approved", "rejected")]
    urls += [f"{reverse('dashboard:access')}?status={s}" for s in ("all", "pending", "approved", "rejected")]
    urls += [f"{reverse('dashboard:access_grant')}?user_q=ot"]
    urls += [f"{reverse('dashboard:users')}?user={u.pk}" for u in User.objects.all()[:10]]
    urls += [f"{reverse('dashboard:projects')}?project={p.pk}&view=list" for p in Project.objects.all()]
    urls += [reverse("dashboard:project_edit", args=[p.pk]) for p in Project.objects.all()]
    urls += [reverse("dashboard:article_edit", args=[a.pk]) for a in Article.objects.all()]
    urls += [reverse("dashboard:track_edit", args=[t.pk]) for t in Track.objects.all()]
    urls += [reverse("dashboard:playlist_edit", args=[p.pk]) for p in Playlist.objects.all()]
    urls += [reverse("dashboard:experience_edit", args=[e.pk]) for e in Experience.objects.all()]
    urls += [reverse("dashboard:skill_edit", args=[s.pk]) for s in Skill.objects.all()]
    urls += [reverse("dashboard:channel_edit", args=[c.pk]) for c in ChannelPost.objects.all()]
    urls += [reverse("dashboard:broadcast_edit", args=[b.pk]) for b in Broadcast.objects.filter(status__in=["draft", "scheduled"])]
    return urls


def miniapp_urls():
    urls = [reverse("miniapp:shell"), reverse("miniapp:home"), reverse("miniapp:courses"), reverse("miniapp:journal"),
            reverse("miniapp:projects"), reverse("miniapp:profile")]
    urls += [reverse("miniapp:course", args=[c.slug]) for c in Course.objects.listed()]
    urls += [reverse("miniapp:lesson", args=[l.course.slug, l.slug]) for l in Lesson.objects.filter(course__status="published", course__is_private=False).select_related("course")[:30]]
    urls += [reverse("miniapp:article", args=[a.slug]) for a in Article.objects.published()]
    urls += [reverse("miniapp:project", args=[p.slug]) for p in Project.objects.published()]
    return urls


class _FakeReq:
    def __init__(self):
        self.user = User.objects.filter(is_superuser=True).first()


def admin_urls():
    urls = [reverse("admin:index")]
    for model, model_admin in admin.site._registry.items():
        info = (model._meta.app_label, model._meta.model_name)
        names = ("changelist", "add") if model_admin.has_add_permission(_FakeReq()) else ("changelist",)
        for name in names:
            try:
                urls.append(reverse(f"admin:{info[0]}_{info[1]}_{name}"))
            except NoReverseMatch:
                pass
        for obj in model.objects.all()[:3]:
            try:
                urls.append(reverse(f"admin:{info[0]}_{info[1]}_change", args=[obj.pk]))
            except NoReverseMatch:
                pass
    return urls


def run():
    staff = User.objects.filter(is_superuser=True).first()
    member, _ = User.objects.get_or_create(username="crawl_member", defaults={"is_registered": True, "first_name": "Crawl"})
    tma_user = User.objects.filter(telegram_id__isnull=False, is_registered=True).first() or member

    clients = {"anon": Client(raise_request_exception=False), "staff": Client(raise_request_exception=False),
               "member": Client(raise_request_exception=False)}
    clients["staff"].force_login(staff)
    clients["member"].force_login(member)

    plan = []
    for lang in LANGS:
        for u in public_urls(lang):
            plan += [("anon", u), ("member", u), ("staff", u)]
        plan += [("member", u) for u in user_urls(lang)]
        with translation.override(lang):
            plan += [("staff", u) for u in dashboard_urls()]
            plan += [("tma", u) for u in miniapp_urls()]
    plan += [("staff", u) for u in admin_urls()]

    seen, failures, slow = set(), [], []
    started = time.time()
    for who, url in plan:
        if (who, url) in seen:
            continue
        seen.add((who, url))
        client = clients.get(who) or clients["anon"]
        extra = {"HTTP_X_TMA_DEBUG_USER": str(tma_user.telegram_id or 0)} if who == "tma" and tma_user.telegram_id else {}
        t0 = time.time()
        try:
            r = client.get(url, **extra)
            code = r.status_code
        except Exception:  # noqa: BLE001
            code, r = "EXC", None
            failures.append((who, url, traceback.format_exc()))
        dt = time.time() - t0
        if dt > 1.0:
            slow.append((round(dt, 2), who, url))
        if code == 500 or (code not in (200, 301, 302, 304, 404, "EXC")):
            failures.append((who, url, f"HTTP {code}"))
        if code == 404 and "does-not-exist" not in url and who != "anon":
            failures.append((who, url, "HTTP 404"))

    print(f"\nTekshirildi: {len(seen)} so'rov, {time.time() - started:.1f}s")
    if slow:
        print(f"Sekin (>1s): {len(slow)}")
        for s in sorted(slow, reverse=True)[:8]:
            print("  ", s)
    if failures:
        print(f"\nXATOLAR: {len(failures)}")
        for who, url, info in failures:
            print(f"\n[{who}] {url}\n{info[-1500:]}")
        sys.exit(1)
    print("Xato yo'q ✓")
    member.delete()


if __name__ == "__main__":
    run()

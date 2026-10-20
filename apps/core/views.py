from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET

from apps.blog.models import Article
from apps.education.models import Course
from apps.gallery.models import Photo, Track, Video
from apps.interactions.forms import ContactForm
from apps.interactions.models import ShareEvent
from apps.interactions.notify import notify_admins_contact
from apps.portfolio.models import Project, Skill

from .models import CurrentStatus, Faq, Role, SocialLink
from .utils import client_ip, get_hero

SHAREABLE = {
    "project": (Project, lambda qs: qs.published()),
    "article": (Article, lambda qs: qs.published()),
    "course": (Course, lambda qs: qs.published()),
    "photo": (Photo, lambda qs: qs.filter(is_published=True)),
    "video": (Video, lambda qs: qs.filter(is_published=True)),
}


def home(request):
    from apps.portfolio.models import Experience

    return render(request, "core/home.html", {
        "hero": get_hero("home"),
        "roles": Role.objects.filter(is_active=True),
        "career": Experience.objects.filter(is_published=True).exclude(kind="education").order_by("-is_current", "-start_date")[:4],
        "skills": Skill.objects.select_related("category").order_by("-is_featured", "order")[:18],
        "statuses": CurrentStatus.objects.filter(is_active=True),
        "featured_projects": Project.objects.published().filter(is_featured=True).prefetch_related("tags")[:3]
        or Project.objects.published().prefetch_related("tags")[:3],
        "projects_count": Project.objects.published().count(),
        "track": Track.objects.filter(is_published=True).exclude(audio="").order_by("-is_favorite", "order").first(),
        "home_tracks": list(Track.objects.filter(is_published=True).exclude(audio="").order_by("-is_favorite", "order")[:30]),
        "courses_count": Course.objects.listed().count(),
        "companies_count": Experience.objects.filter(is_published=True, kind__in=["work", "startup"]).values("company").distinct().count(),
        "latest_articles": Article.objects.published()[:3],
        "courses": Course.objects.listed()[:3],
    })


def contact(request):
    form = ContactForm(request.POST or None, request.FILES or None, user=request.user)
    if request.method == "POST":
        ip = client_ip(request) or "unknown"
        key = f"contact:{ip}"
        if cache.get(key, 0) >= 5:
            messages.error(request, _("Juda ko'p xabar yuborildi. Bir soatdan keyin urinib ko'ring."))
        elif form.is_valid():
            msg = form.save(commit=False)
            msg.ip_address = ip if ip != "unknown" else None
            if request.user.is_authenticated:
                msg.user = request.user
            msg.save()
            cache.set(key, cache.get(key, 0) + 1, 3600)
            notify_admins_contact(msg)
            if request.htmx:
                return render(request, "core/partials/contact_success.html", {"msg": msg})
            messages.success(request, _("Xabaringiz yuborildi. Tez orada javob beraman!"))
            return redirect("core:contact")
        if request.htmx:
            return render(request, "core/partials/contact_form.html", {"form": form})
    return render(request, "core/contact.html", {
        "hero": get_hero("contact"),
        "form": form,
        "faqs": Faq.objects.filter(is_active=True),
        "faq_jsonld": _faq_ld(),
        "contact_socials": SocialLink.objects.filter(is_active=True, show_in_contact=True),
    })


def _faq_ld():
    from . import seo

    items = list(Faq.objects.filter(is_active=True))
    return seo.faq(items) if items else None


def search(request):
    q = request.GET.get("q", "").strip()
    results = {}
    if len(q) >= 2:
        results = {
            "projects": Project.objects.published().filter(Q(title__icontains=q) | Q(short_description__icontains=q))[:6],
            "articles": Article.objects.published().filter(Q(title__icontains=q) | Q(excerpt__icontains=q))[:6],
            "courses": Course.objects.listed().filter(Q(title__icontains=q) | Q(subtitle__icontains=q))[:6],
            "skills": Skill.objects.filter(name__icontains=q)[:8],
        }
    template = "core/partials/search_results.html" if request.htmx else "core/search.html"
    return render(request, template, {"q": q, "results": results, "has_results": any(results.values()) if results else False})


def share(request, kind, slug):
    if kind not in SHAREABLE:
        raise Http404
    model, scope = SHAREABLE[kind]
    obj = scope(model.objects).filter(slug=slug).first()
    if obj is None:
        raise Http404
    ct = ContentType.objects.get_for_model(obj)
    events = ShareEvent.objects.filter(content_type=ct, object_id=obj.pk)
    total = events.count()
    from django.db.models import Count
    from django.utils import timezone

    top = events.values("platform").annotate(n=Count("id")).order_by("-n").first()
    month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    absolute = request.build_absolute_uri(obj.get_absolute_url())
    return render(request, "core/share.html", {
        "hero": get_hero("share"),
        "obj": obj,
        "kind": kind,
        "url": absolute,
        "total": total,
        "this_month": events.filter(created_at__gte=month_start).count(),
        "top_platform": top and (dict(ShareEvent.Platform.choices).get(top["platform"]), round(top["n"] * 100 / total)),
        "recent": events.select_related("user")[:5],
        "image": getattr(obj, "cover", None) or getattr(obj, "image", None) or getattr(obj, "thumbnail", None),
        "description": getattr(obj, "short_description", None) or getattr(obj, "excerpt", None)
        or getattr(obj, "subtitle", None) or getattr(obj, "description", ""),
    })


def page_not_found(request, exception=None):
    return render(request, "404.html", {"hero": get_hero("404")}, status=404)


@require_GET
def robots_txt(request):
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /*/dashboard/",
        "Disallow: /*/accounts/",
        f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def indexnow_key(request, key):
    """IndexNow talabi: kalit fayli sayt ildizida /<key>.txt manzilida bo'lishi kerak."""
    from django.http import Http404

    from .models import SiteSettings

    if not key or key != SiteSettings.load().indexnow_key:
        raise Http404
    return HttpResponse(key, content_type="text/plain")


def journal_redirect(request, rest=""):
    """/uz/journal/... -> /uz/blog/... (bo'lim nomi o'zgargan; 301 qidiruv tizimlariga ham yangi manzilni bildiradi)."""
    from django.http import HttpResponsePermanentRedirect

    qs = request.META.get("QUERY_STRING")
    return HttpResponsePermanentRedirect(f"/{request.LANGUAGE_CODE}/blog/{rest}" + (f"?{qs}" if qs else ""))

from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path, re_path
from django.views.i18n import set_language

from apps.core.sitemaps import SITEMAPS
from apps.core.views import indexnow_key, journal_redirect, robots_txt
from apps.miniapp.views import preview as miniapp_preview

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("i18n/setlang/", set_language, name="set_language"),
    path("ckeditor5/", include("django_ckeditor_5.urls")),
    path("tg/", include("apps.telegram_bot.urls")),
    path("sitemap.xml", sitemap, {"sitemaps": SITEMAPS}, name="sitemap"),
    path("robots.txt", robots_txt, name="robots"),
    path("app-preview/", miniapp_preview, name="miniapp_preview"),
    path("<str:key>.txt", indexnow_key, name="indexnow_key"),
]

urlpatterns += i18n_patterns(
    path("dashboard/", include("apps.dashboard.urls")),
    path("app/", include("apps.miniapp.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("", include("apps.portfolio.urls")),
    path("blog/", include("apps.blog.urls")),
    # Eski manzillar (SEO: 301 bilan yangisiga)
    re_path(r"^journal/(?P<rest>.*)$", journal_redirect, name="journal_redirect"),
    path("media/", include("apps.gallery.urls")),
    path("education/", include("apps.education.urls")),
    path("i/", include("apps.interactions.urls")),
    path("", include("apps.core.urls")),
    prefix_default_language=True,
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = "apps.core.views.page_not_found"

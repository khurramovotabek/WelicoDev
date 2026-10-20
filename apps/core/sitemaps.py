"""3 tilli sitemap: har bir URL uchun uz/ru/en alternativlari va x-default (Google hreflang)."""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from apps.blog.models import Article
from apps.education.models import Course
from apps.gallery.models import Photo, Video
from apps.portfolio.models import Experience, Project


class I18nSitemap(Sitemap):
    i18n = True
    alternates = True
    x_default = True
    protocol = "https"


class StaticSitemap(I18nSitemap):
    priority = 0.8
    changefreq = "weekly"

    def items(self):
        return ["core:home", "portfolio:about", "portfolio:skills", "portfolio:project_list", "portfolio:experience_list",
                "blog:article_list", "education:course_list", "gallery:index", "core:contact"]

    def location(self, item):
        return reverse(item)

    def priority(self, item):  # noqa: F811 - Sitemap API metodi
        return 1.0 if item == "core:home" else 0.8


class ProjectSitemap(I18nSitemap):
    changefreq = "monthly"
    priority = 0.9

    def items(self):
        return Project.objects.published()

    def lastmod(self, obj):
        return obj.updated_at


class ArticleSitemap(I18nSitemap):
    changefreq = "monthly"
    priority = 0.8

    def items(self):
        return Article.objects.published()

    def lastmod(self, obj):
        return obj.updated_at


class CourseSitemap(I18nSitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return Course.objects.listed()

    def lastmod(self, obj):
        return obj.updated_at


class ExperienceSitemap(I18nSitemap):
    priority = 0.6

    def items(self):
        return Experience.objects.filter(is_published=True)

    def lastmod(self, obj):
        return obj.updated_at


class MediaSitemap(I18nSitemap):
    priority = 0.4

    def items(self):
        return [*Photo.objects.filter(is_published=True), *Video.objects.filter(is_published=True)]

    def lastmod(self, obj):
        return obj.updated_at


SITEMAPS = {
    "static": StaticSitemap, "projects": ProjectSitemap, "articles": ArticleSitemap,
    "courses": CourseSitemap, "experience": ExperienceSitemap, "media": MediaSitemap,
}

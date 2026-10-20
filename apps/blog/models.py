import math
import re

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _
from django_ckeditor_5.fields import CKEditor5Field

from apps.core.models import (
    PublishedQuerySet, PublishStatus, SeoModel, Tag, TimeStampedModel, unique_slugify,
)


class ArticleCategory(models.Model):
    name = models.CharField(_("nomi"), max_length=60)
    slug = models.SlugField(_("slug"), max_length=60, unique=True, blank=True)
    icon = models.CharField(_("belgi"), max_length=40, blank=True, help_text=_("Lucide belgi nomi"))
    order = models.PositiveSmallIntegerField(_("tartib"), default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = _("maqola turkumi")
        verbose_name_plural = _("maqola turkumlari")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.name_en or self.name)
        super().save(*args, **kwargs)


class Article(TimeStampedModel, SeoModel):
    title = models.CharField(_("sarlavha"), max_length=200)
    slug = models.SlugField(_("slug"), max_length=220, unique=True, blank=True)
    excerpt = models.TextField(_("qisqa mazmun"), max_length=300)
    content = CKEditor5Field(_("matn"), config_name="default")
    cover = models.ImageField(_("muqova"), upload_to="articles/covers/")

    category = models.ForeignKey(ArticleCategory, verbose_name=_("turkum"), on_delete=models.SET_NULL, null=True, blank=True, related_name="articles")
    tags = models.ManyToManyField(Tag, verbose_name=_("teglar"), blank=True, related_name="articles")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_("muallif"), on_delete=models.SET_NULL, null=True, blank=True, related_name="articles")

    status = models.CharField(_("holati"), max_length=10, choices=PublishStatus.choices, default=PublishStatus.DRAFT)
    is_featured = models.BooleanField(_("tanlangan"), default=False)
    allow_comments = models.BooleanField(_("izohlarga ruxsat"), default=True)
    published_at = models.DateTimeField(_("nashr sanasi"), default=timezone.now)
    focus_keyword = models.CharField(_("asosiy kalit so'z"), max_length=80, blank=True,
                                     help_text=_("Masalan: docker darslari. SEO tekshiruvi shu so'z bo'yicha ishlaydi"))
    posted_to_channel_at = models.DateTimeField(_("kanalga joylangan"), null=True, blank=True, editable=False)
    reading_minutes = models.PositiveSmallIntegerField(_("o'qish vaqti (daqiqa)"), default=1, editable=False)
    views_count = models.PositiveIntegerField(_("ko'rishlar"), default=0, editable=False)

    objects = PublishedQuerySet.as_manager()

    class Meta:
        ordering = ["-published_at"]
        verbose_name = _("maqola")
        verbose_name_plural = _("maqolalar")

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.title_en or self.title)
        words = len(strip_tags(self.content or "").split())
        self.reading_minutes = max(1, math.ceil(words / 200))
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("blog:article_detail", args=[self.slug])

    @property
    def toc(self):
        """Matndagi h2 sarlavhalaridan mundarija."""
        return [strip_tags(h) for h in re.findall(r"<h2[^>]*>(.*?)</h2>", self.content or "", flags=re.S)]


class ArticleImage(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(_("rasm"), upload_to="articles/gallery/")
    caption = models.CharField(_("izoh"), max_length=100, blank=True)
    order = models.PositiveSmallIntegerField(_("tartib"), default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = _("rasm")
        verbose_name_plural = _("rasmlar")


class Subscriber(models.Model):
    email = models.EmailField(_("email"), unique=True)
    language = models.CharField(_("til"), max_length=5, default="uz")
    is_active = models.BooleanField(_("faol"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("obunachi")
        verbose_name_plural = _("obunachilar")

    def __str__(self):
        return self.email

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import display

from apps.core.admin_mixins import TranslatedAdmin, TranslatedTabularInline
from apps.portfolio.admin import STATUS_LABELS, thumb

from .models import Article, ArticleCategory, ArticleImage, Subscriber


@admin.register(ArticleCategory)
class ArticleCategoryAdmin(TranslatedAdmin):
    list_display = ("name", "slug", "icon", "order")
    list_editable = ("order",)


class ArticleImageInline(TranslatedTabularInline):
    model = ArticleImage
    fields = ("image", "caption", "order")
    tab = True


@admin.register(Article)
class ArticleAdmin(TranslatedAdmin):
    list_display = ("cover_preview", "title", "category", "author", "status_badge", "is_featured", "views_count", "published_at")
    list_display_links = ("cover_preview", "title")
    list_filter = ("status", "category", "is_featured", "published_at")
    search_fields = ("title", "excerpt")
    autocomplete_fields = ("tags",)
    date_hierarchy = "published_at"
    inlines = [ArticleImageInline]
    fieldsets = (
        (_("Matn"), {"fields": ("title", "slug", "excerpt", "content"), "classes": ["tab"]}),
        (_("Nashr"), {
            "fields": ("cover", "category", "tags", "author", "status", "published_at", "is_featured", "allow_comments"),
            "classes": ["tab"],
        }),
        (_("SEO"), {"fields": ("meta_title", "meta_description"), "classes": ["tab"]}),
    )

    def save_model(self, request, obj, form, change):
        if not obj.author_id:
            obj.author = request.user
        super().save_model(request, obj, form, change)

    @display(description="")
    def cover_preview(self, obj):
        return thumb(obj.cover)

    @display(description=_("Holati"), label=STATUS_LABELS)
    def status_badge(self, obj):
        return obj.status, obj.get_status_display()


@admin.register(Subscriber)
class SubscriberAdmin(ModelAdmin):
    list_display = ("email", "language", "is_active", "created_at")
    list_filter = ("is_active", "language")
    search_fields = ("email",)

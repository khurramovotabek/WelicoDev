from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin

from .admin_mixins import SingletonAdminMixin, TranslatedAdmin
from .models import CurrentStatus, Faq, PageHero, Role, SiteSettings, SocialLink, Tag


@admin.register(SiteSettings)
class SiteSettingsAdmin(SingletonAdminMixin, TranslatedAdmin):
    fieldsets = (
        (_("Brend"), {"fields": ("brand_name", "brand_tagline", "logo", "favicon"), "classes": ["tab"]}),
        (_("Shaxsiy"), {
            "fields": ("owner_name", "owner_role", "owner_bio", "avatar", "portrait", "cv_file", "hero_badges",
                       "intro_video_url", "intro_video_duration", "available_for_work"),
            "classes": ["tab"],
        }),
        (_("Statistika"), {"fields": ("years_experience", "people_impacted"), "classes": ["tab"]}),
        (_("Aloqa"), {
            "fields": ("email", "phone", "location", "map_url", "latitude", "longitude", "map_zoom", "timezone_name",
                       "working_hours", "timezone_label", "response_time"),
            "classes": ["tab"],
        }),
        (_("Fon"), {"fields": ("background_preset", "background_image", "background_dim", "background_blur", "background_motion"), "classes": ["tab"]}),
        (_("To'lovlar"), {"fields": ("payment_telegram", "payment_note"), "classes": ["tab"]}),
        (_("SEO va footer"), {"fields": ("meta_description", "og_image", "footer_text"), "classes": ["tab"]}),
    )


@admin.register(SocialLink)
class SocialLinkAdmin(ModelAdmin):
    list_display = ("display_name", "platform", "url", "order", "is_active", "show_in_header", "show_in_footer", "show_in_contact")
    list_editable = ("order", "is_active", "show_in_header", "show_in_footer", "show_in_contact")
    list_filter = ("platform", "is_active")
    search_fields = ("label", "url", "username")


@admin.register(CurrentStatus)
class CurrentStatusAdmin(TranslatedAdmin):
    list_display = ("label", "value", "color", "order", "is_active")
    list_editable = ("order", "is_active")


@admin.register(Role)
class RoleAdmin(TranslatedAdmin):
    list_display = ("title", "subtitle", "icon", "color", "order", "is_active")
    list_editable = ("order", "is_active")


@admin.register(PageHero)
class PageHeroAdmin(TranslatedAdmin):
    list_display = ("page", "title", "quote")
    fields = ("page", "eyebrow", "title", "subtitle", "description", "quote", "background")


@admin.register(Faq)
class FaqAdmin(TranslatedAdmin):
    list_display = ("question", "order", "is_active")
    list_editable = ("order", "is_active")


@admin.register(Tag)
class TagAdmin(ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)

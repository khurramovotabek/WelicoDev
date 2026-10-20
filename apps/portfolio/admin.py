from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import TabularInline
from unfold.decorators import display

from apps.core.admin_mixins import TranslatedAdmin, TranslatedTabularInline

from .models import (
    Experience, ExperienceImage, Interest, JourneyStep, Milestone, Project, ProjectCategory,
    ProjectChallenge, ProjectFeature, ProjectImage, ProjectResult, Responsibility, Skill, SkillCategory,
)

STATUS_LABELS = {"draft": "warning", "published": "success", "archived": "info"}


def thumb(image, size=44):
    if not image:
        return "—"
    return format_html('<img src="{}" style="width:{}px;height:{}px;object-fit:cover;border-radius:8px">', image.url, size, size)


@admin.register(SkillCategory)
class SkillCategoryAdmin(TranslatedAdmin):
    list_display = ("name", "slug", "order")
    list_editable = ("order",)


@admin.register(Skill)
class SkillAdmin(TranslatedAdmin):
    list_display = ("icon_preview", "name", "category", "level", "proficiency", "years", "is_featured", "is_learning", "order")
    list_display_links = ("icon_preview", "name")
    list_editable = ("is_featured", "is_learning", "order")
    list_filter = ("category", "level", "is_featured", "is_learning")
    search_fields = ("name",)

    @display(description="")
    def icon_preview(self, obj):
        if not obj.icon_url:
            return "—"
        return format_html('<img src="{}" style="width:24px;height:24px">', obj.icon_url)


@admin.register(ProjectCategory)
class ProjectCategoryAdmin(TranslatedAdmin):
    list_display = ("name", "slug", "order")
    list_editable = ("order",)


class ProjectImageInline(TranslatedTabularInline):
    model = ProjectImage
    fields = ("image", "caption", "order")
    tab = True


class ProjectFeatureInline(TranslatedTabularInline):
    model = ProjectFeature
    fields = ("title", "description", "icon", "order")
    tab = True


class ProjectChallengeInline(TranslatedTabularInline):
    model = ProjectChallenge
    fields = ("text", "order")
    tab = True


class ProjectResultInline(TranslatedTabularInline):
    model = ProjectResult
    fields = ("value", "label", "icon", "order")
    tab = True


@admin.register(Project)
class ProjectAdmin(TranslatedAdmin):
    list_display = ("cover_preview", "title", "category", "status_badge", "is_featured", "views_count", "updated_at")
    list_display_links = ("cover_preview", "title")
    list_filter = ("status", "category", "is_featured")
    search_fields = ("title", "short_description")
    autocomplete_fields = ("tags", "tech_stack")
    inlines = [ProjectImageInline, ProjectFeatureInline, ProjectChallengeInline, ProjectResultInline]
    fieldsets = (
        (_("Asosiy"), {"fields": ("title", "slug", "subtitle", "short_description", "description"), "classes": ["tab"]}),
        (_("Media"), {"fields": ("cover", "video", "video_url", "video_duration"), "classes": ["tab"]}),
        (_("Ma'lumot"), {
            "fields": ("category", "tags", "tech_stack", "project_type", "role", "duration", "team_size",
                       "completed_year", "live_url", "source_url"),
            "classes": ["tab"],
        }),
        (_("Nashr"), {"fields": ("status", "is_featured", "allow_comments", "allow_reviews", "order"), "classes": ["tab"]}),
        (_("SEO"), {"fields": ("meta_title", "meta_description"), "classes": ["tab"]}),
    )

    @display(description="")
    def cover_preview(self, obj):
        return thumb(obj.cover)

    @display(description=_("Holati"), label=STATUS_LABELS)
    def status_badge(self, obj):
        return obj.status, obj.get_status_display()


class ResponsibilityInline(TranslatedTabularInline):
    model = Responsibility
    fields = ("text", "order")
    tab = True


class MilestoneInline(TranslatedTabularInline):
    model = Milestone
    fields = ("date_label", "title", "description", "order")
    tab = True


class ExperienceImageInline(TabularInline):
    model = ExperienceImage
    extra = 0
    tab = True


@admin.register(Experience)
class ExperienceAdmin(TranslatedAdmin):
    list_display = ("logo_preview", "company", "role", "kind", "start_date", "end_date", "is_current", "is_published")
    list_display_links = ("logo_preview", "company")
    list_filter = ("kind", "is_current", "is_published")
    search_fields = ("company", "role")
    autocomplete_fields = ("technologies", "projects")
    inlines = [ResponsibilityInline, MilestoneInline, ExperienceImageInline]
    fieldsets = (
        (_("Asosiy"), {
            "fields": ("company", "slug", "role", "kind", "logo", "location", "start_date", "end_date", "is_current",
                       "summary", "description", "quote"),
            "classes": ["tab"],
        }),
        (_("Kompaniya"), {
            "fields": ("company_description", "company_industry", "website", "map_url", "team_size", "products_count"),
            "classes": ["tab"],
        }),
        (_("Bog'liqlar"), {"fields": ("technologies", "projects", "is_published", "order"), "classes": ["tab"]}),
    )

    @display(description="")
    def logo_preview(self, obj):
        return thumb(obj.logo, 36)


@admin.register(JourneyStep)
class JourneyStepAdmin(TranslatedAdmin):
    list_display = ("year", "title", "order")
    list_editable = ("order",)


@admin.register(Interest)
class InterestAdmin(TranslatedAdmin):
    list_display = ("title", "order")
    list_editable = ("order",)

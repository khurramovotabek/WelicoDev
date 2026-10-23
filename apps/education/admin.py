from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action, display

from apps.core.admin_mixins import TranslatedAdmin, TranslatedTabularInline
from apps.portfolio.admin import STATUS_LABELS, thumb

from . import services
from .models import (
    AccessRequest, Certificate, Course, Enrollment, HomeworkSubmission, Lesson, LessonProgress, LessonResource, Module,
)


class ModuleInline(TranslatedTabularInline):
    model = Module
    fields = ("title", "order")
    tab = True


class LessonInline(TabularInline):
    model = Lesson
    fields = ("order", "title", "module", "duration_seconds", "homework_mode", "is_preview", "status")
    show_change_link = True
    extra = 0
    tab = True
    ordering = ("order",)


@admin.register(Course)
class CourseAdmin(TranslatedAdmin):
    list_display = ("cover_preview", "title", "level", "lessons_count", "students_count", "is_free", "status_badge", "is_featured")
    list_display_links = ("cover_preview", "title")
    list_filter = ("status", "level", "is_free", "is_private", "is_featured")
    search_fields = ("title", "subtitle")
    autocomplete_fields = ("technologies",)
    inlines = [ModuleInline, LessonInline]
    fieldsets = (
        (_("Asosiy"), {"fields": ("title", "slug", "subtitle", "cover", "trailer_url", "author_name", "author_url", "level", "technologies"), "classes": ["tab"]}),
        (_("Tavsif"), {"fields": ("description", "what_you_learn", "requirements"), "classes": ["tab"]}),
        (_("Qoidalar"), {
            "fields": ("is_free", "price", "old_price", "is_private", "sequential", "require_login_for_preview", "allow_reviews",
                       "status", "is_featured", "order"),
            "classes": ["tab"],
        }),
        (_("SEO"), {"fields": ("meta_title", "meta_description"), "classes": ["tab"]}),
    )

    @display(description="")
    def cover_preview(self, obj):
        return thumb(obj.cover)

    @display(description=_("Darslar"))
    def lessons_count(self, obj):
        return obj.lessons.count()

    @display(description=_("O'quvchilar"))
    def students_count(self, obj):
        return obj.enrollments.count()

    @display(description=_("Holati"), label=STATUS_LABELS)
    def status_badge(self, obj):
        return obj.status, obj.get_status_display()


class LessonResourceInline(TranslatedTabularInline):
    model = LessonResource
    fields = ("kind", "title", "url", "file", "order")
    tab = True


@admin.register(Lesson)
class LessonAdmin(TranslatedAdmin):
    list_display = ("order", "title", "course", "module", "duration_label", "homework_mode", "is_preview", "status_badge")
    list_display_links = ("title",)
    list_filter = ("course", "status", "homework_mode", "is_preview")
    search_fields = ("title", "course__title")
    list_select_related = ("course", "module")
    ordering = ("course", "order")
    inlines = [LessonResourceInline]
    fieldsets = (
        (_("Asosiy"), {"fields": ("course", "module", "order", "title", "slug", "summary", "status", "is_preview"), "classes": ["tab"]}),
        (_("Video"), {"fields": ("video", "video_url", "duration_seconds", "thumbnail"), "classes": ["tab"]}),
        (_("Konspekt"), {"fields": ("content",), "classes": ["tab"]}),
        (_("Uyga vazifa"), {"fields": ("homework_mode", "homework"), "classes": ["tab"]}),
    )

    @display(description=_("Davomiyligi"))
    def duration_label(self, obj):
        return obj.duration_label

    @display(description=_("Holati"), label=STATUS_LABELS)
    def status_badge(self, obj):
        return obj.status, obj.get_status_display()


@admin.register(HomeworkSubmission)
class HomeworkSubmissionAdmin(ModelAdmin):
    list_display = ("user", "lesson", "status_badge", "created_at", "reviewed_at")
    list_filter = ("status", "lesson__course")
    search_fields = ("user__first_name", "user__last_name", "user__phone", "lesson__title")
    readonly_fields = ("user", "lesson", "text", "link", "file", "created_at")
    fields = ("user", "lesson", "text", "link", "file", "status", "feedback", "created_at")
    actions = ["approve", "reject"]

    @display(description=_("Holati"), label={"pending": "warning", "approved": "success", "rejected": "danger"})
    def status_badge(self, obj):
        return obj.status, obj.get_status_display()

    def save_model(self, request, obj, form, change):
        if "status" in form.changed_data:
            obj.mark_reviewed(obj.status, obj.feedback)
            services.try_complete(obj.user, obj.lesson)
        else:
            super().save_model(request, obj, form, change)

    @action(description=_("Qabul qilish"))
    def approve(self, request, queryset):
        for sub in queryset:
            sub.mark_reviewed(HomeworkSubmission.Status.APPROVED, sub.feedback)
            services.try_complete(sub.user, sub.lesson)
        messages.success(request, _("Tanlangan javoblar qabul qilindi"))

    @action(description=_("Qaytarish"))
    def reject(self, request, queryset):
        for sub in queryset:
            sub.mark_reviewed(HomeworkSubmission.Status.REJECTED, sub.feedback)
        messages.warning(request, _("Tanlangan javoblar qaytarildi"))


@admin.register(Enrollment)
class EnrollmentAdmin(ModelAdmin):
    list_display = ("user", "course", "progress", "is_active", "expires_at", "created_at", "completed_at")
    list_filter = ("course", "is_active")
    readonly_fields = ("granted_by",)
    search_fields = ("user__first_name", "user__last_name", "user__phone")
    autocomplete_fields = ("user",)

    @display(description=_("Progress"))
    def progress(self, obj):
        return f"{services.course_progress(obj.user, obj.course)}%"


@admin.register(AccessRequest)
class AccessRequestAdmin(ModelAdmin):
    list_display = ("reference", "user", "course", "status", "amount", "created_at", "reviewed_at")
    list_filter = ("status", "course")
    search_fields = ("user__first_name", "user__last_name", "user__phone", "user__username")
    autocomplete_fields = ("user",)
    readonly_fields = ("reviewed_at", "reviewed_by")


@admin.register(LessonProgress)
class LessonProgressAdmin(ModelAdmin):
    list_display = ("user", "lesson", "watched_seconds", "video_completed", "completed_at")
    list_filter = ("lesson__course", "video_completed")


@admin.register(Certificate)
class CertificateAdmin(ModelAdmin):
    list_display = ("code", "enrollment", "issued_at")
    search_fields = ("code",)

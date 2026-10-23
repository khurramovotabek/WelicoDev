from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import display

from apps.core.admin_mixins import SingletonAdminMixin, TranslatedAdmin

from .models import BotEvent, BotMessage, BotSettings, Broadcast


@admin.register(BotSettings)
class BotSettingsAdmin(SingletonAdminMixin, TranslatedAdmin):
    fieldsets = (
        (_("Holat"), {"fields": ("is_enabled", "maintenance_text"), "classes": ["tab"]}),
        (_("Matnlar"), {"fields": ("welcome_text", "registered_text", "help_text", "mini_app_button_text"), "classes": ["tab"]}),
        (_("Bildirishnomalar"), {
            "fields": ("notify_new_user", "notify_new_comment", "notify_new_review", "notify_contact_message", "notify_homework"),
            "classes": ["tab"],
        }),
        (_("Kanal"), {"fields": ("channel_id", "auto_post_articles", "auto_post_lessons"), "classes": ["tab"]}),
    )


@admin.register(Broadcast)
class BroadcastAdmin(ModelAdmin):
    list_display = ("title", "audience", "status_badge", "sent", "failed", "total", "scheduled_at", "created_at")
    list_filter = ("status", "audience")
    readonly_fields = ("status", "total", "sent", "failed", "started_at", "finished_at", "created_by")

    @display(description=_("Holati"), label={"draft": "info", "scheduled": "warning", "sending": "warning", "done": "success", "failed": "danger"})
    def status_badge(self, obj):
        return obj.status, obj.get_status_display()

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(BotMessage)
class BotMessageAdmin(ModelAdmin):
    list_display = ("user", "direction", "short_text", "is_read", "created_at")
    list_filter = ("direction", "is_read")
    search_fields = ("text", "user__first_name", "user__phone")

    @display(description=_("Matn"))
    def short_text(self, obj):
        return obj.text[:80]


@admin.register(BotEvent)
class BotEventAdmin(ModelAdmin):
    list_display = ("kind", "user", "payload", "created_at")
    list_filter = ("kind",)

    def has_add_permission(self, request):
        return False

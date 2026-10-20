from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import action, display

from .models import Comment, ContactMessage, Review


@admin.register(Comment)
class CommentAdmin(ModelAdmin):
    list_display = ("user", "short_body", "target", "is_approved", "is_pinned", "likes_count", "created_at")
    list_filter = ("is_approved", "is_pinned", "content_type")
    list_editable = ("is_approved", "is_pinned")
    search_fields = ("body", "user__first_name", "user__last_name")
    readonly_fields = ("user", "content_type", "object_id", "parent", "created_at")
    actions = ["approve", "hide"]

    @display(description=_("Izoh"))
    def short_body(self, obj):
        return obj.body[:80]

    @action(description=_("Tasdiqlash"))
    def approve(self, request, queryset):
        queryset.update(is_approved=True)

    @action(description=_("Yashirish"))
    def hide(self, request, queryset):
        queryset.update(is_approved=False)


@admin.register(Review)
class ReviewAdmin(ModelAdmin):
    list_display = ("user", "rating", "short_body", "target", "is_approved", "created_at")
    list_filter = ("is_approved", "rating", "content_type")
    list_editable = ("is_approved",)
    readonly_fields = ("user", "content_type", "object_id", "rating", "created_at")

    @display(description=_("Sharh"))
    def short_body(self, obj):
        return obj.body[:80]


@admin.register(ContactMessage)
class ContactMessageAdmin(ModelAdmin):
    list_display = ("name", "email", "subject", "status_badge", "created_at")
    list_filter = ("status",)
    search_fields = ("name", "email", "subject", "message")
    readonly_fields = ("user", "name", "email", "subject", "message", "attachment", "ip_address", "created_at")

    @display(description=_("Holati"), label={"new": "danger", "read": "info", "replied": "success", "archived": "warning"})
    def status_badge(self, obj):
        return obj.status, obj.get_status_display()

    def change_view(self, request, object_id, form_url="", extra_context=None):
        ContactMessage.objects.filter(pk=object_id, status=ContactMessage.Status.NEW).update(status=ContactMessage.Status.READ)
        return super().change_view(request, object_id, form_url, extra_context)

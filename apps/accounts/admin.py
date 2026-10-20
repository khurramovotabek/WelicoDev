from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import display
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from .models import LoginCode, User

admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    list_display = ("display_name", "phone", "telegram_link", "status_badge", "date_joined", "last_login")
    list_filter = ("is_registered", "is_blocked", "bot_blocked", "is_staff", "language", "date_joined")
    search_fields = ("username", "first_name", "last_name", "phone", "telegram_username", "telegram_id")
    ordering = ("-date_joined",)
    readonly_fields = ("telegram_id", "last_bot_activity", "date_joined", "last_login")
    fieldsets = (
        (_("Profil"), {"fields": ("username", "first_name", "last_name", "phone", "avatar", "bio", "language")}),
        (_("Telegram"), {"fields": ("telegram_id", "telegram_username", "is_registered", "bot_blocked", "last_bot_activity")}),
        (_("Holat"), {"fields": ("is_active", "is_blocked", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Parol (faqat adminlar uchun)"), {"fields": ("password",), "classes": ["collapse"]}),
        (_("Sanalar"), {"fields": ("date_joined", "last_login")}),
    )

    @display(description=_("Ism"), ordering="first_name")
    def display_name(self, obj):
        return obj.display_name

    @display(description="Telegram")
    def telegram_link(self, obj):
        return f"@{obj.telegram_username}" if obj.telegram_username else (obj.telegram_id or "—")

    @display(
        description=_("Holat"),
        label={"Admin": "info", "Faol": "success", "Bloklangan": "danger", "To'liq emas": "warning"},
    )
    def status_badge(self, obj):
        if obj.is_staff:
            return "Admin"
        if obj.is_blocked:
            return "Bloklangan"
        return "Faol" if obj.is_registered else "To'liq emas"


@admin.register(LoginCode)
class LoginCodeAdmin(ModelAdmin):
    list_display = ("user", "created_at", "expires_at", "attempts", "is_used")
    list_filter = ("is_used",)
    readonly_fields = ("user", "request", "code", "attempts", "is_used", "created_at", "expires_at")

    def has_add_permission(self, request):
        return False

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    label = "accounts"
    verbose_name = _("Foydalanuvchilar")

    def ready(self):
        from django.contrib import admin

        from .admin_security import secure_admin_login

        # Admin panelga parol bilan kirish: urinishlar cheklovi + Telegram 2FA
        admin.site.login = secure_admin_login

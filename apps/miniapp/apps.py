from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class MiniappConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.miniapp"
    label = "miniapp"
    verbose_name = _("Telegram Mini App")

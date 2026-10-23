from modeltranslation.translator import TranslationOptions, register

from .models import BotSettings


@register(BotSettings)
class BotSettingsTR(TranslationOptions):
    fields = ("maintenance_text", "welcome_text", "registered_text", "help_text", "mini_app_button_text")
    fallback_undefined = ""

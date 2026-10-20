from modeltranslation.translator import TranslationOptions, register

from .models import CurrentStatus, Faq, PageHero, Role, SiteSettings


@register(SiteSettings)
class SiteSettingsTR(TranslationOptions):
    fields = (
        "brand_tagline", "owner_role", "owner_bio", "hero_badges", "location",
        "working_hours", "response_time", "meta_description", "footer_text", "payment_note",
    )
    # Default qiymat bilan bir xil bo'lgan tarjima ham haqiqiy tarjima hisoblanadi; faqat bo'sh qator zaxiraga o'tadi
    fallback_undefined = ""


@register(CurrentStatus)
class CurrentStatusTR(TranslationOptions):
    fields = ("label", "value")


@register(PageHero)
class PageHeroTR(TranslationOptions):
    fields = ("eyebrow", "title", "subtitle", "description", "quote")


@register(Faq)
class FaqTR(TranslationOptions):
    fields = ("question", "answer")


@register(Role)
class RoleTR(TranslationOptions):
    fields = ("title", "subtitle", "description")

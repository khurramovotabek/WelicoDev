"""Nashr hodisalari: Telegram kanalga avtomatik post va IndexNow orqali qidiruv tizimlariga xabar."""

from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import translate_url
from django.utils import translation

from apps.blog.models import Article
from apps.education.models import Course, Lesson
from apps.portfolio.models import Project


def _all_lang_paths(obj):
    with translation.override("uz"):
        path = obj.get_absolute_url()
    return [translate_url(path, code) for code, _n in settings.LANGUAGES]


def _ping(obj):
    from apps.telegram_bot.tasks import indexnow_ping

    paths = _all_lang_paths(obj)
    transaction.on_commit(lambda: indexnow_ping.delay(paths))


@receiver(post_save, sender=Article)
def article_published(sender, instance, **kwargs):
    if instance.status != "published":
        return
    _ping(instance)
    from apps.telegram_bot.models import BotSettings
    from apps.telegram_bot.tasks import post_to_channel

    if not instance.posted_to_channel_at and BotSettings.load().auto_post_articles:
        transaction.on_commit(lambda: post_to_channel.delay("blog.Article", instance.pk))


@receiver(post_save, sender=Lesson)
def lesson_published(sender, instance, **kwargs):
    # Dars faqat videosi bilan e'lon qilinadi: "video tez orada" holatidagi dars kanalga chiqmaydi
    if instance.status != "published" or instance.course.status != "published" or not instance.has_video:
        return
    from apps.telegram_bot.models import BotSettings
    from apps.telegram_bot.tasks import post_to_channel

    if not instance.posted_to_channel_at and BotSettings.load().auto_post_lessons:
        transaction.on_commit(lambda: post_to_channel.delay("education.Lesson", instance.pk))


@receiver(post_save, sender=Project)
@receiver(post_save, sender=Course)
def page_published(sender, instance, **kwargs):
    if instance.status == "published":
        _ping(instance)

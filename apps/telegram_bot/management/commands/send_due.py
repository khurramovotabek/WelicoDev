"""Rejalashtirilgan kanal postlari va ommaviy xabarlarni yuboradi (Celery beat bo'lmasa cron orqali: * * * * *)."""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Vaqti kelgan kanal postlari va ommaviy xabarlarni yuboradi"

    def handle(self, *args, **opts):
        from apps.telegram_bot.tasks import send_due

        send_due()

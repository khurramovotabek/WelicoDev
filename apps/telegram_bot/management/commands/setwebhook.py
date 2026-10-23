"""Production uchun: webhook, buyruqlar ro'yxati va Mini App menyu tugmasini o'rnatadi.

    python manage.py setwebhook            # SITE_URL/tg/webhook/ (+ ta'lim boti: SITE_URL/tg/edu-webhook/)
    python manage.py setwebhook --delete   # webhook'ni o'chirish (polling'ga qaytish)

Ta'lim boti (@welicodev_educationbot) faqat TELEGRAM_EDU_BOT_TOKEN berilgan bo'lsa sozlanadi.
"""

import asyncio

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Telegram webhook, buyruqlar va Mini App tugmasini o'rnatadi"

    def add_arguments(self, parser):
        parser.add_argument("--delete", action="store_true")

    def handle(self, *args, delete=False, **options):
        if not settings.TELEGRAM_BOT_TOKEN:
            raise CommandError("TELEGRAM_BOT_TOKEN .env faylida ko'rsatilmagan")
        if not delete and not settings.SITE_URL.startswith("https://"):
            raise CommandError("Webhook faqat HTTPS SITE_URL bilan ishlaydi")
        asyncio.run(self._run(delete))

    async def _run(self, delete):
        from apps.telegram_bot.bot.dispatcher import get_bot, get_dispatcher, setup_bot
        from apps.telegram_bot.views import _webhook_secret

        bot = get_bot()
        try:
            if delete:
                await bot.delete_webhook(drop_pending_updates=False)
                self.stdout.write(self.style.WARNING("Webhook o'chirildi"))
                return
            url = f"{settings.SITE_URL}/tg/webhook/"
            await bot.set_webhook(
                url, secret_token=_webhook_secret(), allowed_updates=get_dispatcher().resolve_used_update_types(),
                drop_pending_updates=False, max_connections=40,
            )
            await setup_bot(bot)
            info = await bot.get_webhook_info()
            self.stdout.write(self.style.SUCCESS(f"Webhook: {info.url} · kutilmoqda: {info.pending_update_count}"))
        finally:
            await bot.session.close()
        if settings.TELEGRAM_EDU_BOT_TOKEN:
            await self._run_edu(delete)

    async def _run_edu(self, delete):
        from apps.telegram_bot.edu.dispatcher import get_bot, get_dispatcher, setup_bot
        from apps.telegram_bot.views import _webhook_secret

        bot = get_bot()
        try:
            if delete:
                await bot.delete_webhook(drop_pending_updates=False)
                self.stdout.write(self.style.WARNING("Ta'lim boti webhook'i o'chirildi"))
                return
            await bot.set_webhook(
                f"{settings.SITE_URL}/tg/edu-webhook/", secret_token=_webhook_secret(settings.TELEGRAM_EDU_BOT_TOKEN),
                allowed_updates=get_dispatcher().resolve_used_update_types(), drop_pending_updates=False,
            )
            await setup_bot(bot)
            me = await bot.get_me()
            info = await bot.get_webhook_info()
            self.stdout.write(self.style.SUCCESS(f"Ta'lim boti @{me.username}: {info.url} · kutilmoqda: {info.pending_update_count}"))
        finally:
            await bot.session.close()

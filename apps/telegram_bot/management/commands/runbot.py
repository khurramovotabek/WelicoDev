"""Botni polling rejimida ishga tushiradi (lokal muhit va webhook'siz serverlar uchun).

    python manage.py runbot
"""

import asyncio
import logging

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "@welicodevbot ni polling rejimida ishga tushiradi"

    def handle(self, *args, **options):
        if not settings.TELEGRAM_BOT_TOKEN:
            raise CommandError("TELEGRAM_BOT_TOKEN .env faylida ko'rsatilmagan")
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
        asyncio.run(self._run())

    async def _run(self):
        from apps.telegram_bot.bot.dispatcher import get_bot, get_dispatcher, setup_bot

        bot, dp = get_bot(), get_dispatcher()
        me = await bot.get_me()
        self.stdout.write(self.style.SUCCESS(f"Bot ishga tushdi: @{me.username}"))
        await bot.delete_webhook(drop_pending_updates=False)
        await setup_bot(bot)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

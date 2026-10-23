"""Ta'lim boti (@welicodev_educationbot): Bot va Dispatcher. Webhook: /tg/edu-webhook/."""

import re
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeDefault, CallbackQuery, Message, TelegramObject
from asgiref.sync import sync_to_async
from django.conf import settings

from . import db, handlers
from .texts import t

_bot = None
_dp = None


class EduUserMiddleware(BaseMiddleware):
    """Django foydalanuvchisini topadi, ta'lim botini ochganini belgilaydi va `user`, `lang` ni beradi."""

    async def __call__(self, handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]], event: TelegramObject, data: dict[str, Any]) -> Any:
        tg_user = data.get("event_from_user")
        if tg_user is None or tg_user.is_bot:
            return await handler(event, data)
        user = await sync_to_async(db.touch_user)(tg_user)
        data["user"] = user
        data["lang"] = user.language or "uz"
        if user.is_blocked:
            text = t("blocked", data["lang"])
            if isinstance(event, Message):
                await event.answer(text)
            elif isinstance(event, CallbackQuery):
                await event.answer(re.sub(r"<[^>]+>", "", text), show_alert=True)
            return None
        return await handler(event, data)


def get_bot() -> Bot:
    global _bot
    if _bot is None:
        _bot = Bot(settings.TELEGRAM_EDU_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML, link_preview_is_disabled=True))
    return _bot


def get_dispatcher() -> Dispatcher:
    global _dp
    if _dp is None:
        # Admin post yozish holati Redis'da: uvicorn bir nechta worker'da ishlaydi
        from aiogram.fsm.storage.base import DefaultKeyBuilder
        from aiogram.fsm.storage.redis import RedisStorage

        storage = RedisStorage.from_url(settings.REDIS_URL.rsplit("/", 1)[0] + "/2", key_builder=DefaultKeyBuilder(prefix="edufsm"))
        dp = Dispatcher(storage=storage)
        dp.message.outer_middleware(EduUserMiddleware())
        dp.callback_query.outer_middleware(EduUserMiddleware())
        dp.include_router(handlers.router)
        _dp = dp
    return _dp


COMMANDS = {
    "uz": [("start", "Boshlash"), ("courses", "Kurslar"), ("my", "Mening kurslarim"), ("homework", "Uyga vazifalar"), ("lang", "Til"), ("help", "Yordam")],
    "ru": [("start", "Начать"), ("courses", "Курсы"), ("my", "Мои курсы"), ("homework", "Домашние задания"), ("lang", "Язык"), ("help", "Помощь")],
    "en": [("start", "Start"), ("courses", "Courses"), ("my", "My courses"), ("homework", "Homework"), ("lang", "Language"), ("help", "Help")],
}

DESCRIPTION = {
    "uz": "WeliCoDev Academy — o'zbek tilidagi dasturlash kurslari. Kurslarga yoziling, progressingizni kuzating va uyga vazifa natijalarini shu yerda oling.",
    "ru": "WeliCoDev Academy — курсы программирования. Записывайтесь на курсы, следите за прогрессом и получайте результаты домашних заданий.",
    "en": "WeliCoDev Academy — programming courses. Enroll, track your progress and get homework results right here.",
}


async def setup_bot(bot: Bot):
    """Buyruqlar ro'yxati va bot tavsifi (har til uchun)."""
    for lang, items in COMMANDS.items():
        code = None if lang == "uz" else lang
        await bot.set_my_commands([BotCommand(command=c, description=d) for c, d in items],
                                  scope=BotCommandScopeDefault(), language_code=code)
        await bot.set_my_description(DESCRIPTION[lang], language_code=code)
        await bot.set_my_short_description(DESCRIPTION[lang][:120], language_code=code)

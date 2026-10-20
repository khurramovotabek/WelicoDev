from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from . import db
from .texts import t


class UserMiddleware(BaseMiddleware):
    """Har bir xabar/tugma uchun Django foydalanuvchisini topadi va `user`, `lang` ni handlerga beradi."""

    async def __call__(self, handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]], event: TelegramObject, data: dict[str, Any]) -> Any:
        tg_user = data.get("event_from_user")
        if tg_user is None or tg_user.is_bot:
            return await handler(event, data)

        settings_obj = await db.get_settings()
        user, created = await db.touch_user(tg_user)
        data["user"] = user
        data["lang"] = user.language or "uz"
        data["is_new"] = created

        if not settings_obj.is_enabled and not user.is_staff:
            await _answer(event, settings_obj.maintenance_text)
            return None
        if user.is_blocked:
            await _answer(event, t("blocked", data["lang"]))
            return None
        return await handler(event, data)


async def _answer(event, text):
    if isinstance(event, Message):
        await event.answer(text)
    elif isinstance(event, CallbackQuery):
        await event.answer(text, show_alert=True)

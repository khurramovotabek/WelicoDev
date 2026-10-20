"""Bot va Dispatcher yaratish. Polling (lokal) va webhook (prod) ikkalasi shu yerdan foydalanadi."""

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand, BotCommandScopeDefault, MenuButtonWebApp, WebAppInfo
from django.conf import settings

from .handlers import login, menu, start
from .middlewares import UserMiddleware

_bot = None
_dp = None


def get_bot() -> Bot:
    global _bot
    if _bot is None:
        _bot = Bot(settings.TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML, link_preview_is_disabled=True))
    return _bot


def get_dispatcher() -> Dispatcher:
    global _dp
    if _dp is None:
        storage = RedisStorage.from_url(settings.REDIS_URL.rsplit("/", 1)[0] + "/2")
        dp = Dispatcher(storage=storage)
        dp.message.outer_middleware(UserMiddleware())
        dp.callback_query.outer_middleware(UserMiddleware())
        # Tartib muhim: start (ro'yxatdan o'tish holatlari) -> login -> menu (erkin matn oxirida)
        dp.include_routers(start.router, login.router, menu.router)
        _dp = dp
    return _dp


COMMANDS = {
    "uz": [("start", "Boshlash"), ("login", "Saytga kirish kodi"), ("courses", "Kurslar"), ("profile", "Profilim"), ("lang", "Til"), ("help", "Yordam")],
    "ru": [("start", "Начать"), ("login", "Код для входа"), ("courses", "Курсы"), ("profile", "Профиль"), ("lang", "Язык"), ("help", "Помощь")],
    "en": [("start", "Start"), ("login", "Sign-in code"), ("courses", "Courses"), ("profile", "My profile"), ("lang", "Language"), ("help", "Help")],
}


async def setup_bot(bot: Bot):
    """Buyruqlar ro'yxati va Mini App menyu tugmasini o'rnatadi."""
    for lang, items in COMMANDS.items():
        cmds = [BotCommand(command=c, description=d) for c, d in items]
        await bot.set_my_commands(cmds, scope=BotCommandScopeDefault(), language_code=None if lang == "uz" else lang)
    if settings.SITE_URL.startswith("https://"):
        from apps.telegram_bot.models import BotSettings
        from asgiref.sync import sync_to_async

        s = await sync_to_async(BotSettings.load)()
        await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text=s.mini_app_button_text, web_app=WebAppInfo(url=f"{settings.SITE_URL}/uz/app/")))

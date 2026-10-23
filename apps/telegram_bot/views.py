import json
import logging
import secrets

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)


def _webhook_secret():
    # Token'dan kelib chiqadigan barqaror maxfiy kalit: Telegram har so'rovda shu sarlavhani yuboradi
    import hashlib

    return hashlib.sha256(f"wcd-webhook:{settings.TELEGRAM_BOT_TOKEN}".encode()).hexdigest()[:48]


@csrf_exempt
async def webhook(request):
    if request.method != "POST":
        return HttpResponse(status=405)
    if not secrets.compare_digest(request.headers.get("X-Telegram-Bot-Api-Secret-Token", ""), _webhook_secret()):
        return HttpResponseForbidden()
    from aiogram.types import Update

    from .bot.dispatcher import get_bot, get_dispatcher

    bot, dp = get_bot(), get_dispatcher()
    try:
        update = Update.model_validate(json.loads(request.body), context={"bot": bot})
        await dp.feed_update(bot, update)
    except Exception:  # noqa: BLE001
        # 500 qaytsa Telegram shu update'ni qayta-qayta yuboradi va navbat tiqilib qoladi
        logger.exception("Telegram update ishlovida xato")
    return HttpResponse("ok")

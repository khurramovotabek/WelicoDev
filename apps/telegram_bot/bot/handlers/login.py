"""Saytga kirish: deep link orqali tasdiqlash va /login bilan kod olish."""

from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from django.conf import settings
from django.utils import timezone

from .. import db
from ..keyboards import confirm_kb, site_kb
from ..texts import TEXTS, t

router = Router(name="login")


def _device(user_agent):
    ua = user_agent or ""
    browser = next((b for b in ("Edg", "OPR", "Chrome", "Firefox", "Safari") if b in ua), "Browser")
    browser = {"Edg": "Edge", "OPR": "Opera"}.get(browser, browser)
    os_name = next((o for o in ("Windows", "Android", "iPhone", "iPad", "Mac OS", "Linux") if o in ua), "")
    return f"{browser}{' · ' + os_name if os_name else ''}"


async def send_login_confirmation(message: Message, user, lang, token_hex):
    req = await db.get_login_request(token_hex)
    if req is None or req.is_expired or req.status != "pending":
        await message.answer(t("login_expired", lang))
        return
    text = t(
        "login_confirm", lang,
        site=escape(settings.SITE_URL.replace("https://", "").replace("http://", "")),
        device=escape(_device(req.user_agent)),
        ip=escape(req.ip_address or "—"),
        time=timezone.localtime(req.created_at).strftime("%d.%m.%Y %H:%M"),
    )
    await message.answer(text, reply_markup=confirm_kb(req.pk, lang))


@router.callback_query(F.data.startswith("login:"))
async def on_login_decision(call: CallbackQuery, user, lang):
    _prefix, action, request_id = call.data.split(":")
    if not user.is_registered:
        await call.answer(t("need_register", lang), show_alert=True)
        return
    req, code = await db.resolve_login_request(int(request_id), user.pk, approve=(action == "ok"))
    if req is None:
        await call.message.edit_text(t("login_expired", lang))
        await call.answer()
        return
    if action == "ok":
        await call.message.edit_text(t("login_confirmed", lang, code=code, ttl=settings.LOGIN_CODE_TTL_SECONDS))
    else:
        await call.message.edit_text(t("login_rejected", lang))
    await call.answer()


@router.message(Command("login"))
@router.message(F.text.in_({v for v in TEXTS["btn_login"].values()}))
async def cmd_login(message: Message, user, lang):
    if not user.is_registered:
        await message.answer(t("need_register", lang))
        return
    code = await db.issue_code(user.pk)
    await message.answer(t("login_code", lang, code=code, ttl=settings.LOGIN_CODE_TTL_SECONDS), reply_markup=site_kb(lang, "/accounts/login/"))

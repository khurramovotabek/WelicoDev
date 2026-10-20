"""Asosiy menyu: profil, kurslar, til, murojaat va erkin xabarlar."""

from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ChatMemberUpdated, InlineKeyboardButton, InlineKeyboardMarkup, Message

from .. import db
from ..keyboards import lang_kb, main_menu, site_kb
from ..texts import TEXTS, t

router = Router(name="menu")


class Contact(StatesGroup):
    waiting = State()


def _btn(key):
    return F.text.in_(set(TEXTS[key].values()))


@router.message(Command("help"))
async def cmd_help(message: Message, lang):
    settings_obj = await db.get_settings()
    await message.answer(settings_obj.help_text, reply_markup=main_menu(lang))


@router.message(Command("profile"))
@router.message(_btn("btn_profile"))
async def cmd_profile(message: Message, user, lang):
    if not user.is_registered:
        await message.answer(t("need_register", lang))
        return
    s = await db.profile_stats(user.pk)
    u = s["user"]
    text = t("profile", lang, name=escape(u.get_full_name()), phone=escape(u.phone or "—"),
             joined=u.date_joined.strftime("%d.%m.%Y"), courses=s["courses"], comments=s["comments"])
    await message.answer(text, reply_markup=site_kb(lang, "/accounts/profile/"))


@router.message(Command("courses"))
@router.message(_btn("btn_courses"))
async def cmd_courses(message: Message, lang):
    courses = await db.published_courses(lang)
    if not courses:
        await message.answer(t("courses_empty", lang))
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"🎓 {title}", url=url)] for title, url in courses])
    await message.answer(t("courses_header", lang), reply_markup=kb)


@router.message(Command("lang"))
@router.message(_btn("btn_lang"))
async def cmd_lang(message: Message, lang):
    await message.answer(t("choose_lang", lang), reply_markup=lang_kb())


@router.message(Command("contact"))
@router.message(_btn("btn_contact"))
async def cmd_contact(message: Message, state: FSMContext, lang):
    await state.set_state(Contact.waiting)
    await message.answer(t("contact_prompt", lang))


@router.message(F.text & ~F.text.startswith("/"))
async def on_free_text(message: Message, state: FSMContext, user, lang):
    """Menyudan tashqari har qanday matn adminga murojaat sifatida saqlanadi."""
    await state.set_state(None)
    await db.save_incoming(user.pk, message.text[:4000], message.message_id)
    settings_obj = await db.get_settings()
    if settings_obj.notify_contact_message:
        name = escape(user.get_full_name() or user.username)
        handle = f" · @{escape(user.telegram_username)}" if user.telegram_username else ""
        for chat_id in await db.admin_chat_ids():
            if chat_id == user.telegram_id:
                continue
            try:
                await message.bot.send_message(chat_id, f"💬 <b>Botga xabar</b> — {name}{handle}\n\n{escape(message.text[:3000])}")
            except Exception:  # noqa: BLE001
                pass
    await message.answer(t("message_received", lang), reply_markup=main_menu(lang))


@router.my_chat_member()
async def on_chat_member(update: ChatMemberUpdated):
    # Foydalanuvchi botni to'xtatsa, ommaviy xabarlar unga yuborilmaydi
    if update.new_chat_member.status == "kicked":
        await db.mark_blocked(update.from_user.id)

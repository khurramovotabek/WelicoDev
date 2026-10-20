"""/start, til tanlash va ro'yxatdan o'tish (ism → familiya → telefon)."""

from aiogram import F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from .. import db
from ..keyboards import REMOVE, lang_kb, main_menu, name_kb, phone_kb, site_kb
from ..texts import t
from .login import send_login_confirmation

router = Router(name="start")



class Reg(StatesGroup):
    language = State()
    first_name = State()
    last_name = State()
    phone = State()


def _clean_name(text):
    text = " ".join((text or "").split())
    if 2 <= len(text) <= 40 and all(ch.isalpha() or ch in " '-ʻʼ‘’" for ch in text):
        return text.title() if text.islower() else text
    return None


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, state: FSMContext, user, lang, is_new):
    payload = command.args or ""
    await state.update_data(pending_login=payload[6:] if payload.startswith("login_") else None)
    settings_obj = await db.get_settings()

    if not user.is_registered:
        if is_new:
            await message.answer(settings_obj.welcome_text)
        await state.set_state(Reg.language)
        await message.answer(t("choose_lang", lang), reply_markup=lang_kb())
        return

    await state.set_state(None)
    data = await state.get_data()
    if data.get("pending_login"):
        await send_login_confirmation(message, user, lang, data["pending_login"])
        await state.update_data(pending_login=None)
        return
    await message.answer(settings_obj.welcome_text, reply_markup=main_menu(lang))
    await message.answer(t("menu", lang), reply_markup=site_kb(lang))


@router.callback_query(F.data.startswith("lang:"))
async def on_language(call: CallbackQuery, state: FSMContext, user):
    lang = call.data.split(":", 1)[1]
    if lang not in ("uz", "ru", "en"):
        lang = "uz"
    await db.set_language(user.pk, lang)
    await call.answer(t("lang_saved", lang))
    await call.message.edit_text(t("lang_saved", lang))
    if await state.get_state() == Reg.language.state or not user.is_registered:
        await state.set_state(Reg.first_name)
        suggestion = _clean_name(call.from_user.first_name)
        await call.message.answer(t("ask_first_name", lang), reply_markup=name_kb(suggestion) if suggestion else REMOVE)
    else:
        await call.message.answer(t("menu", lang), reply_markup=main_menu(lang))


@router.message(Reg.first_name, F.text)
async def on_first_name(message: Message, state: FSMContext, lang):
    name = _clean_name(message.text)
    if not name:
        await message.answer(t("invalid_name", lang))
        return
    await state.update_data(first_name=name)
    await state.set_state(Reg.last_name)
    suggestion = _clean_name(message.from_user.last_name)
    await message.answer(t("ask_last_name", lang, name=name), reply_markup=name_kb(suggestion) if suggestion else REMOVE)


@router.message(Reg.last_name, F.text)
async def on_last_name(message: Message, state: FSMContext, lang):
    name = _clean_name(message.text)
    if not name:
        await message.answer(t("invalid_name", lang))
        return
    await state.update_data(last_name=name)
    await state.set_state(Reg.phone)
    await message.answer(t("ask_phone", lang), reply_markup=phone_kb(lang))


@router.message(Reg.phone, F.contact)
async def on_phone(message: Message, state: FSMContext, user, lang):
    # Boshqa odamning kontaktini yuborib ro'yxatdan o'tishning oldini olish
    if message.contact.user_id != message.from_user.id:
        await message.answer(t("phone_not_own", lang), reply_markup=phone_kb(lang))
        return
    data = await state.get_data()
    user = await db.complete_registration(user.pk, data["first_name"], data["last_name"], message.contact.phone_number)
    await state.set_state(None)
    settings_obj = await db.get_settings()
    await message.answer(t("registered", lang, name=user.first_name), reply_markup=main_menu(lang))
    await message.answer(settings_obj.registered_text)
    await fetch_avatar(message.bot, user)
    await notify_new_user(message.bot, user, settings_obj)
    if data.get("pending_login"):
        await state.update_data(pending_login=None)
        await send_login_confirmation(message, user, lang, data["pending_login"])
    else:
        await message.answer(t("menu", lang), reply_markup=site_kb(lang))


@router.message(Reg.phone)
async def on_phone_text(message: Message, lang):
    await message.answer(t("phone_use_button", lang), reply_markup=phone_kb(lang))


async def fetch_avatar(bot, user):
    """Telegram profil rasmini avatar sifatida saqlaydi (foydalanuvchi o'zi yuklamagan bo'lsa)."""
    if user.avatar:
        return
    try:
        photos = await bot.get_user_profile_photos(user.telegram_id, limit=1)
        if not photos.total_count:
            return
        biggest = photos.photos[0][-1]
        file = await bot.get_file(biggest.file_id)
        data = await bot.download_file(file.file_path)
        await db.save_avatar(user.pk, data.read())
    except Exception:  # noqa: BLE001 - avatar bo'lmasa ro'yxatdan o'tish to'xtamasin
        pass


async def notify_new_user(bot, user, settings_obj):
    if not settings_obj.notify_new_user:
        return
    from html import escape

    text = f"👤 <b>Yangi foydalanuvchi</b>\n\n{escape(user.get_full_name())}\n📱 {escape(user.phone)}"
    if user.telegram_username:
        text += f"\n@{escape(user.telegram_username)}"
    for chat_id in await db.admin_chat_ids():
        if chat_id == user.telegram_id:
            continue
        try:
            await bot.send_message(chat_id, text)
        except Exception:  # noqa: BLE001 - admin xabari yetmasa, ro'yxatdan o'tish to'xtamasin
            pass


@router.message(F.contact)
async def on_contact_any_state(message: Message, state: FSMContext, user, lang):
    """Mini App'dagi "Raqamni ulashish" (WebApp.requestContact) kontaktni botga shu yerda yuboradi."""
    if message.contact.user_id != message.from_user.id:
        await message.answer(t("phone_not_own", lang))
        return
    first = user.first_name or message.from_user.first_name or ""
    last = user.last_name or message.from_user.last_name or ""
    was_registered = user.is_registered
    user = await db.complete_registration(user.pk, first, last, message.contact.phone_number)
    await state.set_state(None)
    if not was_registered:
        settings_obj = await db.get_settings()
        await message.answer(t("registered", lang, name=user.first_name or "👋"), reply_markup=main_menu(lang))
        await fetch_avatar(message.bot, user)
        await notify_new_user(message.bot, user, settings_obj)

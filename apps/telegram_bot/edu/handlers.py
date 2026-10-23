"""@welicodev_educationbot: kurslar, yozilish, progress, uyga vazifalar va admin boshqaruvi."""

import re
from html import escape

from aiogram import F, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery, ChatMemberUpdated, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, Message,
    ReplyKeyboardMarkup,
)
from asgiref.sync import sync_to_async
from django.conf import settings

from ..bot.texts import LANG_BUTTONS
from . import db
from .texts import TEXTS, t

router = Router(name="edu")


class ComposePost(StatesGroup):
    waiting = State()


def _btn(key):
    return F.text.in_(set(TEXTS[key].values()))


def menu(lang, is_staff=False):
    rows = [
        [KeyboardButton(text=t("btn_courses", lang)), KeyboardButton(text=t("btn_my", lang))],
        [KeyboardButton(text=t("btn_homework", lang)), KeyboardButton(text=t("btn_lang", lang))],
    ]
    if is_staff:
        rows.append([KeyboardButton(text=t("btn_admin", lang))])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def _kb(buttons):
    rows = []
    for kind, text, value in buttons:
        btn = InlineKeyboardButton(text=text, url=value) if kind == "url" else InlineKeyboardButton(text=text, callback_data=value)
        rows.append([btn])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _register_kb(lang):
    url = f"https://t.me/{settings.TELEGRAM_BOT_USERNAME}?start=edu"
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t("btn_register", lang), url=url)]])


async def _need_registration(event, user, lang):
    """Kurs amallari uchun asosiy botda ro'yxatdan o'tish (ism + telefon) shart."""
    if user.is_registered or user.is_staff:
        return False
    target = event.message if isinstance(event, CallbackQuery) else event
    await target.answer(t("need_register", lang), reply_markup=_register_kb(lang))
    if isinstance(event, CallbackQuery):
        await event.answer()
    return True


# --------------------------------------------------------------------------- Umumiy

@router.message(CommandStart())
async def cmd_start(message: Message, user, lang):
    if not user.is_registered and not user.is_staff:
        await message.answer(t("need_register", lang), reply_markup=_register_kb(lang))
        return
    await message.answer(t("welcome", lang, name=escape(user.first_name or user.username)), reply_markup=menu(lang, user.is_staff))


@router.message(Command("help"))
async def cmd_help(message: Message, user, lang):
    await message.answer(t("help", lang, main=settings.TELEGRAM_BOT_USERNAME), reply_markup=menu(lang, user.is_staff))


@router.message(Command("lang"))
@router.message(_btn("btn_lang"))
async def cmd_lang(message: Message, lang):
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=label, callback_data=f"lang:{code}") for code, label in LANG_BUTTONS]])
    await message.answer(t("choose_lang", lang), reply_markup=kb)


@router.callback_query(F.data.startswith("lang:"))
async def on_lang(cb: CallbackQuery, user):
    lang = cb.data.split(":", 1)[1]
    if lang not in ("uz", "ru", "en"):
        await cb.answer()
        return
    await sync_to_async(db.set_language)(user.pk, lang)
    await cb.answer(t("lang_saved", lang))
    await cb.message.answer(t("lang_saved", lang), reply_markup=menu(lang, user.is_staff))


# --------------------------------------------------------------------------- Kurslar

async def _course_list_kb(lang):
    courses = await sync_to_async(db.course_list)(lang)
    if not courses:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{'🆓' if free else '💎'} {title}", callback_data=f"c:{pk}")] for pk, title, free in courses
    ])


@router.message(Command("courses"))
@router.message(_btn("btn_courses"))
async def cmd_courses(message: Message, lang):
    kb = await _course_list_kb(lang)
    await message.answer(t("courses_header", lang) if kb else t("courses_empty", lang), reply_markup=kb)


@router.callback_query(F.data == "cl")
async def on_course_list(cb: CallbackQuery, lang):
    kb = await _course_list_kb(lang)
    await cb.message.edit_text(t("courses_header", lang) if kb else t("courses_empty", lang), reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data.regexp(r"^c:\d+$"))
async def on_course(cb: CallbackQuery, user, lang):
    card = await sync_to_async(db.course_card)(user, int(cb.data[2:]), lang)
    if card is None:
        await cb.answer(t("not_found", lang), show_alert=True)
        return
    text, buttons = card
    await cb.message.edit_text(text, reply_markup=_kb(buttons))
    await cb.answer()


@router.callback_query(F.data.regexp(r"^en:\d+$"))
async def on_enroll(cb: CallbackQuery, user, lang):
    if await _need_registration(cb, user, lang):
        return
    result = await sync_to_async(db.enroll_free)(user, int(cb.data[3:]), lang)
    if result is None:
        await cb.answer(t("not_found", lang), show_alert=True)
        return
    title, url = result
    await cb.message.answer(t("enrolled", lang, title=escape(title)), reply_markup=_kb([("url", t("btn_continue", lang), url)]))
    await cb.answer()


@router.callback_query(F.data.regexp(r"^rq:\d+$"))
async def on_request(cb: CallbackQuery, user, lang):
    if await _need_registration(cb, user, lang):
        return
    ref = await sync_to_async(db.request_access)(user, int(cb.data[3:]))
    if ref is None:
        await cb.answer(t("not_found", lang), show_alert=True)
        return
    await cb.message.answer(t("requested", lang, ref=ref))
    await cb.answer()


@router.message(Command("my"))
@router.message(_btn("btn_my"))
async def cmd_my(message: Message, user, lang):
    rows = await sync_to_async(db.my_courses)(user, lang)
    if not rows:
        await message.answer(t("my_empty", lang))
        return
    text = t("my_header", lang)
    buttons = []
    for r in rows:
        filled = round(r["progress"] / 10)
        bar = "▰" * filled + "▱" * (10 - filled)
        text += t("my_row", lang, title=escape(r["title"]), bar=bar, p=r["progress"], done=t("done_mark", lang) if r["done"] else "")
        if not r["done"]:
            buttons.append(("url", f"▶️ {r['title'][:40]}", r["url"]))
    await message.answer(text, reply_markup=_kb(buttons) if buttons else None)


@router.message(Command("homework"))
@router.message(_btn("btn_homework"))
async def cmd_homework(message: Message, user, lang):
    rows = await sync_to_async(db.my_homework)(user, lang)
    if not rows:
        await message.answer(t("hw_empty", lang))
        return
    statuses = t("hw_status", lang)
    text = t("hw_header", lang)
    for course, lesson, status, feedback in rows:
        text += f"\n\n<b>{escape(lesson)}</b>\n<i>{escape(course)}</i> · {statuses.get(status, status)}"
        if feedback:
            text += f"\n💬 {escape(feedback[:300])}"
    await message.answer(text)


# --------------------------------------------------------------------------- Admin

async def _staff_only(event, user, lang):
    if user.is_staff:
        return True
    if isinstance(event, CallbackQuery):
        await event.answer(t("no_access", lang), show_alert=True)
    else:
        await event.answer(t("no_access", lang))
    return False


@router.message(Command("admin"))
@router.message(_btn("btn_admin"))
async def cmd_admin(message: Message, user, lang):
    if not await _staff_only(message, user, lang):
        return
    s = await sync_to_async(db.admin_stats)()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_adm_requests", lang, n=s["requests"]), callback_data="adm:req"),
         InlineKeyboardButton(text=t("btn_adm_homework", lang, n=s["homework"]), callback_data="adm:hw")],
        [InlineKeyboardButton(text=t("btn_adm_post", lang), callback_data="adm:post")],
        [InlineKeyboardButton(text=t("btn_adm_lessons", lang), callback_data="adm:an:lesson"),
         InlineKeyboardButton(text=t("btn_adm_courses", lang), callback_data="adm:an:course")],
        [InlineKeyboardButton(text=t("btn_dashboard", lang), url=f"{settings.SITE_URL}/{lang}/dashboard/courses/")],
    ])
    await message.answer(t("admin_panel", lang, **s), reply_markup=kb)


# --------------------------------------------------------------------------- Kanal: post va e'lonlar

@router.callback_query(F.data == "adm:post")
async def on_compose(cb: CallbackQuery, state: FSMContext, user, lang):
    if not await _staff_only(cb, user, lang):
        return
    await cb.answer()
    chat = await sync_to_async(db.edu_channel)()
    if not chat:
        await cb.message.answer(t("no_channel", lang))
        return
    await state.set_state(ComposePost.waiting)
    await cb.message.answer(t("post_prompt", lang, channel=escape(chat)))


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext, user, lang):
    await state.clear()
    await message.answer(t("cancelled", lang), reply_markup=menu(lang, user.is_staff))


@router.message(StateFilter(ComposePost.waiting))
async def on_post_draft(message: Message, state: FSMContext, user, lang):
    if not user.is_staff:
        await state.clear()
        return
    html = message.html_text if (message.text or message.caption) else ""
    await state.update_data(src_chat=message.chat.id, src_id=message.message_id, html=html)
    # Admin chatiga nusxa — kanalda qanday ko'rinishini oldindan ko'rish
    await message.bot.copy_message(message.chat.id, message.chat.id, message.message_id)
    await message.answer(t("post_preview", lang), reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_publish", lang), callback_data="pub:go"),
         InlineKeyboardButton(text=t("btn_publish_silent", lang), callback_data="pub:silent")],
        [InlineKeyboardButton(text=t("btn_cancel", lang), callback_data="pub:no")],
    ]))


@router.callback_query(F.data.in_({"pub:go", "pub:silent", "pub:no"}))
async def on_publish(cb: CallbackQuery, state: FSMContext, user, lang):
    if not await _staff_only(cb, user, lang):
        return
    data = await state.get_data()
    await state.clear()
    await cb.answer()
    if cb.data == "pub:no" or not data.get("src_id"):
        await cb.message.edit_text(t("cancelled", lang))
        return
    chat = await sync_to_async(db.edu_channel)()
    try:
        sent = await cb.bot.copy_message(chat, data["src_chat"], data["src_id"], disable_notification=cb.data == "pub:silent")
    except Exception as e:  # noqa: BLE001 — Telegram xatosi adminga ko'rsatiladi
        await cb.message.edit_text(t("post_failed", lang, error=escape(str(e)[:200])))
        return
    await sync_to_async(db.record_manual_post)(user, data.get("html", ""), sent.message_id)
    link = f"https://t.me/{chat.lstrip('@')}/{sent.message_id}" if chat.startswith("@") else chat
    await cb.message.edit_text(t("post_done", lang, link=link))


@router.callback_query(F.data.regexp(r"^adm:an:(lesson|course)$"))
async def on_announce_list(cb: CallbackQuery, user, lang):
    if not await _staff_only(cb, user, lang):
        return
    await cb.answer()
    if not await sync_to_async(db.edu_channel)():
        await cb.message.answer(t("no_channel", lang))
        return
    kind = cb.data.rsplit(":", 1)[1]
    items = await sync_to_async(db.unannounced)(kind)
    if not items:
        await cb.message.answer(t("nothing_to_announce", lang))
        return
    prefix = "pl" if kind == "lesson" else "pc"
    await cb.message.answer(t("pick_announce", lang), reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=title, callback_data=f"{prefix}:{pk}")] for pk, title in items
    ]))


@router.callback_query(F.data.regexp(r"^p[lc]:\d+$"))
async def on_announce(cb: CallbackQuery, user, lang):
    if not await _staff_only(cb, user, lang):
        return
    kind = "lesson" if cb.data.startswith("pl:") else "course"
    post = await sync_to_async(db.announce)(kind, int(cb.data[3:]), user)
    await cb.answer()
    if post is None:
        await cb.message.answer(t("not_found", lang))
    elif post.status == "sent":
        chat = await sync_to_async(db.edu_channel)()
        link = f"https://t.me/{chat.lstrip('@')}/{post.message_id}" if chat.startswith("@") else chat
        await cb.message.answer(t("post_done", lang, link=link))
    else:
        await cb.message.answer(t("post_failed", lang, error=escape(post.error or "?")))


@router.callback_query(F.data == "adm:req")
async def on_adm_requests(cb: CallbackQuery, user, lang):
    if not await _staff_only(cb, user, lang):
        return
    reqs = await sync_to_async(db.pending_requests)()
    await cb.answer()
    if not reqs:
        await cb.message.answer(t("adm_nothing", lang))
    for r in reqs:
        text = (f"💳 <code>{r.reference}</code> · <b>{escape(r.course.title)}</b>\n"
                f"👤 {escape(r.user.display_name)}" + (f" · {escape(r.user.phone)}" if r.user.phone else "")
                + (f" · @{escape(r.user.telegram_username)}" if r.user.telegram_username else "")
                + (f"\n📝 {escape(r.note)}" if r.note else ""))
        await cb.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=t("btn_approve", lang), callback_data=f"ar:ok:{r.pk}"),
            InlineKeyboardButton(text=t("btn_reject", lang), callback_data=f"ar:no:{r.pk}"),
        ]]))


@router.callback_query(F.data == "adm:hw")
async def on_adm_homework(cb: CallbackQuery, user, lang):
    if not await _staff_only(cb, user, lang):
        return
    subs = await sync_to_async(db.pending_homework)()
    await cb.answer()
    if not subs:
        await cb.message.answer(t("adm_nothing", lang))
    for s in subs:
        text = (f"📝 <b>{escape(s.user.display_name)}</b>\n{escape(s.lesson.course.title)} → {escape(s.lesson.title)}"
                + (f"\n\n{escape(s.text[:1200])}" if s.text else "") + (f"\n🔗 {escape(s.link)}" if s.link else ""))
        url = f"{settings.SITE_URL}/admin/education/homeworksubmission/{s.pk}/change/"
        await cb.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t("btn_hw_ok", lang), callback_data=f"hw:ok:{s.pk}"),
             InlineKeyboardButton(text=t("btn_hw_redo", lang), callback_data=f"hw:no:{s.pk}")],
            [InlineKeyboardButton(text=t("btn_open", lang), url=url)],
        ]))


async def _close_card(cb: CallbackQuery, verdict, user):
    """Admin xabaridagi tugmalarni olib tashlab, natijani yozib qo'yadi."""
    original = cb.message.html_text if cb.message and cb.message.text else ""
    text = original + t("adm_done", "uz", verdict=verdict, by=escape(user.first_name or user.username))
    try:
        await cb.message.edit_text(text, reply_markup=None)
    except Exception:  # noqa: BLE001 — xabar o'zgarmagan yoki juda eski bo'lsa ham asosiy amal bajarilgan
        pass


@router.callback_query(F.data.regexp(r"^ar:(ok|no):\d+$"))
async def on_access_decision(cb: CallbackQuery, user, lang):
    if not await _staff_only(cb, user, lang):
        return
    _, action, pk = cb.data.split(":")
    req = await sync_to_async(db.resolve_request)(user, int(pk), action == "ok")
    if req is None:
        await cb.answer(t("adm_already", lang), show_alert=True)
        return
    verdict = t("v_granted", lang) if action == "ok" else t("v_rejected", lang)
    await cb.answer(re.sub(r"<[^>]+>", "", verdict))
    await _close_card(cb, verdict, user)


@router.callback_query(F.data.regexp(r"^hw:(ok|no):\d+$"))
async def on_homework_decision(cb: CallbackQuery, user, lang):
    if not await _staff_only(cb, user, lang):
        return
    _, action, pk = cb.data.split(":")
    sub = await sync_to_async(db.review_homework)(user, int(pk), action == "ok")
    if sub is None:
        await cb.answer(t("adm_already", lang), show_alert=True)
        return
    verdict = t("v_hw_ok", lang) if action == "ok" else t("v_hw_redo", lang)
    await cb.answer(verdict)
    await _close_card(cb, verdict, user)


# --------------------------------------------------------------------------- Qolganlari

@router.message(F.text)
async def on_other(message: Message, user, lang):
    await message.answer(t("unknown", lang, main=settings.TELEGRAM_BOT_USERNAME), reply_markup=menu(lang, user.is_staff))


@router.my_chat_member()
async def on_chat_member(update: ChatMemberUpdated):
    if update.new_chat_member.status == "kicked":
        await sync_to_async(db.mark_blocked)(update.from_user.id)

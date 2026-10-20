from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, WebAppInfo,
)
from django.conf import settings

from .texts import LANG_BUTTONS, t


def lang_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=label, callback_data=f"lang:{code}") for code, label in LANG_BUTTONS]])


def name_kb(name):
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=name)]], resize_keyboard=True, one_time_keyboard=True)


def phone_kb(lang):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t("btn_share_phone", lang), request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True,
    )


def main_menu(lang):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t("btn_login", lang)), KeyboardButton(text=t("btn_courses", lang))],
            [KeyboardButton(text=t("btn_profile", lang)), KeyboardButton(text=t("btn_contact", lang))],
            [KeyboardButton(text=t("btn_lang", lang))],
        ],
        resize_keyboard=True,
    )


def confirm_kb(request_id, lang):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("btn_confirm", lang), callback_data=f"login:ok:{request_id}"),
        InlineKeyboardButton(text=t("btn_reject", lang), callback_data=f"login:no:{request_id}"),
    ]])


def site_kb(lang, path="/"):
    url = f"{settings.SITE_URL}/{lang}{path}"
    rows = [[InlineKeyboardButton(text=t("btn_open_site", lang), url=url)]]
    # Mini App faqat HTTPS orqali ishlaydi (Telegram talabi)
    if settings.SITE_URL.startswith("https://"):
        rows.append([InlineKeyboardButton(text=t("btn_open_app", lang), web_app=WebAppInfo(url=f"{settings.SITE_URL}/{lang}/app/"))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


REMOVE = ReplyKeyboardRemove()

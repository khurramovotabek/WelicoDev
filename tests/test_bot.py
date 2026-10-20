"""@welicodevbot handlerlari: Telegram API soxta session bilan almashtiriladi."""

import itertools

from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.methods import AnswerCallbackQuery, EditMessageText, SendMessage, TelegramMethod
from aiogram.types import CallbackQuery, Chat, Contact, Message, Update, User as TgUser
from asgiref.sync import async_to_sync
from django.test import TransactionTestCase, override_settings
from django.utils import timezone

from apps.accounts.models import LoginRequest, User
from apps.telegram_bot.models import BotMessage

_ids = itertools.count(1)


class FakeSession(BaseSession):
    """Botning barcha so'rovlarini yozib oladi va soxta javob qaytaradi."""

    def __init__(self):
        super().__init__()
        self.calls = []

    async def make_request(self, bot, method: TelegramMethod, timeout=None):
        self.calls.append(method)
        if isinstance(method, (SendMessage, EditMessageText)):
            return Message(message_id=next(_ids), date=timezone.now(), chat=Chat(id=getattr(method, "chat_id", 1) or 1, type="private"), text=method.text)
        if isinstance(method, AnswerCallbackQuery):
            return True
        return True

    async def close(self):
        pass

    async def stream_content(self, *a, **kw):  # pragma: no cover
        yield b""

    def texts(self):
        return [c.text for c in self.calls if isinstance(c, (SendMessage, EditMessageText))]


TG = TgUser(id=555, is_bot=False, first_name="Bekzod", last_name="Karimov", username="bekzod", language_code="uz")
CHAT = Chat(id=555, type="private")


@override_settings(TELEGRAM_BOT_TOKEN="123456:TEST", TELEGRAM_ADMIN_IDS=[])
class BotFlowTests(TransactionTestCase):
    def setUp(self):
        from aiogram.fsm.storage.memory import MemoryStorage

        from apps.telegram_bot.bot import dispatcher as d

        self.session = FakeSession()
        self.bot = Bot("123456:TEST", session=self.session)
        dp = d.get_dispatcher()
        dp.fsm.storage = MemoryStorage()
        self.dp = dp

    def feed(self, *, text=None, contact=None, callback=None):
        msg = Message(message_id=next(_ids), date=timezone.now(), chat=CHAT, from_user=TG, text=text, contact=contact)
        if callback:
            update = Update(update_id=next(_ids), callback_query=CallbackQuery(id=str(next(_ids)), from_user=TG, chat_instance="x", data=callback, message=msg))
        else:
            update = Update(update_id=next(_ids), message=msg)
        async_to_sync(self.dp.feed_update)(self.bot, update)

    def test_full_registration_then_login_confirmation(self):
        req = LoginRequest.objects.create(session_key="abc", user_agent="Mozilla/5.0 (Windows NT 10.0) Chrome/130")
        self.feed(text=f"/start login_{req.token.hex}")
        self.assertTrue(any("Tilni tanlang" in t for t in self.session.texts()))
        self.feed(callback="lang:uz")
        self.feed(text="Bekzod")
        self.feed(text="Karimov")
        # Boshqa odamning kontakti rad etiladi
        self.feed(contact=Contact(phone_number="998901234567", first_name="X", user_id=999))
        self.assertFalse(User.objects.get(telegram_id=555).is_registered)
        self.feed(contact=Contact(phone_number="998901234567", first_name="Bekzod", user_id=555))
        user = User.objects.get(telegram_id=555)
        self.assertTrue(user.is_registered)
        self.assertEqual((user.first_name, user.last_name, user.phone), ("Bekzod", "Karimov", "+998901234567"))
        # Ro'yxatdan keyin kirish so'rovi tasdiqlash uchun ko'rsatildi
        self.assertTrue(any("Saytga kirish so'rovi" in t for t in self.session.texts()))
        self.feed(callback=f"login:ok:{req.pk}")
        req.refresh_from_db()
        self.assertEqual(req.status, LoginRequest.Status.CONFIRMED)
        self.assertEqual(req.user, user)
        self.assertTrue(any("Kirish tasdiqlandi" in t for t in self.session.texts()))

    def test_login_command_requires_registration_then_returns_code(self):
        self.feed(text="/login")
        self.assertTrue(any("ro'yxatdan o'ting" in t for t in self.session.texts()))
        User.objects.filter(telegram_id=555).update(is_registered=True, phone="+998900000000")
        self.feed(text="/login")
        self.assertTrue(any("Saytga kirish kodi" in t for t in self.session.texts()))

    def test_free_text_saved_for_admin_inbox(self):
        self.feed(text="/start")
        User.objects.filter(telegram_id=555).update(is_registered=True)
        self.feed(text="Salom, kurs qachon chiqadi?")
        self.assertTrue(BotMessage.objects.filter(direction="in", text__startswith="Salom").exists())

    def test_blocked_user_gets_blocked_message(self):
        self.feed(text="/start")
        User.objects.filter(telegram_id=555).update(is_blocked=True)
        self.session.calls.clear()
        self.feed(text="/login")
        self.assertTrue(any("bloklangan" in t for t in self.session.texts()))


@override_settings(TELEGRAM_BOT_TOKEN="123456:TEST", TELEGRAM_ADMIN_IDS=[])
class MiniAppContactTests(BotFlowTests):
    def test_contact_from_mini_app_registers_user(self):
        # Foydalanuvchi botda /start bosmagan, faqat Mini App'dan kontakt ulashdi
        self.feed(contact=Contact(phone_number="+998977777777", first_name="Bekzod", user_id=555))
        user = User.objects.get(telegram_id=555)
        self.assertTrue(user.is_registered)
        self.assertEqual(user.phone, "+998977777777")
        self.assertEqual(user.first_name, "Bekzod")

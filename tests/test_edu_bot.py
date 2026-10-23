"""@welicodev_educationbot: katalog, yozilish, so'rov, admin tasdiqlashi va xabarlarni to'g'ri botdan yuborish."""

from unittest import mock

from aiogram import Bot
from aiogram.types import CallbackQuery, Chat, Message, Update, User as TgUser
from asgiref.sync import async_to_sync
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from apps.accounts.models import User
from apps.education.models import AccessRequest, Course, Enrollment, HomeworkSubmission, Lesson

from .test_bot import FakeSession, _ids
from .test_education import PNG

STUDENT = TgUser(id=701, is_bot=False, first_name="Aziz", username="aziz", language_code="uz")
ADMIN = TgUser(id=702, is_bot=False, first_name="Otabek", username="otabek", language_code="uz")


@override_settings(TELEGRAM_BOT_TOKEN="1:MAIN", TELEGRAM_EDU_BOT_TOKEN="2:EDU", TELEGRAM_ADMIN_IDS=[], SITE_URL="https://welicodev.uz")
class EduBotTests(TransactionTestCase):
    def setUp(self):
        from apps.telegram_bot.edu import dispatcher as d

        self.session = FakeSession()
        self.bot = Bot("2:EDU", session=self.session)
        self.dp = d.get_dispatcher()
        self.free = Course.objects.create(title_uz="Python", title_en="Python", subtitle="Asoslar", status="published",
                                          is_free=True, cover=SimpleUploadedFile("c.png", PNG))
        self.paid = Course.objects.create(title_uz="Django", title_en="Django", subtitle="Pro", status="published",
                                          is_free=False, price=349000, cover=SimpleUploadedFile("d.png", PNG))
        self.lesson = Lesson.objects.create(course=self.free, order=1, title_uz="Kirish", title_en="Intro", status="published")
        self.notify_admins = mock.patch("apps.telegram_bot.tasks.notify_admins.delay").start()
        self.send_to_user = mock.patch("apps.telegram_bot.tasks.send_to_user.delay").start()
        self.addCleanup(mock.patch.stopall)

    def feed(self, who=STUDENT, *, text=None, callback=None):
        chat = Chat(id=who.id, type="private")
        msg = Message(message_id=next(_ids), date=timezone.now(), chat=chat, from_user=who, text=text or "x")
        if callback:
            update = Update(update_id=next(_ids), callback_query=CallbackQuery(
                id=str(next(_ids)), from_user=who, chat_instance="x", data=callback, message=msg))
        else:
            update = Update(update_id=next(_ids), message=msg)
        async_to_sync(self.dp.feed_update)(self.bot, update)

    def last(self):
        return self.session.texts()[-1]

    def register(self, who=STUDENT, **kw):
        self.feed(who, text="/start")
        User.objects.filter(telegram_id=who.id).update(is_registered=True, phone="+998900000000", **kw)

    def test_unregistered_user_is_sent_to_main_bot(self):
        self.feed(text="/start")
        self.assertIn("ro'yxatdan o'ting", self.last())
        self.assertTrue(User.objects.get(telegram_id=701).edu_bot_started)

    def test_catalog_card_and_free_enrollment(self):
        self.register()
        self.feed(text="/start")
        self.assertIn("WeliCoDev Academy", self.last())
        self.feed(text="/courses")
        self.feed(callback=f"c:{self.free.pk}")
        self.assertIn("<b>Python</b>", self.last())
        self.feed(callback=f"en:{self.free.pk}")
        self.assertTrue(Enrollment.objects.filter(user__telegram_id=701, course=self.free).exists())
        self.assertIn("yozildingiz", self.last())
        self.feed(text="/my")
        self.assertIn("Python", self.last())

    def test_paid_course_request_notifies_admins_with_buttons(self):
        self.register()
        self.feed(callback=f"rq:{self.paid.pk}")
        req = AccessRequest.objects.get(user__telegram_id=701, course=self.paid)
        self.assertIn(req.reference, self.last())
        kwargs = self.notify_admins.call_args.kwargs
        self.assertEqual(kwargs["bot"], "edu")
        self.assertEqual(kwargs["edu_markup"]["inline_keyboard"][0][0]["callback_data"], f"ar:ok:{req.pk}")

    def test_paid_enrollment_not_possible_via_free_callback(self):
        self.register()
        self.feed(callback=f"en:{self.paid.pk}")
        self.assertFalse(Enrollment.objects.filter(course=self.paid).exists())

    def test_admin_grants_access_from_bot_student_cannot(self):
        self.register()
        self.feed(callback=f"rq:{self.paid.pk}")
        req = AccessRequest.objects.get(course=self.paid)
        self.feed(callback=f"ar:ok:{req.pk}")  # oddiy foydalanuvchi
        req.refresh_from_db()
        self.assertEqual(req.status, "pending")
        self.register(ADMIN, is_staff=True)
        self.feed(ADMIN, callback=f"ar:ok:{req.pk}")
        req.refresh_from_db()
        self.assertEqual(req.status, "approved")
        self.assertTrue(Enrollment.objects.filter(user__telegram_id=701, course=self.paid, is_active=True).exists())
        self.assertEqual(self.send_to_user.call_args.kwargs["bot"], "edu")
        self.feed(ADMIN, callback=f"ar:ok:{req.pk}")  # ikkinchi bosish — hech narsa o'zgarmaydi
        self.assertEqual(Enrollment.objects.filter(course=self.paid).count(), 1)

    def test_admin_reviews_homework(self):
        self.register()
        student = User.objects.get(telegram_id=701)
        sub = HomeworkSubmission.objects.create(user=student, lesson=self.lesson, text="Javob")
        self.register(ADMIN, is_staff=True)
        self.feed(ADMIN, text="/admin")
        self.assertIn("Ta'lim boshqaruvi", self.last())
        self.feed(ADMIN, callback=f"hw:ok:{sub.pk}")
        sub.refresh_from_db()
        self.assertEqual(sub.status, "approved")


@override_settings(TELEGRAM_BOT_TOKEN="1:MAIN", TELEGRAM_EDU_BOT_TOKEN="2:EDU")
class DeliverTests(TestCase):
    def setUp(self):
        self.send = mock.patch("apps.telegram_bot.api.send_message", return_value={"message_id": 1}).start()
        self.addCleanup(mock.patch.stopall)
        self.user = User.objects.create(username="s", telegram_id=900)

    def test_edu_used_only_after_user_opened_it(self):
        from apps.telegram_bot.tasks import deliver

        deliver(self.user, "salom", bot="edu")
        self.assertIsNone(self.send.call_args.kwargs.get("token"))  # asosiy bot
        self.user.edu_bot_started = True
        deliver(self.user, "salom", bot="edu")
        self.assertEqual(self.send.call_args.kwargs["token"], "2:EDU")

    def test_edu_blocked_falls_back_to_main(self):
        from apps.telegram_bot.api import TelegramError
        from apps.telegram_bot.tasks import deliver

        self.user.edu_bot_started = True
        self.send.side_effect = [TelegramError("Forbidden", code=403), {"message_id": 2}]
        deliver(self.user, "salom", bot="edu")
        self.user.refresh_from_db()
        self.assertTrue(self.user.edu_bot_blocked)
        self.assertEqual(self.send.call_count, 2)

    @override_settings(TELEGRAM_EDU_BOT_TOKEN="")
    def test_no_edu_token_means_main_bot(self):
        from apps.telegram_bot.tasks import deliver

        self.user.edu_bot_started = True
        deliver(self.user, "salom", bot="edu")
        self.assertIsNone(self.send.call_args.kwargs.get("token"))

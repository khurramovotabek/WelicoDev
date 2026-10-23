"""Kunlik o'quvchi eslatmalari (nudge_learners): kimga, qachon va necha marta yuboriladi."""

from datetime import timedelta
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import User
from apps.education.models import Course, Enrollment, Lesson, LessonProgress
from apps.telegram_bot.tasks import nudge_learners

from .test_education import PNG


@override_settings(SITE_URL="https://welicodev.uz")
class NudgeTests(TestCase):
    def setUp(self):
        self.course = Course.objects.create(title_uz="Docker <pro>", title_en="Docker", subtitle="x", status="published",
                                            is_free=True, cover=SimpleUploadedFile("c.png", PNG))
        self.l1 = Lesson.objects.create(course=self.course, order=1, title_uz="Bir", title_en="One", status="published")
        self.l2 = Lesson.objects.create(course=self.course, order=2, title_uz="Ikki", title_en="Two", status="published")
        self.send = mock.patch("apps.telegram_bot.api.send_message", return_value={"message_id": 1}).start()
        self.addCleanup(mock.patch.stopall)

    def user(self, days_ago, **kw):
        u = User.objects.create(username=f"u{User.objects.count()}", telegram_id=5000 + User.objects.count(),
                                is_registered=True, first_name="Ali", **kw)
        User.objects.filter(pk=u.pk).update(date_joined=timezone.now() - timedelta(days=days_ago))
        return u

    def test_new_user_gets_two_start_nudges_then_stops(self):
        u = self.user(1)
        nudge_learners()
        self.assertEqual(self.send.call_count, 1)
        self.assertIn("Docker &lt;pro&gt;", self.send.call_args.args[1])  # HTML escape
        nudge_learners()
        self.assertEqual(self.send.call_count, 1)  # 3 kun hali o'tmagan
        User.objects.filter(pk=u.pk).update(date_joined=timezone.now() - timedelta(days=3))
        nudge_learners()
        nudge_learners()
        self.assertEqual(self.send.call_count, 2)
        self.assertEqual(User.objects.get(pk=u.pk).nudge_stage, 2)

    def test_skips_fresh_staff_blocked_and_opted_out(self):
        self.user(0)
        self.user(5, is_staff=True)
        self.user(5, bot_blocked=True)
        self.user(5, notify_news=False)
        nudge_learners()
        self.send.assert_not_called()

    def test_stale_enrollment_gets_next_lesson_once(self):
        u = self.user(10, nudge_stage=2)
        e = Enrollment.objects.create(user=u, course=self.course, last_lesson=self.l1)
        Enrollment.objects.filter(pk=e.pk).update(created_at=timezone.now() - timedelta(days=5))
        nudge_learners()
        self.assertEqual(self.send.call_count, 1)
        self.assertIn("Ikki", self.send.call_args.args[1])
        nudge_learners()
        self.assertEqual(self.send.call_count, 1)

    def test_active_learner_not_disturbed(self):
        u = self.user(10, nudge_stage=2)
        e = Enrollment.objects.create(user=u, course=self.course)
        Enrollment.objects.filter(pk=e.pk).update(created_at=timezone.now() - timedelta(days=5))
        LessonProgress.objects.create(user=u, lesson=self.l1)
        nudge_learners()
        self.send.assert_not_called()

    def test_blocked_bot_is_marked(self):
        from apps.telegram_bot.api import TelegramError

        u = self.user(2)
        self.send.side_effect = TelegramError("Forbidden", code=403)
        nudge_learners()
        u.refresh_from_db()
        self.assertTrue(u.bot_blocked)
        self.assertEqual(u.nudge_stage, 1)

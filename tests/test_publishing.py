"""Nashr hodisalari: Telegram kanalga avtomatik post, IndexNow va SEO tekshiruvi."""

from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.blog.models import Article
from apps.core.models import SiteSettings
from apps.core.seo_audit import audit_article
from apps.telegram_bot.models import BotSettings

from .test_education import PNG


@override_settings(TELEGRAM_BOT_TOKEN="123:T", SITE_URL="https://welicodev.uz", CELERY_TASK_ALWAYS_EAGER=True)
class ChannelPostTests(TestCase):
    def setUp(self):
        bs = BotSettings.load()
        bs.channel_id, bs.auto_post_articles = "@welicodev", True
        bs.save()

    def _article(self, status="published"):
        return Article.objects.create(
            title_uz="Docker darslari", title_en="Docker lessons", excerpt_uz="Qisqa", content_uz="<p>Matn</p>",
            status=status, cover=SimpleUploadedFile("c.png", PNG),
        )

    @mock.patch("apps.telegram_bot.api.call", return_value={"message_id": 77})
    def test_published_article_posted_once(self, call):
        with self.captureOnCommitCallbacks(execute=True):
            a = self._article()
        self.assertEqual(call.call_count, 1)
        method, payload = call.call_args.args[0], call.call_args.args[1]
        self.assertEqual(method, "sendPhoto")
        self.assertEqual(payload["chat_id"], "@welicodev")
        self.assertIn("<b>Docker darslari</b>", payload["caption"])
        self.assertEqual(payload["parse_mode"], "HTML")
        a.refresh_from_db()
        self.assertIsNotNone(a.posted_to_channel_at)
        from apps.telegram_bot.models import ChannelPost

        post = ChannelPost.objects.get()
        self.assertEqual((post.kind, post.status, post.message_id), ("article", "sent", 77))
        with self.captureOnCommitCallbacks(execute=True):
            a.save()  # tahrirlash qayta post qilmaydi
        self.assertEqual(call.call_count, 1)

    @mock.patch("apps.telegram_bot.api.call")
    def test_draft_not_posted(self, call):
        with self.captureOnCommitCallbacks(execute=True):
            self._article(status="draft")
        call.assert_not_called()

    @mock.patch("apps.telegram_bot.api.call", return_value={"message_id": 1})
    def test_scheduled_post_and_edit(self, call):
        from datetime import timedelta

        from django.utils import timezone

        from apps.telegram_bot import channel
        from apps.telegram_bot.models import ChannelPost
        from apps.telegram_bot.tasks import send_due

        p = ChannelPost.objects.create(title="t", body="<p><strong>Salom</strong> kanal</p>", status="scheduled",
                                       scheduled_at=timezone.now() + timedelta(minutes=5))
        send_due()
        call.assert_not_called()
        ChannelPost.objects.filter(pk=p.pk).update(scheduled_at=timezone.now() - timedelta(minutes=1))
        send_due()
        p.refresh_from_db()
        self.assertEqual(p.status, "sent")
        self.assertEqual(call.call_args.args[1]["text"], "<b>Salom</b> kanal")
        p.body = "<p>Yangilangan</p>"
        self.assertTrue(channel.edit(p))
        self.assertEqual(call.call_args.args[0], "editMessageText")

    @mock.patch("urllib.request.urlopen")
    @mock.patch("apps.telegram_bot.api.call", return_value={"message_id": 1})
    def test_indexnow_ping_all_languages(self, _send, urlopen):
        s = SiteSettings.load()
        s.indexnow_key = "a" * 32
        s.save()
        with self.captureOnCommitCallbacks(execute=True):
            self._article()
        body = urlopen.call_args.args[0].data.decode()
        for lang in ("uz", "ru", "en"):
            self.assertIn(f"https://welicodev.uz/{lang}/blog/docker-lessons/", body)

    def test_indexnow_key_file(self):
        s = SiteSettings.load()
        s.indexnow_key = "b" * 32
        s.save()
        self.assertEqual(self.client.get(f"/{'b' * 32}.txt").content.decode(), "b" * 32)
        self.assertEqual(self.client.get(f"/{'c' * 32}.txt").status_code, 404)


class SeoAuditTests(TestCase):
    def test_audit_scores(self):
        a = Article(title_uz="Docker darslari: o'zbek tilida to'liq qo'llanma", slug="docker-darslari", focus_keyword="docker darslari",
                    excerpt_uz="Docker darslari o'zbek tilida: konteynerlar, image, compose va production deploy amaliy misollar bilan to'liq tushuntiriladi.",
                    content_uz="<p>Docker darslari boshlanadi.</p><h2>Docker darslari: kirish</h2><h2>Amaliyot</h2>" + "<p>" + "so'z " * 650 + '</p><a href="/uz/education/">kurs</a>',
                    title_ru="Уроки Docker", title_en="Docker lessons")
        r = audit_article(a)
        self.assertEqual(r["score"], 100, [c["text"] for c in r["checks"] if not c["ok"]])
        weak = audit_article(Article(title_uz="Salom", content_uz="<p>qisqa</p>"))
        self.assertLess(weak["score"], 30)


@override_settings(TELEGRAM_BOT_TOKEN="123:T", SITE_URL="https://welicodev.uz", CELERY_TASK_ALWAYS_EAGER=True)
class LessonAutopostTests(TestCase):
    def setUp(self):
        from apps.education.models import Course

        bs = BotSettings.load()
        bs.channel_id, bs.auto_post_lessons = "@welicodev", True
        bs.save()
        self.course = Course.objects.create(title_uz="Docker", title_en="Docker", subtitle="x", status="published",
                                            cover=SimpleUploadedFile("c.png", PNG))

    @mock.patch("apps.telegram_bot.api.call", return_value={"message_id": 5})
    def test_lesson_posted_only_when_video_added(self, call):
        from apps.education.models import Lesson

        with self.captureOnCommitCallbacks(execute=True):
            les = Lesson.objects.create(course=self.course, order=1, title_uz="Kirish", title_en="Intro", status="published")
        call.assert_not_called()
        les.video_url = "https://youtu.be/abcdefghijk"
        with self.captureOnCommitCallbacks(execute=True):
            les.save()
        self.assertEqual(call.call_count, 1)
        self.assertIn("Yangi dars: 1. Kirish", call.call_args.args[1]["caption"])
        with self.captureOnCommitCallbacks(execute=True):
            les.save()
        self.assertEqual(call.call_count, 1)

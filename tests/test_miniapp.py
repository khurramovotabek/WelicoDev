"""Telegram Mini App: initData imzosi, ruxsatlar va dars oqimi."""

import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.accounts.models import User
from apps.education.models import Course, Enrollment
from apps.miniapp.auth import sign_video, unsign_video, validate_init_data

TOKEN = "123456:TEST-TOKEN"


def make_init_data(user, token=TOKEN, auth_date=None):
    data = {"auth_date": str(auth_date or int(time.time())), "query_id": "AAE", "user": json.dumps(user, separators=(",", ":"))}
    check = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    data["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(data)


@override_settings(TELEGRAM_BOT_TOKEN=TOKEN, ALLOWED_HOSTS=["testserver"])
class InitDataTests(TestCase):
    def test_valid_signature(self):
        self.assertEqual(validate_init_data(make_init_data({"id": 7, "first_name": "A"}))["id"], 7)

    def test_tampered_or_foreign_token_rejected(self):
        good = make_init_data({"id": 7})
        self.assertIsNone(validate_init_data(good.replace("%22id%22%3A7", "%22id%22%3A8")))
        self.assertIsNone(validate_init_data(make_init_data({"id": 7}, token="999:OTHER")))

    def test_expired_rejected(self):
        self.assertIsNone(validate_init_data(make_init_data({"id": 7}, auth_date=int(time.time()) - 90000)))

    def test_video_token(self):
        tok = sign_video(1, 2)
        self.assertEqual(unsign_video(tok), (1, 2))
        self.assertIsNone(unsign_video(tok + "x"))


@override_settings(TELEGRAM_BOT_TOKEN=TOKEN, ALLOWED_HOSTS=["testserver"], DEBUG=False)
class MiniAppViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)

    def h(self, uid=4242):
        return {"HTTP_X_TELEGRAM_INIT_DATA": make_init_data({"id": uid, "first_name": "Ali", "username": "ali"})}

    def test_shell_is_public_but_screens_need_signature(self):
        self.assertEqual(self.client.get("/uz/app/").status_code, 200)
        self.assertEqual(self.client.get("/uz/app/home/").status_code, 401)
        # DEBUG=False bo'lsa debug sarlavhasi ishlamaydi
        self.assertEqual(self.client.get("/uz/app/home/", HTTP_X_TMA_DEBUG_USER="1").status_code, 401)

    def test_unregistered_user_sees_register_screen(self):
        r = self.client.get("/uz/app/home/", **self.h())
        self.assertContains(r, "tmaShareContact")
        self.assertTrue(User.objects.filter(telegram_id=4242, is_registered=False).exists())

    def test_registered_flow_enroll_and_lesson(self):
        User.objects.create(username="tg_4242", telegram_id=4242, first_name="Ali", is_registered=True, phone="+998900000000")
        for url in ("/uz/app/home/", "/uz/app/courses/", "/uz/app/blog/", "/uz/app/projects/", "/uz/app/profile/",
                    "/ru/app/blog/why-i-love-building-with-django/", "/en/app/projects/nutrizone/"):
            self.assertEqual(self.client.get(url, **self.h()).status_code, 200, url)
        course = Course.objects.get()
        r = self.client.post(f"/uz/app/courses/{course.slug}/enroll/", **self.h())
        self.assertEqual(r.status_code, 200)
        self.assertTrue(Enrollment.objects.filter(user__telegram_id=4242).exists())
        first, second = list(course.published_lessons()[:2])
        self.assertContains(self.client.get(f"/uz/app/courses/{course.slug}/{second.slug}/", **self.h()), "lock")
        self.client.post(f"/uz/app/courses/{course.slug}/{first.slug}/watched/", **self.h())
        r = self.client.get(f"/uz/app/courses/{course.slug}/{second.slug}/", **self.h())
        from django.utils.html import escape

        self.assertContains(r, escape(second.title))
        self.assertNotContains(r, "Bu dars hali yopiq")

    def test_blocked_user_rejected(self):
        User.objects.create(username="tg_4242", telegram_id=4242, is_registered=True, is_blocked=True)
        self.assertEqual(self.client.get("/uz/app/home/", **self.h()).status_code, 401)


@override_settings(X_FRAME_OPTIONS="DENY")  # prod qiymati
class FramingTests(TestCase):
    def test_shell_can_be_framed_only_by_telegram(self):
        r = self.client.get("/uz/app/")
        self.assertNotIn("X-Frame-Options", r)
        self.assertIn("https://web.telegram.org", r["Content-Security-Policy"])
        # Saytning boshqa sahifalari iframe'ga tushmaydi
        self.assertEqual(self.client.get("/uz/").get("X-Frame-Options"), "DENY")

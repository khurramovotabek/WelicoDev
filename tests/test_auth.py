"""Telegram orqali kirish: deep link tasdiqlash va 6 xonali kod."""

from asgiref.sync import async_to_sync
from django.core.cache import cache
from django.test import TestCase, override_settings

from apps.accounts.models import LoginCode, LoginRequest, User
from apps.telegram_bot.bot import db as bot_db


@override_settings(ALLOWED_HOSTS=["testserver"])
class TelegramLoginTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create(
            username="tg_1001", telegram_id=1001, first_name="Ali", last_name="Valiyev", phone="+998901112233", is_registered=True,
        )

    def test_login_page_creates_request_bound_to_session(self):
        r = self.client.get("/uz/accounts/login/")
        self.assertEqual(r.status_code, 200)
        req = LoginRequest.objects.get()
        self.assertEqual(req.session_key, self.client.session.session_key)
        self.assertContains(r, f"start=login_{req.token.hex}")

    def test_deep_link_confirmation_logs_browser_in(self):
        self.client.get("/uz/accounts/login/")
        req = LoginRequest.objects.get()
        # Foydalanuvchi botda "Tasdiqlash"ni bosdi
        resolved, code = async_to_sync(bot_db.resolve_login_request)(req.pk, self.user.pk, True)
        self.assertIsNotNone(code)
        r = self.client.get("/uz/accounts/login/status/", HTTP_HX_REQUEST="true")
        self.assertIn("HX-Redirect", r)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)
        req.refresh_from_db()
        self.assertEqual(req.status, LoginRequest.Status.USED)

    def test_rejected_request_does_not_log_in(self):
        self.client.get("/uz/accounts/login/")
        req = LoginRequest.objects.get()
        async_to_sync(bot_db.resolve_login_request)(req.pk, self.user.pk, False)
        self.client.get("/uz/accounts/login/status/", HTTP_HX_REQUEST="true")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_other_browser_cannot_use_confirmed_request(self):
        self.client.get("/uz/accounts/login/")
        req = LoginRequest.objects.get()
        async_to_sync(bot_db.resolve_login_request)(req.pk, self.user.pk, True)
        other = self.client_class()
        other.get("/uz/accounts/login/")
        other.get("/uz/accounts/login/status/", HTTP_HX_REQUEST="true")
        self.assertNotIn("_auth_user_id", other.session)

    def test_code_login(self):
        code = async_to_sync(bot_db.issue_code)(self.user.pk)
        r = self.client.post("/uz/accounts/login/verify/", {"code": code, "next": "/uz/projects/"})
        self.assertRedirects(r, "/uz/projects/", fetch_redirect_response=False)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)
        # Kod bir martalik
        self.client.logout()
        self.client.post("/uz/accounts/login/verify/", {"code": code})
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_next_must_be_local(self):
        code = async_to_sync(bot_db.issue_code)(self.user.pk)
        r = self.client.post("/uz/accounts/login/verify/", {"code": code, "next": "https://evil.example/"})
        self.assertRedirects(r, "/uz/", fetch_redirect_response=False)

    def test_wrong_code_and_rate_limit(self):
        for _ in range(10):
            self.client.post("/uz/accounts/login/verify/", {"code": "000000"})
        code = async_to_sync(bot_db.issue_code)(self.user.pk)
        self.client.post("/uz/accounts/login/verify/", {"code": code})
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_blocked_user_cannot_log_in(self):
        self.user.is_blocked = True
        self.user.save()
        code = async_to_sync(bot_db.issue_code)(self.user.pk)
        self.client.post("/uz/accounts/login/verify/", {"code": code})
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_new_code_invalidates_old(self):
        first = LoginCode.issue(self.user)
        LoginCode.issue(self.user)
        first.refresh_from_db()
        self.assertTrue(first.is_used)

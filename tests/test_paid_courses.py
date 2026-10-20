"""Pullik va yopiq kurslar, kirish so'rovlari, admin 2FA va dashboard himoyasi."""

from datetime import timedelta
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.core.models import SiteSettings
from apps.education import services
from apps.education.models import AccessRequest, Course, Enrollment, Lesson

from .test_education import PNG


def make_course(**kw):
    defaults = dict(title_uz="Kurs", title_en="Course", subtitle="x", status="published", cover=SimpleUploadedFile("c.png", PNG))
    defaults.update(kw)
    c = Course.objects.create(**defaults)
    Lesson.objects.create(course=c, order=1, title_uz="Bir", title_en="One", status="published", video_url="https://youtu.be/abcdefghijk")
    return c


@override_settings(ALLOWED_HOSTS=["testserver"], TELEGRAM_BOT_TOKEN="")
class PaidCourseTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="buyer", first_name="Ali", telegram_id=3001, is_registered=True)
        self.admin = User.objects.create(username="boss", is_staff=True, is_superuser=True, telegram_id=3002)
        self.paid = make_course(slug="pro", is_free=False, price=300000, old_price=400000)
        self.private = make_course(slug="secret", is_free=False, price=500000, is_private=True)

    def test_private_course_hidden_until_granted(self):
        self.client.force_login(self.user)
        self.assertNotContains(self.client.get(reverse("education:course_list")), "/education/secret/")
        self.assertEqual(self.client.get(self.private.get_absolute_url()).status_code, 404)
        self.assertNotIn(self.private, Course.objects.listed())
        services.grant_access(self.private, self.user, by=self.admin)
        self.assertEqual(self.client.get(self.private.get_absolute_url()).status_code, 200)
        # Boshqa foydalanuvchi baribir ko'rmaydi
        self.assertFalse(self.private.visible_to(User.objects.create(username="other")))

    def test_paid_enroll_redirects_to_buy_and_request_flow(self):
        self.client.force_login(self.user)
        r = self.client.post(reverse("education:enroll", args=[self.paid.slug]))
        self.assertRedirects(r, reverse("education:buy", args=[self.paid.slug]))
        page = self.client.get(reverse("education:buy", args=[self.paid.slug]))
        self.assertContains(page, "300")
        self.assertContains(page, "25%")
        r = self.client.post(reverse("education:buy", args=[self.paid.slug]), {"note": "Click", "go": "telegram"})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r["Location"].startswith("https://t.me/"))
        req = AccessRequest.objects.get(user=self.user, course=self.paid)
        self.assertEqual((req.status, req.note), ("pending", "Click"))
        self.assertIn(req.reference, r["Location"].replace("%2D", "-"))
        # Takroriy so'rov dublikat yaratmaydi
        self.client.post(reverse("education:buy", args=[self.paid.slug]), {"go": "request"})
        self.assertEqual(AccessRequest.objects.filter(user=self.user).count(), 1)
        self.assertFalse(services.is_lesson_unlocked(self.user, self.paid.published_lessons().first()))

    def test_dashboard_approve_reject_revoke(self):
        req, _ = services.request_access(self.user, self.paid)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("dashboard:access")).status_code, 200)
        r = self.client.post(reverse("dashboard:access_request_action", args=[req.pk, "approve"]), {"amount": "250000", "days": "30"})
        self.assertEqual(r.status_code, 302)
        req.refresh_from_db()
        self.assertEqual((req.status, req.amount, req.reviewed_by), ("approved", 250000, self.admin))
        e = Enrollment.objects.get(user=self.user, course=self.paid)
        self.assertTrue(e.is_active and e.expires_at and e.granted_by == self.admin)
        self.assertTrue(services.is_lesson_unlocked(self.user, self.paid.published_lessons().first()))
        self.client.post(reverse("dashboard:access_enrollment_action", args=[e.pk, "revoke"]))
        self.assertIsNone(services.get_enrollment(self.user, self.paid))
        # Rad etish
        req2, _ = services.request_access(self.user, self.private)
        self.client.post(reverse("dashboard:access_request_action", args=[req2.pk, "reject"]), {"admin_note": "To'lov topilmadi"})
        req2.refresh_from_db()
        self.assertEqual((req2.status, req2.admin_note), ("rejected", "To'lov topilmadi"))

    def test_manual_grant_and_expiry(self):
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse("dashboard:access_grant"), {"user_q": "Ali"}), "Ali")
        self.client.post(reverse("dashboard:access_grant"), {"user": self.user.pk, "course": self.paid.pk, "days": ""})
        self.assertIsNotNone(services.get_enrollment(self.user, self.paid))
        Enrollment.objects.filter(user=self.user).update(expires_at=timezone.now() - timedelta(days=1))
        self.assertIsNone(services.get_enrollment(self.user, self.paid))

    def test_miniapp_buy(self):
        with override_settings(DEBUG=True):
            r = self.client.post(reverse("miniapp:buy", args=[self.paid.slug]), HTTP_X_TMA_DEBUG_USER="3001", HTTP_HX_REQUEST="true")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(AccessRequest.objects.filter(user=self.user, course=self.paid, status="pending").exists())

    def test_profile_purchases_tab(self):
        services.request_access(self.user, self.paid)
        self.client.force_login(self.user)
        r = self.client.get(reverse("accounts:profile") + "?tab=purchases")
        self.assertContains(r, AccessRequest.objects.first().reference)


@override_settings(ALLOWED_HOSTS=["testserver"], TELEGRAM_BOT_TOKEN="test-token", ADMIN_2FA=True, TELEGRAM_ADMIN_IDS=[])
class AdminSecurityTests(TestCase):
    def setUp(self):
        from django.core.cache import cache

        # Bloklash hisoblagichlari Redis'da: testlar bir-biriga ta'sir qilmasin
        cache.delete_many(["admin-login:ip:127.0.0.1", "admin-login:user:root", "admin-login:user:notg"])
        self.admin = User.objects.create_superuser("root", password="S3cure-pass!", telegram_id=4001)
        self.login_url = reverse("admin:login")

    def _password_step(self, password="S3cure-pass!"):
        return self.client.post(self.login_url, {"username": "root", "password": password})

    def test_password_then_telegram_code(self):
        sent = {}
        with mock.patch("apps.telegram_bot.api.send_message", side_effect=lambda chat, text, **kw: sent.update(chat=chat, text=text)):
            r = self._password_step()
        self.assertContains(r, 'name="step" value="code"')
        self.assertEqual(sent["chat"], 4001)
        self.assertNotIn("_auth_user_id", self.client.session)
        code = sent["text"].split("<code>")[1].split("</code>")[0]
        with mock.patch("apps.telegram_bot.tasks.notify_admins.delay"):
            r = self.client.post(self.login_url, {"step": "code", "code": "000000" if code != "000000" else "111111"})
            self.assertContains(r, "noto")
            r = self.client.post(self.login_url, {"step": "code", "code": code})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.admin.pk)

    def test_lockout_after_failed_passwords(self):
        for _ in range(5):
            self._password_step("wrong")
        with mock.patch("apps.telegram_bot.api.send_message") as send:
            r = self._password_step()
        send.assert_not_called()
        self.assertContains(r, "daqiqadan keyin")

    def test_staff_without_telegram_cannot_password_login(self):
        User.objects.create_superuser("notg", password="S3cure-pass!")
        r = self.client.post(self.login_url, {"username": "notg", "password": "S3cure-pass!"})
        self.assertContains(r, "Telegram")
        self.assertNotIn("_auth_user_id", self.client.session)


@override_settings(ALLOWED_HOSTS=["testserver"], TELEGRAM_BOT_TOKEN="")
class DashboardGuardTests(TestCase):
    def test_anonymous_redirects_to_telegram_login_and_member_gets_404(self):
        r = self.client.get(reverse("dashboard:home"))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("accounts:login"), r["Location"])
        self.client.force_login(User.objects.create(username="m"))
        self.assertEqual(self.client.get(reverse("dashboard:home")).status_code, 404)

    def test_settings_background_and_map(self):
        admin = User.objects.create(username="a", is_staff=True, is_superuser=True)
        self.client.force_login(admin)
        page = self.client.get(reverse("dashboard:settings"))
        self.assertContains(page, "background_preset")
        s = SiteSettings.load()
        self.assertTrue(s.background_url.endswith("img/bg/dawn.webp"))
        s.background_preset = "scene"
        self.assertEqual(s.background_url, "")
        home = self.client.get("/uz/")
        self.assertContains(home, "data-map")

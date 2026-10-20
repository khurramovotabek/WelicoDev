"""Ommaviy sahifalar, izohlar va dashboard ruxsatlari."""

from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.accounts.models import User
from apps.interactions.models import Comment
from apps.portfolio.models import Project


@override_settings(ALLOWED_HOSTS=["testserver"], TELEGRAM_BOT_TOKEN="")
class SiteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)

    def test_public_pages(self):
        p = Project.objects.first()
        for lang in ("uz", "ru", "en"):
            for path in ("", "about/", "skills/", "projects/", f"projects/{p.slug}/", "experience/", "blog/",
                         "media/", "education/", "contact/", "search/?q=django", f"share/project/{p.slug}/", "accounts/login/"):
                r = self.client.get(f"/{lang}/{path}")
                self.assertEqual(r.status_code, 200, f"/{lang}/{path}")

    def test_media_pages_with_link_only_tracks(self):
        """Audio fayli yo'q (faqat Spotify havolasi) qo'shiqlar sahifani buzmasligi kerak."""
        from apps.gallery.models import Track

        Track.objects.update(audio="")
        Track.objects.create(title="Link only", artist="Artist", external_url="https://open.spotify.com/track/x", is_favorite=True)
        for path in ("", "media/", "media/music/"):
            r = self.client.get(f"/uz/{path}")
            self.assertEqual(r.status_code, 200, path)

    def test_404_page(self):
        self.assertEqual(self.client.get("/uz/no-such-page/").status_code, 404)

    def test_comment_requires_login(self):
        p = Project.objects.first()
        r = self.client.post(f"/uz/i/comments/project/{p.pk}/add/", {"body": "Zo'r!"})
        self.assertEqual(r.status_code, 401)
        user = User.objects.create(username="u1", is_registered=True)
        self.client.force_login(user)
        self.client.post(f"/uz/i/comments/project/{p.pk}/add/", {"body": "Zo'r loyiha!"})
        self.assertEqual(Comment.objects.filter(user=user).count(), 1)

    def test_blocked_user_cannot_comment(self):
        p = Project.objects.first()
        user = User.objects.create(username="u2", is_registered=True, is_blocked=True)
        self.client.force_login(user)
        r = self.client.post(f"/uz/i/comments/project/{p.pk}/add/", {"body": "spam"})
        self.assertEqual(r.status_code, 403)

    def test_dashboard_is_staff_only(self):
        self.assertEqual(self.client.get("/uz/dashboard/").status_code, 302)
        self.client.force_login(User.objects.create(username="u3"))
        # Oddiy foydalanuvchi uchun panel umuman ko'rinmaydi
        self.assertEqual(self.client.get("/uz/dashboard/").status_code, 404)
        self.client.force_login(User.objects.create(username="staff", is_staff=True))
        self.assertEqual(self.client.get("/uz/dashboard/").status_code, 200)

    def test_contact_form(self):
        r = self.client.post("/uz/contact/", {"name": "Ali", "email": "ali@example.com", "subject": "Salom", "message": "Loyiha bor"})
        self.assertEqual(r.status_code, 302)
        from apps.interactions.models import ContactMessage

        self.assertEqual(ContactMessage.objects.count(), 1)


@override_settings(ALLOWED_HOSTS=["testserver"])
class SeoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)

    def test_sitemap_has_hreflang_alternates(self):
        r = self.client.get("/sitemap.xml")
        self.assertEqual(r.status_code, 200)
        body = r.content.decode()
        self.assertIn('hreflang="x-default"', body)
        self.assertIn("/ru/projects/nutrizone/", body)

    def test_robots_and_feed(self):
        self.assertIn("Sitemap:", self.client.get("/robots.txt").content.decode())
        self.assertEqual(self.client.get("/uz/blog/feed/").status_code, 200)

    def test_detail_pages_have_valid_jsonld(self):
        import json
        import re

        for url in ("/en/projects/nutrizone/", "/en/blog/why-i-love-building-with-django/", "/en/education/docker-from-zero-to-production/"):
            html = self.client.get(url).content.decode()
            blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
            self.assertGreaterEqual(len(blocks), 3, url)
            for b in blocks:
                json.loads(b)
            self.assertIn('rel="canonical"', html)

    def test_private_pages_are_noindex(self):
        html = self.client.get("/uz/accounts/login/").content.decode()
        self.assertIn('content="noindex, nofollow"', html)

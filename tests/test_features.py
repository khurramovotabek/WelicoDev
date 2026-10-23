"""Yangi bo'limlar: dashboard (kanal, musiqa, tajriba, ko'nikmalar), musiqa sahifasi, profil, ta'lim tarixi."""

from unittest import mock

from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.accounts.models import User
from apps.gallery.models import Track
from apps.interactions.models import Comment
from apps.portfolio.models import Experience, Project
from apps.telegram_bot.models import ChannelPost


@override_settings(ALLOWED_HOSTS=["testserver"], TELEGRAM_BOT_TOKEN="")
class FeatureTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)
        call_command("seed_extra", verbosity=0)
        cls.staff = User.objects.create(username="boss", is_staff=True, is_superuser=True)

    def test_dashboard_pages(self):
        self.client.force_login(self.staff)
        exp = Experience.objects.get(slug="tatu")
        for url in ["channel/", "channel/new/", "music/", "music/new/", f"music/{Track.objects.first().pk}/", "music/playlist/new/",
                    "experience/", "experience/new/?kind=education", f"experience/{exp.pk}/", "skills/", "skills/new/", "courses/"]:
            self.assertEqual(self.client.get(f"/uz/dashboard/{url}").status_code, 200, url)

    def test_channel_compose_draft_and_preview(self):
        self.client.force_login(self.staff)
        r = self.client.post("/uz/dashboard/channel/new/", {"title": "Test", "body": "<p><strong>Salom</strong></p>", "disable_preview": "on", "action": "save"})
        self.assertEqual(r.status_code, 302)
        post = ChannelPost.objects.get()
        self.assertEqual(post.status, "draft")
        r = self.client.post("/uz/dashboard/channel/preview/", {"body": "<h2>Sarlavha</h2><p>matn</p>"})
        self.assertEqual(r.json()["html"], "<b>Sarlavha</b>\n\nmatn")

    def test_music_page_and_seed(self):
        r = self.client.get("/uz/media/music/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Spotify")  # tashqi havolali sevimli treklar
        self.assertEqual(self.client.get("/uz/media/music/?category=favorites").status_code, 200)

    def test_experience_shows_education_separately(self):
        r = self.client.get("/uz/experience/")
        self.assertContains(r, "Toshkent axborot texnologiyalari universiteti")
        self.assertContains(r, "Dasturiy injiniring fakulteti")
        self.assertContains(r, "2014")

    def test_journal_redirects_to_blog(self):
        r = self.client.get("/uz/journal/why-i-love-building-with-django/")
        self.assertEqual(r.status_code, 301)
        self.assertEqual(r["Location"], "/uz/blog/why-i-love-building-with-django/")

    def test_profile_tabs_and_settings(self):
        user = User.objects.create(username="u", is_registered=True, first_name="Ali")
        self.client.force_login(user)
        for tab in ("overview", "courses", "saved", "certificates", "activity", "settings"):
            self.assertEqual(self.client.get(f"/uz/accounts/profile/?tab={tab}").status_code, 200, tab)
        self.client.post("/uz/accounts/profile/", {"first_name": "Vali", "last_name": "", "bio": "", "language": "ru"})
        user.refresh_from_db()
        self.assertEqual(user.first_name, "Vali")
        self.assertFalse(user.notify_news)  # belgilanmagan checkbox -> o'chiq

    @override_settings(TELEGRAM_BOT_TOKEN="1:T", CELERY_TASK_ALWAYS_EAGER=True)
    @mock.patch("apps.telegram_bot.api.send_message", return_value={"message_id": 1})
    def test_reply_notifies_comment_author(self, send):
        p = Project.objects.first()
        author = User.objects.create(username="a", telegram_id=111, is_registered=True, notify_comments=True)
        other = User.objects.create(username="b", telegram_id=222, is_registered=True, first_name="Bek")
        parent = Comment.objects.create(user=author, target=p, body="Zo'r loyiha")
        self.client.force_login(other)
        self.client.post(f"/uz/i/comments/project/{p.pk}/add/", {"body": "Rahmat, qo'shilaman", "parent": parent.pk})
        chats = [c.args[0] for c in send.call_args_list]
        self.assertIn(111, chats)


class YouTubeTrackTests(TestCase):
    """YouTube havolali treklar saytdagi pleyerda embed orqali ijro etiladi."""

    def test_youtube_id_and_payload(self):
        from apps.core.templatetags.wcd import track_payload, tracks_json

        cases = {
            "https://www.youtube.com/watch?v=7wtfhZwyrcc": "7wtfhZwyrcc",
            "https://youtu.be/D9G1VOjN_84?si=x": "D9G1VOjN_84",
            "https://music.youtube.com/watch?v=fKopy74weus&list=RD": "fKopy74weus",
            "https://open.spotify.com/track/abc": "",
        }
        for url, vid in cases.items():
            self.assertEqual(Track(title="t", artist="a", external_url=url).youtube_id, vid)
        t = Track.objects.create(title="Believer", artist="Imagine Dragons", external_url="https://www.youtube.com/watch?v=7wtfhZwyrcc")
        p = track_payload(t)
        self.assertEqual((p["src"], p["yt"]), ("yt:7wtfhZwyrcc", "7wtfhZwyrcc"))
        spotify = Track.objects.create(title="x", artist="y", external_url="https://open.spotify.com/track/abc")
        html = tracks_json([t, spotify], "ids")
        self.assertIn("7wtfhZwyrcc", html)
        self.assertNotIn('"title": "x"', html)

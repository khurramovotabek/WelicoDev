"""Darslarning ketma-ket ochilishi, video progress va uyga vazifa qoidalari."""

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.accounts.models import User
from apps.education import services
from apps.education.models import Course, Enrollment, HomeworkSubmission, Lesson

PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


@override_settings(ALLOWED_HOSTS=["testserver"])
class SequentialLessonsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="s1", telegram_id=2001, is_registered=True)
        self.course = Course.objects.create(title_uz="Docker", title_en="Docker", subtitle="x", status="published",
                                            cover=SimpleUploadedFile("c.png", PNG))
        self.l1 = Lesson.objects.create(course=self.course, order=1, title_uz="Bir", title_en="One", status="published",
                                        video_url="https://youtu.be/abcdefghijk", duration_seconds=100)
        self.l2 = Lesson.objects.create(course=self.course, order=2, title_uz="Ikki", title_en="Two", status="published",
                                        duration_seconds=100, video_url="https://youtu.be/abcdefghijk", homework_mode="submit")
        self.l3 = Lesson.objects.create(course=self.course, order=3, title_uz="Uch", title_en="Three", status="published",
                                        homework_mode="approval")
        self.client.force_login(self.user)

    def test_not_enrolled_cannot_open(self):
        self.assertFalse(services.is_lesson_unlocked(self.user, self.l1))
        r = self.client.get(self.l1.get_absolute_url())
        self.assertEqual(r.status_code, 302)

    def test_first_lesson_open_rest_locked(self):
        Enrollment.objects.create(user=self.user, course=self.course)
        self.assertTrue(services.is_lesson_unlocked(self.user, self.l1))
        self.assertFalse(services.is_lesson_unlocked(self.user, self.l2))
        self.assertEqual(self.client.get(self.l2.get_absolute_url()).status_code, 302)

    def test_completing_video_unlocks_next(self):
        Enrollment.objects.create(user=self.user, course=self.course)
        services.mark_video_completed(self.user, self.l1)
        self.assertTrue(services.is_lesson_unlocked(self.user, self.l2))
        self.assertFalse(services.is_lesson_unlocked(self.user, self.l3))

    def test_heartbeat_cannot_skip(self):
        Enrollment.objects.create(user=self.user, course=self.course)
        # Bitta so'rovda 1000 soniya "ko'rdim" deyish faqat 30 soniya hisoblanadi
        p = services.record_watch(self.user, self.l1, position=99, delta=1000)
        self.assertEqual(p.watched_seconds, 30)
        self.assertFalse(p.video_completed)
        for _ in range(3):
            p = services.record_watch(self.user, self.l1, position=99, delta=30)
        self.assertTrue(p.video_completed)
        self.assertTrue(p.is_completed)

    def test_homework_submit_mode(self):
        Enrollment.objects.create(user=self.user, course=self.course)
        services.mark_video_completed(self.user, self.l1)
        services.mark_video_completed(self.user, self.l2)
        self.assertFalse(services.is_lesson_unlocked(self.user, self.l3))
        url = self.l2.get_absolute_url() + "homework/"
        self.client.post(url, {"link": "https://github.com/x/y"})
        self.assertTrue(services.is_lesson_unlocked(self.user, self.l3))

    def test_approval_mode_and_certificate(self):
        Enrollment.objects.create(user=self.user, course=self.course)
        for lesson in (self.l1, self.l2):
            services.mark_video_completed(self.user, lesson)
        HomeworkSubmission.objects.create(user=self.user, lesson=self.l2, link="https://github.com/x/y")
        services.try_complete(self.user, self.l2)
        sub = HomeworkSubmission.objects.create(user=self.user, lesson=self.l3, text="javob")
        services.try_complete(self.user, self.l3)
        self.assertEqual(services.course_progress(self.user, self.course), 67)
        sub.mark_reviewed("approved")
        services.try_complete(self.user, self.l3)
        self.assertEqual(services.course_progress(self.user, self.course), 100)
        enr = Enrollment.objects.get(user=self.user)
        self.assertIsNotNone(enr.completed_at)
        self.assertTrue(enr.certificate.code.startswith("WCD-"))

    def test_lesson_list_states(self):
        Enrollment.objects.create(user=self.user, course=self.course)
        states = [s for _l, s in services.lesson_states(self.user, self.course)]
        self.assertEqual(states, ["current", "locked", "locked"])

    def test_protected_video_requires_unlock(self):
        self.l2.video = SimpleUploadedFile("v.mp4", b"0" * 4096)
        self.l2.save()
        url = self.l2.get_absolute_url() + "video/"
        self.assertEqual(self.client.get(url).status_code, 404)
        Enrollment.objects.create(user=self.user, course=self.course)
        services.mark_video_completed(self.user, self.l1)
        r = self.client.get(url, HTTP_RANGE="bytes=0-1023")
        self.assertEqual(r.status_code, 206)
        self.assertEqual(r["Content-Range"], "bytes 0-1023/4096")

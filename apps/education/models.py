from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django_ckeditor_5.fields import CKEditor5Field

from apps.core.models import PublishedQuerySet, PublishStatus, SeoModel, TimeStampedModel, unique_slugify

# Dars videolari ochiq /media/ orqali berilmaydi: faqat ruxsat tekshirilgandan keyin view orqali.
protected_storage = FileSystemStorage(location=settings.PROTECTED_MEDIA_ROOT, base_url=None)

# Videoning shuncha qismi ko'rilganda dars "ko'rilgan" hisoblanadi
WATCH_THRESHOLD = 0.9


class CourseQuerySet(PublishedQuerySet):
    def listed(self):
        """Ommaviy ro'yxatlar uchun: yopiq kurslarsiz."""
        return self.published().filter(is_private=False)

    def for_user(self, user):
        """Foydalanuvchi ko'ra oladigan e'lon qilingan kurslar (yopiqlari faqat ruxsat bo'lsa)."""
        qs = self.published()
        if user.is_authenticated and user.is_staff:
            return qs
        if user.is_authenticated:
            return qs.filter(models.Q(is_private=False) | models.Q(enrollments__user=user)).distinct()
        return qs.filter(is_private=False)


class Course(TimeStampedModel, SeoModel):
    class Level(models.TextChoices):
        BEGINNER = "beginner", _("Boshlang'ich")
        INTERMEDIATE = "intermediate", _("O'rta")
        ADVANCED = "advanced", _("Yuqori")

    title = models.CharField(_("nomi"), max_length=150)
    slug = models.SlugField(_("slug"), max_length=170, unique=True, blank=True)
    subtitle = models.CharField(_("qisqa tavsif"), max_length=200)
    description = CKEditor5Field(_("to'liq tavsif"), config_name="default", blank=True)
    what_you_learn = CKEditor5Field(_("nimalarni o'rganasiz"), config_name="default", blank=True)
    requirements = CKEditor5Field(_("talablar"), config_name="default", blank=True)
    for_whom = CKEditor5Field(_("kurs kimlar uchun"), config_name="default", blank=True)
    language = models.CharField(_("dars tili"), max_length=5, choices=settings.LANGUAGES, default="uz")
    has_certificate = models.BooleanField(_("sertifikat beriladi"), default=True)
    cover = models.ImageField(_("muqova"), upload_to="courses/covers/")
    trailer_url = models.URLField(_("treyler havolasi"), blank=True)
    level = models.CharField(_("daraja"), max_length=15, choices=Level.choices, default=Level.BEGINNER)
    technologies = models.ManyToManyField("portfolio.Skill", verbose_name=_("texnologiyalar"), blank=True, related_name="courses")

    is_free = models.BooleanField(_("bepul"), default=True)
    price = models.DecimalField(_("narxi (so'm)"), max_digits=12, decimal_places=0, default=0)
    old_price = models.DecimalField(_("eski narx (chegirma uchun)"), max_digits=12, decimal_places=0, null=True, blank=True)
    is_private = models.BooleanField(
        _("yopiq kurs"), default=False,
        help_text=_("Faqat siz ruxsat bergan foydalanuvchilar ko'radi; ro'yxatlarda va qidiruvda chiqmaydi"),
    )
    sequential = models.BooleanField(
        _("ketma-ket ochilish"), default=True,
        help_text=_("Yoqilgan bo'lsa, keyingi dars oldingisi tugatilgandan keyin ochiladi"),
    )
    require_login_for_preview = models.BooleanField(_("kurs sahifasi uchun login"), default=False)
    status = models.CharField(_("holati"), max_length=10, choices=PublishStatus.choices, default=PublishStatus.DRAFT)
    is_featured = models.BooleanField(_("tanlangan"), default=False)
    allow_reviews = models.BooleanField(_("sharhlarga ruxsat"), default=True)
    focus_keyword = models.CharField(_("asosiy kalit so'z"), max_length=80, blank=True)
    order = models.PositiveSmallIntegerField(_("tartib"), default=0)

    objects = CourseQuerySet.as_manager()

    class Meta:
        ordering = ["order", "-created_at"]
        verbose_name = _("kurs")
        verbose_name_plural = _("kurslar")

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.title_en or self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("education:course_detail", args=[self.slug])

    def published_lessons(self):
        return self.lessons.filter(status=PublishStatus.PUBLISHED).order_by("order", "id")

    @property
    def discount_percent(self):
        if self.old_price and self.price and self.old_price > self.price:
            return round((1 - self.price / self.old_price) * 100)
        return 0

    def visible_to(self, user):
        """Yopiq kursni faqat ruxsat berilganlar va admin ko'radi."""
        if not self.is_private:
            return True
        if not user.is_authenticated:
            return False
        return user.is_staff or self.enrollments.filter(user=user).exists()

    @cached_property
    def total_seconds(self):
        return sum(self.published_lessons().values_list("duration_seconds", flat=True))


class Module(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="modules")
    title = models.CharField(_("nomi"), max_length=150)
    order = models.PositiveSmallIntegerField(_("tartib"), default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = _("modul")
        verbose_name_plural = _("modullar")

    def __str__(self):
        return self.title


class Lesson(TimeStampedModel):
    class HomeworkMode(models.TextChoices):
        NONE = "none", _("Uyga vazifa yo'q")
        OPTIONAL = "optional", _("Ixtiyoriy")
        SUBMIT = "submit", _("Topshirish shart")
        APPROVAL = "approval", _("Admin qabul qilishi shart")

    course = models.ForeignKey(Course, verbose_name=_("kurs"), on_delete=models.CASCADE, related_name="lessons")
    module = models.ForeignKey(Module, verbose_name=_("modul"), on_delete=models.SET_NULL, null=True, blank=True, related_name="lessons")
    title = models.CharField(_("nomi"), max_length=200)
    slug = models.SlugField(_("slug"), max_length=220, blank=True)
    order = models.PositiveSmallIntegerField(_("tartib raqami"), default=1)
    summary = models.CharField(_("qisqa tavsif"), max_length=250, blank=True)

    video = models.FileField(_("video fayl"), storage=protected_storage, upload_to="lessons/", blank=True)
    video_url = models.URLField(
        _("tashqi video havolasi"), blank=True,
        help_text=_("Fayl o'rniga YouTube (unlisted) yoki boshqa havola"),
    )
    duration_seconds = models.PositiveIntegerField(_("davomiyligi (soniya)"), default=0)
    thumbnail = models.ImageField(_("muqova"), upload_to="lessons/thumbs/", blank=True)

    content = CKEditor5Field(_("konspekt va kodlar"), config_name="default", blank=True)
    homework = CKEditor5Field(_("uyga vazifa"), config_name="default", blank=True)
    homework_mode = models.CharField(_("uyga vazifa talabi"), max_length=10, choices=HomeworkMode.choices, default=HomeworkMode.NONE)

    posted_to_channel_at = models.DateTimeField(_("kanalga joylangan"), null=True, blank=True, editable=False)
    is_preview = models.BooleanField(_("bepul ko'rish"), default=False, help_text=_("Kursga yozilmaganlar ham ko'ra oladi"))
    status = models.CharField(_("holati"), max_length=10, choices=PublishStatus.choices, default=PublishStatus.DRAFT)

    class Meta:
        ordering = ["course", "order", "id"]
        unique_together = [("course", "slug")]
        verbose_name = _("dars")
        verbose_name_plural = _("darslar")

    def __str__(self):
        return f"{self.order}. {self.title}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = unique_slugify(self, self.title_en or self.title)
            self.slug = base
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("education:lesson_detail", args=[self.course.slug, self.slug])

    @property
    def has_video(self):
        return bool(self.video or self.video_url)

    @property
    def duration_label(self):
        m, s = divmod(self.duration_seconds, 60)
        h, m = divmod(m, 60)
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

    def previous_lesson(self):
        return (
            self.course.published_lessons()
            .filter(models.Q(order__lt=self.order) | models.Q(order=self.order, id__lt=self.id))
            .order_by("-order", "-id")
            .first()
        )

    def next_lesson(self):
        return (
            self.course.published_lessons()
            .filter(models.Q(order__gt=self.order) | models.Q(order=self.order, id__gt=self.id))
            .first()
        )


class LessonResource(models.Model):
    class Kind(models.TextChoices):
        LINK = "link", _("Havola")
        FILE = "file", _("Fayl")
        GITHUB = "github", "GitHub"
        DOCS = "docs", _("Hujjat")

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="resources")
    kind = models.CharField(_("turi"), max_length=10, choices=Kind.choices, default=Kind.LINK)
    title = models.CharField(_("nomi"), max_length=150)
    url = models.URLField(_("havola"), blank=True)
    file = models.FileField(_("fayl"), storage=protected_storage, upload_to="resources/", blank=True)
    order = models.PositiveSmallIntegerField(_("tartib"), default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = _("resurs")
        verbose_name_plural = _("resurslar")

    def __str__(self):
        return self.title


class Enrollment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    is_active = models.BooleanField(_("faol"), default=True, help_text=_("O'chirilsa, foydalanuvchi kursni ko'ra olmaydi"))
    created_at = models.DateTimeField(_("yozilgan"), auto_now_add=True)
    completed_at = models.DateTimeField(_("tugatgan"), null=True, blank=True)
    last_lesson = models.ForeignKey(Lesson, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    granted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name="+", verbose_name=_("ruxsat bergan"))
    expires_at = models.DateTimeField(_("ruxsat muddati"), null=True, blank=True, help_text=_("Bo'sh bo'lsa muddatsiz"))

    class Meta:
        unique_together = [("user", "course")]
        ordering = ["-created_at"]
        verbose_name = _("kursga yozilish")
        verbose_name_plural = _("kursga yozilishlar")

    def __str__(self):
        return f"{self.user} → {self.course}"


class AccessRequest(TimeStampedModel):
    """Pullik kursga kirish so'rovi: foydalanuvchi to'lovni Telegram orqali qiladi, admin dashboarddan ruxsat beradi."""

    class Status(models.TextChoices):
        PENDING = "pending", _("Kutilmoqda")
        APPROVED = "approved", _("Ruxsat berildi")
        REJECTED = "rejected", _("Rad etildi")

    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_("foydalanuvchi"), on_delete=models.CASCADE, related_name="access_requests")
    course = models.ForeignKey(Course, verbose_name=_("kurs"), on_delete=models.CASCADE, related_name="access_requests")
    status = models.CharField(_("holati"), max_length=10, choices=Status.choices, default=Status.PENDING)
    note = models.CharField(_("foydalanuvchi izohi"), max_length=300, blank=True)
    admin_note = models.CharField(_("admin izohi"), max_length=300, blank=True)
    amount = models.DecimalField(_("to'langan summa"), max_digits=12, decimal_places=0, null=True, blank=True)
    reviewed_at = models.DateTimeField(_("ko'rib chiqilgan"), null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("kursga kirish so'rovi")
        verbose_name_plural = _("kursga kirish so'rovlari")

    def __str__(self):
        return f"{self.user} → {self.course} ({self.get_status_display()})"

    @property
    def reference(self):
        """Telegram xabarida foydalanuvchini tez topish uchun qisqa kod."""
        return f"WCD-{self.pk:05d}"


class LessonProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lesson_progress")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="progress")
    watched_seconds = models.PositiveIntegerField(_("ko'rilgan soniyalar"), default=0)
    last_position = models.PositiveIntegerField(_("oxirgi joy"), default=0)
    video_completed = models.BooleanField(_("video ko'rildi"), default=False)
    completed_at = models.DateTimeField(_("tugatilgan"), null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("user", "lesson")]
        verbose_name = _("dars progressi")
        verbose_name_plural = _("dars progresslari")

    def __str__(self):
        return f"{self.user} · {self.lesson}"

    @property
    def is_completed(self):
        return self.completed_at is not None


class HomeworkSubmission(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", _("Tekshirilmoqda")
        APPROVED = "approved", _("Qabul qilindi")
        REJECTED = "rejected", _("Qayta ishlash kerak")

    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_("foydalanuvchi"), on_delete=models.CASCADE, related_name="submissions")
    lesson = models.ForeignKey(Lesson, verbose_name=_("dars"), on_delete=models.CASCADE, related_name="submissions")
    text = models.TextField(_("javob"), blank=True)
    link = models.URLField(_("havola"), blank=True, help_text=_("GitHub repo yoki boshqa havola"))
    file = models.FileField(_("fayl"), storage=protected_storage, upload_to="homework/", blank=True)
    status = models.CharField(_("holati"), max_length=10, choices=Status.choices, default=Status.PENDING)
    feedback = models.TextField(_("izoh (admin)"), blank=True)
    reviewed_at = models.DateTimeField(_("tekshirilgan"), null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("uyga vazifa javobi")
        verbose_name_plural = _("uyga vazifa javoblari")

    def __str__(self):
        return f"{self.user} · {self.lesson}"

    def mark_reviewed(self, status, feedback=""):
        self.status = status
        self.feedback = feedback
        self.reviewed_at = timezone.now()
        self.save(update_fields=["status", "feedback", "reviewed_at", "updated_at"])


class Certificate(models.Model):
    enrollment = models.OneToOneField(Enrollment, on_delete=models.CASCADE, related_name="certificate")
    code = models.CharField(_("sertifikat raqami"), max_length=20, unique=True)
    issued_at = models.DateTimeField(_("berilgan"), auto_now_add=True)

    class Meta:
        verbose_name = _("sertifikat")
        verbose_name_plural = _("sertifikatlar")

    def __str__(self):
        return self.code

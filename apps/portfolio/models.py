from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django_ckeditor_5.fields import CKEditor5Field

from apps.core.models import (
    PublishedQuerySet, PublishStatus, SeoModel, Tag, TimeStampedModel, unique_slugify,
)

DEVICON_BASE = "https://cdn.jsdelivr.net/gh/devicons/devicon@v2.16.0/icons"
DEVICON_VARIANTS = ("original-wordmark", "plain-wordmark", "original", "plain", "line")


# --------------------------------------------------------------------------- Skills

class SkillCategory(models.Model):
    name = models.CharField(_("nomi"), max_length=60)
    slug = models.SlugField(_("slug"), max_length=60, unique=True, blank=True)
    order = models.PositiveSmallIntegerField(_("tartib"), default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = _("ko'nikma turkumi")
        verbose_name_plural = _("ko'nikma turkumlari")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.name_en or self.name)
        super().save(*args, **kwargs)


class Skill(models.Model):
    class Level(models.TextChoices):
        BEGINNER = "beginner", _("Boshlang'ich")
        INTERMEDIATE = "intermediate", _("O'rta")
        ADVANCED = "advanced", _("Yuqori")
        EXPERT = "expert", _("Ekspert")

    name = models.CharField(_("nomi"), max_length=60)
    slug = models.SlugField(_("slug"), max_length=60, unique=True, blank=True)
    category = models.ForeignKey(SkillCategory, verbose_name=_("turkum"), on_delete=models.PROTECT, related_name="skills")
    subtitle = models.CharField(_("qisqa izoh"), max_length=80, blank=True, help_text=_("Masalan: Web Framework"))
    devicon = models.CharField(
        _("devicon nomi"), max_length=60, blank=True,
        help_text=_("devicon.dev dagi nom: python, docker. Kerak bo'lsa variant bilan: django-plain. Saytdagi belgilar: wcd:sql, wcd:rest-api, wcd:celery, wcd:aiogram, wcd:vps, wcd:ai, wcd:prompt, wcd:nextjs, wcd:github"),
    )
    icon = models.FileField(_("o'z belgisi"), upload_to="skills/", blank=True, help_text=_("SVG/PNG. Devicon'dan ustun turadi."))
    level = models.CharField(_("daraja"), max_length=15, choices=Level.choices, default=Level.INTERMEDIATE)
    proficiency = models.PositiveSmallIntegerField(_("bilim darajasi %"), default=70)
    years = models.PositiveSmallIntegerField(_("tajriba (yil)"), default=1)
    is_featured = models.BooleanField(_("asosiy ko'nikma"), default=False)
    is_learning = models.BooleanField(_("hozir o'rganilmoqda"), default=False)
    learning_progress = models.PositiveSmallIntegerField(_("o'rganish progressi %"), default=0)
    started_year = models.PositiveSmallIntegerField(_("boshlangan yil"), null=True, blank=True)
    order = models.PositiveSmallIntegerField(_("tartib"), default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = _("ko'nikma")
        verbose_name_plural = _("ko'nikmalar")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.name)
        super().save(*args, **kwargs)

    @property
    def icon_url(self):
        if self.icon:
            return self.icon.url
        if self.devicon.startswith("wcd:"):
            # Sayt bilan birga keladigan belgilar: wcd:sql, wcd:rest-api, wcd:ai ... (static/img/skills/)
            from django.templatetags.static import static

            return static(f"img/skills/{self.devicon[4:]}.svg")
        if self.devicon:
            # "django" -> django-original.svg; "django-plain" yoki "aws-original-wordmark" -> aniq variant
            for variant in DEVICON_VARIANTS:
                if self.devicon.endswith(f"-{variant}"):
                    return f"{DEVICON_BASE}/{self.devicon[: -len(variant) - 1]}/{self.devicon}.svg"
            return f"{DEVICON_BASE}/{self.devicon}/{self.devicon}-original.svg"
        return ""


# --------------------------------------------------------------------------- Projects

class ProjectCategory(models.Model):
    name = models.CharField(_("nomi"), max_length=60)
    slug = models.SlugField(_("slug"), max_length=60, unique=True, blank=True)
    order = models.PositiveSmallIntegerField(_("tartib"), default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = _("loyiha turkumi")
        verbose_name_plural = _("loyiha turkumlari")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.name_en or self.name)
        super().save(*args, **kwargs)


class Project(TimeStampedModel, SeoModel):
    title = models.CharField(_("nomi"), max_length=120)
    slug = models.SlugField(_("slug"), max_length=140, unique=True, blank=True)
    subtitle = models.CharField(_("qisqa shior"), max_length=120, blank=True, help_text=_("Masalan: Smart nutrition ecosystem"))
    short_description = models.CharField(_("qisqa tavsif"), max_length=200)
    description = CKEditor5Field(_("to'liq tavsif"), config_name="default", blank=True)

    category = models.ForeignKey(ProjectCategory, verbose_name=_("turkum"), on_delete=models.SET_NULL, null=True, blank=True, related_name="projects")
    tags = models.ManyToManyField(Tag, verbose_name=_("teglar"), blank=True, related_name="projects")
    tech_stack = models.ManyToManyField(Skill, verbose_name=_("texnologiyalar"), blank=True, related_name="projects")

    cover = models.ImageField(_("muqova"), upload_to="projects/covers/")
    video = models.FileField(_("video fayl"), upload_to="projects/videos/", blank=True)
    video_url = models.URLField(_("video havolasi"), blank=True, help_text=_("YouTube havolasi (fayl bo'lmasa)"))
    video_duration = models.CharField(_("video davomiyligi"), max_length=10, blank=True)

    live_url = models.URLField(_("sayt havolasi"), blank=True)
    source_url = models.URLField(_("manba kod havolasi"), blank=True)
    project_type = models.CharField(_("turi"), max_length=60, blank=True, help_text=_("Web & Mobile"))
    role = models.CharField(_("rolim"), max_length=80, blank=True)
    duration = models.CharField(_("davomiyligi"), max_length=40, blank=True)
    team_size = models.CharField(_("jamoa"), max_length=40, blank=True)
    completed_year = models.PositiveSmallIntegerField(_("yakunlangan yil"), null=True, blank=True)

    status = models.CharField(_("holati"), max_length=10, choices=PublishStatus.choices, default=PublishStatus.DRAFT)
    is_featured = models.BooleanField(_("tanlangan"), default=False)
    allow_comments = models.BooleanField(_("izohlarga ruxsat"), default=True)
    allow_reviews = models.BooleanField(_("sharhlarga ruxsat"), default=True)
    order = models.PositiveSmallIntegerField(_("tartib"), default=0)
    views_count = models.PositiveIntegerField(_("ko'rishlar"), default=0, editable=False)

    objects = PublishedQuerySet.as_manager()

    class Meta:
        ordering = ["order", "-created_at"]
        verbose_name = _("loyiha")
        verbose_name_plural = _("loyihalar")

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.title_en or self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("portfolio:project_detail", args=[self.slug])


class ProjectImage(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(_("rasm"), upload_to="projects/gallery/")
    caption = models.CharField(_("izoh"), max_length=80, blank=True)
    order = models.PositiveSmallIntegerField(_("tartib"), default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = _("loyiha rasmi")
        verbose_name_plural = _("loyiha rasmlari")

    def __str__(self):
        return self.caption or f"#{self.pk}"


class ProjectFeature(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="features")
    title = models.CharField(_("sarlavha"), max_length=80)
    description = models.CharField(_("tavsif"), max_length=160, blank=True)
    icon = models.CharField(_("belgi"), max_length=40, blank=True, help_text=_("Lucide belgi nomi, masalan: store"))
    order = models.PositiveSmallIntegerField(_("tartib"), default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = _("imkoniyat")
        verbose_name_plural = _("imkoniyatlar")

    def __str__(self):
        return self.title


class ProjectChallenge(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="challenges")
    text = models.CharField(_("matn"), max_length=160)
    order = models.PositiveSmallIntegerField(_("tartib"), default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = _("qiyinchilik")
        verbose_name_plural = _("qiyinchiliklar")

    def __str__(self):
        return self.text


class ProjectResult(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="results")
    value = models.CharField(_("qiymat"), max_length=20, help_text="10K+")
    label = models.CharField(_("nomi"), max_length=40, help_text="Active users")
    icon = models.CharField(_("belgi"), max_length=40, blank=True)
    order = models.PositiveSmallIntegerField(_("tartib"), default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = _("natija")
        verbose_name_plural = _("natijalar")

    def __str__(self):
        return f"{self.value} {self.label}"


# --------------------------------------------------------------------------- Experience

class Experience(TimeStampedModel):
    class Kind(models.TextChoices):
        WORK = "work", _("Ish")
        STARTUP = "startup", _("Startap")
        FREELANCE = "freelance", _("Frilans")
        PERSONAL = "personal", _("Shaxsiy loyihalar")
        EDUCATION = "education", _("Ta'lim")
        ACHIEVEMENT = "achievement", _("Yutuq")

    company = models.CharField(_("kompaniya / joy"), max_length=100)
    slug = models.SlugField(_("slug"), max_length=120, unique=True, blank=True)
    role = models.CharField(_("lavozim"), max_length=100)
    kind = models.CharField(_("turi"), max_length=15, choices=Kind.choices, default=Kind.WORK)
    logo = models.ImageField(_("logo"), upload_to="experience/", blank=True)
    location = models.CharField(_("joylashuv"), max_length=80, blank=True)
    start_date = models.DateField(_("boshlangan"))
    end_date = models.DateField(_("tugagan"), null=True, blank=True)
    is_current = models.BooleanField(_("hozir shu yerda"), default=False)
    summary = models.TextField(_("qisqa tavsif"), max_length=400)
    description = CKEditor5Field(_("batafsil"), config_name="default", blank=True)
    quote = models.CharField(_("iqtibos"), max_length=200, blank=True)
    # Ta'lim uchun (kind=education)
    degree = models.CharField(_("daraja"), max_length=100, blank=True, help_text=_("Masalan: Bakalavr, O'rta ma'lumot"))
    field_of_study = models.CharField(_("yo'nalish / fakultet"), max_length=150, blank=True, help_text=_("Masalan: Dasturiy injiniring"))
    grade = models.CharField(_("baho / GPA"), max_length=40, blank=True)
    achievements = CKEditor5Field(_("yutuqlar va faoliyat"), config_name="default", blank=True)

    company_description = models.TextField(_("kompaniya haqida"), blank=True)
    company_industry = models.CharField(_("soha"), max_length=80, blank=True)
    website = models.URLField(_("veb-sayt"), blank=True)
    map_url = models.URLField(_("xarita havolasi"), blank=True)
    team_size = models.PositiveSmallIntegerField(_("jamoa a'zolari"), null=True, blank=True)
    products_count = models.PositiveSmallIntegerField(_("asosiy mahsulotlar"), null=True, blank=True)

    technologies = models.ManyToManyField(Skill, verbose_name=_("texnologiyalar"), blank=True, related_name="experiences")
    projects = models.ManyToManyField(Project, verbose_name=_("loyihalar"), blank=True, related_name="experiences")
    is_published = models.BooleanField(_("ko'rinadi"), default=True)
    order = models.PositiveSmallIntegerField(_("tartib"), default=0)

    class Meta:
        ordering = ["-is_current", "-start_date"]
        verbose_name = _("tajriba")
        verbose_name_plural = _("tajribalar")

    def __str__(self):
        return f"{self.company} — {self.role}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.company)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("portfolio:experience_detail", args=[self.slug])

    @property
    def years(self):
        """Davomiylik to'liq yillarda (kamida 1)."""
        from datetime import date

        end = date.today() if self.is_current or not self.end_date else self.end_date
        return max(1, (end - self.start_date).days // 365)


class ExperienceImage(models.Model):
    experience = models.ForeignKey(Experience, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(_("rasm"), upload_to="experience/gallery/")
    caption = models.CharField(_("izoh"), max_length=80, blank=True)
    order = models.PositiveSmallIntegerField(_("tartib"), default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = _("rasm")
        verbose_name_plural = _("rasmlar")


class Responsibility(models.Model):
    experience = models.ForeignKey(Experience, on_delete=models.CASCADE, related_name="responsibilities")
    text = models.CharField(_("matn"), max_length=200)
    order = models.PositiveSmallIntegerField(_("tartib"), default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = _("vazifa")
        verbose_name_plural = _("vazifalar")

    def __str__(self):
        return self.text


class Milestone(models.Model):
    """Tajriba ichidagi vaqt chizig'i (Work Timeline)."""

    experience = models.ForeignKey(Experience, on_delete=models.CASCADE, related_name="milestones")
    date_label = models.CharField(_("sana"), max_length=20, help_text="Aug 2024")
    title = models.CharField(_("sarlavha"), max_length=100)
    description = models.CharField(_("tavsif"), max_length=160, blank=True)
    order = models.PositiveSmallIntegerField(_("tartib"), default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = _("bosqich")
        verbose_name_plural = _("bosqichlar")

    def __str__(self):
        return self.title


# --------------------------------------------------------------------------- About

class JourneyStep(models.Model):
    """About sahifasidagi "My Journey" vaqt chizig'i."""

    year = models.PositiveSmallIntegerField(_("yil"))
    title = models.CharField(_("sarlavha"), max_length=80)
    order = models.PositiveSmallIntegerField(_("tartib"), default=0)

    class Meta:
        ordering = ["year", "order"]
        verbose_name = _("hayot yo'li bosqichi")
        verbose_name_plural = _("hayot yo'li")

    def __str__(self):
        return f"{self.year} — {self.title}"


class Interest(models.Model):
    title = models.CharField(_("nomi"), max_length=40)
    image = models.ImageField(_("rasm"), upload_to="interests/")
    order = models.PositiveSmallIntegerField(_("tartib"), default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = _("qiziqish")
        verbose_name_plural = _("qiziqishlar")

    def __str__(self):
        return self.title

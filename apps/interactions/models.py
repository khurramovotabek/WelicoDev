from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


class GenericTarget(models.Model):
    """Loyiha, maqola, foto, video yoki kursga bog'lanadigan obyektlar uchun asos."""

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveBigIntegerField()
    target = GenericForeignKey("content_type", "object_id")

    class Meta:
        abstract = True
        indexes = [models.Index(fields=["content_type", "object_id"])]


class Comment(GenericTarget, TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_("foydalanuvchi"), on_delete=models.CASCADE, related_name="comments")
    parent = models.ForeignKey("self", verbose_name=_("javob"), null=True, blank=True, on_delete=models.CASCADE, related_name="replies")
    body = models.TextField(_("izoh"), max_length=2000)
    is_approved = models.BooleanField(_("tasdiqlangan"), default=True)
    is_pinned = models.BooleanField(_("qadalgan"), default=False)
    likes_count = models.PositiveIntegerField(default=0, editable=False)

    class Meta:
        ordering = ["-is_pinned", "-created_at"]
        indexes = GenericTarget.Meta.indexes
        verbose_name = _("izoh")
        verbose_name_plural = _("izohlar")

    def __str__(self):
        return f"{self.user}: {self.body[:40]}"


class CommentLike(models.Model):
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class Meta:
        unique_together = [("comment", "user")]


class Review(GenericTarget, TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_("foydalanuvchi"), on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(_("baho"), validators=[MinValueValidator(1), MaxValueValidator(5)])
    body = models.TextField(_("sharh"), max_length=1000)
    is_approved = models.BooleanField(_("tasdiqlangan"), default=False)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "content_type", "object_id"], name="one_review_per_user"),
        ]
        indexes = GenericTarget.Meta.indexes
        verbose_name = _("sharh")
        verbose_name_plural = _("sharhlar")

    def __str__(self):
        return f"{self.user} · {self.rating}★"


class Reaction(GenericTarget):
    """Like va saqlash (bookmark)."""

    class Kind(models.TextChoices):
        LIKE = "like", _("Like")
        BOOKMARK = "bookmark", _("Saqlangan")

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reactions")
    kind = models.CharField(max_length=10, choices=Kind.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "kind", "content_type", "object_id"], name="one_reaction_per_kind"),
        ]
        indexes = GenericTarget.Meta.indexes
        verbose_name = _("reaksiya")
        verbose_name_plural = _("reaksiyalar")


class ShareEvent(GenericTarget):
    class Platform(models.TextChoices):
        TELEGRAM = "telegram", "Telegram"
        WHATSAPP = "whatsapp", "WhatsApp"
        LINKEDIN = "linkedin", "LinkedIn"
        X = "x", "X (Twitter)"
        FACEBOOK = "facebook", "Facebook"
        REDDIT = "reddit", "Reddit"
        LINK = "link", _("Havola nusxasi")
        QR = "qr", "QR"
        OTHER = "other", _("Boshqa")

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    platform = models.CharField(max_length=15, choices=Platform.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = GenericTarget.Meta.indexes
        verbose_name = _("ulashish")
        verbose_name_plural = _("ulashishlar")


class ContactMessage(TimeStampedModel):
    class Status(models.TextChoices):
        NEW = "new", _("Yangi")
        READ = "read", _("O'qilgan")
        REPLIED = "replied", _("Javob berilgan")
        ARCHIVED = "archived", _("Arxiv")

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="contact_messages")
    name = models.CharField(_("ism"), max_length=100)
    email = models.EmailField(_("email"))
    subject = models.CharField(_("mavzu"), max_length=150, blank=True)
    message = models.TextField(_("xabar"), max_length=5000)
    attachment = models.FileField(_("ilova"), upload_to="contact/", blank=True)
    status = models.CharField(_("holati"), max_length=10, choices=Status.choices, default=Status.NEW)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("xabar")
        verbose_name_plural = _("xabarlar")

    def __str__(self):
        return f"{self.name}: {self.subject or self.message[:40]}"


class PageVisit(models.Model):
    """Kunlik yig'ma statistika (dashboard grafigi uchun). Har bir so'rov emas, kun bo'yicha hisob."""

    date = models.DateField(unique=True)
    views = models.PositiveIntegerField(default=0)
    unique_visitors = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-date"]
        verbose_name = _("kunlik tashrif")
        verbose_name_plural = _("kunlik tashriflar")

import secrets
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """Saytga faqat Telegram orqali kiriladi; parol faqat adminlar uchun ishlatiladi."""

    telegram_id = models.BigIntegerField(_("Telegram ID"), unique=True, null=True, blank=True)
    telegram_username = models.CharField(_("Telegram username"), max_length=64, blank=True)
    phone = models.CharField(_("telefon"), max_length=20, blank=True)
    avatar = models.ImageField(_("avatar"), upload_to="avatars/", blank=True)
    language = models.CharField(_("til"), max_length=5, choices=settings.LANGUAGES, default="uz")
    bio = models.CharField(_("bio"), max_length=200, blank=True)
    is_registered = models.BooleanField(
        _("ro'yxatdan o'tgan"), default=False,
        help_text=_("Botda ism, familiya va telefonni to'liq kiritgan"),
    )
    is_blocked = models.BooleanField(_("bloklangan"), default=False)
    bot_blocked = models.BooleanField(
        _("botni bloklagan"), default=False, help_text=_("Foydalanuvchi botni to'xtatgan, xabar yetib bormaydi"),
    )
    notify_news = models.BooleanField(_("yangi kurs va maqolalar haqida xabar"), default=True,
                                      help_text=_("Bot orqali yangi kontent haqida xabar olish"))
    notify_comments = models.BooleanField(_("izohimga javob haqida xabar"), default=True)
    last_bot_activity = models.DateTimeField(_("botdagi oxirgi faollik"), null=True, blank=True)
    nudge_stage = models.PositiveSmallIntegerField(
        _("yuborilgan eslatmalar"), default=0, editable=False,
        help_text=_("Kursga yozilmaganlarga yuborilgan 'kursni boshlang' eslatmalari soni"),
    )

    class Meta:
        verbose_name = _("foydalanuvchi")
        verbose_name_plural = _("foydalanuvchilar")

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def display_name(self):
        return self.get_full_name() or (f"@{self.telegram_username}" if self.telegram_username else self.username)

    @property
    def initials(self):
        parts = [self.first_name[:1], self.last_name[:1]]
        return "".join(parts).upper() or self.username[:2].upper()


def _generate_code():
    return f"{secrets.randbelow(1_000_000):06d}"


class LoginRequest(models.Model):
    """Saytdagi bitta kirish urinishi. Brauzer sessiyasiga bog'lanadi.

    Bot deep link (`/start login_<token>`) orqali foydalanuvchi tasdiqlasa, shu brauzer
    kod kiritmasdan ham kiradi. Aks holda bot bergan 6 xonali kod kiritiladi.
    """

    class Status(models.TextChoices):
        PENDING = "pending", _("Kutilmoqda")
        CONFIRMED = "confirmed", _("Tasdiqlandi")
        REJECTED = "rejected", _("Rad etildi")
        USED = "used", _("Ishlatildi")

    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    session_key = models.CharField(max_length=64, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("kirish so'rovi")
        verbose_name_plural = _("kirish so'rovlari")

    @property
    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=10)


class LoginCode(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="login_codes")
    request = models.ForeignKey(LoginRequest, null=True, blank=True, on_delete=models.SET_NULL)
    code = models.CharField(max_length=6, default=_generate_code, db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("kirish kodi")
        verbose_name_plural = _("kirish kodlari")

    def __str__(self):
        return f"{self.user} · {self.created_at:%Y-%m-%d %H:%M}"

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(seconds=settings.LOGIN_CODE_TTL_SECONDS)
        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        return (
            not self.is_used
            and timezone.now() < self.expires_at
            and self.attempts < settings.LOGIN_CODE_MAX_ATTEMPTS
        )

    @classmethod
    def issue(cls, user, request=None):
        """Eski kodlarni bekor qilib, yangi takrorlanmas kod beradi."""
        cls.objects.filter(user=user, is_used=False).update(is_used=True)
        now = timezone.now()
        for _attempt in range(10):
            code = _generate_code()
            if not cls.objects.filter(code=code, is_used=False, expires_at__gt=now).exists():
                return cls.objects.create(user=user, request=request, code=code)
        raise RuntimeError("Could not allocate a unique login code")

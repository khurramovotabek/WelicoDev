from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_ckeditor_5.fields import CKEditor5Field

from apps.core.models import TimeStampedModel


class BotSettings(models.Model):
    """@welicodevbot sozlamalari (singleton). Dashboard'dan boshqariladi."""

    is_enabled = models.BooleanField(_("bot yoqilgan"), default=True)
    maintenance_text = models.TextField(_("texnik ishlar matni"), blank=True, default="Bot vaqtincha texnik ishlar sababli to'xtatilgan.")
    welcome_text = models.TextField(
        _("salomlashish matni"),
        default="Assalomu alaykum! WeliCoDev rasmiy botiga xush kelibsiz.\nBu yerda saytga kirish kodini olasiz, kurslar va yangiliklardan xabardor bo'lasiz.",
    )
    registered_text = models.TextField(_("ro'yxatdan o'tgandan keyingi matn"), default="Ro'yxatdan o'tdingiz! Endi saytga kirishingiz mumkin.")
    help_text = models.TextField(
        _("yordam matni"),
        default="/login — saytga kirish kodi\n/profile — profilim\n/courses — kurslar\n/help — yordam",
    )
    mini_app_button_text = models.CharField(_("Mini App tugmasi"), max_length=40, default="WeliCoDev")

    notify_new_user = models.BooleanField(_("yangi foydalanuvchi haqida xabar"), default=True)
    notify_new_comment = models.BooleanField(_("yangi izoh haqida xabar"), default=True)
    notify_new_review = models.BooleanField(_("yangi sharh haqida xabar"), default=True)
    notify_contact_message = models.BooleanField(_("contact xabari haqida xabar"), default=True)
    notify_homework = models.BooleanField(_("uyga vazifa haqida xabar"), default=True)

    channel_id = models.CharField(_("kanal ID / @username"), max_length=64, blank=True, help_text=_("Yangi maqola va darslar shu kanalga e'lon qilinadi"))
    auto_post_articles = models.BooleanField(_("maqolalarni kanalga avtomatik joylash"), default=False)
    auto_post_lessons = models.BooleanField(_("darslarni kanalga avtomatik joylash"), default=False)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("bot sozlamalari")
        verbose_name_plural = _("bot sozlamalari")

    def __str__(self):
        return str(_("Bot sozlamalari"))

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
        from django.core.cache import cache

        cache.delete("channel_url")

    @classmethod
    def load(cls):
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj


class Broadcast(TimeStampedModel):
    class Audience(models.TextChoices):
        ALL = "all", _("Barcha foydalanuvchilar")
        REGISTERED = "registered", _("Ro'yxatdan o'tganlar")
        STUDENTS = "students", _("Kursga yozilganlar")
        COURSE = "course", _("Ma'lum kurs o'quvchilari")
        STAFF = "staff", _("Faqat adminlar (test)")

    class Status(models.TextChoices):
        DRAFT = "draft", _("Qoralama")
        SCHEDULED = "scheduled", _("Rejalashtirilgan")
        SENDING = "sending", _("Yuborilmoqda")
        DONE = "done", _("Yuborildi")
        FAILED = "failed", _("Xato")

    title = models.CharField(_("ichki nomi"), max_length=120)
    text = CKEditor5Field(_("matn"), config_name="telegram")
    image = models.ImageField(_("rasm"), upload_to="broadcasts/", blank=True)
    button_text = models.CharField(_("tugma matni"), max_length=40, blank=True)
    button_url = models.URLField(_("tugma havolasi"), blank=True)
    audience = models.CharField(_("auditoriya"), max_length=12, choices=Audience.choices, default=Audience.ALL)
    course = models.ForeignKey("education.Course", verbose_name=_("kurs"), null=True, blank=True, on_delete=models.SET_NULL)
    scheduled_at = models.DateTimeField(_("yuborish vaqti"), null=True, blank=True)
    status = models.CharField(_("holati"), max_length=10, choices=Status.choices, default=Status.DRAFT)
    total = models.PositiveIntegerField(_("jami"), default=0)
    sent = models.PositiveIntegerField(_("yuborildi"), default=0)
    failed = models.PositiveIntegerField(_("xato"), default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("ommaviy xabar")
        verbose_name_plural = _("ommaviy xabarlar")

    def __str__(self):
        return self.title


class BotMessage(models.Model):
    """Bot bilan yozishmalar: foydalanuvchi yozgan erkin xabarlar va admin javoblari."""

    class Direction(models.TextChoices):
        IN = "in", _("Kiruvchi")
        OUT = "out", _("Chiquvchi")

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bot_messages")
    direction = models.CharField(max_length=3, choices=Direction.choices)
    text = models.TextField(_("matn"))
    telegram_message_id = models.BigIntegerField(null=True, blank=True)
    is_read = models.BooleanField(_("o'qilgan"), default=False)
    sent_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("bot xabari")
        verbose_name_plural = _("bot xabarlari")

    def __str__(self):
        return f"{self.get_direction_display()} · {self.user}"


class BotEvent(models.Model):
    """Bot statistikasi uchun hodisalar jurnali (start, login, register, command)."""

    class Kind(models.TextChoices):
        START = "start", "start"
        REGISTER = "register", _("ro'yxatdan o'tish")
        LOGIN_CODE = "login_code", _("kirish kodi")
        LOGIN_CONFIRM = "login_confirm", _("kirishni tasdiqlash")
        COMMAND = "command", _("buyruq")
        MINI_APP = "mini_app", "Mini App"
        BLOCKED = "blocked", _("botni bloklash")

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="bot_events")
    kind = models.CharField(max_length=15, choices=Kind.choices)
    payload = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("bot hodisasi")
        verbose_name_plural = _("bot hodisalari")


class ChannelPost(TimeStampedModel):
    """Telegram kanal posti: rich text (CKEditor) -> Telegram HTML. Yuborilgandan keyin tahrirlansa, kanaldagi post ham yangilanadi."""

    class Status(models.TextChoices):
        DRAFT = "draft", _("Qoralama")
        SCHEDULED = "scheduled", _("Rejalashtirilgan")
        SENT = "sent", _("Joylandi")
        FAILED = "failed", _("Xato")

    class Kind(models.TextChoices):
        MANUAL = "manual", _("Qo'lda yozilgan")
        ARTICLE = "article", _("Maqola")
        LESSON = "lesson", _("Dars")
        COURSE = "course", _("Kurs")
        PROJECT = "project", _("Loyiha")

    kind = models.CharField(_("turi"), max_length=10, choices=Kind.choices, default=Kind.MANUAL)
    title = models.CharField(_("ichki nomi"), max_length=150)
    body = CKEditor5Field(_("post matni"), config_name="telegram")
    image = models.ImageField(_("rasm"), upload_to="channel/", blank=True)
    button_text = models.CharField(_("tugma matni"), max_length=40, blank=True)
    button_url = models.URLField(_("tugma havolasi"), blank=True)
    disable_preview = models.BooleanField(_("havola previewsiz"), default=True)
    silent = models.BooleanField(_("ovozsiz yuborish"), default=False)
    pin = models.BooleanField(_("kanalda qadash"), default=False)
    scheduled_at = models.DateTimeField(_("yuborish vaqti"), null=True, blank=True)
    status = models.CharField(_("holati"), max_length=10, choices=Status.choices, default=Status.DRAFT)
    message_id = models.BigIntegerField(null=True, blank=True, editable=False)
    sent_at = models.DateTimeField(_("joylangan"), null=True, blank=True)
    error = models.CharField(_("xato"), max_length=300, blank=True)
    object_id = models.PositiveBigIntegerField(null=True, blank=True, editable=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("kanal posti")
        verbose_name_plural = _("kanal postlari")

    def __str__(self):
        return self.title

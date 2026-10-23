from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import Tag, TimeStampedModel, unique_slugify


class MediaCategory(models.Model):
    class Kind(models.TextChoices):
        PHOTO = "photo", _("Foto")
        VIDEO = "video", _("Video")
        MUSIC = "music", _("Musiqa")

    kind = models.CharField(_("turi"), max_length=10, choices=Kind.choices)
    name = models.CharField(_("nomi"), max_length=40)
    slug = models.SlugField(_("slug"), max_length=50, blank=True)
    order = models.PositiveSmallIntegerField(_("tartib"), default=0)

    class Meta:
        ordering = ["kind", "order", "id"]
        unique_together = [("kind", "slug")]
        verbose_name = _("media turkumi")
        verbose_name_plural = _("media turkumlari")

    def __str__(self):
        return f"{self.get_kind_display()} · {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.name_en or self.name)
        super().save(*args, **kwargs)


class Album(TimeStampedModel):
    """Bir joy yoki voqeaga oid rasmlar to'plami ("Mountains · Kyrgyzstan, 2026")."""

    title = models.CharField(_("nomi"), max_length=100)
    slug = models.SlugField(_("slug"), max_length=120, unique=True, blank=True)
    location = models.CharField(_("joy"), max_length=100, blank=True)
    cover = models.ImageField(_("muqova"), upload_to="gallery/albums/", blank=True)
    is_published = models.BooleanField(_("ko'rinadi"), default=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("albom")
        verbose_name_plural = _("albomlar")

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.title_en or self.title)
        super().save(*args, **kwargs)


class Photo(TimeStampedModel):
    title = models.CharField(_("nomi"), max_length=120)
    slug = models.SlugField(_("slug"), max_length=140, unique=True, blank=True)
    description = models.TextField(_("tavsif"), blank=True)
    image = models.ImageField(_("rasm"), upload_to="gallery/photos/")
    album = models.ForeignKey(Album, verbose_name=_("albom"), on_delete=models.SET_NULL, null=True, blank=True, related_name="photos")
    category = models.ForeignKey(MediaCategory, verbose_name=_("turkum"), on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={"kind": "photo"}, related_name="photos")
    tags = models.ManyToManyField(Tag, verbose_name=_("teglar"), blank=True, related_name="photos")

    location = models.CharField(_("joy"), max_length=100, blank=True)
    map_url = models.URLField(_("xarita havolasi"), blank=True)
    taken_at = models.DateTimeField(_("olingan vaqt"), default=timezone.now)
    camera = models.CharField(_("kamera"), max_length=60, blank=True)
    lens = models.CharField(_("obyektiv"), max_length=60, blank=True)
    exposure = models.CharField(_("sozlamalar"), max_length=60, blank=True, help_text="f/2.8 • 1/50s • ISO 800")
    allow_download = models.BooleanField(_("yuklab olishga ruxsat"), default=True)
    allow_comments = models.BooleanField(_("izohlarga ruxsat"), default=True)
    is_featured = models.BooleanField(_("tanlangan"), default=False)
    is_published = models.BooleanField(_("ko'rinadi"), default=True)
    views_count = models.PositiveIntegerField(default=0, editable=False)
    downloads_count = models.PositiveIntegerField(default=0, editable=False)

    class Meta:
        ordering = ["-taken_at"]
        verbose_name = _("foto")
        verbose_name_plural = _("fotolar")

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.title_en or self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("gallery:photo_detail", args=[self.slug])


class Video(TimeStampedModel):
    title = models.CharField(_("nomi"), max_length=120)
    slug = models.SlugField(_("slug"), max_length=140, unique=True, blank=True)
    description = models.TextField(_("tavsif"), blank=True)
    file = models.FileField(_("video fayl"), upload_to="gallery/videos/", blank=True)
    youtube_url = models.URLField(_("YouTube havolasi"), blank=True)
    thumbnail = models.ImageField(_("muqova"), upload_to="gallery/thumbs/")
    duration = models.CharField(_("davomiyligi"), max_length=10, blank=True, help_text="12:34")
    category = models.ForeignKey(MediaCategory, verbose_name=_("turkum"), on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={"kind": "video"}, related_name="videos")
    tags = models.ManyToManyField(Tag, verbose_name=_("teglar"), blank=True, related_name="videos")
    recorded_at = models.DateField(_("sana"), default=timezone.now)
    allow_comments = models.BooleanField(_("izohlarga ruxsat"), default=True)
    is_published = models.BooleanField(_("ko'rinadi"), default=True)
    views_count = models.PositiveIntegerField(default=0, editable=False)

    class Meta:
        ordering = ["-recorded_at"]
        verbose_name = _("video")
        verbose_name_plural = _("videolar")

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.title_en or self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("gallery:video_detail", args=[self.slug])

    @property
    def youtube_id(self):
        import re

        m = re.search(r"(?:v=|youtu\.be/|embed/|shorts/)([\w-]{11})", self.youtube_url or "")
        return m.group(1) if m else ""


class Track(TimeStampedModel):
    title = models.CharField(_("nomi"), max_length=120)
    artist = models.CharField(_("ijrochi"), max_length=120)
    audio = models.FileField(_("audio fayl"), upload_to="gallery/music/", blank=True,
                             help_text=_("MP3/M4A/OGG. Fayl bo'lmasa, tashqi havola ishlatiladi"))
    external_url = models.URLField(_("tashqi havola"), blank=True, help_text=_("Spotify, YouTube Music, Apple Music yoki SoundCloud"))
    note = models.CharField(_("nega yoqadi"), max_length=200, blank=True)
    album = models.CharField(_("albom"), max_length=120, blank=True)
    year = models.PositiveSmallIntegerField(_("yil"), null=True, blank=True)
    cover = models.ImageField(_("muqova"), upload_to="gallery/music/covers/", blank=True)
    duration = models.CharField(_("davomiyligi"), max_length=10, blank=True)
    category = models.ForeignKey(MediaCategory, verbose_name=_("turkum"), on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={"kind": "music"}, related_name="tracks")
    is_favorite = models.BooleanField(_("sevimli"), default=False)
    is_published = models.BooleanField(_("ko'rinadi"), default=True)
    order = models.PositiveSmallIntegerField(_("tartib"), default=0)

    class Meta:
        ordering = ["order", "-created_at"]
        verbose_name = _("trek")
        verbose_name_plural = _("treklar")

    def __str__(self):
        return f"{self.title} — {self.artist}"

    @property
    def platform(self):
        url = self.external_url or ""
        for key, name in (("spotify", "Spotify"), ("music.youtube", "YouTube Music"), ("youtu", "YouTube"),
                          ("apple", "Apple Music"), ("soundcloud", "SoundCloud"), ("yandex", "Yandex Music")):
            if key in url:
                return name
        return ""

    @property
    def youtube_id(self):
        """YouTube havolasidan video ID (watch?v=, youtu.be/, music.youtube, shorts) — saytda embed orqali ijro uchun."""
        import re

        m = re.search(r"(?:youtube\.com/(?:watch\?(?:.*&)?v=|shorts/|embed/)|youtu\.be/)([\w-]{11})", self.external_url or "")
        return m.group(1) if m else ""

    @property
    def is_playable(self):
        return bool(self.audio or self.youtube_id)


class Playlist(TimeStampedModel):
    title = models.CharField(_("nomi"), max_length=80)
    cover = models.ImageField(_("muqova"), upload_to="gallery/playlists/", blank=True)
    tracks = models.ManyToManyField(Track, verbose_name=_("treklar"), blank=True, related_name="playlists")
    order = models.PositiveSmallIntegerField(_("tartib"), default=0)
    is_published = models.BooleanField(_("ko'rinadi"), default=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = _("pleylist")
        verbose_name_plural = _("pleylistlar")

    def __str__(self):
        return self.title

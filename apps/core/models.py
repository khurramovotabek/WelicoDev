from django.core.cache import cache
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(_("yaratilgan"), auto_now_add=True)
    updated_at = models.DateTimeField(_("yangilangan"), auto_now=True)

    class Meta:
        abstract = True


class SeoModel(models.Model):
    meta_title = models.CharField(_("meta title"), max_length=70, blank=True)
    meta_description = models.CharField(_("meta description"), max_length=170, blank=True)

    class Meta:
        abstract = True


class PublishStatus(models.TextChoices):
    DRAFT = "draft", _("Qoralama")
    PUBLISHED = "published", _("Nashr qilingan")
    ARCHIVED = "archived", _("Arxiv")


class PublishedQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status=PublishStatus.PUBLISHED)


# O'zbek (lotin va kirill) va rus harflarini SEO uchun qulay lotin slug'ga o'girish
_TRANSLIT = {
    "o'": "o", "g'": "g", "oʻ": "o", "gʻ": "g", "o‘": "o", "g‘": "g", "o’": "o", "g’": "g", "ʼ": "", "'": "", "’": "",
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "j", "з": "z", "и": "i", "й": "y",
    "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f",
    "х": "x", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sh", "ъ": "", "ы": "i", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    "ў": "o", "қ": "q", "ғ": "g", "ҳ": "h",
}


def translit(value):
    text = (value or "").lower()
    for src, dst in sorted(_TRANSLIT.items(), key=lambda kv: -len(kv[0])):
        text = text.replace(src, dst)
    return text


def unique_slugify(instance, value, field="slug"):
    """Model uchun takrorlanmas slug yaratadi (lotin harflarida, o'zbekcha va kirill matnlar transliteratsiya qilinadi)."""
    base = (slugify(translit(value), allow_unicode=False) or "item")[:120].strip("-")
    slug, n = base, 2
    qs = type(instance)._default_manager.all()
    if instance.pk:
        qs = qs.exclude(pk=instance.pk)
    while qs.filter(**{field: slug}).exists():
        slug = f"{base}-{n}"
        n += 1
    return slug


class Tag(models.Model):
    name = models.CharField(_("nomi"), max_length=50, unique=True)
    slug = models.SlugField(_("slug"), max_length=60, unique=True, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _("teg")
        verbose_name_plural = _("teglar")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.name)
        super().save(*args, **kwargs)


BG_PRESETS = [
    ("dawn", _("Bulutlar ustida tong")),
    ("dusk", _("Tog'lar va shahar chiroqlari")),
    ("night", _("Yulduzli tun")),
    ("galaxy", _("Somon yo'li va qorli cho'qqilar")),
    ("cosmos", _("Bulutlar ustidagi koinot")),
    ("aurora", _("Shimoliy yog'du")),
    ("peaks", _("Moviy soatdagi tog'lar")),
    ("metropolis", _("Tungi megapolis")),
    ("workspace", _("Dasturchi ish stoli")),
    ("scene", _("Animatsion tog'lar")),
]


class SiteSettings(models.Model):
    """Saytning yagona sozlamalari (singleton). Dashboard orqali tahrirlanadi."""

    CACHE_KEY = "site_settings"

    brand_name = models.CharField(_("brend nomi"), max_length=60, default="WeliCoDev")
    brand_tagline = models.CharField(_("brend shiori"), max_length=120, default="Build • Learn • Create • Live")
    logo = models.ImageField(_("logo"), upload_to="site/", blank=True)
    favicon = models.ImageField(_("favicon"), upload_to="site/", blank=True)

    owner_name = models.CharField(_("ism familiya"), max_length=100, default="Otabek")
    owner_role = models.CharField(_("lavozim"), max_length=100, default="Python Backend Engineer")
    owner_bio = models.TextField(_("qisqa bio"), blank=True)
    avatar = models.ImageField(_("avatar"), upload_to="site/", blank=True)
    portrait = models.ImageField(
        _("shaxsiy rasm (hero)"), upload_to="site/", blank=True,
        help_text=_("Bosh sahifadagi katta rasm. Vertikal (3:4) va kamida 1200px bo'lsa yaxshi ko'rinadi."),
    )
    cv_file = models.FileField(_("CV fayli"), upload_to="site/cv/", blank=True)

    hero_badges = models.CharField(
        _("hero teglar"), max_length=200, default="Developer, Human, Explorer",
        help_text=_("Vergul bilan ajrating"),
    )
    intro_video_url = models.URLField(_("intro video havolasi"), blank=True)
    intro_video_duration = models.CharField(_("intro video davomiyligi"), max_length=10, blank=True)
    available_for_work = models.BooleanField(_("ishga ochiq"), default=True)

    years_experience = models.PositiveSmallIntegerField(_("tajriba (yil)"), default=3)
    people_impacted = models.CharField(_("ta'sir qilingan odamlar"), max_length=20, blank=True, default="",
                                       help_text=_("Faqat haqiqiy raqam (masalan, mahsulotlaringiz foydalanuvchilari). Bo'sh — ko'rsatilmaydi"))

    email = models.EmailField(_("email"), blank=True)
    phone = models.CharField(_("telefon"), max_length=30, blank=True)
    location = models.CharField(_("manzil"), max_length=120, default="Tashkent, Uzbekistan")
    map_url = models.URLField(_("xarita havolasi"), blank=True)
    latitude = models.DecimalField(_("kenglik (lat)"), max_digits=9, decimal_places=6, default=41.311081,
                                   help_text=_("Google Maps'da joyni o'ng tugma bilan bosing va birinchi raqamni oling"))
    longitude = models.DecimalField(_("uzunlik (lng)"), max_digits=9, decimal_places=6, default=69.240562)
    map_zoom = models.PositiveSmallIntegerField(_("xarita yaqinligi"), default=12, help_text="3–18")
    timezone_name = models.CharField(_("vaqt zonasi (IANA)"), max_length=40, default="Asia/Tashkent",
                                     help_text=_("Mahalliy vaqtni ko'rsatish uchun: Asia/Tashkent"))
    working_hours = models.CharField(_("ish vaqti"), max_length=60, default="Mon - Fri, 9:00 - 18:00")
    timezone_label = models.CharField(_("vaqt mintaqasi"), max_length=20, default="UTC +5")
    response_time = models.CharField(_("javob berish vaqti"), max_length=30, default="24 hours")

    # Fon (butun sayt). Sahifa uchun alohida fon PageHero orqali beriladi.
    background_preset = models.CharField(_("fon"), max_length=10, choices=BG_PRESETS, default="dawn")
    background_image = models.ImageField(
        _("o'z fon rasmingiz"), upload_to="site/backgrounds/", blank=True,
        help_text=_("Yuklansa, tanlangan tayyor fondan ustun turadi. Kamida 2560px kenglik tavsiya etiladi; sifati o'zgartirilmaydi."),
    )
    background_dim = models.PositiveSmallIntegerField(_("fon qoraytirish %"), default=35, help_text=_("Matn o'qilishi uchun: 0–80"))
    background_blur = models.PositiveSmallIntegerField(_("fon xiralashtirish (px)"), default=0, help_text="0–24")
    background_motion = models.BooleanField(_("fonda yengil harakat"), default=True)

    # Pullik kurslar: to'lov Telegram orqali kelishiladi
    payment_telegram = models.CharField(
        _("to'lov uchun Telegram"), max_length=64, blank=True,
        help_text=_("Kurs sotib olmoqchi bo'lganlar yozadigan Telegram username (@siz). Bo'sh bo'lsa bot ishlatiladi."),
    )
    payment_note = models.TextField(_("to'lov bo'yicha izoh"), blank=True,
                                    help_text=_("Sotib olish sahifasida ko'rinadi: to'lov usullari, muddatlar va h.k."))

    meta_description = models.CharField(_("meta description"), max_length=170, blank=True)
    og_image = models.ImageField(_("OG rasm"), upload_to="site/", blank=True)
    footer_text = models.CharField(_("footer matni"), max_length=160, blank=True)

    # Qidiruv tizimlari va statistika (dashboard → Sozlamalar → SEO)
    google_verification = models.CharField(_("Google Search Console kodi"), max_length=120, blank=True,
                                           help_text=_("google-site-verification meta tegidagi content qiymati"))
    yandex_verification = models.CharField(_("Yandex Webmaster kodi"), max_length=120, blank=True)
    bing_verification = models.CharField(_("Bing Webmaster kodi"), max_length=120, blank=True)
    indexnow_key = models.CharField(_("IndexNow kaliti"), max_length=64, blank=True,
                                    help_text=_("Yangi sahifalar Yandex va Bing'ga darhol yuboriladi"))
    umami_script_url = models.URLField(_("Umami skript manzili"), blank=True, help_text="https://stats.welicodev.uz/script.js")
    umami_website_id = models.CharField(_("Umami website ID"), max_length=64, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("sayt sozlamalari")
        verbose_name_plural = _("sayt sozlamalari")

    def __str__(self):
        return str(_("Sayt sozlamalari"))

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
        cache.delete(self.CACHE_KEY)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def background_url(self):
        """Fon rasmi manzili (animatsion fon uchun bo'sh)."""
        from django.templatetags.static import static

        if self.background_image:
            return self.background_image.url
        if self.background_preset == "scene":
            return ""
        return static(f"img/bg/{self.background_preset}.webp")

    @property
    def background_url_sm(self):
        from django.templatetags.static import static

        if self.background_image or self.background_preset == "scene":
            return self.background_url
        return static(f"img/bg/{self.background_preset}-sm.webp")

    @property
    def payment_link(self):
        from django.conf import settings

        username = (self.payment_telegram or settings.TELEGRAM_BOT_USERNAME).lstrip("@").strip()
        return f"https://t.me/{username}"

    @property
    def badges(self):
        return [b.strip() for b in self.hero_badges.split(",") if b.strip()]


class SocialLink(models.Model):
    class Platform(models.TextChoices):
        GITHUB = "github", "GitHub"
        GITLAB = "gitlab", "GitLab"
        LINKEDIN = "linkedin", "LinkedIn"
        TELEGRAM = "telegram", "Telegram"
        INSTAGRAM = "instagram", "Instagram"
        YOUTUBE = "youtube", "YouTube"
        X = "x", "X (Twitter)"
        FACEBOOK = "facebook", "Facebook"
        TIKTOK = "tiktok", "TikTok"
        WHATSAPP = "whatsapp", "WhatsApp"
        DRIBBBLE = "dribbble", "Dribbble"
        BEHANCE = "behance", "Behance"
        MEDIUM = "medium", "Medium"
        DEVTO = "devto", "dev.to"
        LEETCODE = "leetcode", "LeetCode"
        STACKOVERFLOW = "stackoverflow", "Stack Overflow"
        EMAIL = "email", "Email"
        WEBSITE = "website", _("Veb-sayt")

    platform = models.CharField(_("platforma"), max_length=20, choices=Platform.choices)
    label = models.CharField(_("nomi"), max_length=60, blank=True, help_text=_("Bo'sh qolsa platforma nomi olinadi"))
    username = models.CharField(_("username"), max_length=80, blank=True)
    url = models.CharField(_("havola"), max_length=300, help_text=_("https://... yoki mailto:..."))
    order = models.PositiveSmallIntegerField(_("tartib"), default=0)
    is_active = models.BooleanField(_("faol"), default=True)
    show_in_header = models.BooleanField(_("hero/headerda"), default=False)
    show_in_footer = models.BooleanField(_("footerda"), default=True)
    show_in_contact = models.BooleanField(_("contact sahifasida"), default=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = _("ijtimoiy tarmoq")
        verbose_name_plural = _("ijtimoiy tarmoqlar")

    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        return self.label or self.get_platform_display()


class CurrentStatus(models.Model):
    """Home va About sahifalaridagi "Currently" bloki."""

    class Color(models.TextChoices):
        GREEN = "green", _("Yashil")
        BLUE = "blue", _("Ko'k")
        PURPLE = "purple", _("Binafsha")
        ORANGE = "orange", _("To'q sariq")
        GRAY = "gray", _("Kulrang")

    label = models.CharField(_("sarlavha"), max_length=40)
    value = models.CharField(_("qiymat"), max_length=80)
    color = models.CharField(_("rang"), max_length=10, choices=Color.choices, default=Color.BLUE)
    order = models.PositiveSmallIntegerField(_("tartib"), default=0)
    is_active = models.BooleanField(_("faol"), default=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = _("hozirgi holat")
        verbose_name_plural = _("hozirgi holatlar")

    def __str__(self):
        return f"{self.label}: {self.value}"


class Role(models.Model):
    """Bosh sahifadagi rollar: Developer, StartUp CEO, Sales Manager, Creator."""

    class Color(models.TextChoices):
        BLUE = "blue", _("Ko'k")
        VIOLET = "violet", _("Binafsha")
        GREEN = "green", _("Yashil")
        ORANGE = "orange", _("To'q sariq")

    title = models.CharField(_("nomi"), max_length=40)
    subtitle = models.CharField(_("qisqa izoh"), max_length=80, blank=True, help_text=_("Masalan: NutriZone asoschisi"))
    description = models.CharField(_("tavsif"), max_length=200, blank=True)
    icon = models.CharField(_("belgi"), max_length=40, default="sparkles", help_text=_("Lucide belgi nomi: code-xml, rocket, trending-up, clapperboard"))
    color = models.CharField(_("rang"), max_length=10, choices=Color.choices, default=Color.BLUE)
    link = models.CharField(_("havola"), max_length=200, blank=True, help_text=_("/uz/projects/ yoki https://..."))
    order = models.PositiveSmallIntegerField(_("tartib"), default=0)
    is_active = models.BooleanField(_("faol"), default=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = _("rol")
        verbose_name_plural = _("rollar")

    def __str__(self):
        return self.title


class PageHero(models.Model):
    """Har bir sahifaning yuqori qismi: sarlavha, matn, iqtibos va fon rasmi."""

    class Page(models.TextChoices):
        HOME = "home", "Home"
        ABOUT = "about", "About"
        SKILLS = "skills", "Skills"
        EXPERIENCE = "experience", "Experience"
        PROJECTS = "projects", "Projects"
        JOURNAL = "journal", "Blog"
        MEDIA = "media", "Media"
        EDUCATION = "education", "Education"
        CONTACT = "contact", "Contact"
        SHARE = "share", "Share"
        NOT_FOUND = "404", "404"

    page = models.CharField(_("sahifa"), max_length=20, choices=Page.choices, unique=True)
    eyebrow = models.CharField(_("kichik yozuv"), max_length=60, blank=True)
    title = models.CharField(_("sarlavha"), max_length=120)
    subtitle = models.CharField(_("qo'shimcha sarlavha"), max_length=200, blank=True)
    description = models.TextField(_("tavsif"), blank=True)
    quote = models.CharField(_("iqtibos"), max_length=160, blank=True)
    background = models.ImageField(_("fon rasmi"), upload_to="heroes/", blank=True)

    class Meta:
        ordering = ["page"]
        verbose_name = _("sahifa sarlavhasi")
        verbose_name_plural = _("sahifa sarlavhalari")

    def __str__(self):
        return self.get_page_display()


class Faq(models.Model):
    question = models.CharField(_("savol"), max_length=200)
    answer = models.TextField(_("javob"))
    order = models.PositiveSmallIntegerField(_("tartib"), default=0)
    is_active = models.BooleanField(_("faol"), default=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = _("FAQ")
        verbose_name_plural = _("FAQ")

    def __str__(self):
        return self.question

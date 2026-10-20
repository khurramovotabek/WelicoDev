from pathlib import Path

import environ
from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    TELEGRAM_ADMIN_IDS=(list, []),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")
SITE_URL = env("SITE_URL", default="http://localhost:8000").rstrip("/")

INSTALLED_APPS = [
    # Admin mavzusi django.contrib.admin'dan oldin turishi shart
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.inlines",
    "modeltranslation",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "django.contrib.humanize",
    "django_ckeditor_5",
    "django_htmx",
    # Loyiha ilovalari
    "apps.core",
    "apps.accounts",
    "apps.portfolio",
    "apps.blog",
    "apps.gallery",
    "apps.education",
    "apps.interactions",
    "apps.telegram_bot",
    "apps.dashboard",
    "apps.miniapp",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.miniapp.auth.TelegramWebAppMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "apps.interactions.analytics.VisitMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.site",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", default="welicodev"),
        "USER": env("POSTGRES_USER", default="welicodev"),
        "PASSWORD": env("POSTGRES_PASSWORD", default="welicodev"),
        "HOST": env("POSTGRES_HOST", default="localhost"),
        "PORT": env("POSTGRES_PORT", default="5433"),
        "CONN_MAX_AGE": 60,
    }
}

REDIS_URL = env("REDIS_URL", default="redis://localhost:6380/0")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        "KEY_PREFIX": "welicodev",
    }
}

AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend"]
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "core:home"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Tillar ---
LANGUAGE_CODE = "uz"
LANGUAGES = [
    ("uz", "O'zbekcha"),
    ("ru", "Русский"),
    ("en", "English"),
]
MODELTRANSLATION_DEFAULT_LANGUAGE = "uz"
MODELTRANSLATION_FALLBACK_LANGUAGES = ("uz", "en", "ru")
MODELTRANSLATION_CUSTOM_FIELDS = ("CKEditor5Field",)
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "Asia/Tashkent"
USE_I18N = True
USE_TZ = True

# --- Fayllar ---
STATIC_URL = "/static/"
WHITENOISE_MAX_AGE = 60 * 60 * 24 * 365  # prod: fayl nomida hash bor, shuning uchun 1 yil kesh xavfsiz
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
# Himoyalangan dars videolari: MEDIA_ROOT'dan tashqarida, faqat view orqali beriladi
PROTECTED_MEDIA_ROOT = BASE_DIR / "protected_media"

DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Celery ---
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_ALWAYS_EAGER = False
CELERY_BEAT_SCHEDULE = {
    "send-due-telegram-posts": {"task": "apps.telegram_bot.tasks.send_due", "schedule": 60.0},
}

# --- Telegram ---
TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN", default="")
TELEGRAM_BOT_USERNAME = env("TELEGRAM_BOT_USERNAME", default="welicodevbot")
TELEGRAM_ADMIN_IDS = [int(x) for x in env("TELEGRAM_ADMIN_IDS") if str(x).strip()]
LOGIN_CODE_TTL_SECONDS = 120
LOGIN_CODE_MAX_ATTEMPTS = 5

# Admin panel xavfsizligi: manzilni prod'da yashiring (masalan ADMIN_URL=wcd-control-7f3a/)
ADMIN_URL = env("ADMIN_URL", default="admin/").strip("/") + "/"
ADMIN_2FA = env.bool("ADMIN_2FA", default=not DEBUG)
ADMIN_LOGIN_MAX_ATTEMPTS = 5
ADMIN_LOGIN_LOCKOUT_SECONDS = 15 * 60

# --- CKEditor 5 ---
CKEDITOR_5_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
CKEDITOR_5_UPLOAD_FILE_TYPES = ["jpeg", "jpg", "png", "gif", "webp"]
CKEDITOR_5_ALLOW_ALL_FILE_TYPES = False
CKEDITOR_5_CONFIGS = {
    "default": {
        "toolbar": {
            "items": [
                "heading", "|", "bold", "italic", "underline", "strikethrough", "code", "link",
                "|", "bulletedList", "numberedList", "todoList", "|", "blockQuote", "codeBlock",
                "insertTable", "imageUpload", "mediaEmbed", "horizontalLine", "|",
                "fontColor", "highlight", "removeFormat", "|", "undo", "redo",
            ],
            "shouldNotGroupWhenFull": True,
        },
        "heading": {
            "options": [
                {"model": "paragraph", "title": "Paragraph", "class": "ck-heading_paragraph"},
                {"model": "heading2", "view": "h2", "title": "Heading 2", "class": "ck-heading_heading2"},
                {"model": "heading3", "view": "h3", "title": "Heading 3", "class": "ck-heading_heading3"},
                {"model": "heading4", "view": "h4", "title": "Heading 4", "class": "ck-heading_heading4"},
            ]
        },
        "codeBlock": {
            "languages": [
                {"language": "python", "label": "Python"},
                {"language": "bash", "label": "Bash"},
                {"language": "dockerfile", "label": "Dockerfile"},
                {"language": "yaml", "label": "YAML"},
                {"language": "javascript", "label": "JavaScript"},
                {"language": "typescript", "label": "TypeScript"},
                {"language": "html", "label": "HTML"},
                {"language": "css", "label": "CSS"},
                {"language": "sql", "label": "SQL"},
                {"language": "json", "label": "JSON"},
                {"language": "nginx", "label": "Nginx"},
                {"language": "plaintext", "label": "Text"},
            ]
        },
        "image": {
            "toolbar": ["imageTextAlternative", "|", "imageStyle:alignLeft", "imageStyle:alignCenter",
                        "imageStyle:alignRight", "|", "toggleImageCaption"],
        },
        "table": {"contentToolbar": ["tableColumn", "tableRow", "mergeTableCells"]},
        "mediaEmbed": {"previewsInData": True},
    },
}
# Telegram post uchun: faqat Telegram qo'llaydigan formatlash (qalin, kursiv, tagiga chizilgan, ustiga chizilgan,
# havola, kod, kod bloki, iqtibos, ro'yxat). Saqlanganda Telegram HTML'ga o'giriladi.
CKEDITOR_5_CONFIGS["telegram"] = {
    "toolbar": {
        "items": ["bold", "italic", "underline", "strikethrough", "|", "link", "code", "codeBlock", "blockQuote",
                  "|", "bulletedList", "numberedList", "|", "undo", "redo"],
        "shouldNotGroupWhenFull": True,
    },
    "codeBlock": CKEDITOR_5_CONFIGS["default"]["codeBlock"],
}
CKEDITOR_5_CUSTOM_CSS = "admin/ckeditor.css"

from .unfold import UNFOLD  # noqa: E402,F401

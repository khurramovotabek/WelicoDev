from .base import *  # noqa: F401,F403

DEBUG = True
INTERNAL_IPS = ["127.0.0.1"]
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Lokal muhitda Celery worker'siz ham vazifalar darhol bajariladi
CELERY_TASK_ALWAYS_EAGER = True
X_FRAME_OPTIONS = "SAMEORIGIN"  # app-preview telefon ramkasida sayt sahifalarini korsatish uchun

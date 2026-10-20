"""Admin panelga kirish xavfsizligi.

1. Parol bilan kirishda IP va login bo'yicha urinishlar cheklanadi (bloklash).
2. Parol to'g'ri bo'lsa ham, ikkinchi qadam: Telegram bot orqali yuborilgan 6 xonali kod (2FA).
   Telegram'i ulanmagan staff prod'da parol bilan kira olmaydi — faqat sayt orqali Telegram login.
3. Har bir staff kirishi haqida adminlarga Telegram'da xabar yuboriladi (IP, brauzer, vaqt).
Telegram orqali saytga kirgan staff admin panelga to'g'ridan-to'g'ri o'tadi (parol kerak emas).
"""

import hashlib
import hmac
import logging
import secrets
import time
from html import escape

from django.conf import settings
from django.contrib import admin
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth import login as auth_login
from django.contrib.auth.signals import user_logged_in
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.dispatch import receiver
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _

from apps.core.utils import client_ip

log = logging.getLogger(__name__)

SESSION_KEY = "admin_2fa"
CODE_TTL = 300


def _lock_keys(request, username=""):
    ip = client_ip(request) or "unknown"
    keys = [f"admin-login:ip:{ip}"]
    if username:
        keys.append(f"admin-login:user:{username.lower()}")
    return keys


def is_locked(request, username=""):
    limit = settings.ADMIN_LOGIN_MAX_ATTEMPTS
    return any(cache.get(k, 0) >= limit for k in _lock_keys(request, username))


def register_failure(request, username=""):
    for k in _lock_keys(request, username):
        cache.set(k, cache.get(k, 0) + 1, settings.ADMIN_LOGIN_LOCKOUT_SECONDS)


def clear_failures(request, username=""):
    cache.delete_many(_lock_keys(request, username))


def _hash(code, salt):
    return hmac.new(settings.SECRET_KEY.encode(), f"{salt}:{code}".encode(), hashlib.sha256).hexdigest()


def _safe_next(request):
    nxt = request.POST.get("next") or request.GET.get("next") or ""
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return nxt
    return reverse("admin:index")


class SecureAdminAuthenticationForm(AdminAuthenticationForm):
    """Bloklangan IP/login uchun parol umuman tekshirilmaydi."""

    def clean(self):
        username = self.cleaned_data.get("username", "")
        if is_locked(self.request, username):
            minutes = settings.ADMIN_LOGIN_LOCKOUT_SECONDS // 60
            raise ValidationError(
                _("Juda ko'p noto'g'ri urinish. %(m)s daqiqadan keyin qayta urinib ko'ring.") % {"m": minutes},
                code="locked",
            )
        try:
            return super().clean()
        except Exception:
            register_failure(self.request, username)
            raise


def _send_code(user, code, request):
    from apps.telegram_bot import api

    ua = escape(request.META.get("HTTP_USER_AGENT", "")[:90])
    text = (
        f"🔐 <b>Admin panelga kirish kodi</b>\n\n<code>{code}</code>\n\n"
        f"IP: <code>{escape(client_ip(request) or '-')}</code>\n{ua}\n\n"
        "Agar bu siz bo'lmasangiz — kodni hech kimga bermang va parolni almashtiring."
    )
    api.send_message(user.telegram_id, text)


def secure_admin_login(request, extra_context=None):
    """admin.site.login o'rniga: parol + Telegram kodi."""
    if request.user.is_authenticated and request.user.is_active and request.user.is_staff:
        return HttpResponseRedirect(_safe_next(request))

    pending = request.session.get(SESSION_KEY)
    if request.method == "POST" and request.POST.get("step") == "code" and pending:
        return _verify_code(request, pending)

    form = SecureAdminAuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        clear_failures(request, user.get_username())
        if not settings.ADMIN_2FA:
            auth_login(request, user)
            return HttpResponseRedirect(_safe_next(request))
        if not user.telegram_id or not settings.TELEGRAM_BOT_TOKEN:
            form.add_error(None, _("Bu hisob uchun Telegram ulanmagan. Saytga Telegram orqali kiring — admin panel o'zi ochiladi."))
        else:
            code = f"{secrets.randbelow(10**6):06d}"
            salt = secrets.token_hex(8)
            try:
                _send_code(user, code, request)
            except Exception as e:  # noqa: BLE001
                log.warning("admin 2fa send failed: %s", e)
                form.add_error(None, _("Telegram'ga kod yuborib bo'lmadi. Keyinroq urinib ko'ring."))
            else:
                request.session[SESSION_KEY] = {"uid": user.pk, "hash": _hash(code, salt), "salt": salt,
                                                "exp": time.time() + CODE_TTL, "tries": 0, "next": _safe_next(request)}
                return render(request, "accounts/admin_2fa.html", {"ttl": CODE_TTL})

    context = {
        **admin.site.each_context(request),
        "title": _("Kirish"),
        "app_path": request.get_full_path(),
        "form": form,
        "next": request.GET.get("next", ""),
        "telegram_login_url": f"{reverse('accounts:login')}?next={reverse('admin:index')}",
        **(extra_context or {}),
    }
    return render(request, "admin/login.html", context)


def _verify_code(request, pending):
    from apps.accounts.models import User

    code = "".join(ch for ch in request.POST.get("code", "") if ch.isdigit())
    error = None
    if time.time() > pending["exp"]:
        request.session.pop(SESSION_KEY, None)
        error = _("Kod muddati tugadi. Qaytadan kiring.")
    elif pending["tries"] >= 5 or is_locked(request):
        request.session.pop(SESSION_KEY, None)
        register_failure(request)
        error = _("Urinishlar soni tugadi. Qaytadan kiring.")
    elif not hmac.compare_digest(_hash(code, pending["salt"]), pending["hash"]):
        pending["tries"] += 1
        request.session[SESSION_KEY] = pending
        register_failure(request)
        return render(request, "accounts/admin_2fa.html", {"ttl": int(pending["exp"] - time.time()), "error": _("Kod noto'g'ri")})
    else:
        user = User.objects.filter(pk=pending["uid"], is_active=True, is_staff=True).first()
        request.session.pop(SESSION_KEY, None)
        if user:
            auth_login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            clear_failures(request)
            return HttpResponseRedirect(pending.get("next") or reverse("admin:index"))
        error = _("Hisob topilmadi")
    form = SecureAdminAuthenticationForm(request)
    form.add_error(None, error)
    return render(request, "admin/login.html", {**admin.site.each_context(request), "form": form, "title": _("Kirish"),
                                                "app_path": reverse("admin:login")})


@receiver(user_logged_in)
def notify_staff_login(sender, request, user, **kwargs):
    """Staff hisobiga har qanday kirish (parol yoki Telegram) haqida adminlarga xabar."""
    # force_login (testlar, skriptlar) haqiqiy so'rov emas: REMOTE_ADDR bo'lmaydi
    if not user.is_staff or not settings.TELEGRAM_BOT_TOKEN or request is None or not request.META.get("REMOTE_ADDR"):
        return
    from django.db import transaction

    from apps.telegram_bot.tasks import notify_admins

    ua = escape(request.META.get("HTTP_USER_AGENT", "")[:100])
    text = (f"🛡 <b>Staff kirishi</b>: {escape(user.display_name)}\n"
            f"IP: <code>{escape(client_ip(request) or '-')}</code>\n{ua}")
    transaction.on_commit(lambda: notify_admins.delay(text))

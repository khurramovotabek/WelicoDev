"""Yengil tashriflar statistikasi: Redis'da kunlik hisoblagich, dashboard ochilganda bazaga yoziladi."""

import hashlib
from datetime import date, timedelta

from django.core.cache import cache
from django.utils import timezone

from .models import PageVisit

SKIP_PREFIXES = ("/static/", "/media/", "/admin/", "/ckeditor5/", "/tg/", "/favicon")
TTL = 60 * 60 * 24 * 40


def _redis():
    try:
        from django_redis import get_redis_connection

        return get_redis_connection("default")
    except Exception:  # noqa: BLE001 - Redis bo'lmasa statistika shunchaki yozilmaydi
        return None


class VisitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            self._count(request, response)
        except Exception:  # noqa: BLE001 - statistika hech qachon sahifani buzmasligi kerak
            pass
        return response

    def _count(self, request, response):
        if request.method != "GET" or response.status_code != 200 or getattr(request, "htmx", False):
            return
        path = request.path
        if path.startswith(SKIP_PREFIXES) or "/dashboard/" in path:
            return
        if "text/html" not in response.get("Content-Type", ""):
            return
        ua = request.META.get("HTTP_USER_AGENT", "").lower()
        if not ua or any(b in ua for b in ("bot", "crawl", "spider", "preview")):
            return
        r = _redis()
        if r is None:
            return
        day = timezone.localdate().isoformat()
        ident = request.session.session_key or request.META.get("REMOTE_ADDR", "") + ua
        pipe = r.pipeline()
        pipe.incr(f"wcd:pv:{day}")
        pipe.expire(f"wcd:pv:{day}", TTL)
        pipe.pfadd(f"wcd:uv:{day}", hashlib.sha1(ident.encode()).hexdigest())
        pipe.expire(f"wcd:uv:{day}", TTL)
        pipe.execute()


def flush_to_db(days=35):
    """Redis'dagi hisoblagichlarni PageVisit jadvaliga ko'chiradi."""
    r = _redis()
    if r is None:
        return
    today = timezone.localdate()
    for i in range(days):
        d = today - timedelta(days=i)
        pv = r.get(f"wcd:pv:{d.isoformat()}")
        if pv is None:
            continue
        uv = r.pfcount(f"wcd:uv:{d.isoformat()}")
        PageVisit.objects.update_or_create(date=d, defaults={"views": int(pv), "unique_visitors": int(uv)})


def series(days=30):
    flush_to_db(days + 2)
    start = timezone.localdate() - timedelta(days=days - 1)
    rows = {v.date: v for v in PageVisit.objects.filter(date__gte=start)}
    return [(start + timedelta(days=i), rows.get(start + timedelta(days=i))) for i in range(days)]

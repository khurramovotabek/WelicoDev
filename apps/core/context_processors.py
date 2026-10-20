from django.conf import settings
from django.core.cache import cache

from .models import SiteSettings, SocialLink


def _asset_version():
    """Lokal muhitda fayl o'zgarishi bilan versiya o'zgaradi (brauzer keshi eski CSS bermasligi uchun)."""
    if not settings.DEBUG:
        return "1"
    css = settings.BASE_DIR / "static" / "dist" / "app.css"
    js = settings.BASE_DIR / "static" / "js" / "app.js"
    return str(int(max(p.stat().st_mtime for p in (css, js) if p.exists())))


def site(request):
    site_settings = cache.get(SiteSettings.CACHE_KEY)
    if site_settings is None:
        site_settings = SiteSettings.load()
        cache.set(SiteSettings.CACHE_KEY, site_settings, 60 * 10)
    socials = list(SocialLink.objects.filter(is_active=True))
    channel_url = cache.get("channel_url")
    if channel_url is None:
        from apps.telegram_bot.models import BotSettings

        cid = BotSettings.load().channel_id.strip()
        # Faqat ochiq kanal (@username) uchun havola; yopiq kanal ID'si (-100...) ochiq havola bermaydi
        channel_url = f"https://t.me/{cid.lstrip('@')}" if cid.startswith("@") else ""
        cache.set("channel_url", channel_url, 300)
    return {
        "site": site_settings,
        "socials": socials,
        "footer_socials": [s for s in socials if s.show_in_footer],
        "bot_username": settings.TELEGRAM_BOT_USERNAME,
        "SITE_URL": settings.SITE_URL,
        "ASSET_V": _asset_version(),
        "channel_url": channel_url,
    }

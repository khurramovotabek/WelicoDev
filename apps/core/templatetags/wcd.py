from urllib.parse import urlencode

from django import template
from django.conf import settings
from django.urls import translate_url
from django.utils import translation
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()

# Ijtimoiy tarmoqlar uchun Lucide belgilari; brend belgisi yo'qlari uchun o'zimizning SVG
SOCIAL_ICONS = {
    "github": "github",
    "gitlab": "gitlab",
    "linkedin": "linkedin",
    "instagram": "instagram",
    "youtube": "youtube",
    "facebook": "facebook",
    "dribbble": "dribbble",
    "email": "mail",
    "website": "globe",
    "medium": "book-open-text",
    "devto": "square-code",
    "leetcode": "code-xml",
    "stackoverflow": "layers",
    "behance": "palette",
}

# Lucide brend ikonlarini olib tashlagan: ular shu yerda (Lucide uslubidagi chiziqlar)
CUSTOM_SVGS = {
    "github": '<path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.4 5.4 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4"/><path d="M9 18c-4.51 2-5-2-7-2"/>',
    "linkedin": '<path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-4 0v7h-4v-7a6 6 0 0 1 6-6z"/><rect width="4" height="12" x="2" y="9"/><circle cx="4" cy="4" r="2"/>',
    "instagram": '<rect width="20" height="20" x="2" y="2" rx="5" ry="5"/><path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/><path d="M17.5 6.5h.01"/>',
    "youtube": '<path d="M2.5 17a24.1 24.1 0 0 1 0-10 2 2 0 0 1 1.4-1.4 49.6 49.6 0 0 1 16.2 0A2 2 0 0 1 21.5 7a24.1 24.1 0 0 1 0 10 2 2 0 0 1-1.4 1.4 49.6 49.6 0 0 1-16.2 0A2 2 0 0 1 2.5 17"/><path d="m10 15 5-3-5-3z"/>',
    "facebook": '<path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"/>',
    "telegram": '<path d="M21.5 4.5 2.9 11.7c-.9.4-.9 1.6.1 1.9l4.6 1.5 1.8 5.6c.2.7 1.1.9 1.6.4l2.6-2.5 4.7 3.5c.6.4 1.4.1 1.6-.6l3.2-15.3c.2-.9-.7-1.6-1.6-1.2Z"/><path d="m8 15 9.5-7.5"/>',
    "x": '<path d="M4 4l16 16"/><path d="M20 4 4 20"/>',
    "whatsapp": '<path d="M3 21l1.6-4.6A8.5 8.5 0 1 1 8 19.6Z"/><path d="M9 9.5c0 3 2.5 5.5 5.5 5.5l1-1.5-2-1-1 .8a4 4 0 0 1-1.8-1.8l.8-1-1-2Z"/>',
    "tiktok": '<path d="M14 3v11.5a3.5 3.5 0 1 1-3.5-3.5"/><path d="M14 3c.5 2.6 2.4 4.4 5 4.6"/>',
}


@register.simple_tag
def social_icon(platform, css="w-[18px] h-[18px]"):
    if platform in CUSTOM_SVGS:
        return format_html(
            '<svg class="{}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
            'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{}</svg>',
            css, mark_safe(CUSTOM_SVGS[platform]),
        )
    return format_html('<i data-lucide="{}" class="{}" aria-hidden="true"></i>', SOCIAL_ICONS.get(platform, "link"), css)


@register.simple_tag(takes_context=True)
def nav_active(context, *prefixes):
    """Joriy URL berilgan bo'lim ichida bo'lsa `is-active` qaytaradi."""
    request = context.get("request")
    if not request:
        return ""
    path = request.path
    # /uz/projects/... -> /projects/...
    parts = path.split("/", 2)
    tail = "/" + (parts[2] if len(parts) > 2 and parts[1] in dict(settings.LANGUAGES) else path.lstrip("/"))
    for p in prefixes:
        if (p == "/" and tail == "/") or (p != "/" and tail.startswith(p)):
            return "is-active"
    return ""


@register.simple_tag(takes_context=True)
def lang_url(context, lang):
    request = context["request"]
    url = translate_url(request.get_full_path(), lang)
    return url


@register.simple_tag(takes_context=True)
def query(context, **kwargs):
    """Joriy GET parametrlarini saqlab, berilganlarini almashtiradi: {% query page=2 %}"""
    params = context["request"].GET.copy()
    for k, v in kwargs.items():
        if v in (None, ""):
            params.pop(k, None)
        else:
            params[k] = v
    return "?" + urlencode(params, doseq=True) if params else "?"


@register.filter
def compact(value):
    """12400 -> 12.4K"""
    try:
        n = float(value)
    except (TypeError, ValueError):
        return value
    for unit, size in (("M", 1_000_000), ("K", 1_000)):
        if n >= size:
            s = f"{n / size:.1f}".rstrip("0").rstrip(".")
            return f"{s}{unit}"
    return f"{int(n)}"


@register.simple_tag(takes_context=True)
def site_link(context, link):
    """"/projects/" -> "/uz/projects/" (joriy til bilan); to'liq havolalar o'zgarmaydi."""
    lang = context.get("LANG") or translation.get_language() or settings.LANGUAGE_CODE
    codes = [c for c, _n in settings.LANGUAGES]
    if link.startswith("/") and link.split("/")[1:2] and link.split("/")[1] not in codes:
        return f"/{lang}{link}"
    return link


@register.filter
def bg_dim(value):
    """Foiz (0..80) -> CSS uchun 0..0.8."""
    try:
        return f"{max(0, min(80, int(value))) / 100:.2f}"
    except (TypeError, ValueError):
        return "0.35"


@register.filter
def money(value):
    """1290000 -> "1 290 000" (bo'shliq bilan, har bir tilda bir xil)."""
    try:
        return f"{int(value):,}".replace(",", "\u202f")
    except (TypeError, ValueError):
        return value


@register.filter
def seconds_hms(value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return ""
    h, rem = divmod(value, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


@register.filter
def initials(name):
    parts = str(name or "").split()
    return "".join(p[0] for p in parts[:2]).upper() or "?"


@register.filter
def split(value, sep=","):
    return [v.strip() for v in str(value or "").split(sep) if v.strip()]


@register.filter
def bf(form, name):
    """Formadan maydonni nomi bo'yicha olish: {{ form|bf:"title_uz" }}"""
    try:
        return form[name]
    except KeyError:
        return ""


@register.simple_tag(takes_context=True)
def lang_path(context, lang):
    """Joriy sahifaning boshqa tildagi manzili (query string'siz — canonical/hreflang uchun)."""
    return translate_url(context["request"].path, lang)


@register.filter
def jsonld(value):
    """Python dict -> <script type=application/ld+json> ichiga xavfsiz JSON."""
    import json

    from django.utils.safestring import mark_safe

    text = json.dumps(value, ensure_ascii=False, default=str)
    return mark_safe(text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026"))


@register.simple_tag(takes_context=True)
def site_jsonld(context):
    from apps.core import seo

    return format_html('<script type="application/ld+json">{}</script>', jsonld(seo.site_graph(context["site"], context["socials"])))


@register.simple_tag
def ld(data):
    return format_html('<script type="application/ld+json">{}</script>', jsonld(data))


@register.simple_tag
def crumbs(*pairs):
    """{% crumbs "Loyihalar" url1 project.title url2 %}"""
    from apps.core import seo

    items = list(zip(pairs[::2], pairs[1::2]))
    return format_html('<script type="application/ld+json">{}</script>', jsonld(seo.breadcrumbs(*items)))


@register.simple_tag
def thumb(image, width=640, quality=80):
    """{% thumb project.cover 640 as src %} -> WebP thumbnail URL."""
    from apps.core.thumbs import thumb_url

    return thumb_url(image, int(width), int(quality))


def track_payload(t):
    """Global pleyer uchun trek ma'lumoti: audio fayl yoki YouTube video ("yt:<id>" — embed orqali ijro)."""
    from apps.core.thumbs import thumb_url

    yt = "" if t.audio else t.youtube_id
    return {
        "id": t.pk, "src": t.audio.url if t.audio else f"yt:{yt}", "yt": yt, "url": t.external_url or "",
        "title": t.title, "artist": t.artist, "album": t.album or "",
        "note": t.note or "", "duration": t.duration or "", "cover": thumb_url(t.cover, 512) if t.cover else "",
    }


@register.simple_tag
def tracks_json(tracks, element_id):
    """{% tracks_json tracks "music-tracks" %} -> <script type="application/json" id="music-tracks">[...]</script>"""
    from django.utils.html import json_script

    return json_script([track_payload(t) for t in tracks if t.is_playable], element_id)


@register.filter
def role_titles_json(roles):
    """Alpine uchun rollar nomlari: ["Developer", "StartUp CEO", ...] (HTML atribut ichida xavfsiz)."""
    import json

    from django.utils.html import escape

    return mark_safe(escape(json.dumps([r.title for r in roles], ensure_ascii=False)))

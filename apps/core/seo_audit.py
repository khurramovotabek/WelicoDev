"""Maqola uchun SEO tekshiruvi: asosiy kalit so'z, uzunliklar, struktura (o'zbek tiliga moslangan)."""

import re

from django.utils.html import strip_tags
from django.utils.text import slugify
from django.utils.translation import gettext as _

from .models import translit


def _norm(text):
    return translit(strip_tags(text or "")).lower()


def audit_article(article, lang="uz"):
    get = lambda f: getattr(article, f"{f}_{lang}", "") or ""  # noqa: E731
    title, excerpt, content = get("title"), get("excerpt"), get("content")
    meta_title = get("meta_title") or title
    meta_desc = get("meta_description") or excerpt
    kw = (article.focus_keyword or "").strip()
    nkw = _norm(kw)
    text = strip_tags(content)
    words = len(text.split())
    first_par = _norm(re.split(r"</p>", content or "", maxsplit=1)[0])
    h2 = re.findall(r"<h2[^>]*>(.*?)</h2>", content or "", flags=re.S)
    imgs = re.findall(r"<img[^>]*>", content or "")
    imgs_no_alt = [i for i in imgs if not re.search(r'alt="[^"]+"', i)]
    links = re.findall(r'<a [^>]*href="([^"]+)"', content or "")
    internal = [lnk for lnk in links if lnk.startswith("/") or "welicodev.uz" in lnk]

    checks = []

    def add(ok, good, bad, weight=1):
        checks.append({"ok": ok, "text": good if ok else bad, "weight": weight})

    add(bool(kw), _("Asosiy kalit so'z tanlangan: “%(kw)s”") % {"kw": kw}, _("Asosiy kalit so'z kiritilmagan (masalan: docker darslari)"), 2)
    if kw:
        add(nkw in _norm(meta_title), _("Kalit so'z sarlavhada bor"), _("Kalit so'zni sarlavhaga qo'shing"), 2)
        add(nkw in _norm(meta_desc), _("Kalit so'z meta tavsifda bor"), _("Kalit so'zni meta tavsifga qo'shing"))
        add(nkw in first_par, _("Kalit so'z birinchi paragrafda bor"), _("Kalit so'zni birinchi paragrafda ishlating"))
        add(slugify(translit(kw)) in (article.slug or ""), _("Kalit so'z URL'da bor"), _("URL (slug) kalit so'zni o'z ichiga olsin"))
        add(any(nkw in _norm(h) for h in h2), _("Kalit so'z H2 sarlavhalardan birida bor"), _("Kalit so'zni kamida bitta H2 sarlavhaga qo'shing"))
    add(30 <= len(meta_title) <= 60, _("Sarlavha uzunligi yaxshi (%(n)s belgi)") % {"n": len(meta_title)},
        _("Sarlavha 30–60 belgi bo'lsin (hozir %(n)s)") % {"n": len(meta_title)}, 2)
    add(110 <= len(meta_desc) <= 160, _("Meta tavsif uzunligi yaxshi (%(n)s belgi)") % {"n": len(meta_desc)},
        _("Meta tavsif 110–160 belgi bo'lsin (hozir %(n)s)") % {"n": len(meta_desc)})
    add(words >= 600, _("Matn hajmi yetarli (%(n)s so'z)") % {"n": words},
        _("Matn kamida 600 so'z bo'lsin (hozir %(n)s). Uzun va foydali maqolalar yuqoriroq chiqadi") % {"n": words}, 2)
    add(len(h2) >= 2, _("Matn H2 sarlavhalar bilan bo'lingan"), _("Matnni kamida 2 ta H2 sarlavha bilan bo'ling"))
    add(not imgs_no_alt, _("Barcha rasmlarda alt matn bor"), _("%(n)s ta rasmga alt matn yozing") % {"n": len(imgs_no_alt)})
    add(bool(internal), _("Saytning boshqa sahifalariga havola bor"), _("Boshqa maqola yoki kursga ichki havola qo'shing"))
    add(bool(getattr(article, f"title_ru", "")) and bool(getattr(article, f"title_en", "")) and article.title_ru != article.title_uz,
        _("Rus va ingliz tarjimalari kiritilgan"), _("Rus/ingliz tarjimasini qo'shing — Yandex va xalqaro qidiruv uchun"))

    total = sum(c["weight"] for c in checks)
    score = round(sum(c["weight"] for c in checks if c["ok"]) * 100 / total) if total else 0
    return {"score": score, "checks": checks, "words": words}

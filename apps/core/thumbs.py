"""Rasm thumbnail'lari: kerakli kenglikda WebP (birinchi so'rovda yaratiladi va diskda keshlanadi).

Kartochka va ro'yxatlarda 1600px asl rasm o'rniga ~600px WebP: sahifa hajmi 5-10 barobar kamayadi.
"""

import hashlib
import logging
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from PIL import Image, ImageOps

log = logging.getLogger(__name__)
THUMB_DIR = "thumbs"


def thumb_url(fieldfile, width, quality=80):
    if not fieldfile:
        return ""
    name = getattr(fieldfile, "name", "") or ""
    if not name or name.lower().endswith((".svg", ".gif")):
        return fieldfile.url
    key = f"thumb:{name}:{width}"
    url = cache.get(key)
    if url:
        return url
    try:
        src = Path(fieldfile.path)
        digest = hashlib.md5(f"{name}:{src.stat().st_mtime}:{width}:{quality}".encode()).hexdigest()[:16]
        rel = f"{THUMB_DIR}/{width}/{digest}.webp"
        dst = Path(settings.MEDIA_ROOT) / rel
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            with Image.open(src) as im:
                im = ImageOps.exif_transpose(im)
                if im.width > width:
                    im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
                if im.mode not in ("RGB", "RGBA"):
                    im = im.convert("RGBA" if "A" in im.getbands() else "RGB")
                tmp = dst.with_suffix(".tmp")
                im.save(tmp, "WEBP", quality=quality, method=5)
                tmp.replace(dst)  # atomik: parallel so'rovlar yarim fayl ko'rmaydi
        url = settings.MEDIA_URL + rel
    except Exception as e:  # noqa: BLE001 - thumbnail bo'lmasa asl rasm ko'rsatiladi
        log.warning("thumb failed for %s: %s", name, e)
        return fieldfile.url
    cache.set(key, url, 60 * 60 * 24)
    return url

"""Demo kontent uchun rasm va audio generatsiyasi (haqiqiy fayllar yuklanguncha)."""

import io
import math
import random
import struct
import wave

from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT_BOLD = "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf"
FONT_REG = "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf"

PALETTES = [
    ((12, 22, 54), (46, 86, 180), (120, 170, 255)),
    ((20, 14, 48), (88, 52, 170), (190, 150, 255)),
    ((8, 30, 40), (20, 110, 120), (110, 230, 210)),
    ((40, 16, 24), (170, 70, 70), (255, 180, 140)),
    ((14, 24, 30), (40, 80, 70), (160, 220, 140)),
    ((26, 20, 10), (140, 100, 40), (255, 210, 120)),
]


def _font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def landscape(seed, size=(1600, 1000), title=None):
    """Tog' manzarasi uslubidagi rasm."""
    rnd = random.Random(seed)
    w, h = size
    top, mid, glow = PALETTES[seed % len(PALETTES)]
    img = Image.new("RGB", size)
    px = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        c = tuple(int(top[i] + (mid[i] - top[i]) * min(1, t * 1.4) + (glow[i] - mid[i]) * max(0, t - 0.45) * 0.9) for i in range(3))
        px.line([(0, y), (w, y)], fill=c)
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for k, (base, amp, shade) in enumerate([(0.55, 0.18, 0.55), (0.68, 0.12, 0.35), (0.82, 0.08, 0.18)]):
        pts, y = [(0, h)], h * base
        for x in range(0, w + 40, 40):
            y += rnd.uniform(-1, 1) * amp * h * 0.25
            y = h * base + (y - h * base) * 0.85
            pts.append((x, y))
        pts.append((w, h))
        col = tuple(int(top[i] * shade + 4) for i in range(3)) + (255,)
        d.polygon(pts, fill=col)
    img = Image.alpha_composite(img.convert("RGBA"), layer)
    glow_layer = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(glow_layer).ellipse([w * 0.6, h * 0.25, w * 1.1, h * 0.75], fill=glow + (70,))
    img = Image.alpha_composite(img, glow_layer.filter(ImageFilter.GaussianBlur(120)))
    if title:
        d = ImageDraw.Draw(img)
        f = _font(FONT_BOLD, int(h * 0.09))
        d.text((w * 0.06, h * 0.08), title, font=f, fill=(255, 255, 255, 235))
    return _jpeg(img)


def app_screenshot(seed, title, subtitle="", size=(1600, 1000)):
    """Veb-ilova skrinshotiga o'xshash muqova: navbar, hero, kartochkalar."""
    rnd = random.Random(seed)
    w, h = size
    top, mid, glow = PALETTES[seed % len(PALETTES)]
    img = Image.new("RGB", size, tuple(int(c * 0.5) for c in top))
    d = ImageDraw.Draw(img, "RGBA")
    for y in range(h):
        t = y / h
        d.line([(0, y), (w, y)], fill=tuple(int(top[i] * (1 - t) + mid[i] * t * 0.45) for i in range(3)))
    d.rounded_rectangle([40, 30, w - 40, 100], 18, fill=(255, 255, 255, 20), outline=(255, 255, 255, 40))
    d.ellipse([70, 50, 100, 80], fill=glow)
    d.text((115, 50), title, font=_font(FONT_BOLD, 30), fill=(255, 255, 255))
    for i in range(4):
        d.rounded_rectangle([w - 560 + i * 120, 55, w - 470 + i * 120, 75], 8, fill=(255, 255, 255, 60))
    d.text((80, 200), title, font=_font(FONT_BOLD, 110), fill=(255, 255, 255))
    d.text((84, 340), subtitle or "Modern platform", font=_font(FONT_REG, 40), fill=(205, 215, 240))
    d.rounded_rectangle([84, 430, 330, 500], 35, fill=glow)
    d.text((120, 448), "Get started", font=_font(FONT_BOLD, 28), fill=top)
    # O'ngdagi "telefon" va kartochkalar
    d.rounded_rectangle([w - 520, 170, w - 120, 900], 46, fill=tuple(int(c * 0.7) for c in top), outline=glow, width=3)
    for i in range(5):
        y0 = 250 + i * 125
        d.rounded_rectangle([w - 480, y0, w - 160, y0 + 100], 20, fill=tuple(min(255, int(c * 1.4) + 10) for c in top))
        d.rounded_rectangle([w - 460, y0 + 20, w - 400, y0 + 80], 14, fill=glow)
        d.rounded_rectangle([w - 380, y0 + 28, w - 200 - rnd.randint(0, 80), y0 + 44], 8, fill=(255, 255, 255))
        d.rounded_rectangle([w - 380, y0 + 56, w - 240 - rnd.randint(0, 60), y0 + 68], 6, fill=(170, 185, 215))
    for i in range(3):
        x0 = 84 + i * 290
        d.rounded_rectangle([x0, 620, x0 + 260, 900], 24, fill=tuple(min(255, int(c * 1.25) + 8) for c in top))
        bars = [rnd.randint(30, 150) for _ in range(6)]
        for j, b in enumerate(bars):
            d.rounded_rectangle([x0 + 30 + j * 36, 860 - b, x0 + 52 + j * 36, 860], 6, fill=glow if j % 2 else mid)
    return _jpeg(img)


def avatar(seed, letters, size=256):
    top, mid, glow = PALETTES[seed % len(PALETTES)]
    img = Image.new("RGB", (size, size), mid)
    d = ImageDraw.Draw(img)
    for y in range(size):
        d.line([(0, y), (size, y)], fill=tuple(int(mid[i] + (glow[i] - mid[i]) * y / size) for i in range(3)))
    f = _font(FONT_BOLD, size // 2 - 10)
    bbox = d.textbbox((0, 0), letters, font=f)
    d.text(((size - bbox[2]) / 2, (size - bbox[3]) / 2 - 8), letters, font=f, fill=(255, 255, 255))
    return _jpeg(img)


def ambient_wav(seed, seconds=18, rate=22050):
    """Yumshoq ambient akkord (pleyerni sinash uchun)."""
    rnd = random.Random(seed)
    base = rnd.choice([110.0, 130.81, 146.83, 164.81])
    freqs = [base, base * 1.25, base * 1.5, base * 2]
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        frames = bytearray()
        n = seconds * rate
        for i in range(n):
            t = i / rate
            env = min(1, t / 2) * min(1, (seconds - t) / 2)
            v = sum(math.sin(2 * math.pi * f * t + k) * (0.5 + 0.5 * math.sin(t * 0.3 + k)) for k, f in enumerate(freqs))
            frames += struct.pack("<h", int(v / len(freqs) * 9000 * env))
        wf.writeframes(bytes(frames))
    return ContentFile(buf.getvalue())


def logo_tile(seed, text, size=256):
    top, mid, glow = PALETTES[seed % len(PALETTES)]
    img = Image.new("RGB", (size, size), (250, 250, 255))
    d = ImageDraw.Draw(img)
    f = _font(FONT_BOLD, int(size * 0.36))
    bbox = d.textbbox((0, 0), text, font=f)
    d.text(((size - bbox[2]) / 2, (size - bbox[3]) / 2 - 10), text, font=f, fill=top)
    return _jpeg(img)


def _jpeg(img):
    out = io.BytesIO()
    img.convert("RGB").save(out, "JPEG", quality=86, optimize=True)
    return ContentFile(out.getvalue())

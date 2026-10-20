"""CKEditor (sayt) HTML -> Telegram HTML.

Telegram faqat b/i/u/s/a/code/pre/blockquote/tg-spoiler teglarini qo'llaydi
(https://core.telegram.org/bots/api#html-style). Qolganlari mazmuniga qarab o'giriladi:
sarlavhalar -> qalin, ro'yxatlar -> "•"/"1.", paragraflar -> bo'sh qator, rasm va jadvallar tashlab yuboriladi.
"""

import re
from html import escape
from html.parser import HTMLParser

INLINE = {"b": "b", "strong": "b", "i": "i", "em": "i", "u": "u", "ins": "u", "s": "s", "strike": "s", "del": "s"}
BLOCK_BREAK = {"p", "div", "figure", "table", "tr", "section", "article", "figcaption"}
HEADINGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
SKIP = {"img", "script", "style", "iframe", "oembed", "video", "audio", "svg"}


class _Converter(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.lists = []  # [("ul"|"ol", counter)]
        self.in_pre = False
        self.pre_lang = ""
        self.skip_depth = 0
        self.open_inline = []

    # ---------------------------------------------------------------- helpers
    def _nl(self, n=1):
        text = "".join(self.out)
        if text.endswith("<blockquote>"):
            return
        trailing = len(text) - len(text.rstrip("\n"))
        if text.strip() and trailing < n:
            self.out.append("\n" * (n - trailing))

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in SKIP:
            if tag not in ("img",):
                self.skip_depth += 1
            return
        if self.skip_depth:
            return
        if self.in_pre:
            if tag == "code" and not self.pre_lang:
                cls = attrs.get("class") or ""
                m = re.search(r"language-([\w+-]+)", cls)
                self.pre_lang = m.group(1) if m else ""
            return
        if tag in INLINE:
            self.out.append(f"<{INLINE[tag]}>")
            self.open_inline.append(INLINE[tag])
        elif tag == "a":
            href = attrs.get("href") or ""
            if href.startswith("/") and not href.startswith("//"):
                # Saytning ichki havolasi: Telegram'da to'liq manzil kerak
                from django.conf import settings

                href = settings.SITE_URL + href
            if href.startswith(("http://", "https://", "tg://", "mailto:")):
                self.out.append(f'<a href="{escape(href, quote=True)}">')
                self.open_inline.append("a")
            else:
                self.open_inline.append(None)
        elif tag == "code":
            self.out.append("<code>")
            self.open_inline.append("code")
        elif tag == "pre":
            self._nl(2)
            self.in_pre = True
            self.pre_lang = ""
            self.pre_start = len(self.out)
            self.out.append("")  # o'rin: yopilganda <pre> sarlavhasi bilan almashtiriladi
        elif tag == "blockquote":
            self._nl(2)
            self.out.append("<blockquote>")
        elif tag in HEADINGS:
            self._nl(2)
            self.out.append("<b>")
        elif tag in ("ul", "ol"):
            self._nl(1 if self.lists else 2)
            self.lists.append([tag, 0])
        elif tag == "li":
            self._nl(1)
            indent = "   " * (len(self.lists) - 1)
            if self.lists and self.lists[-1][0] == "ol":
                self.lists[-1][1] += 1
                self.out.append(f"{indent}{self.lists[-1][1]}. ")
            else:
                self.out.append(f"{indent}• ")
        elif tag == "br":
            self.out.append("\n")
        elif tag == "hr":
            self._nl(2)
            self.out.append("———")
            self._nl(2)
        elif tag in BLOCK_BREAK:
            self._nl(2)

    def handle_endtag(self, tag):
        if tag in SKIP:
            if tag != "img" and self.skip_depth:
                self.skip_depth -= 1
            return
        if self.skip_depth:
            return
        if tag == "pre" and self.in_pre:
            body = "".join(self.out[self.pre_start + 1:])
            del self.out[self.pre_start:]
            lang = f' class="language-{self.pre_lang}"' if self.pre_lang else ""
            self.out.append(f"<pre><code{lang}>{body.strip(chr(10))}</code></pre>")
            self.in_pre = False
            self._nl(2)
            return
        if self.in_pre:
            return
        if tag in INLINE or tag in ("a", "code"):
            if self.open_inline:
                t = self.open_inline.pop()
                if t:
                    self.out.append(f"</{t}>")
        elif tag == "blockquote":
            while self.out and self.out[-1].endswith("\n"):
                self.out[-1] = self.out[-1].rstrip("\n")
            self.out.append("</blockquote>")
            self._nl(2)
        elif tag in HEADINGS:
            self.out.append("</b>")
            self._nl(2)
        elif tag in ("ul", "ol"):
            if self.lists:
                self.lists.pop()
            self._nl(2)
        elif tag in BLOCK_BREAK:
            self._nl(2)

    def handle_data(self, data):
        if self.skip_depth:
            return
        if self.in_pre:
            self.out.append(escape(data, quote=False))
            return
        text = re.sub(r"\s+", " ", data)
        if not "".join(self.out).strip() or "".join(self.out).endswith("\n"):
            text = text.lstrip()
        if text:
            self.out.append(escape(text, quote=False))


def html_to_telegram(html):
    parser = _Converter()
    parser.feed(html or "")
    parser.close()
    text = "".join(parser.out)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Bo'sh teglarni tozalash: <b></b>
    text = re.sub(r"<(b|i|u|s|code)>\s*</\1>", "", text)
    return text.strip()


def visible_length(tg_html):
    """Telegram limiti teglarsiz matn uzunligi bo'yicha hisoblanadi."""
    from html import unescape

    return len(unescape(re.sub(r"<[^>]+>", "", tg_html)))


def truncate_telegram(tg_html, limit, suffix="…"):
    """Bloklar (bo'sh qator bilan ajratilgan) bo'yicha qisqartiradi: teglar buzilmaydi."""
    if visible_length(tg_html) <= limit:
        return tg_html
    blocks, out = tg_html.split("\n\n"), []
    for b in blocks:
        candidate = "\n\n".join([*out, b])
        if visible_length(candidate) + len(suffix) + 2 > limit:
            break
        out.append(b)
    if not out:
        # Birinchi blokning o'zi juda uzun: teglarsiz matnni kesamiz
        from html import unescape

        plain = unescape(re.sub(r"<[^>]+>", "", blocks[0]))
        return escape(plain[: limit - len(suffix)].rstrip(), quote=False) + suffix
    return "\n\n".join(out) + "\n\n" + suffix

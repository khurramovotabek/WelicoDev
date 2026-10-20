"""gettext o'rnatilmagan muhit uchun tarjima vositasi (Django'ning templatize() funksiyasi asosida).

    python scripts/i18n.py extract   # locale/<lang>/LC_MESSAGES/django.po ni yangilaydi (mavjud tarjimalar saqlanadi)
    python scripts/i18n.py apply     # scripts/translations/<lang>.json dagi tarjimalarni .po ga yozadi
    python scripts/i18n.py compile   # .po -> .mo
"""

import ast
import json
import re
import os
import sys
from pathlib import Path

import django
import polib

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

from django.utils.translation.template import templatize  # noqa: E402

LANGS = ["ru", "en"]
FUNCS = {"_", "gettext", "gettext_lazy", "pgettext", "pgettext_lazy", "ngettext", "ngettext_lazy"}
SKIP = {".venv", "node_modules", "staticfiles", "media", "tests", "migrations", "scripts"}


def _walk(suffix):
    for p in ROOT.rglob(f"*{suffix}"):
        if not SKIP.intersection(p.relative_to(ROOT).parts):
            yield p


def _from_python(src, origin, out):
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", getattr(node.func, "attr", None)) in FUNCS:
            name = getattr(node.func, "id", getattr(node.func, "attr", ""))
            args = node.args
            ctx = None
            if name.startswith("pgettext") and len(args) >= 2:
                ctx, args = args[0], args[1:]
            if args and isinstance(args[0], ast.Constant) and isinstance(args[0].value, str):
                msgid = args[0].value
                plural = args[1].value if name.startswith("ngettext") and len(args) > 1 and isinstance(args[1], ast.Constant) else None
                key = (ctx.value if isinstance(ctx, ast.Constant) else None, msgid)
                entry = out.setdefault(key, {"plural": plural, "refs": []})
                entry["refs"].append((origin, node.lineno))


STR = r"u?(?:'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\")"
TEMPLATE_CALL = re.compile(rf"\b(gettext|pgettext|ngettext)\(\s*({STR})(?:\s*,\s*({STR}))?")


def _from_template(code, origin, out):
    """templatize() natijasi to'liq Python emas, shuning uchun gettext(...) chaqiruvlari regex bilan olinadi."""
    for lineno, line in enumerate(code.splitlines(), 1):
        for m in TEMPLATE_CALL.finditer(line):
            func, a, b = m.group(1), ast.literal_eval(m.group(2)), m.group(3)
            b = ast.literal_eval(b) if b else None
            if func == "pgettext":
                key, plural = (a, b), None
            else:
                key, plural = (None, a), (b if func == "ngettext" else None)
            entry = out.setdefault(key, {"plural": plural, "refs": []})
            entry["refs"].append((origin, lineno))


def extract():
    found = {}
    for p in _walk(".html"):
        try:
            code = templatize(p.read_text(encoding="utf-8"), origin=str(p))
        except Exception as e:  # noqa: BLE001
            print("skip", p, e)
            continue
        _from_template(code, str(p.relative_to(ROOT)), found)
    for p in _walk(".py"):
        _from_python(p.read_text(encoding="utf-8"), str(p.relative_to(ROOT)), found)

    for lang in LANGS:
        path = ROOT / "locale" / lang / "LC_MESSAGES" / "django.po"
        path.parent.mkdir(parents=True, exist_ok=True)
        old = {(e.msgctxt, e.msgid): e for e in polib.pofile(str(path))} if path.exists() else {}
        po = polib.POFile()
        po.metadata = {"Content-Type": "text/plain; charset=UTF-8", "Language": lang, "MIME-Version": "1.0", "Content-Transfer-Encoding": "8bit"}
        for (ctx, msgid), info in sorted(found.items(), key=lambda kv: kv[0][1]):
            prev = old.get((ctx, msgid))
            entry = polib.POEntry(msgctxt=ctx, msgid=msgid, msgstr=prev.msgstr if prev else "",
                                  occurrences=[(f, str(n)) for f, n in info["refs"][:3]])
            if "%(" in msgid:
                entry.flags.append("python-format")
            if info["plural"]:
                entry.msgid_plural = info["plural"]
                entry.msgstr_plural = prev.msgstr_plural if prev and prev.msgstr_plural else {0: "", 1: "", 2: ""}
                entry.msgstr = ""
            po.append(entry)
        po.save(str(path))
        print(f"{lang}: {len(po)} ta matn, tarjima qilingan {len(po.translated_entries())}")


def apply():
    for lang in LANGS:
        src = ROOT / "scripts" / "translations" / f"{lang}.json"
        if not src.exists():
            continue
        data = json.loads(src.read_text(encoding="utf-8"))
        path = ROOT / "locale" / lang / "LC_MESSAGES" / "django.po"
        po = polib.pofile(str(path))
        n = 0
        for e in po:
            if e.msgid in data and data[e.msgid]:
                e.msgstr = data[e.msgid]
                n += 1
        po.save(str(path))
        missing = [e.msgid for e in po if not e.msgstr and not e.msgid_plural]
        print(f"{lang}: {n} ta tarjima yozildi, tarjimasiz: {len(missing)}")
        if missing:
            (ROOT / "scripts" / "translations" / f"{lang}.missing.json").write_text(
                json.dumps({m: "" for m in missing}, ensure_ascii=False, indent=1), encoding="utf-8")


def compile_():
    for lang in LANGS:
        path = ROOT / "locale" / lang / "LC_MESSAGES" / "django.po"
        polib.pofile(str(path)).save_as_mofile(str(path.with_suffix(".mo")))
        print(f"{lang}: django.mo tayyor")


if __name__ == "__main__":
    {"extract": extract, "apply": apply, "compile": compile_}[sys.argv[1]]()

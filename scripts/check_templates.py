"""Barcha shablonlarni kompilyatsiya qilib, sintaksis xatolarini topadi."""
import os
import sys
from pathlib import Path

import django

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

from django.template import TemplateSyntaxError
from django.template.loader import get_template

root = Path(__file__).resolve().parent.parent
bad = 0
for base in [root / "templates", *root.glob("apps/*/templates")]:
    for f in base.rglob("*.html"):
        name = str(f.relative_to(base))
        try:
            get_template(name)
        except TemplateSyntaxError as e:
            bad += 1
            print(f"{f.relative_to(root)}: {e}")
print("OK" if not bad else f"{bad} template(s) failed")

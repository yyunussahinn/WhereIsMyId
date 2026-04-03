"""
build_summary_patch.py
──────────────────────
build_summary.py dosyasina GUI env-var destegi ekler.
GUI, WIMID_EXCEL_FILE env var ile Excel yolunu gecirmek icin kullanir.

Kullanim:  python build_summary_patch.py
"""
import os, re

BASE   = os.path.dirname(os.path.abspath(__file__))
FPATH  = os.path.join(BASE, "build_summary.py")
MARKER = "WIMID_EXCEL_FILE"
PATCH  = (
    '\n# GUI env-var override (Where is My Id)\n'
    'import os as _os\n'
    '_gui_xl = _os.environ.get("WIMID_EXCEL_FILE", "")\n'
    'if _gui_xl:\n'
    '    EXCEL_FILE = _gui_xl\n\n'
)

if not os.path.exists(FPATH):
    print(f"Bulunamadi: {FPATH}")
    raise SystemExit(1)

with open(FPATH, "r", encoding="utf-8") as f:
    src = f.read()

if MARKER in src:
    print("build_summary.py zaten patch edilmis.")
    raise SystemExit(0)

m = re.search(r'^EXCEL_FILE\s*=\s*.+$', src, re.MULTILINE)
if not m:
    print("EXCEL_FILE sabiti bulunamadi. Manuel ekle.")
    raise SystemExit(1)

new = src[:m.end()] + PATCH + src[m.end():]
with open(FPATH, "w", encoding="utf-8") as f:
    f.write(new)

print("build_summary.py basariyla patch edildi.")
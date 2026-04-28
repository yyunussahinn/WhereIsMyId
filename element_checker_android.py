"""
element_checker_android.py — Where is My Id
────────────────────────────────────────────
Android UiAutomator2 element tarama + Word/Excel/JSON çıktı üretimi.
Ortak sabitler ve çıktı fonksiyonları: shared.py
"""

import sys
import os
import time
from collections import Counter

# ── Bağımlılık kontrolü ───────────────────────────────────────────────────────
def _check_deps() -> None:
    missing = []
    for pkg, pip_name in [
        ("docx",    "python-docx"),
        ("openpyxl","openpyxl"),
        ("PIL",     "Pillow"),
        ("appium",  "Appium-Python-Client"),
    ]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(f"   {pkg:12s} →  pip install {pip_name}")
    if missing:
        print("\n❌ Eksik kütüphane(ler):\n" + "\n".join(missing))
        raise SystemExit(1)

_check_deps()

import openpyxl
import config as cfg
import shared as sh
from appium import webdriver
from appium.webdriver.common.appiumby import AppiumBy
from appium.options.android import UiAutomator2Options

# ── Config doğrulama ──────────────────────────────────────────────────────────
OUTPUT_FMT        = cfg.OUTPUT_FORMAT.strip().lower()
OUTPUT_DIR        = cfg.OUTPUT_DIR
APPIUM_SERVER     = cfg.APPIUM_SERVER
DOCUMENT_SECTIONS = [s.strip().lower() for s in cfg.DOCUMENT_SECTIONS]
PLATFORM          = "android"
BLACKLIST         = set(cfg.BLACKLIST_IDS)

if OUTPUT_FMT not in {"word", "excel", "word+excel"}:
    raise ValueError(f"config.py — Geçersiz OUTPUT_FORMAT: '{OUTPUT_FMT}'")
for _s in DOCUMENT_SECTIONS:
    if _s not in {"missing", "undefined", "duplicate", "unique"}:
        raise ValueError(f"config.py — Geçersiz DOCUMENT_SECTIONS değeri: '{_s}'")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Sayfa adı & üzerine yazma onayı ──────────────────────────────────────────
sys.stdout.flush()
PAGE_NAME = input("Sayfa adı gir").strip()

WORD_FILE       = os.path.join(OUTPUT_DIR, f"{PAGE_NAME}_elements_Android.docx")
EXCEL_FILE      = os.path.join(OUTPUT_DIR, "Elements_Report_Android.xlsx")
JSON_FILE       = os.path.join(OUTPUT_DIR, f"{PAGE_NAME}_android.json")
SCREENSHOT_DIR  = os.path.join(OUTPUT_DIR, "screenshots_android")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)
SCREENSHOT_PATH = os.path.join(SCREENSHOT_DIR, f"{PAGE_NAME}.png")

if OUTPUT_FMT in ("word", "word+excel") and os.path.exists(WORD_FILE):
    if not sh.ask_overwrite(f"Word dosyası '{os.path.basename(WORD_FILE)}'"):
        print("\n🚫 İşlem iptal edildi.\n"); raise SystemExit(0)

if OUTPUT_FMT in ("excel", "word+excel") and os.path.exists(EXCEL_FILE):
    try:
        _wb = openpyxl.load_workbook(EXCEL_FILE, read_only=True)
        _has_sheet = PAGE_NAME in _wb.sheetnames
        _wb.close()
        if _has_sheet and not sh.ask_overwrite(f"Excel sheet '{PAGE_NAME}'"):
            print("\n🚫 İşlem iptal edildi.\n"); raise SystemExit(0)
    except openpyxl.utils.exceptions.InvalidFileException:
        pass

if os.path.exists(JSON_FILE):
    if not sh.ask_overwrite(f"JSON dosyası '{os.path.basename(JSON_FILE)}'"):
        print("\n🚫 İşlem iptal edildi.\n"); raise SystemExit(0)

print(f"\n🔧 Platform     : ANDROID")
print(f"📁 Çıktı formatı: {OUTPUT_FMT}")
print(f"📄 Sayfa adı    : {PAGE_NAME}\n")

# ── Appium seçenekleri ────────────────────────────────────────────────────────
_apk    = cfg.ANDROID
options = UiAutomator2Options()
options.platform_name    = "Android"
options.device_name      = _apk["device_name"]
options.platform_version = _apk["platform_version"]
options.automation_name  = "UiAutomator2"
options.app_package      = _apk["app_package"]
options.app_activity     = _apk["app_activity"]
options.no_reset         = _apk["no_reset"]

# ── Android element tipi tanımları ───────────────────────────────────────────
_ALWAYS = [
    "android.widget.EditText",
    "android.widget.Button",
    "android.widget.ImageButton",
    "android.widget.CheckBox",
    "android.widget.RadioButton",
    "android.widget.Switch",
    "android.widget.Spinner",
]
_CONDITIONAL = [
    "android.view.View",
    "android.view.ViewGroup",
    "android.widget.FrameLayout",
    "android.widget.LinearLayout",
    "android.widget.RelativeLayout",
    "android.widget.ImageView",
]
_RES_ID_ONLY = ["android.widget.TextView"]
_ALL_TYPES   = _ALWAYS + _CONDITIONAL + _RES_ID_ONLY

# ── Yardımcı fonksiyonlar ─────────────────────────────────────────────────────
def _short_type(t: str) -> str:
    return t.split(".")[-1]

def _clean(val) -> str:
    v = (val or "").strip()
    return "" if v.lower() in ("null", "none") else v

def _resource_id(el) -> str:
    rid = _clean(el.get_attribute("resource-id"))
    if not rid: return ""
    return rid.split("/")[-1] if "/" in rid else rid

def _label(el) -> str:
    return _clean(el.get_attribute("content-desc")) or _clean(el.get_attribute("text"))

def _value(el) -> str:
    return _clean(el.get_attribute("text"))

def _is_interactive(el, etype: str) -> bool:
    if etype in _ALWAYS:      return True
    if etype in _RES_ID_ONLY: return bool(_resource_id(el))
    if etype in _CONDITIONAL:
        return (el.get_attribute("clickable") == "true") or bool(_resource_id(el))
    return False

def _is_blacklisted(rid: str) -> bool:
    return rid in BLACKLIST or (rid.startswith("__") and rid.endswith("__"))

def _is_undefined(rid: str) -> bool:
    return "undefined" in rid.lower()

def _detected_page(driver) -> str:
    try:
        activity = driver.current_activity or ""
        return activity.split(".")[-1] if activity else ""
    except Exception:
        return ""

# ── Driver & element toplama ──────────────────────────────────────────────────
print("🚀 Appium driver başlatılıyor...")
driver = webdriver.Remote(APPIUM_SERVER, options=options)
time.sleep(3)

print("📸 Ekran görüntüsü alınıyor...")
driver.get_screenshot_as_file(SCREENSHOT_PATH)
print(f"   → {SCREENSHOT_PATH}")

page_detected = _detected_page(driver)
print(f"   → Tespit edilen sayfa: {page_detected or '(bulunamadı)'}")
print("🔍 Elementler taranıyor...")

all_elements: list[dict] = []
candidates:   list[dict] = []

for etype in _ALL_TYPES:
    for el in driver.find_elements(AppiumBy.XPATH, f"//{etype}"):
        try:
            if not _is_interactive(el, etype): continue
            rid   = _resource_id(el)
            label = _label(el)
            value = _value(el)
            stype = _short_type(etype)
        except Exception:
            continue

        if not rid and not label and not value:
            continue

        base = {"page": page_detected, "type": stype,
                "label": label, "value": value}

        if rid:
            if _is_blacklisted(rid):
                continue
            if _is_undefined(rid):
                all_elements.append({**base, "acc_id": rid,
                                     "status": sh.STATUS_UNDEFINED})
            else:
                candidates.append({**base, "acc_id": rid})
        else:
            all_elements.append({**base, "acc_id": "",
                                  "status": sh.STATUS_MISSING})

driver.quit()
print("✅ Driver kapatıldı.\n")

# Duplicate kontrolü
_counts = Counter(r["acc_id"] for r in candidates)
for r in candidates:
    r["status"] = (sh.STATUS_UNIQUE if _counts[r["acc_id"]] == 1
                   else sh.STATUS_DUPLICATE)
    all_elements.append(r)

# Özet
_grouped = {s: [e for e in all_elements if e["status"] == s]
            for s in sh.ALL_STATUSES}
print("=" * 45)
print(f"✅ Unique ID     : {len(_grouped[sh.STATUS_UNIQUE])}")
print(f"⚠️  Undefined ID  : {len(_grouped[sh.STATUS_UNDEFINED])}")
print(f"🔁 Duplicate ID  : {len(_grouped[sh.STATUS_DUPLICATE])}")
print(f"❌ Missing ID    : {len(_grouped[sh.STATUS_MISSING])}")
print("=" * 45 + "\n")

# AI Suggestion — önce enrich et, JSON da bu veriyi kullanır
all_elements = sh.enrich_with_ai(all_elements, PLATFORM)

# ── Çıktı üret ────────────────────────────────────────────────────────────────
if OUTPUT_FMT in ("word", "word+excel"):
    sh.generate_word(all_elements, PAGE_NAME, WORD_FILE,
                     DOCUMENT_SECTIONS, PLATFORM, SCREENSHOT_PATH)
if OUTPUT_FMT in ("excel", "word+excel"):
    sh.generate_excel(all_elements, PAGE_NAME, EXCEL_FILE,
                      DOCUMENT_SECTIONS, PLATFORM, SCREENSHOT_PATH)

# JSON — OUTPUT_FORMAT'tan bağımsız, her zaman üretilir
sh.generate_json(all_elements, PAGE_NAME, JSON_FILE, PLATFORM)
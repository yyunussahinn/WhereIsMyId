"""
element_checker_ios.py — Where is My Id
────────────────────────────────────────
iOS XCUITest element tarama + Word/Excel/JSON çıktı üretimi.
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
from appium.options.ios import XCUITestOptions

# ── Config doğrulama ──────────────────────────────────────────────────────────
OUTPUT_FMT        = cfg.OUTPUT_FORMAT.strip().lower()
OUTPUT_DIR        = cfg.OUTPUT_DIR
APPIUM_SERVER     = cfg.APPIUM_SERVER
DOCUMENT_SECTIONS = [s.strip().lower() for s in cfg.DOCUMENT_SECTIONS]
PLATFORM          = "ios"

# Geçerli format parçaları
_VALID_PARTS = {"word", "excel", "json"}
_fmt_parts   = set(OUTPUT_FMT.split("+"))
if not _fmt_parts or not _fmt_parts.issubset(_VALID_PARTS):
    raise ValueError(f"config.py — Geçersiz OUTPUT_FORMAT: '{OUTPUT_FMT}'. "
                     f"Geçerli değerler: word, excel, json (+ ile birleştirilebilir)")

OUT_WORD  = "word"  in _fmt_parts
OUT_EXCEL = "excel" in _fmt_parts
OUT_JSON  = "json"  in _fmt_parts

for _s in DOCUMENT_SECTIONS:
    if _s not in {"missing", "undefined", "duplicate", "unique"}:
        raise ValueError(f"config.py — Geçersiz DOCUMENT_SECTIONS değeri: '{_s}'")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Sayfa adı & üzerine yazma onayı ──────────────────────────────────────────
sys.stdout.flush()
PAGE_NAME = input("Sayfa adı gir: ").strip()

WORD_FILE       = os.path.join(OUTPUT_DIR, f"{PAGE_NAME}_elements_IOS.docx")
EXCEL_FILE      = os.path.join(OUTPUT_DIR, "Elements_Report_IOS.xlsx")
JSON_FILE       = os.path.join(OUTPUT_DIR, f"{PAGE_NAME}_ios.json")
SCREENSHOT_DIR  = os.path.join(OUTPUT_DIR, "screenshots_ios")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)
SCREENSHOT_PATH = os.path.join(SCREENSHOT_DIR, f"{PAGE_NAME}.png")

if OUT_WORD and os.path.exists(WORD_FILE):
    if not sh.ask_overwrite(f"Word dosyası '{os.path.basename(WORD_FILE)}'"):
        print("\n🚫 İşlem iptal edildi.\n"); raise SystemExit(0)

if OUT_EXCEL and os.path.exists(EXCEL_FILE):
    try:
        _wb = openpyxl.load_workbook(EXCEL_FILE, read_only=True)
        _has_sheet = PAGE_NAME in _wb.sheetnames
        _wb.close()
        if _has_sheet and not sh.ask_overwrite(f"Excel sheet '{PAGE_NAME}'"):
            print("\n🚫 İşlem iptal edildi.\n"); raise SystemExit(0)
    except openpyxl.utils.exceptions.InvalidFileException:
        pass

if OUT_JSON and os.path.exists(JSON_FILE):
    if not sh.ask_overwrite(f"JSON dosyası '{os.path.basename(JSON_FILE)}'"):
        print("\n🚫 İşlem iptal edildi.\n"); raise SystemExit(0)

print(f"\n🔧 Platform     : iOS")
print(f"📁 Çıktı formatı: {OUTPUT_FMT}")
print(f"📄 Sayfa adı    : {PAGE_NAME}\n")

# ── Appium seçenekleri ────────────────────────────────────────────────────────
_ios    = cfg.IOS
options = XCUITestOptions()
options.platform_name    = "iOS"
options.device_name      = _ios["device_name"]
options.platform_version = _ios["platform_version"]
options.automation_name  = "XCUITest"
options.bundle_id        = _ios["bundle_id"]
options.udid             = _ios["udid"]
options.no_reset         = _ios["no_reset"]

# ── Element tipi tanımları ────────────────────────────────────────────────────
_ALWAYS = [
    "XCUIElementTypeTextField",
    "XCUIElementTypeSecureTextField",
    "XCUIElementTypeButton",
    "XCUIElementTypeCell",
]
_CONDITIONAL = ["XCUIElementTypeOther"]
_ALL_TYPES   = _ALWAYS + _CONDITIONAL

# ── Yardımcı fonksiyonlar ─────────────────────────────────────────────────────
def _is_interactive(el, etype: str) -> bool:
    if etype in _ALWAYS:       return True
    if etype in _CONDITIONAL:  return el.get_attribute("accessible") == "true"
    return False

def _short_type(t: str) -> str:
    return t.replace("XCUIElementType", "")

def _detected_page(driver) -> str:
    try:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(driver.page_source)
        for tag in ("XCUIElementTypeNavigationBar", "XCUIElementTypeStaticText"):
            el = root.find(f".//{tag}")
            if el is not None:
                lbl = el.get("label") or el.get("name") or ""
                if lbl: return lbl
    except Exception:
        pass
    return ""

def _screen_size(driver) -> tuple[int, int]:
    s = driver.get_window_size()
    return s["width"], s["height"]

def _is_visible(el, sw: int, sh_: int) -> bool:
    try:
        r = el.rect
        w = r.get("width", 0); h = r.get("height", 0)
        x = r.get("x", 0)
        return w > 0 and h > 0 and x < sw and (x + w) > 0
    except Exception:
        return False

def _find_acc_id(driver, name: str) -> bool:
    try:
        driver.find_element(AppiumBy.ACCESSIBILITY_ID, name); return True
    except Exception:
        return False

def _has_real_id(driver, name: str, label: str) -> bool:
    return (bool(name) and name != label
            and not name.startswith("__")
            and _find_acc_id(driver, name))

def _is_undefined(name: str) -> bool:
    return "undefined" in name.lower() or name.startswith("__")

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

sw, sh_px    = _screen_size(driver)
all_elements: list[dict] = []
candidates:   list[dict] = []

for etype in _ALL_TYPES:
    for el in driver.find_elements(AppiumBy.XPATH, f"//{etype}"):
        if not _is_interactive(el, etype):        continue
        if not _is_visible(el, sw, sh_px):        continue

        name    = el.get_attribute("name")  or ""
        label   = el.get_attribute("label") or ""
        value   = el.get_attribute("value") or ""
        display = label or value or ""
        stype   = _short_type(etype)
        base    = {"page": page_detected, "type": stype,
                   "label": display, "value": value}

        if _has_real_id(driver, name, label):
            if _is_undefined(name):
                all_elements.append({**base, "acc_id": name,
                                     "status": sh.STATUS_UNDEFINED})
            else:
                candidates.append({**base, "acc_id": name})
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

# AI Suggestion — önce enrich et
all_elements = sh.enrich_with_ai(all_elements, PLATFORM)

# ── Çıktı üret ────────────────────────────────────────────────────────────────
if OUT_WORD:
    sh.generate_word(all_elements, PAGE_NAME, WORD_FILE,
                     DOCUMENT_SECTIONS, PLATFORM, SCREENSHOT_PATH)

if OUT_EXCEL:
    sh.generate_excel(all_elements, PAGE_NAME, EXCEL_FILE,
                      DOCUMENT_SECTIONS, PLATFORM, SCREENSHOT_PATH)

if OUT_JSON:
    sh.generate_json(all_elements, PAGE_NAME, JSON_FILE, PLATFORM)
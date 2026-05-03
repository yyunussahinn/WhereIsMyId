"""
smart_checker.py — v4.2
────────────────────────────────────────────────────────────────
Akıllı Tarama modülü.

Görevler:
  1. Appium'a bağlan, ekran görüntüsü al, elementleri topla (rect dahil)
  2. Driver'ı kapat
  3. claude_filter ile annotation kutularını eşleştir
  4. shared.py fonksiyonlarıyla Word + Excel + JSON raporu üret

v4.2: generate_reports artık shared.generate_word / generate_excel / generate_json
      kullanıyor → tam tarama ile aynı çıktı formatı.
"""

import time
import os
from datetime import datetime
from collections import Counter


# ════════════════════════════════════════════════════════════════════════════
#  PLATFORM SABITLERI
# ════════════════════════════════════════════════════════════════════════════

IOS_ALWAYS = [
    "XCUIElementTypeTextField",
    "XCUIElementTypeSecureTextField",
    "XCUIElementTypeButton",
    "XCUIElementTypeCell",
]
IOS_CONDITIONAL = ["XCUIElementTypeOther"]

AND_ALWAYS = [
    "android.widget.EditText",
    "android.widget.Button",
    "android.widget.ImageButton",
    "android.widget.CheckBox",
    "android.widget.RadioButton",
    "android.widget.Switch",
    "android.widget.Spinner",
]
AND_CONDITIONAL = [
    "android.view.View",
    "android.view.ViewGroup",
    "android.widget.FrameLayout",
    "android.widget.LinearLayout",
    "android.widget.RelativeLayout",
    "android.widget.ImageView",
]
AND_RESOURCE_ONLY = ["android.widget.TextView"]

# Status sabitleri — shared.py ile aynı
STATUS_UNIQUE    = "ID Var"
STATUS_DUPLICATE = "Duplicate"
STATUS_MISSING   = "ID Yok"
STATUS_UNDEFINED = "Undefined ID"


def get_new_status(status: str) -> str:
    return "" if status == STATUS_UNIQUE else "ID Eklenecek (Waiting Dev)"


# ════════════════════════════════════════════════════════════════════════════
#  APPIUM BAĞLANTI & ELEMENT TOPLAMA
# ════════════════════════════════════════════════════════════════════════════

def connect_and_capture(platform: str, profile: dict,
                         appium_server: str, screenshot_path: str,
                         log_cb=print) -> tuple[list, str]:
    """
    Appium'a bağlan, screenshot al, elementleri topla, driver'ı kapat.
    Dönüş: (all_elements, detected_page)
    """
    from appium import webdriver
    from appium.webdriver.common.appiumby import AppiumBy

    log_cb("🚀 Appium driver başlatılıyor...")

    if platform == "ios":
        from appium.options.ios import XCUITestOptions
        options = XCUITestOptions()
        options.platform_name    = "iOS"
        options.device_name      = profile["device_name"]
        options.platform_version = profile["platform_version"]
        options.automation_name  = "XCUITest"
        options.bundle_id        = profile["bundle_id"]
        options.no_reset         = profile.get("no_reset", True)
        options.udid             = profile["udid"]
    else:
        from appium.options.android import UiAutomator2Options
        options = UiAutomator2Options()
        options.platform_name    = "Android"
        options.device_name      = profile["device_name"]
        options.platform_version = profile["platform_version"]
        options.automation_name  = "UiAutomator2"
        options.app_package      = profile["app_package"]
        options.app_activity     = profile["app_activity"]
        options.no_reset         = profile.get("no_reset", True)

    driver = webdriver.Remote(appium_server, options=options)
    time.sleep(3)

    log_cb("📸 Ekran görüntüsü alınıyor...")
    os.makedirs(os.path.dirname(os.path.abspath(screenshot_path)), exist_ok=True)
    driver.get_screenshot_as_file(screenshot_path)
    log_cb(f"   → {screenshot_path}")

    detected_page = _get_detected_page(driver, platform)
    log_cb(f"   → Tespit edilen sayfa: {detected_page or '(bulunamadı)'}")

    log_cb("🔍 Elementler taranıyor...")
    screen_size = driver.get_window_size()
    sw = screen_size["width"]
    sh = screen_size["height"]

    all_elements = _collect_elements(driver, platform, detected_page, sw, sh, log_cb)

    driver.quit()
    log_cb("✅ Driver kapatıldı.")

    counts = Counter(e["status"] for e in all_elements)
    log_cb(f"{'='*40}")
    log_cb(f"✅ Unique    : {counts[STATUS_UNIQUE]}")
    log_cb(f"⚠️  Undefined : {counts[STATUS_UNDEFINED]}")
    log_cb(f"🔁 Duplicate : {counts[STATUS_DUPLICATE]}")
    log_cb(f"❌ Missing   : {counts[STATUS_MISSING]}")
    log_cb(f"{'='*40}")

    return all_elements, detected_page


def _get_detected_page(driver, platform: str) -> str:
    try:
        if platform == "ios":
            import xml.etree.ElementTree as ET
            root = ET.fromstring(driver.page_source)
            for tag in ["XCUIElementTypeNavigationBar", "XCUIElementTypeStaticText"]:
                el = root.find(f".//{tag}")
                if el is not None:
                    lbl = el.get("label") or el.get("name") or ""
                    if lbl:
                        return lbl
        else:
            activity = driver.current_activity or ""
            return activity.split(".")[-1] if activity else ""
    except Exception:
        pass
    return ""


def _collect_elements(driver, platform: str, detected_page: str,
                       sw: int, sh: int, log_cb) -> list:
    from appium.webdriver.common.appiumby import AppiumBy as AB

    candidates   = []
    all_elements = []

    if platform == "ios":
        all_elements, candidates = _collect_ios(driver, detected_page, sw, sh, AB)
    else:
        all_elements, candidates = _collect_android(driver, detected_page, AB)

    name_counts = Counter(r["acc_id"] for r in candidates)
    for row in candidates:
        row["status"] = (STATUS_UNIQUE
                         if name_counts[row["acc_id"]] == 1
                         else STATUS_DUPLICATE)
        all_elements.append(row)

    return all_elements


def _collect_ios(driver, detected_page, sw, sh, AppiumBy):
    from appium.webdriver.common.appiumby import AppiumBy as AB

    def get_name(el):  return el.get_attribute("name")  or ""
    def get_label(el): return el.get_attribute("label") or ""
    def get_value(el): return el.get_attribute("value") or ""
    def short_type(t): return t.replace("XCUIElementType", "")

    def is_visible(el):
        try:
            r = el.rect
            w, h = r.get("width", 0), r.get("height", 0)
            x = r.get("x", 0)
            return w > 0 and h > 0 and x < sw and (x + w) > 0
        except Exception:
            return False

    def find_by_acc(name):
        try:
            driver.find_element(AB.ACCESSIBILITY_ID, name)
            return True
        except Exception:
            return False

    def has_real_id(name, label):
        return (name and name != label
                and not name.startswith("__")
                and find_by_acc(name))

    def is_undefined(name):
        return "undefined" in name.lower() or name.startswith("__")

    def get_rect(el):
        try:
            r = el.rect
            return {"x": r["x"], "y": r["y"],
                    "width": r["width"], "height": r["height"]}
        except Exception:
            return None

    all_elems  = []
    candidates = []

    for etype in IOS_ALWAYS + IOS_CONDITIONAL:
        elems = driver.find_elements(AB.XPATH, f"//{etype}")
        for el in elems:
            if etype in IOS_CONDITIONAL:
                if el.get_attribute("accessible") != "true":
                    continue
            if not is_visible(el):
                continue

            name    = get_name(el)
            label   = get_label(el)
            value   = get_value(el)
            display = label or value or ""
            stype   = short_type(etype)
            rect    = get_rect(el)

            if has_real_id(name, label):
                entry = {"page": detected_page, "type": stype,
                         "label": display, "value": value,
                         "acc_id": name, "rect": rect}
                if is_undefined(name):
                    entry["status"] = STATUS_UNDEFINED
                    all_elems.append(entry)
                else:
                    candidates.append(entry)
            else:
                all_elems.append({"page": detected_page, "type": stype,
                                   "label": display, "value": value,
                                   "acc_id": "", "status": STATUS_MISSING,
                                   "rect": rect})

    return all_elems, candidates


def _collect_android(driver, detected_page, AppiumBy):
    from appium.webdriver.common.appiumby import AppiumBy as AB

    def short_type(t):  return t.split(".")[-1]
    def clean(v):
        s = (v or "").strip()
        return "" if s.lower() in ("null", "none") else s

    def get_rid(el):
        rid = clean(el.get_attribute("resource-id"))
        if not rid:
            return ""
        return rid.split("/")[-1] if "/" in rid else rid

    def get_label(el):
        return clean(el.get_attribute("content-desc")) or clean(el.get_attribute("text"))

    def get_value(el):
        return clean(el.get_attribute("text"))

    def is_undefined(rid):
        return "undefined" in rid.lower()

    def is_interactive(el, etype):
        if etype in AND_ALWAYS:
            return True
        if etype in AND_RESOURCE_ONLY:
            return bool(get_rid(el))
        if etype in AND_CONDITIONAL:
            return (el.get_attribute("clickable") == "true"
                    or bool(get_rid(el)))
        return False

    def get_rect(el):
        try:
            r = el.rect
            return {"x": r["x"], "y": r["y"],
                    "width": r["width"], "height": r["height"]}
        except Exception:
            return None

    all_elems  = []
    candidates = []
    ALL_TYPES  = AND_ALWAYS + AND_CONDITIONAL + AND_RESOURCE_ONLY

    for etype in ALL_TYPES:
        elems = driver.find_elements(AB.XPATH, f"//{etype}")
        for el in elems:
            try:
                if not is_interactive(el, etype):
                    continue
                rid   = get_rid(el)
                label = get_label(el)
                value = get_value(el)
                stype = short_type(etype)
                rect  = get_rect(el)
            except Exception:
                continue

            if not rid and not label and not value:
                continue

            if rid:
                entry = {"page": detected_page, "type": stype,
                         "label": label, "value": value,
                         "acc_id": rid, "rect": rect}
                if is_undefined(rid):
                    entry["status"] = STATUS_UNDEFINED
                    all_elems.append(entry)
                else:
                    candidates.append(entry)
            else:
                all_elems.append({"page": detected_page, "type": stype,
                                   "label": label, "value": value,
                                   "acc_id": "", "status": STATUS_MISSING,
                                   "rect": rect})

    return all_elems, candidates


# ════════════════════════════════════════════════════════════════════════════
#  RAPOR ÜRETIMI — shared.py fonksiyonları kullanılıyor (tam tarama ile aynı)
# ════════════════════════════════════════════════════════════════════════════

def generate_reports(
    elements:          list,
    page_name:         str,
    output_dir:        str,
    platform:          str,
    screenshot_path:   str,
    output_fmt:        str,
    document_sections: list = None,
    log_cb=print,
):
    """
    Word / Excel / JSON raporu üret.
    shared.py'deki generate_word, generate_excel, generate_json kullanılır
    → tam tarama ile birebir aynı çıktı formatı ve JSON yapısı.
    """
    import shared as sh

    os.makedirs(output_dir, exist_ok=True)

    if document_sections is None:
        document_sections = ["unique", "undefined", "duplicate", "missing"]

    plat_suffix = "IOS" if platform == "ios" else "Android"

    word_file  = os.path.join(output_dir, f"{page_name}_smart_{plat_suffix}.docx")
    excel_file = os.path.join(output_dir, f"Smart_Report_{plat_suffix}.xlsx")
    json_file  = os.path.join(output_dir, f"{page_name}_smart_{platform}.json")

    fmt_parts = set(output_fmt.split("+"))

    if "word" in fmt_parts:
        try:
            sh.generate_word(
                all_elements=elements,
                page_name=page_name,
                word_file=word_file,
                document_sections=document_sections,
                platform=platform,
                screenshot_path=screenshot_path,
            )
            log_cb(f"📄 Word kaydedildi: {word_file}")
        except Exception as ex:
            log_cb(f"⚠️  Word hatası: {ex}", )

    if "excel" in fmt_parts:
        try:
            sh.generate_excel(
                all_elements=elements,
                page_name=page_name,
                excel_file=excel_file,
                document_sections=document_sections,
                platform=platform,
                screenshot_path=screenshot_path,
            )
            log_cb(f"📊 Excel kaydedildi: {excel_file}")
        except Exception as ex:
            log_cb(f"⚠️  Excel hatası: {ex}")

    if "json" in fmt_parts:
        try:
            sh.generate_json(
                elements=elements,
                page_name=page_name,
                json_file=json_file,
                platform=platform,
            )
            log_cb(f"🗂  JSON kaydedildi: {json_file}")
        except Exception as ex:
            log_cb(f"⚠️  JSON hatası: {ex}")
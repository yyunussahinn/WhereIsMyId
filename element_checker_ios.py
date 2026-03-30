import time
import os
import re
from datetime import datetime
from collections import Counter

# ========================
# DEPENDENCY CHECK
# ========================
missing_deps = []
try:
    from docx import Document
except ImportError:
    missing_deps.append("python-docx  →  pip install python-docx")
try:
    import openpyxl
except ImportError:
    missing_deps.append("openpyxl     →  pip install openpyxl")
try:
    from PIL import Image as PILImage
except ImportError:
    missing_deps.append("Pillow       →  pip install Pillow")
try:
    from appium import webdriver
    from appium.webdriver.common.appiumby import AppiumBy
except ImportError:
    missing_deps.append("appium       →  pip install Appium-Python-Client")

if missing_deps:
    print("\n❌ Eksik kütüphane(ler):\n")
    for d in missing_deps:
        print(f"   {d}")
    raise SystemExit(1)

# ========================
# CONFIG
# ========================
import config as cfg

PLATFORM          = cfg.PLATFORM.strip().lower()
OUTPUT_FMT        = cfg.OUTPUT_FORMAT.strip().lower()
OUTPUT_DIR        = cfg.OUTPUT_DIR
APPIUM_SERVER     = cfg.APPIUM_SERVER
DOCUMENT_SECTIONS = [s.strip().lower() for s in cfg.DOCUMENT_SECTIONS]

VALID_SECTIONS = {"missing", "undefined", "duplicate", "unique"}
if PLATFORM not in ("ios", "android"):
    raise ValueError(f"config.py — Geçersiz PLATFORM: '{PLATFORM}'")
if OUTPUT_FMT not in ("word", "excel", "word+excel"):
    raise ValueError(f"config.py — Geçersiz OUTPUT_FORMAT: '{OUTPUT_FMT}'")
for s in DOCUMENT_SECTIONS:
    if s not in VALID_SECTIONS:
        raise ValueError(f"config.py — Geçersiz DOCUMENT_SECTIONS değeri: '{s}'")

os.makedirs(OUTPUT_DIR, exist_ok=True)

PAGE_NAME       = input("Sayfa adı gir (örnek: login, book_flight): ").strip()
WORD_FILE       = os.path.join(OUTPUT_DIR, f"{PAGE_NAME}_elements_IOS.docx")
EXCEL_FILE      = os.path.join(OUTPUT_DIR, "Elements_Report_IOS.xlsx")
SCREENSHOT_DIR  = os.path.join(OUTPUT_DIR, "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)
SCREENSHOT_PATH = os.path.join(SCREENSHOT_DIR, f"{PAGE_NAME}.png")

print(f"\n🔧 Platform     : {PLATFORM.upper()}")
print(f"📁 Çıktı formatı: {OUTPUT_FMT}")
print(f"📄 Sayfa adı    : {PAGE_NAME}\n")

# ========================
# UNDEFINED ID KONTROLÜ
# Sadece içinde "undefined" (büyük/küçük harf fark etmez) geçen ID'ler
# ========================
def is_undefined_id(name: str) -> bool:
    return "undefined" in name.lower()

# ========================
# PLATFORM OPTIONS
# ========================
if PLATFORM == "ios":
    from appium.options.ios import XCUITestOptions
    ios     = cfg.IOS
    options = XCUITestOptions()
    options.platform_name    = "iOS"
    options.device_name      = ios["device_name"]
    options.platform_version = ios["platform_version"]
    options.automation_name  = "XCUITest"
    options.bundle_id        = ios["bundle_id"]
    options.no_reset         = ios["no_reset"]
    options.udid             = ios["udid"]
else:
    from appium.options.android import UiAutomator2Options
    apk     = cfg.ANDROID
    options = UiAutomator2Options()
    options.platform_name    = "Android"
    options.device_name      = apk["device_name"]
    options.platform_version = apk["platform_version"]
    options.automation_name  = "UiAutomator2"
    options.app_package      = apk["app_package"]
    options.app_activity     = apk["app_activity"]
    options.no_reset         = apk["no_reset"]

# ========================
# ELEMENT TİPLERİ & YARDIMCILAR
# ========================
if PLATFORM == "ios":
    ALWAYS_INTERACTIVE      = [
        "XCUIElementTypeTextField",
        "XCUIElementTypeSecureTextField",
        "XCUIElementTypeButton",
        "XCUIElementTypeCell",
    ]
    CONDITIONAL_INTERACTIVE = ["XCUIElementTypeOther"]

    def is_interactive(el, elem_type):
        if elem_type in ALWAYS_INTERACTIVE:
            return True
        if elem_type in CONDITIONAL_INTERACTIVE:
            return el.get_attribute("accessible") == "true"
        return False

    def get_name(el):  return el.get_attribute("name")  or ""
    def get_label(el): return el.get_attribute("label") or ""
    def get_value(el): return el.get_attribute("value") or ""
    def short_type(t): return t.replace("XCUIElementType", "")

    def get_detected_page(driver):
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(driver.page_source)
            for tag in ["XCUIElementTypeNavigationBar", "XCUIElementTypeStaticText"]:
                el = root.find(f".//{tag}")
                if el is not None:
                    lbl = el.get("label") or el.get("name") or ""
                    if lbl:
                        return lbl
        except Exception:
            pass
        return ""

    def find_by_acc_id(driver, name):
        try:
            driver.find_element(AppiumBy.ACCESSIBILITY_ID, name)
            return True
        except Exception:
            return False

    def has_real_id(driver, name, label):
        return (
            name != ""
            and name != label
            and not name.startswith("__")
            and find_by_acc_id(driver, name)
        )

else:
    ALWAYS_INTERACTIVE      = [
        "android.widget.EditText",
        "android.widget.Button",
        "android.widget.ImageButton",
        "android.widget.CheckBox",
        "android.widget.RadioButton",
        "android.widget.Switch",
        "android.widget.Spinner",
    ]
    CONDITIONAL_INTERACTIVE = [
        "android.view.View",
        "android.widget.FrameLayout",
        "android.widget.LinearLayout",
        "android.widget.RelativeLayout",
    ]

    def is_interactive(el, elem_type):
        if elem_type in ALWAYS_INTERACTIVE:
            return True
        if elem_type in CONDITIONAL_INTERACTIVE:
            return el.get_attribute("clickable") == "true"
        return False

    def get_name(el):  return el.get_attribute("content-desc") or el.get_attribute("resource-id") or ""
    def get_label(el): return el.get_attribute("text") or el.get_attribute("content-desc") or ""
    def get_value(el): return el.get_attribute("text") or ""
    def short_type(t): return t.split(".")[-1]

    def get_detected_page(driver):
        try:
            activity = driver.current_activity or ""
            return activity.split(".")[-1] if activity else ""
        except Exception:
            return ""

    def find_by_acc_id(driver, name):
        try:
            driver.find_element(AppiumBy.ACCESSIBILITY_ID, name)
            return True
        except Exception:
            return False

    def has_real_id(driver, name, label):
        return (
            name != ""
            and name != label
            and find_by_acc_id(driver, name)
        )

# ========================
# STATUS SABİTLERİ
# ========================
STATUS_UNIQUE    = "ID Var"
STATUS_DUPLICATE = "Duplicate"
STATUS_MISSING   = "ID Yok"
STATUS_UNDEFINED = "Undefined ID"

SECTION_TO_STATUS = {
    "missing":   STATUS_MISSING,
    "undefined": STATUS_UNDEFINED,
    "duplicate": STATUS_DUPLICATE,
    "unique":    STATUS_UNIQUE,
}

STATUS_PALETTE = {
    STATUS_MISSING:   {"hdr": "C00000", "row": "FFDAD6", "alt": "FCEBEB", "txt": "501313"},
    STATUS_UNDEFINED: {"hdr": "C55A11", "row": "FCE4D6", "alt": "FFF3EC", "txt": "412402"},
    STATUS_DUPLICATE: {"hdr": "7B3F00", "row": "FAEEDA", "alt": "FEF6E4", "txt": "3B1F00"},
    STATUS_UNIQUE:    {"hdr": "375623", "row": "E2EFDA", "alt": "EAF3DE", "txt": "173404"},
}

# ========================
# DRIVER & ELEMENT TOPLAMA
# ========================
print("🚀 Appium driver başlatılıyor...")
driver = webdriver.Remote(APPIUM_SERVER, options=options)
time.sleep(3)

print("📸 Ekran görüntüsü alınıyor...")
driver.get_screenshot_as_file(SCREENSHOT_PATH)
print(f"   → {SCREENSHOT_PATH}")

detected_page = get_detected_page(driver)
print(f"   → Tespit edilen sayfa: {detected_page or '(bulunamadı)'}")

print("🔍 Elementler taranıyor...")

all_elements = []
candidates   = []

for elem_type in ALWAYS_INTERACTIVE + CONDITIONAL_INTERACTIVE:
    elems = driver.find_elements(AppiumBy.XPATH, f'//{elem_type}')
    for el in elems:
        if not is_interactive(el, elem_type):
            continue
        name    = get_name(el)
        label   = get_label(el)
        value   = get_value(el)
        display = label or value or ""
        stype   = short_type(elem_type)

        if has_real_id(driver, name, label):
            if is_undefined_id(name):
                all_elements.append({
                    "page":   detected_page,
                    "type":   stype,
                    "label":  display,
                    "value":  value,
                    "acc_id": name,
                    "status": STATUS_UNDEFINED,
                })
            else:
                candidates.append({
                    "page":   detected_page,
                    "type":   stype,
                    "label":  display,
                    "value":  value,
                    "acc_id": name,
                })
        else:
            all_elements.append({
                "page":   detected_page,
                "type":   stype,
                "label":  display,
                "value":  value,
                "acc_id": "",          # boş — ID yok
                "status": STATUS_MISSING,
            })

driver.quit()
print("✅ Driver kapatıldı.\n")

# Duplicate kontrolü
name_counts = Counter(row["acc_id"] for row in candidates)
for row in candidates:
    row["status"] = STATUS_UNIQUE if name_counts[row["acc_id"]] == 1 else STATUS_DUPLICATE
    all_elements.append(row)

# Gruplama
grouped = {
    STATUS_MISSING:   [e for e in all_elements if e["status"] == STATUS_MISSING],
    STATUS_UNDEFINED: [e for e in all_elements if e["status"] == STATUS_UNDEFINED],
    STATUS_DUPLICATE: [e for e in all_elements if e["status"] == STATUS_DUPLICATE],
    STATUS_UNIQUE:    [e for e in all_elements if e["status"] == STATUS_UNIQUE],
}

def build_ordered_list():
    """DOCUMENT_SECTIONS sırasına göre birleşik element listesi döner."""
    result = []
    for section_key in DOCUMENT_SECTIONS:
        result.extend(grouped[SECTION_TO_STATUS[section_key]])
    return result

# Konsol özet
print(f"{'='*45}")
print(f"✅ Unique ID     : {len(grouped[STATUS_UNIQUE])} adet")
print(f"⚠️  Undefined ID  : {len(grouped[STATUS_UNDEFINED])} adet")
print(f"🔁 Duplicate ID  : {len(grouped[STATUS_DUPLICATE])} adet")
print(f"❌ Missing ID    : {len(grouped[STATUS_MISSING])} adet")
print(f"{'='*45}\n")

# ========================
# WORD ÇIKTISI
# ========================
def generate_word():
    from docx import Document
    from docx.shared import RGBColor, Inches, Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    def add_shading(cell, hex_color):
        shading = OxmlElement('w:shd')
        shading.set(qn('w:fill'), hex_color)
        shading.set(qn('w:color'), 'auto')
        shading.set(qn('w:val'), 'clear')
        cell._tc.get_or_add_tcPr().append(shading)

    def hex_to_rgb(h):
        return RGBColor(*bytes.fromhex(h))

    COLS     = ["Page", "Type", "Label / Text", "Value", "Accessibility ID", "Status"]
    COL_KEYS = ["page", "type", "label", "value", "acc_id", "status"]
    WIDTHS   = [Inches(0.9), Inches(1.1), Inches(1.6), Inches(1.1), Inches(1.7), Inches(0.9)]

    word_exists = os.path.exists(WORD_FILE)
    doc = Document(WORD_FILE) if word_exists else Document()
    if word_exists:
        doc.add_page_break()

    # Başlık
    title = doc.add_heading(f"Accessibility ID Report — {PAGE_NAME}", level=1)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    date_para = doc.add_paragraph(
        f"Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}  |  Platform: {PLATFORM.upper()}"
    )
    date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph("")

    ordered = build_ordered_list()
    if ordered:
        table = doc.add_table(rows=1, cols=len(COLS))
        table.style = "Table Grid"

        # Header
        hdr = table.rows[0].cells
        for i, col_name in enumerate(COLS):
            hdr[i].text = col_name
            run = hdr[i].paragraphs[0].runs[0]
            run.bold = True
            run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            add_shading(hdr[i], "2C2C2A")
            hdr[i].width = WIDTHS[i]

        # Veri satırları
        for idx, elem in enumerate(ordered):
            status  = elem.get("status", STATUS_MISSING)
            palette = STATUS_PALETTE.get(status, STATUS_PALETTE[STATUS_MISSING])
            row_hex = palette["row"] if idx % 2 == 0 else palette["alt"]

            row_cells = table.add_row().cells
            for i, key in enumerate(COL_KEYS):
                val = elem.get(key, "") or ""
                row_cells[i].text  = val
                row_cells[i].width = WIDTHS[i]
                add_shading(row_cells[i], row_hex)
                runs = row_cells[i].paragraphs[0].runs
                if runs and key == "status":
                    runs[0].bold            = True
                    runs[0].font.color.rgb  = hex_to_rgb(palette["txt"])

    doc.add_paragraph("")

    # Ekran görüntüsü
    if os.path.exists(SCREENSHOT_PATH):
        doc.add_heading("📸 Ekran Görüntüsü", level=2)
        with PILImage.open(SCREENSHOT_PATH) as img:
            w_px, h_px = img.size
        max_w_in = 5.5
        w_in     = min(w_px / 96, max_w_in)
        h_in     = (h_px / 96) * (w_in / (w_px / 96))
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run().add_picture(SCREENSHOT_PATH, width=Inches(w_in))
        cap = doc.add_paragraph(f"{PAGE_NAME} sayfası ekran görüntüsü")
        cap.alignment  = WD_ALIGN_PARAGRAPH.CENTER
        cap.runs[0].font.size = Pt(9)
        cap.runs[0].italic    = True

    doc.save(WORD_FILE)
    print(f"📄 Word kaydedildi: {WORD_FILE}")

# ========================
# EXCEL ÇIKTISI
# ========================
def generate_excel():
    import openpyxl
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.drawing.image import Image as XLImage

    THIN     = Side(style="thin")
    BORDER   = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
    CENTER   = Alignment(horizontal="center", vertical="center", wrap_text=True)
    LEFT     = Alignment(horizontal="left",   vertical="center", wrap_text=True)
    HDR_FONT = Font(bold=True, color="FFFFFF", size=10)

    COLS     = ["Page", "Type", "Label / Text", "Value", "Accessibility ID", "Status"]
    COL_KEYS = ["page", "type", "label", "value", "acc_id", "status"]
    WIDTHS   = [16, 16, 26, 18, 32, 14]   # karakter

    DATA_COL_COUNT = len(COLS)             # 6 sütun veri (A–F)
    IMG_COL        = DATA_COL_COUNT + 2    # H sütunu (G boşluk)
    IMG_COL_LTR    = get_column_letter(IMG_COL)

    excel_exists = os.path.exists(EXCEL_FILE)
    wb = openpyxl.load_workbook(EXCEL_FILE) if excel_exists else openpyxl.Workbook()
    if not excel_exists and "Sheet" in wb.sheetnames:
        del wb["Sheet"]
    if PAGE_NAME in wb.sheetnames:
        del wb[PAGE_NAME]
    ws = wb.create_sheet(title=PAGE_NAME)

    # ── Başlık satırı (row 1)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=DATA_COL_COUNT)
    c = ws.cell(row=1, column=1,
                value=f"{PAGE_NAME}  |  "
                      f"{datetime.now().strftime('%d.%m.%Y %H:%M')}  |  {PLATFORM.upper()}")
    c.font      = Font(bold=True, color="FFFFFF", size=13)
    c.fill      = PatternFill("solid", fgColor="1F3864")
    c.alignment = CENTER
    c.border    = BORDER
    ws.row_dimensions[1].height = 26

    # ── Tablo header (row 2)
    for ci, col_name in enumerate(COLS, 1):
        c = ws.cell(row=2, column=ci, value=col_name)
        c.font      = HDR_FONT
        c.fill      = PatternFill("solid", fgColor="2C2C2A")
        c.alignment = CENTER
        c.border    = BORDER
    ws.row_dimensions[2].height = 18
    ws.freeze_panes = "A3"

    # ── Veri satırları (row 3+)
    ordered    = build_ordered_list()
    data_start = 3

    for idx, elem in enumerate(ordered):
        row_num = data_start + idx
        status  = elem.get("status", STATUS_MISSING)
        palette = STATUS_PALETTE.get(status, STATUS_PALETTE[STATUS_MISSING])
        row_fill = PatternFill("solid", fgColor=palette["row"] if idx % 2 == 0 else palette["alt"])

        for ci, key in enumerate(COL_KEYS, 1):
            val = elem.get(key, "") or ""
            c   = ws.cell(row=row_num, column=ci, value=val)
            c.fill   = row_fill
            c.border = BORDER
            if key == "status":
                c.font      = Font(bold=True, color=palette["txt"], size=10)
                c.alignment = CENTER
            else:
                c.font      = Font(size=10)
                c.alignment = LEFT
        ws.row_dimensions[row_num].height = 16

    # Kolon genişlikleri
    for ci, w in enumerate(WIDTHS, 1):
        ws.column_dimensions[get_column_letter(ci)].width = w

    # ── Screenshot — G sütununa başlık, H sütunundan görsel
    if os.path.exists(SCREENSHOT_PATH):

        # Görseli ölçekle
        with PILImage.open(SCREENSHOT_PATH) as img:
            orig_w, orig_h = img.size
        target_w = 300
        scale    = target_w / orig_w
        target_h = int(orig_h * scale)

        tmp_path = SCREENSHOT_PATH.replace(".png", "_xl_tmp.png")
        with PILImage.open(SCREENSHOT_PATH) as img:
            img.resize((target_w, target_h), PILImage.LANCZOS).save(tmp_path, format="PNG")

        # G sütunu: başlık hücresi (row 1–2 merge)
        gap_col     = DATA_COL_COUNT + 1          # G
        gap_col_ltr = get_column_letter(gap_col)
        ws.column_dimensions[gap_col_ltr].width = 2   # ince boşluk

        ws.merge_cells(start_row=1, start_column=IMG_COL,
                       end_row=2,   end_column=IMG_COL)
        hdr_c = ws.cell(row=1, column=IMG_COL,
                        value=f"📸 {PAGE_NAME}")
        hdr_c.font      = HDR_FONT
        hdr_c.fill      = PatternFill("solid", fgColor="1F3864")
        hdr_c.alignment = CENTER
        hdr_c.border    = BORDER
        ws.column_dimensions[IMG_COL_LTR].width = 42

        # Görseli H3'e anchor'la
        xl_img        = XLImage(tmp_path)
        xl_img.width  = target_w
        xl_img.height = target_h
        ws.add_image(xl_img, f"{IMG_COL_LTR}3")

    wb.save(EXCEL_FILE)
    print(f"📊 Excel kaydedildi: {EXCEL_FILE}  (sheet: {PAGE_NAME})")

    # Geçici dosyayı wb.save() sonrasında temizle
    if os.path.exists(SCREENSHOT_PATH):
        try:
            os.remove(tmp_path)
        except Exception:
            pass

# ========================
# ÇIKTI ÜRET
# ========================
if OUTPUT_FMT == "word":
    generate_word()
elif OUTPUT_FMT == "excel":
    generate_excel()
elif OUTPUT_FMT == "word+excel":
    generate_word()
    generate_excel()
import time
import sys  # GUI flush için eklendi
import os
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

OUTPUT_FMT        = cfg.OUTPUT_FORMAT.strip().lower()
OUTPUT_DIR        = cfg.OUTPUT_DIR
APPIUM_SERVER     = cfg.APPIUM_SERVER
DOCUMENT_SECTIONS = [s.strip().lower() for s in cfg.DOCUMENT_SECTIONS]
RESOURCE_ID_BLACKLIST = set(cfg.BLACKLIST_IDS)

VALID_SECTIONS = {"missing", "undefined", "duplicate", "unique"}
if OUTPUT_FMT not in ("word", "excel", "word+excel"):
    raise ValueError(f"config.py — Geçersiz OUTPUT_FORMAT: '{OUTPUT_FMT}'")
for s in DOCUMENT_SECTIONS:
    if s not in VALID_SECTIONS:
        raise ValueError(f"config.py — Geçersiz DOCUMENT_SECTIONS değeri: '{s}'")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ========================
# SAYFA ADI & ÜZERINE YAZMA ONAYI
# ========================
def ask_overwrite(label: str) -> bool:
    while True:
        sys.stdout.flush()
        answer = input(f"   ⚠️  {label} zaten mevcut. Üzerine yazmak istiyor musunuz? [e/h]: ").strip().lower()
        if answer in ("e", "evet", "y", "yes"):
            return True
        if answer in ("h", "hayır", "n", "no"):
            return False
        print("   Lütfen 'e' (evet) veya 'h' (hayır) girin.")

sys.stdout.flush()  # GUI subprocess flush
PAGE_NAME = input("Sayfa adı asd girilmesi bekleniyor").strip()

WORD_FILE       = os.path.join(OUTPUT_DIR, f"{PAGE_NAME}_elements_Android.docx")
EXCEL_FILE      = os.path.join(OUTPUT_DIR, "Elements_Report_Android.xlsx")
SCREENSHOT_DIR  = os.path.join(OUTPUT_DIR, "screenshots_android")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)
SCREENSHOT_PATH = os.path.join(SCREENSHOT_DIR, f"{PAGE_NAME}.png")

PLATFORM = "android"

# ---------- Word dosyası kontrolü ----------
WORD_OVERWRITE = True
if OUTPUT_FMT in ("word", "word+excel") and os.path.exists(WORD_FILE):
    WORD_OVERWRITE = ask_overwrite(f"Word dosyası '{os.path.basename(WORD_FILE)}'")
    if not WORD_OVERWRITE:
        print("\n🚫 İşlem iptal edildi. Farklı bir sayfa adıyla tekrar çalıştırın.\n")
        raise SystemExit(0)

# ---------- Excel sheet kontrolü ----------
EXCEL_SHEET_OVERWRITE = True
if OUTPUT_FMT in ("excel", "word+excel") and os.path.exists(EXCEL_FILE):
    try:
        _wb_check = openpyxl.load_workbook(EXCEL_FILE, read_only=True)
        if PAGE_NAME in _wb_check.sheetnames:
            EXCEL_SHEET_OVERWRITE = ask_overwrite(f"Excel sheet '{PAGE_NAME}'")
            if not EXCEL_SHEET_OVERWRITE:
                print("\n🚫 İşlem iptal edildi. Farklı bir sayfa adıyla tekrar çalıştırın.\n")
                raise SystemExit(0)
        _wb_check.close()
    except Exception:
        pass

print(f"\n🔧 Platform     : ANDROID")
print(f"📁 Çıktı formatı: {OUTPUT_FMT}")
print(f"📄 Sayfa adı    : {PAGE_NAME}\n")

# ========================
# UNDEFINED ID KONTROLÜ
# ========================
def is_undefined_id(name: str) -> bool:
    return "undefined" in name.lower()

# ========================
# APPIUM OPTIONS
# ========================
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy

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
# ANDROID ELEMENT KURALLARI
# ========================
def short_type(t):
    return t.split(".")[-1]

def get_resource_id(el):
    rid = el.get_attribute("resource-id") or ""
    rid = rid.strip()
    if rid.lower() in ("", "null", "none"):
        return ""
    return rid.split("/")[-1] if "/" in rid else rid

def _clean(val):
    v = (val or "").strip()
    return "" if v.lower() in ("null", "none") else v

def get_label(el):
    return _clean(el.get_attribute("content-desc")) or _clean(el.get_attribute("text"))

def get_value(el):
    return _clean(el.get_attribute("text"))

def get_detected_page(driver):
    try:
        activity = driver.current_activity or ""
        return activity.split(".")[-1] if activity else ""
    except Exception:
        return ""

ALWAYS_INTERACTIVE = [
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
    "android.view.ViewGroup",
    "android.widget.FrameLayout",
    "android.widget.LinearLayout",
    "android.widget.RelativeLayout",
    "android.widget.ImageView",
]

RESOURCE_ID_ONLY = [
    "android.widget.TextView",
]

ALL_TYPES = ALWAYS_INTERACTIVE + CONDITIONAL_INTERACTIVE + RESOURCE_ID_ONLY

def is_interactive(el, elem_type):
    if elem_type in ALWAYS_INTERACTIVE:
        return True
    if elem_type in RESOURCE_ID_ONLY:
        return bool(get_resource_id(el))
    if elem_type in CONDITIONAL_INTERACTIVE:
        clickable  = el.get_attribute("clickable") == "true"
        has_res_id = bool(get_resource_id(el))
        return clickable or has_res_id
    return False

def is_blacklisted_id(rid: str) -> bool:
    if rid in RESOURCE_ID_BLACKLIST:
        return True
    if rid.startswith("__") and rid.endswith("__"):
        return True
    return False

# ========================
# STATUS SABİTLERİ
# ========================
STATUS_UNIQUE    = "ID Var"
STATUS_DUPLICATE = "Duplicate"
STATUS_MISSING   = "ID Yok"
STATUS_UNDEFINED = "Undefined ID"

NEW_STATUS_WAITING = "ID Eklenecek (Waiting Dev)"
NEW_STATUS_EMPTY   = ""

def get_new_status(status: str) -> str:
    return NEW_STATUS_EMPTY if status == STATUS_UNIQUE else NEW_STATUS_WAITING

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

NEW_STATUS_COLOR = {
    "hdr": "843C0C",
    "row": "FDE9D9",
    "alt": "FEF3EC",
    "txt": "843C0C",
}

AI_SUGGESTION_COLOR = {
    "hdr": "1F4E79", "row": "DEEAF1", "alt": "EBF3F9", "txt": "1F4E79",
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

for elem_type in ALL_TYPES:
    elems = driver.find_elements(AppiumBy.XPATH, f'//{elem_type}')
    for el in elems:
        try:
            if not is_interactive(el, elem_type):
                continue
            rid   = get_resource_id(el)
            label = get_label(el)
            value = get_value(el)
            stype = short_type(elem_type)
        except Exception:
            continue

        if not rid and not label and not value:
            continue

        if rid:
            if is_blacklisted_id(rid):
                continue
            if is_undefined_id(rid):
                all_elements.append({
                    "page":   detected_page,
                    "type":   stype,
                    "label":  label,
                    "value":  value,
                    "acc_id": rid,
                    "status": STATUS_UNDEFINED,
                })
            else:
                candidates.append({
                    "page":   detected_page,
                    "type":   stype,
                    "label":  label,
                    "value":  value,
                    "acc_id": rid,
                })
        else:
            all_elements.append({
                "page":   detected_page,
                "type":   stype,
                "label":  label,
                "value":  value,
                "acc_id": "",
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
# AI SUGGESTION
# ========================
try:
    from ai_suggestion import enrich_elements
    all_elements = enrich_elements(all_elements, PLATFORM)
    grouped = {
        STATUS_MISSING:   [e for e in all_elements if e["status"] == STATUS_MISSING],
        STATUS_UNDEFINED: [e for e in all_elements if e["status"] == STATUS_UNDEFINED],
        STATUS_DUPLICATE: [e for e in all_elements if e["status"] == STATUS_DUPLICATE],
        STATUS_UNIQUE:    [e for e in all_elements if e["status"] == STATUS_UNIQUE],
    }
except ImportError:
    print("⚠️  ai_suggestion.py bulunamadı. AI Suggestion sütunu boş bırakılacak.")
    for e in all_elements:
        e["ai_suggestion"] = ""
except Exception as ex:
    print(f"⚠️  AI Suggestion hatası: {ex}. Sütun boş bırakılacak.")
    for e in all_elements:
        if "ai_suggestion" not in e:
            e["ai_suggestion"] = ""

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

    COLS     = ["Element ID", "Page", "Type", "Label / Text", "Value", "Resource ID", "Status", "New Status", "AI Suggestion"]
    COL_KEYS = ["element_id", "page", "type", "label", "value", "acc_id", "status", "new_status", "ai_suggestion"]
    WIDTHS   = [Inches(1.0), Inches(0.7), Inches(0.8), Inches(1.1), Inches(0.8), Inches(1.2), Inches(0.8), Inches(1.3), Inches(2.0)]

    if os.path.exists(WORD_FILE):
        os.remove(WORD_FILE)
    doc = Document()

    title = doc.add_heading(f"Accessibility Report — {PAGE_NAME}", level=1)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    date_para = doc.add_paragraph(
        f"Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}  |  Platform: ANDROID"
    )
    date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph("")

    ordered = build_ordered_list()
    if ordered:
        table = doc.add_table(rows=1, cols=len(COLS))
        table.style = "Table Grid"
        hdr = table.rows[0].cells
        for i, col_name in enumerate(COLS):
            hdr[i].text = col_name
            run = hdr[i].paragraphs[0].runs[0]
            run.bold = True
            run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            if col_name == "AI Suggestion":
                hdr_color = AI_SUGGESTION_COLOR["hdr"]
            elif col_name == "New Status":
                hdr_color = NEW_STATUS_COLOR["hdr"]
            else:
                hdr_color = "2C2C2A"
            add_shading(hdr[i], hdr_color)
            hdr[i].width = WIDTHS[i]

        for idx, elem in enumerate(ordered):
            elem_id    = f"{PAGE_NAME}_element_{idx + 1}"
            status     = elem.get("status", STATUS_MISSING)
            new_status = get_new_status(status)
            palette    = STATUS_PALETTE.get(status, STATUS_PALETTE[STATUS_MISSING])
            row_hex    = palette["row"] if idx % 2 == 0 else palette["alt"]
            ns_hex     = NEW_STATUS_COLOR["row"] if idx % 2 == 0 else NEW_STATUS_COLOR["alt"]
            ai_hex     = AI_SUGGESTION_COLOR["row"] if idx % 2 == 0 else AI_SUGGESTION_COLOR["alt"]

            row_cells = table.add_row().cells
            for i, key in enumerate(COL_KEYS):
                if key == "element_id":
                    val = elem_id
                elif key == "new_status":
                    val = new_status
                elif key == "ai_suggestion":
                    val = elem.get("ai_suggestion", "")
                else:
                    val = elem.get(key, "") or ""

                row_cells[i].text  = val
                row_cells[i].width = WIDTHS[i]

                if key == "ai_suggestion":
                    cell_hex = ai_hex
                elif key == "new_status":
                    cell_hex = ns_hex
                else:
                    cell_hex = row_hex
                add_shading(row_cells[i], cell_hex)

                runs = row_cells[i].paragraphs[0].runs
                if runs:
                    if key == "status":
                        runs[0].bold           = True
                        runs[0].font.color.rgb = hex_to_rgb(palette["txt"])
                    elif key == "new_status" and new_status:
                        runs[0].bold           = True
                        runs[0].font.color.rgb = hex_to_rgb(NEW_STATUS_COLOR["txt"])
                    elif key == "ai_suggestion" and val:
                        runs[0].font.size      = Pt(7)
                        runs[0].font.color.rgb = hex_to_rgb(AI_SUGGESTION_COLOR["txt"])

    doc.add_paragraph("")

    if os.path.exists(SCREENSHOT_PATH):
        doc.add_heading("📸 Ekran Görüntüsü", level=2)
        with PILImage.open(SCREENSHOT_PATH) as img:
            w_px, h_px = img.size
        max_w_in = 5.5
        w_in = min(w_px / 96, max_w_in)
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run().add_picture(SCREENSHOT_PATH, width=Inches(w_in))
        cap = doc.add_paragraph(f"{PAGE_NAME} sayfası ekran görüntüsü")
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
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

    COLS     = ["Element ID", "Page", "Type", "Label / Text", "Value", "Resource ID", "Status", "New Status", "AI Suggestion"]
    COL_KEYS = ["element_id", "page", "type", "label", "value", "acc_id", "status", "new_status", "ai_suggestion"]
    WIDTHS   = [22, 16, 16, 26, 18, 32, 14, 28, 45]

    DATA_COL_COUNT = len(COLS)
    IMG_COL        = DATA_COL_COUNT + 2
    IMG_COL_LTR    = get_column_letter(IMG_COL)

    excel_exists = os.path.exists(EXCEL_FILE)
    wb = openpyxl.load_workbook(EXCEL_FILE) if excel_exists else openpyxl.Workbook()
    if not excel_exists and "Sheet" in wb.sheetnames:
        del wb["Sheet"]

    if PAGE_NAME in wb.sheetnames:
        del wb[PAGE_NAME]
    ws = wb.create_sheet(title=PAGE_NAME)

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=DATA_COL_COUNT)
    c = ws.cell(row=1, column=1,
                value=f"{PAGE_NAME}  |  {datetime.now().strftime('%d.%m.%Y %H:%M')}  |  ANDROID")
    c.font      = Font(bold=True, color="FFFFFF", size=13)
    c.fill      = PatternFill("solid", fgColor="1F3864")
    c.alignment = CENTER
    c.border    = BORDER
    ws.row_dimensions[1].height = 26

    for ci, col_name in enumerate(COLS, 1):
        c = ws.cell(row=2, column=ci, value=col_name)
        c.font = HDR_FONT
        if col_name == "AI Suggestion":
            hdr_color = AI_SUGGESTION_COLOR["hdr"]
        elif col_name == "New Status":
            hdr_color = NEW_STATUS_COLOR["hdr"]
        else:
            hdr_color = "2C2C2A"
        c.fill      = PatternFill("solid", fgColor=hdr_color)
        c.alignment = CENTER
        c.border    = BORDER
    ws.row_dimensions[2].height = 18
    ws.freeze_panes = "A3"

    ordered    = build_ordered_list()
    data_start = 3

    for idx, elem in enumerate(ordered):
        elem_id    = f"{PAGE_NAME}_element_{idx + 1}"
        status     = elem.get("status", STATUS_MISSING)
        new_status = get_new_status(status)

        row_num  = data_start + idx
        palette  = STATUS_PALETTE.get(status, STATUS_PALETTE[STATUS_MISSING])
        row_fill = PatternFill("solid", fgColor=palette["row"] if idx % 2 == 0 else palette["alt"])
        ns_fill  = PatternFill("solid", fgColor=NEW_STATUS_COLOR["row"] if idx % 2 == 0 else NEW_STATUS_COLOR["alt"])
        ai_fill  = PatternFill("solid", fgColor=AI_SUGGESTION_COLOR["row"] if idx % 2 == 0 else AI_SUGGESTION_COLOR["alt"])

        for ci, key in enumerate(COL_KEYS, 1):
            if key == "element_id":
                val = elem_id
            elif key == "new_status":
                val = new_status
            elif key == "ai_suggestion":
                val = elem.get("ai_suggestion", "")
            else:
                val = elem.get(key, "") or ""

            c = ws.cell(row=row_num, column=ci, value=val)
            c.border = BORDER

            if key == "ai_suggestion":
                c.fill      = ai_fill
                c.font      = Font(size=8, color=AI_SUGGESTION_COLOR["txt"])
                c.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
            elif key == "new_status":
                c.fill = ns_fill
                if new_status:
                    c.font      = Font(bold=True, color=NEW_STATUS_COLOR["txt"], size=10)
                    c.alignment = CENTER
                else:
                    c.font      = Font(size=10)
                    c.alignment = CENTER
            elif key == "status":
                c.fill      = row_fill
                c.font      = Font(bold=True, color=palette["txt"], size=10)
                c.alignment = CENTER
            elif key == "element_id":
                c.fill      = row_fill
                c.font      = Font(bold=True, size=10)
                c.alignment = CENTER
            else:
                c.fill      = row_fill
                c.font      = Font(size=10)
                c.alignment = LEFT

        ws.row_dimensions[row_num].height = 60  # AI Suggestion için yüksek satır

    for ci, w in enumerate(WIDTHS, 1):
        ws.column_dimensions[get_column_letter(ci)].width = w

    if os.path.exists(SCREENSHOT_PATH):
        with PILImage.open(SCREENSHOT_PATH) as img:
            orig_w, orig_h = img.size
        target_w = 300
        target_h = int(orig_h * (target_w / orig_w))

        tmp_path = SCREENSHOT_PATH.replace(".png", "_xl_tmp.png")
        with PILImage.open(SCREENSHOT_PATH) as img:
            img.resize((target_w, target_h), PILImage.LANCZOS).save(tmp_path, format="PNG")

        gap_col_ltr = get_column_letter(DATA_COL_COUNT + 1)
        ws.column_dimensions[gap_col_ltr].width = 2

        ws.merge_cells(start_row=1, start_column=IMG_COL, end_row=2, end_column=IMG_COL)
        hdr_c = ws.cell(row=1, column=IMG_COL, value=f"📸 {PAGE_NAME}")
        hdr_c.font      = HDR_FONT
        hdr_c.fill      = PatternFill("solid", fgColor="1F3864")
        hdr_c.alignment = CENTER
        hdr_c.border    = BORDER
        ws.column_dimensions[IMG_COL_LTR].width = 42

        xl_img        = XLImage(tmp_path)
        xl_img.width  = target_w
        xl_img.height = target_h
        ws.add_image(xl_img, f"{IMG_COL_LTR}3")

    wb.save(EXCEL_FILE)
    print(f"📊 Excel kaydedildi: {EXCEL_FILE}  (sheet: {PAGE_NAME})")

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
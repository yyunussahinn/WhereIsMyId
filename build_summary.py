"""
build_summary.py
────────────────
Excel File klasöründeki dosyayı okur,
tüm sayfa sheetlerini birleştirerek:
  - "Data"    → ham verinin tamamı (pivot için)
  - "Summary" → sayfa bazlı özet tablo
  - "Task"    → sadece New Status = "ID Eklenecek (Waiting Dev)" olanlar
                New Status hücresi formülle kaynak sheet'e bağlıdır:
                sheet'te değiştirilen değer Task'a otomatik yansır.

Çalıştırma:
  python build_summary.py

NOT: "Data", "Summary" ve "Task" sheetleri varsa üzerine yazar.
"""

import os
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ── Dosyanın olduğu konum ──────────────────────────────────────────────────
EXCEL_FILE = "/Users/yunus.sahin/PycharmProjects/PythonProject/PIA_Elements/Revize_Elements_Report_Android.xlsx"

SKIP_SHEETS    = {"Data", "Summary", "Task"}
DATA_START_ROW = 3
DATA_COL_COUNT = 8   # Element ID(1) Page(2) Type(3) Label(4) Value(5) AccID(6) Status(7) NewStatus(8)

# New Status kaynak sheet'te kaçıncı kolon?  →  H
NEW_STATUS_COL_LTR = get_column_letter(8)

STATUS_MISSING   = "ID Yok"
STATUS_UNDEFINED = "Undefined ID"
STATUS_DUPLICATE = "Duplicate"
STATUS_UNIQUE    = "ID Var"
ALL_STATUSES     = [STATUS_MISSING, STATUS_UNDEFINED, STATUS_DUPLICATE, STATUS_UNIQUE]

NS_WAITING = "ID Eklenecek (Waiting Dev)"

def get_new_status_default(status: str) -> str:
    return "" if status == STATUS_UNIQUE else NS_WAITING

def sheet_ref(name: str) -> str:
    """Sheet adını Excel formülü için güvenli hale getirir."""
    special = set(" !@#$%^&*()-+=[]{}|;:,.<>?")
    return f"'{name}'" if any(ch in special for ch in name) else name

PALETTE = {
    STATUS_MISSING:   {"hdr": "C00000", "row": "FFDAD6", "alt": "FCEBEB", "txt": "501313"},
    STATUS_UNDEFINED: {"hdr": "C55A11", "row": "FCE4D6", "alt": "FFF3EC", "txt": "412402"},
    STATUS_DUPLICATE: {"hdr": "7B3F00", "row": "FAEEDA", "alt": "FEF6E4", "txt": "3B1F00"},
    STATUS_UNIQUE:    {"hdr": "375623", "row": "E2EFDA", "alt": "EAF3DE", "txt": "173404"},
}

NEW_STATUS_COLOR = {
    "hdr": "843C0C", "row": "FDE9D9", "alt": "FEF3EC", "txt": "843C0C",
}

THIN   = Side(style="thin")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT   = Alignment(horizontal="left",   vertical="center", wrap_text=True)

def fill(hex_c): return PatternFill("solid", fgColor=hex_c)
def font(bold=False, color="000000", size=10):
    return Font(bold=bold, color=color, size=size)

# ─────────────────────────────────────────────────────────────
# 1. Dosyayı aç
# ─────────────────────────────────────────────────────────────
if not os.path.exists(EXCEL_FILE):
    raise FileNotFoundError(f"Dosya bulunamadı: {EXCEL_FILE}")

wb = openpyxl.load_workbook(EXCEL_FILE)

page_sheets = [s for s in wb.sheetnames if s not in SKIP_SHEETS]
print(f"📂 {len(page_sheets)} sayfa sheet'i bulundu: {', '.join(page_sheets)}")

# ─────────────────────────────────────────────────────────────
# 2. Tüm sheetlerden veriyi oku
#    src_sheet + src_row: Task sheet'teki formül için saklanır
# ─────────────────────────────────────────────────────────────
all_rows   = []
page_stats = {}

for sheet_name in page_sheets:
    ws     = wb[sheet_name]
    counts = {s: 0 for s in ALL_STATUSES}
    found  = 0

    for row_obj in ws.iter_rows(min_row=DATA_START_ROW, max_col=DATA_COL_COUNT):
        src_row = row_obj[0].row

        vals = [str(cell.value or "").strip() if cell.value is not None else ""
                for cell in row_obj]
        while len(vals) < DATA_COL_COUNT:
            vals.append("")

        element_id, page, typ, label, value, acc_id, status, new_status = vals

        if all(v == "" for v in vals):
            continue
        if status not in ALL_STATUSES:
            continue

        if not new_status:
            new_status = get_new_status_default(status)

        all_rows.append({
            "element_id": element_id,
            "page":       page or sheet_name,
            "type":       typ,
            "label":      label,
            "value":      value,
            "acc_id":     acc_id,
            "status":     status,
            "new_status": new_status,
            "src_sheet":  sheet_name,
            "src_row":    src_row,
        })
        counts[status] += 1
        found += 1

    page_stats[sheet_name] = counts
    print(f"   ✓ {sheet_name:25s} → "
          f"Missing:{counts[STATUS_MISSING]:3d}  "
          f"Undefined:{counts[STATUS_UNDEFINED]:3d}  "
          f"Duplicate:{counts[STATUS_DUPLICATE]:3d}  "
          f"Unique:{counts[STATUS_UNIQUE]:3d}  "
          f"(toplam {found})")

# ─────────────────────────────────────────────────────────────
# 3. "Data" sheet'i oluştur  (orijinal — statik değerler)
# ─────────────────────────────────────────────────────────────
if "Data" in wb.sheetnames:
    del wb["Data"]
wd = wb.create_sheet("Data", 0)

COLS_D   = ["Element ID", "Page", "Type", "Label / Text", "Value", "Resource ID", "Status"]
WIDTHS_D = [22, 20, 16, 26, 18, 32, 14]

wd.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(COLS_D))
c = wd.cell(row=1, column=1, value="Accessibility ID — Ham Veri (Tüm Sayfalar)")
c.font      = font(bold=True, color="FFFFFF", size=13)
c.fill      = fill("375623")
c.alignment = CENTER
c.border    = BORDER
wd.row_dimensions[1].height = 26

for ci, col_name in enumerate(COLS_D, 1):
    c = wd.cell(row=2, column=ci, value=col_name)
    c.font      = font(bold=True, color="FFFFFF", size=10)
    c.fill      = fill("2C2C2A")
    c.alignment = CENTER
    c.border    = BORDER
wd.row_dimensions[2].height = 18
wd.freeze_panes = "A3"

for idx, row in enumerate(all_rows):
    data_row = idx + 3
    status   = row["status"]
    palette  = PALETTE.get(status, PALETTE[STATUS_MISSING])
    row_fill = fill(palette["row"] if idx % 2 == 0 else palette["alt"])

    values = [row["element_id"], row["page"], row["type"], row["label"],
              row["value"], row["acc_id"], row["status"]]

    for ci, val in enumerate(values, 1):
        c = wd.cell(row=data_row, column=ci, value=val)
        c.border = BORDER
        c.fill   = row_fill
        if ci == 7:   # Status
            c.font      = font(bold=True, color=palette["txt"], size=10)
            c.alignment = CENTER
        elif ci == 1: # Element ID
            c.font      = font(bold=True, size=10)
            c.alignment = CENTER
        else:
            c.font      = font(size=10)
            c.alignment = LEFT
    wd.row_dimensions[data_row].height = 16

for ci, w in enumerate(WIDTHS_D, 1):
    wd.column_dimensions[get_column_letter(ci)].width = w

print(f"\n✅ Data sheet oluşturuldu — {len(all_rows)} satır")

# ─────────────────────────────────────────────────────────────
# 4. "Summary" sheet'i oluştur  (orijinal)
# ─────────────────────────────────────────────────────────────
if "Summary" in wb.sheetnames:
    del wb["Summary"]
ws_sum = wb.create_sheet("Summary", 1)

totals      = {s: sum(page_stats[p][s] for p in page_sheets) for s in ALL_STATUSES}
grand_total = sum(totals.values())

ws_sum.merge_cells(start_row=1, start_column=1, end_row=1, end_column=5)
c = ws_sum.cell(row=1, column=1, value="Accessibility ID — Özet Rapor")
c.font      = font(bold=True, color="FFFFFF", size=14)
c.fill      = fill("1F3864")
c.alignment = CENTER
c.border    = BORDER
ws_sum.row_dimensions[1].height = 30

METRIC_COLS = {
    STATUS_MISSING:   (1, "C00000", "FFDAD6", "501313"),
    STATUS_UNDEFINED: (2, "C55A11", "FCE4D6", "412402"),
    STATUS_DUPLICATE: (3, "7B3F00", "FAEEDA", "3B1F00"),
    STATUS_UNIQUE:    (4, "375623", "E2EFDA", "173404"),
}

for status, (col, hdr_c, bg_c, txt_c) in METRIC_COLS.items():
    c = ws_sum.cell(row=3, column=col, value=status)
    c.font = font(bold=True, color="FFFFFF", size=10)
    c.fill = fill(hdr_c); c.alignment = CENTER; c.border = BORDER
    ws_sum.row_dimensions[3].height = 20

    c = ws_sum.cell(row=4, column=col, value=totals[status])
    c.font = font(bold=True, color=txt_c, size=22)
    c.fill = fill(bg_c); c.alignment = CENTER; c.border = BORDER
    ws_sum.row_dimensions[4].height = 36

    pct = f"%{round(totals[status] / grand_total * 100) if grand_total else 0}"
    c = ws_sum.cell(row=5, column=col, value=pct)
    c.font = font(color=txt_c, size=10); c.fill = fill(bg_c)
    c.alignment = CENTER; c.border = BORDER
    ws_sum.row_dimensions[5].height = 18

for col in range(1, 5):
    ws_sum.column_dimensions[get_column_letter(col)].width = 22

TABLE_COLS   = ["Sayfa", STATUS_MISSING, STATUS_UNDEFINED, STATUS_DUPLICATE, STATUS_UNIQUE, "Toplam"]
TABLE_COLORS = ["2C2C2A", "C00000", "C55A11", "7B3F00", "375623", "1F3864"]
WIDTHS_S     = [24, 14, 14, 14, 14, 12]
tbl_start    = 8

ws_sum.merge_cells(start_row=tbl_start - 1, start_column=1,
                   end_row=tbl_start - 1,   end_column=len(TABLE_COLS))
c = ws_sum.cell(row=tbl_start - 1, column=1, value="Sayfa Bazlı Dağılım")
c.font = font(bold=True, color="FFFFFF", size=11)
c.fill = fill("1F3864"); c.alignment = CENTER; c.border = BORDER
ws_sum.row_dimensions[tbl_start - 1].height = 22

for ci, (col_name, col_color) in enumerate(zip(TABLE_COLS, TABLE_COLORS), 1):
    c = ws_sum.cell(row=tbl_start, column=ci, value=col_name)
    c.font = font(bold=True, color="FFFFFF", size=10)
    c.fill = fill(col_color); c.alignment = CENTER; c.border = BORDER
ws_sum.row_dimensions[tbl_start].height = 18
ws_sum.freeze_panes = f"A{tbl_start + 1}"

for idx, page_name in enumerate(page_sheets):
    row_num   = tbl_start + 1 + idx
    counts    = page_stats[page_name]
    row_total = sum(counts.values())
    row_bg    = "F1EFE8" if idx % 2 == 0 else "FFFFFF"
    txt_colors = ["2C2C2A", "C00000", "C55A11", "7B3F00", "375623", "1F3864"]

    values = [page_name, counts[STATUS_MISSING], counts[STATUS_UNDEFINED],
              counts[STATUS_DUPLICATE], counts[STATUS_UNIQUE], row_total]

    for ci, (val, txt_c) in enumerate(zip(values, txt_colors), 1):
        c = ws_sum.cell(row=row_num, column=ci, value=val)
        c.fill = fill(row_bg); c.border = BORDER
        if ci == 1:
            c.font = font(bold=True, color=txt_c, size=10); c.alignment = LEFT
        else:
            c.font = font(bold=(val > 0 and ci != 6), color=txt_c, size=10)
            c.alignment = CENTER
    ws_sum.row_dimensions[row_num].height = 16

total_row = tbl_start + 1 + len(page_sheets)
ws_sum.row_dimensions[total_row].height = 20
totals_row_values = [
    "TOPLAM", totals[STATUS_MISSING], totals[STATUS_UNDEFINED],
    totals[STATUS_DUPLICATE], totals[STATUS_UNIQUE], grand_total,
]
for ci, (val, col_color) in enumerate(zip(totals_row_values, TABLE_COLORS), 1):
    c = ws_sum.cell(row=total_row, column=ci, value=val)
    c.font = font(bold=True, color="FFFFFF", size=10)
    c.fill = fill(col_color)
    c.alignment = CENTER if ci > 1 else LEFT
    c.border = BORDER

for ci, w in enumerate(WIDTHS_S, 1):
    ws_sum.column_dimensions[get_column_letter(ci)].width = w

print(f"✅ Summary sheet oluşturuldu — {len(page_sheets)} sayfa, {grand_total} element")

# ─────────────────────────────────────────────────────────────
# 5. "Task" sheet'i oluştur
#    Sadece new_status == NS_WAITING olan satırlar
#    New Status sütunu: statik değer değil, formülle kaynak hücreye bağlı
#      → =login!H5  gibi  (kaynak sheet'te değişince Task'ta da değişir)
# ─────────────────────────────────────────────────────────────
if "Task" in wb.sheetnames:
    del wb["Task"]
wt = wb.create_sheet("Task", 2)   # Data=0, Summary=1, Task=2

# Sadece Waiting Dev olanları filtrele
task_rows = [r for r in all_rows if r["new_status"] == NS_WAITING]

COLS_T   = ["Element ID", "Page", "Type", "Label / Text", "Value", "Resource ID", "Status", "New Status"]
COL_KEYS = ["element_id", "page", "type", "label", "value", "acc_id", "status"]   # new_status formülle gelecek
WIDTHS_T = [22, 20, 16, 26, 18, 32, 14, 28]

# Başlık satırı
wt.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(COLS_T))
c = wt.cell(row=1, column=1,
            value=f"ID Eklenecek Elementler — Waiting Dev  ({len(task_rows)} adet)")
c.font      = font(bold=True, color="FFFFFF", size=13)
c.fill      = fill(NEW_STATUS_COLOR["hdr"])
c.alignment = CENTER
c.border    = BORDER
wt.row_dimensions[1].height = 26

# Kolon başlıkları
for ci, col_name in enumerate(COLS_T, 1):
    c = wt.cell(row=2, column=ci, value=col_name)
    c.font      = font(bold=True, color="FFFFFF", size=10)
    c.fill      = fill(NEW_STATUS_COLOR["hdr"] if col_name == "New Status" else "2C2C2A")
    c.alignment = CENTER
    c.border    = BORDER
wt.row_dimensions[2].height = 18
wt.freeze_panes = "A3"

# Veri satırları
for idx, row in enumerate(task_rows):
    task_row = idx + 3
    status   = row["status"]
    palette  = PALETTE.get(status, PALETTE[STATUS_MISSING])
    row_fill = fill(palette["row"] if idx % 2 == 0 else palette["alt"])
    ns_fill  = fill(NEW_STATUS_COLOR["row"] if idx % 2 == 0 else NEW_STATUS_COLOR["alt"])

    # Sütun 1–7: statik değerler
    for ci, key in enumerate(COL_KEYS, 1):
        c = wt.cell(row=task_row, column=ci, value=row[key])
        c.border = BORDER
        c.fill   = row_fill
        if ci == 7:   # Status
            c.font      = font(bold=True, color=palette["txt"], size=10)
            c.alignment = CENTER
        elif ci == 1: # Element ID
            c.font      = font(bold=True, size=10)
            c.alignment = CENTER
        else:
            c.font      = font(size=10)
            c.alignment = LEFT
    wt.row_dimensions[task_row].height = 16

    # Sütun 8: New Status → formülle kaynak hücreye bağla
    # Örnek: =login!H5  veya  ='book flight'!H12
    formula = f"={sheet_ref(row['src_sheet'])}!{NEW_STATUS_COL_LTR}{row['src_row']}"
    c = wt.cell(row=task_row, column=8, value=formula)
    c.border    = BORDER
    c.fill      = ns_fill
    c.font      = font(bold=True, color=NEW_STATUS_COLOR["txt"], size=10)
    c.alignment = CENTER

for ci, w in enumerate(WIDTHS_T, 1):
    wt.column_dimensions[get_column_letter(ci)].width = w

print(f"✅ Task sheet oluşturuldu — {len(task_rows)} satır (New Status formülle bağlandı)")

# ─────────────────────────────────────────────────────────────
# 6. Kaydet
# ─────────────────────────────────────────────────────────────
wb.save(EXCEL_FILE)
print(f"\n📊 Dosya güncellendi: {EXCEL_FILE}")
print(f"   Sheet sırası: Data → Summary → Task → {' → '.join(page_sheets)}")
print(f"\n💡 Task sheet'indeki New Status formülle bağlı.")
print(f"   Developer/QA kaynak sheet'te güncellediğinde Task otomatik yansır.")
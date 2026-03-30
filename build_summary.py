"""
build_summary.py
────────────────
Mevcut PIA_Elements_Report.xlsx dosyasını okur,
tüm sayfa sheetlerini birleştirerek:
  - "Data"    → ham verinin tamamı (pivot için)
  - "Summary" → sayfa bazlı özet tablo

Çalıştırma:
  python build_summary.py

NOT: Önce düzenlemelerini yap, sonra bu scripti çalıştır.
     "Data" ve "Summary" sheetleri varsa üzerine yazar.
"""

import os
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ── Ayarlar ──────────────────────────────────────────────────
EXCEL_FILE = "/Users/yunus.sahin/PycharmProjects/PythonProject/PIA_Elements/PIA_Elements_Report_revize.xlsx"

# Bu sheetler sayfa verisi sayılmaz, atlanır
SKIP_SHEETS = {"Data", "Summary"}

# Tablo verisi hangi satırdan başlıyor? (başlık row 2, veri row 3)
DATA_START_ROW = 3

# Veri kolonları (A=1 … F=6) — Page,Type,Label,Value,AccID,Status
DATA_COL_COUNT = 6

# Status değerleri
STATUS_MISSING   = "ID Yok"
STATUS_UNDEFINED = "Undefined ID"
STATUS_DUPLICATE = "Duplicate"
STATUS_UNIQUE    = "ID Var"
ALL_STATUSES     = [STATUS_MISSING, STATUS_UNDEFINED, STATUS_DUPLICATE, STATUS_UNIQUE]

# Renkler
PALETTE = {
    STATUS_MISSING:   {"hdr": "C00000", "row": "FFDAD6", "alt": "FCEBEB", "txt": "501313"},
    STATUS_UNDEFINED: {"hdr": "C55A11", "row": "FCE4D6", "alt": "FFF3EC", "txt": "412402"},
    STATUS_DUPLICATE: {"hdr": "7B3F00", "row": "FAEEDA", "alt": "FEF6E4", "txt": "3B1F00"},
    STATUS_UNIQUE:    {"hdr": "375623", "row": "E2EFDA", "alt": "EAF3DE", "txt": "173404"},
}

THIN    = Side(style="thin")
BORDER  = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
CENTER  = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT    = Alignment(horizontal="left",   vertical="center", wrap_text=True)

def fill(hex_c):  return PatternFill("solid", fgColor=hex_c)
def font(bold=False, color="000000", size=10):
    return Font(bold=bold, color=color, size=size)

# ─────────────────────────────────────────────────────────────
# 1. Dosyayı aç
# ─────────────────────────────────────────────────────────────
if not os.path.exists(EXCEL_FILE):
    raise FileNotFoundError(f"Dosya bulunamadı: {EXCEL_FILE}")

wb = openpyxl.load_workbook(EXCEL_FILE)

# Sayfa sheetlerini belirle (SKIP_SHEETS dışındakiler)
page_sheets = [s for s in wb.sheetnames if s not in SKIP_SHEETS]
print(f"📂 {len(page_sheets)} sayfa sheet'i bulundu: {', '.join(page_sheets)}")

# ─────────────────────────────────────────────────────────────
# 2. Tüm sheetlerden veriyi oku
# ─────────────────────────────────────────────────────────────
all_rows   = []   # (page_name, type, label, value, acc_id, status)
page_stats = {}   # {page_name: {status: count}}

for sheet_name in page_sheets:
    ws      = wb[sheet_name]
    counts  = {s: 0 for s in ALL_STATUSES}
    found   = 0

    for row in ws.iter_rows(min_row=DATA_START_ROW, max_col=DATA_COL_COUNT, values_only=True):
        # Tamamen boş satırı atla
        if all(cell is None or str(cell).strip() == "" for cell in row):
            continue

        page, typ, label, value, acc_id, status = (
            str(row[0] or "").strip(),
            str(row[1] or "").strip(),
            str(row[2] or "").strip(),
            str(row[3] or "").strip(),
            str(row[4] or "").strip(),
            str(row[5] or "").strip(),
        )

        # Status değeri tanımlı değilse atla (screenshot satırı vs.)
        if status not in ALL_STATUSES:
            continue

        all_rows.append((page or sheet_name, typ, label, value, acc_id, status))
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
# 3. "Data" sheet'i oluştur
# ─────────────────────────────────────────────────────────────
if "Data" in wb.sheetnames:
    del wb["Data"]
wd = wb.create_sheet("Data", 0)   # en başa ekle

COLS     = ["Page", "Type", "Label / Text", "Value", "Accessibility ID", "Status"]
WIDTHS_D = [20, 16, 26, 18, 32, 14]

# Başlık
wd.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(COLS))
c = wd.cell(row=1, column=1, value="Accessibility ID — Ham Veri (Tüm Sayfalar)")
c.font      = font(bold=True, color="FFFFFF", size=13)
c.fill      = fill("375623")
c.alignment = CENTER
c.border    = BORDER
wd.row_dimensions[1].height = 26

# Kolon başlıkları
for ci, col_name in enumerate(COLS, 1):
    c = wd.cell(row=2, column=ci, value=col_name)
    c.font      = font(bold=True, color="FFFFFF", size=10)
    c.fill      = fill("2C2C2A")
    c.alignment = CENTER
    c.border    = BORDER
wd.row_dimensions[2].height = 18
wd.freeze_panes = "A3"

# Veri satırları
for idx, (page, typ, label, value, acc_id, status) in enumerate(all_rows):
    row_num = idx + 3
    palette = PALETTE.get(status, PALETTE[STATUS_MISSING])
    row_fill = fill(palette["row"] if idx % 2 == 0 else palette["alt"])

    values = [page, typ, label, value, acc_id, status]
    for ci, val in enumerate(values, 1):
        c = wd.cell(row=row_num, column=ci, value=val)
        c.fill   = row_fill
        c.border = BORDER
        if ci == 6:  # Status kolonu
            c.font      = font(bold=True, color=palette["txt"], size=10)
            c.alignment = CENTER
        else:
            c.font      = font(size=10)
            c.alignment = LEFT
    wd.row_dimensions[row_num].height = 16

for ci, w in enumerate(WIDTHS_D, 1):
    wd.column_dimensions[get_column_letter(ci)].width = w

print(f"\n✅ Data sheet oluşturuldu — {len(all_rows)} satır")

# ─────────────────────────────────────────────────────────────
# 4. "Summary" sheet'i oluştur
# ─────────────────────────────────────────────────────────────
if "Summary" in wb.sheetnames:
    del wb["Summary"]
ws_sum = wb.create_sheet("Summary", 1)  # Data'dan sonra

# Toplam hesapla
totals = {s: sum(page_stats[p][s] for p in page_sheets) for s in ALL_STATUSES}
grand_total = sum(totals.values())

# ── Sayfa başlığı
ws_sum.merge_cells(start_row=1, start_column=1, end_row=1, end_column=6)
c = ws_sum.cell(row=1, column=1, value="Accessibility ID — Özet Rapor")
c.font      = font(bold=True, color="FFFFFF", size=14)
c.fill      = fill("1F3864")
c.alignment = CENTER
c.border    = BORDER
ws_sum.row_dimensions[1].height = 30

# ── Metrik kartlar (row 3–5, her status bir kart)
METRIC_COLS = {
    STATUS_MISSING:   (1, "C00000", "FFDAD6", "501313"),
    STATUS_UNDEFINED: (2, "C55A11", "FCE4D6", "412402"),
    STATUS_DUPLICATE: (3, "7B3F00", "FAEEDA", "3B1F00"),
    STATUS_UNIQUE:    (4, "375623", "E2EFDA", "173404"),
}

for status, (col, hdr_c, bg_c, txt_c) in METRIC_COLS.items():
    # Başlık hücresi
    c = ws_sum.cell(row=3, column=col, value=status)
    c.font      = font(bold=True, color="FFFFFF", size=10)
    c.fill      = fill(hdr_c)
    c.alignment = CENTER
    c.border    = BORDER
    ws_sum.row_dimensions[3].height = 20

    # Sayı hücresi
    c = ws_sum.cell(row=4, column=col, value=totals[status])
    c.font      = font(bold=True, color=txt_c, size=22)
    c.fill      = fill(bg_c)
    c.alignment = CENTER
    c.border    = BORDER
    ws_sum.row_dimensions[4].height = 36

    # Yüzde hücresi
    pct = f"%{round(totals[status] / grand_total * 100) if grand_total else 0}"
    c = ws_sum.cell(row=5, column=col, value=pct)
    c.font      = font(color=txt_c, size=10)
    c.fill      = fill(bg_c)
    c.alignment = CENTER
    c.border    = BORDER
    ws_sum.row_dimensions[5].height = 18

# Kart kolon genişlikleri
for col in range(1, 5):
    ws_sum.column_dimensions[get_column_letter(col)].width = 18

# ── Sayfa bazlı tablo (row 8+)
TABLE_COLS   = ["Sayfa", STATUS_MISSING, STATUS_UNDEFINED, STATUS_DUPLICATE, STATUS_UNIQUE, "Toplam"]
TABLE_COLORS = ["2C2C2A", "C00000", "C55A11", "7B3F00", "375623", "1F3864"]
WIDTHS_S     = [24, 14, 14, 14, 14, 12]

tbl_start = 8

# Tablo başlığı
ws_sum.merge_cells(start_row=tbl_start - 1, start_column=1,
                   end_row=tbl_start - 1,   end_column=len(TABLE_COLS))
c = ws_sum.cell(row=tbl_start - 1, column=1, value="Sayfa Bazlı Dağılım")
c.font      = font(bold=True, color="FFFFFF", size=11)
c.fill      = fill("1F3864")
c.alignment = CENTER
c.border    = BORDER
ws_sum.row_dimensions[tbl_start - 1].height = 22

# Header satırı
for ci, (col_name, col_color) in enumerate(zip(TABLE_COLS, TABLE_COLORS), 1):
    c = ws_sum.cell(row=tbl_start, column=ci, value=col_name)
    c.font      = font(bold=True, color="FFFFFF", size=10)
    c.fill      = fill(col_color)
    c.alignment = CENTER
    c.border    = BORDER
ws_sum.row_dimensions[tbl_start].height = 18
ws_sum.freeze_panes = f"A{tbl_start + 1}"

# Sayfa satırları
for idx, page_name in enumerate(page_sheets):
    row_num  = tbl_start + 1 + idx
    counts   = page_stats[page_name]
    row_total = sum(counts.values())
    row_bg   = "F1EFE8" if idx % 2 == 0 else "FFFFFF"

    values = [
        page_name,
        counts[STATUS_MISSING],
        counts[STATUS_UNDEFINED],
        counts[STATUS_DUPLICATE],
        counts[STATUS_UNIQUE],
        row_total,
    ]
    txt_colors = ["2C2C2A", "C00000", "C55A11", "7B3F00", "375623", "1F3864"]

    for ci, (val, txt_c) in enumerate(zip(values, txt_colors), 1):
        c = ws_sum.cell(row=row_num, column=ci, value=val)
        c.fill   = fill(row_bg)
        c.border = BORDER
        if ci == 1:
            c.font      = font(bold=True, color=txt_c, size=10)
            c.alignment = LEFT
        else:
            c.font      = font(bold=(val > 0 and ci != 6), color=txt_c, size=10)
            c.alignment = CENTER
    ws_sum.row_dimensions[row_num].height = 16

# Toplam satırı
total_row = tbl_start + 1 + len(page_sheets)
ws_sum.row_dimensions[total_row].height = 20
totals_row_values = [
    "TOPLAM",
    totals[STATUS_MISSING],
    totals[STATUS_UNDEFINED],
    totals[STATUS_DUPLICATE],
    totals[STATUS_UNIQUE],
    grand_total,
]
for ci, (val, txt_c) in enumerate(zip(totals_row_values, txt_colors), 1):
    c = ws_sum.cell(row=total_row, column=ci, value=val)
    c.font      = font(bold=True, color="FFFFFF", size=10)
    c.fill      = fill(TABLE_COLORS[ci - 1])
    c.alignment = CENTER if ci > 1 else LEFT
    c.border    = BORDER

# Kolon genişlikleri
for ci, w in enumerate(WIDTHS_S, 1):
    ws_sum.column_dimensions[get_column_letter(ci)].width = w

print(f"✅ Summary sheet oluşturuldu — {len(page_sheets)} sayfa, {grand_total} element")

# ─────────────────────────────────────────────────────────────
# 5. Kaydet
# ─────────────────────────────────────────────────────────────
wb.save(EXCEL_FILE)
print(f"\n📊 Dosya güncellendi: {EXCEL_FILE}")
print(f"   Sheet sırası: Summary → Data → {' → '.join(page_sheets)}")
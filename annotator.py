"""
annotator.py
────────────────────────────────────────────────────────────────
Ekran görüntüsü üzerine mouse ile kırmızı kare çizme penceresi.

Kullanım (standalone test):
    python annotator.py /yol/screenshot.png

Modül olarak kullanım (app.py'den):
    from annotator import open_annotator
    boxes = open_annotator(parent, image_path)
    # boxes → [{"x1":10,"y1":20,"x2":150,"y2":200}, ...]
    # boxes == [] → iptal edildi
"""

import tkinter as tk
from PIL import Image, ImageTk
import os
import sys

# ── Renkler ─────────────────────────────────────────────────────────────────
BG_MAIN   = "#F5F0E8"
BG_PANEL  = "#FFFFFF"
BG_INPUT  = "#EDE8DF"
T_PRI     = "#2C2416"
T_MUT     = "#8C7D6A"
C_OK      = "#1a8242"
C_ERR     = "#7B1515"
ACCENT    = "#000000"
BOX_COLOR = "#FF2020"
BOX_WIDTH = 2

MAX_W = 900
MAX_H = 700


def open_annotator(parent, image_path: str) -> list:
    """
    Annotation penceresini aç, kullanıcı onaylayınca
    orijinal piksel koordinatlarını döndür.
    parent: tk.Tk veya tk.Toplevel
    """

    result = []

    # ── Görüntü yükle ───────────────────────────────────────────────────────
    pil_orig = Image.open(image_path).convert("RGB")
    orig_w, orig_h = pil_orig.size

    scale = min(MAX_W / orig_w, MAX_H / orig_h, 1.0)
    disp_w = int(orig_w * scale)
    disp_h = int(orig_h * scale)

    pil_disp = pil_orig.resize((disp_w, disp_h), Image.LANCZOS)

    # ── Pencere ─────────────────────────────────────────────────────────────
    win = tk.Toplevel(parent)
    win.title("Annotation — Elementleri İşaretle")
    win.configure(bg=BG_MAIN)
    win.resizable(True, True)
    win.protocol("WM_DELETE_WINDOW", win.destroy)

    # ── Başlık ──────────────────────────────────────────────────────────────
    hdr = tk.Frame(win, bg=BG_PANEL, height=46)
    hdr.pack(fill="x")
    hdr.pack_propagate(False)
    tk.Label(hdr, text="📍  ELEMENT ANNOTATION",
             font=("Courier New", 13, "bold"),
             bg=BG_PANEL, fg=ACCENT).pack(side="left", padx=16)
    tk.Label(hdr, text="Mouse ile elementleri kare içine alın",
             font=("Courier New", 10),
             bg=BG_PANEL, fg=T_MUT).pack(side="left", padx=4)

    # ── Canvas ──────────────────────────────────────────────────────────────
    cf = tk.Frame(win, bg="#2C2416", padx=2, pady=2)
    cf.pack(padx=16, pady=(10, 6))

    canvas = tk.Canvas(cf, width=disp_w, height=disp_h,
                       cursor="crosshair", highlightthickness=0)
    canvas.pack()

    # Görüntüyü canvas'a yerleştir — referansı canvas objesinde sakla
    tk_img = ImageTk.PhotoImage(pil_disp)
    canvas.tk_img = tk_img          # GC'den koru
    canvas.create_image(0, 0, anchor="nw", image=tk_img, tags="bg")

    # ── Info bar ────────────────────────────────────────────────────────────
    info_var = tk.StringVar(value="0 kare çizildi")
    info_bar = tk.Frame(win, bg=BG_INPUT, height=28)
    info_bar.pack(fill="x", padx=16)
    info_bar.pack_propagate(False)
    tk.Label(info_bar, textvariable=info_var,
             font=("Courier New", 9), bg=BG_INPUT, fg=T_MUT,
             anchor="w").pack(side="left", padx=10)
    tk.Label(info_bar,
             text=f"Ölçek: {scale:.2f}x  |  Orijinal: {orig_w}×{orig_h}px",
             font=("Courier New", 9), bg=BG_INPUT, fg=T_MUT
             ).pack(side="right", padx=10)

    # ── Butonlar ────────────────────────────────────────────────────────────
    btn_frame = tk.Frame(win, bg=BG_MAIN)
    btn_frame.pack(fill="x", padx=16, pady=10)

    left_btns  = tk.Frame(btn_frame, bg=BG_MAIN)
    left_btns.pack(side="left")
    right_btns = tk.Frame(btn_frame, bg=BG_MAIN)
    right_btns.pack(side="right")

    # ── State ────────────────────────────────────────────────────────────────
    rects      = []        # [(rect_id, label_id, orig_box), ...]
    drag_start = [None]
    tmp_rect   = [None]

    def update_info():
        n = len(rects)
        info_var.set(
            "0 kare çizildi" if n == 0
            else f"{n} element işaretlendi  —  Onaylamak için butona bas"
        )
        btn_confirm.configure(state="normal" if n > 0 else "disabled")

    def renumber():
        for i, (_, lid, _) in enumerate(rects):
            canvas.itemconfigure(lid, text=str(i + 1))

    # ── Mouse olayları ───────────────────────────────────────────────────────
    def on_press(e):
        drag_start[0] = (e.x, e.y)
        tmp_rect[0] = canvas.create_rectangle(
            e.x, e.y, e.x, e.y,
            outline=BOX_COLOR, width=BOX_WIDTH, dash=(4, 2))

    def on_drag(e):
        if tmp_rect[0] and drag_start[0]:
            x0, y0 = drag_start[0]
            canvas.coords(tmp_rect[0], x0, y0, e.x, e.y)

    def on_release(e):
        if not drag_start[0]:
            return
        x0, y0 = drag_start[0]
        x1, y1 = e.x, e.y

        if abs(x1 - x0) < 10 or abs(y1 - y0) < 10:
            canvas.delete(tmp_rect[0])
            tmp_rect[0]   = None
            drag_start[0] = None
            return

        canvas.delete(tmp_rect[0])
        tmp_rect[0] = None

        cx0, cx1 = sorted([x0, x1])
        cy0, cy1 = sorted([y0, y1])

        rid = canvas.create_rectangle(
            cx0, cy0, cx1, cy1,
            outline=BOX_COLOR, width=BOX_WIDTH)
        lid = canvas.create_text(
            cx0 + 4, cy0 + 2, anchor="nw",
            text=str(len(rects) + 1),
            fill=BOX_COLOR,
            font=("Courier New", 10, "bold"))

        orig_box = {
            "x1": int(cx0 / scale), "y1": int(cy0 / scale),
            "x2": int(cx1 / scale), "y2": int(cy1 / scale),
        }
        rects.append((rid, lid, orig_box))
        drag_start[0] = None
        update_info()

    canvas.bind("<ButtonPress-1>",   on_press)
    canvas.bind("<B1-Motion>",       on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)

    # ── Kontrol butonları ────────────────────────────────────────────────────
    def undo():
        if not rects:
            return
        rid, lid, _ = rects.pop()
        canvas.delete(rid)
        canvas.delete(lid)
        renumber()
        update_info()

    def clear():
        for rid, lid, _ in rects:
            canvas.delete(rid)
            canvas.delete(lid)
        rects.clear()
        update_info()

    def confirm():
        result.extend([box for _, _, box in rects])
        win.destroy()

    def cancel():
        win.destroy()

    tk.Button(left_btns, text="↩  Geri Al",
              font=("Courier New", 10, "bold"),
              bg=BG_INPUT, fg=T_PRI, relief="flat",
              padx=14, pady=6, cursor="hand2",
              command=undo).pack(side="left", padx=(0, 6))

    tk.Button(left_btns, text="✕  Temizle",
              font=("Courier New", 10, "bold"),
              bg=BG_INPUT, fg=C_ERR, relief="flat",
              padx=14, pady=6, cursor="hand2",
              command=clear).pack(side="left")

    tk.Button(right_btns, text="İptal",
              font=("Courier New", 10, "bold"),
              bg=BG_INPUT, fg=T_MUT, relief="flat",
              padx=14, pady=6, cursor="hand2",
              command=cancel).pack(side="left", padx=(0, 8))

    btn_confirm = tk.Button(
        right_btns,
        text="✓  Onayla  →  Raporu Oluştur",
        font=("Courier New", 11, "bold"),
        bg=C_OK, fg="#FFFFFF", relief="flat",
        padx=18, pady=6, cursor="hand2",
        state="disabled",
        command=confirm)
    btn_confirm.pack(side="left")

    # ── Modal bekleme ────────────────────────────────────────────────────────
    win.transient(parent)
    win.grab_set()
    win.focus_set()

    # Merkeze al
    win.update_idletasks()
    pw = parent.winfo_rootx() + parent.winfo_width()  // 2
    ph = parent.winfo_rooty() + parent.winfo_height() // 2
    win.geometry(f"+{pw - disp_w//2}+{ph - disp_h//2}")

    parent.wait_window(win)

    return result


# ── Standalone test ──────────────────────────────────────────────────────────
if __name__ == "__main__":

    if len(sys.argv) >= 2:
        image_path = sys.argv[1]
    else:
        image_path = "/Users/yunus.sahin/Desktop/kzr_xpath/checkin.png"

    if not os.path.exists(image_path):
        print(f"❌ Dosya bulunamadı: {image_path}")
        sys.exit(1)

    print(f"📂 Açılıyor: {image_path}")

    root = tk.Tk()
    root.title("Test Host")
    root.geometry("1x1+0+0")   # görünmez ama var — Toplevel'e parent lazım

    boxes = open_annotator(root, image_path)

    if boxes:
        print(f"\n✅ {len(boxes)} kare onaylandı:")
        for i, b in enumerate(boxes, 1):
            print(f"   [{i}] x1={b['x1']}  y1={b['y1']}  x2={b['x2']}  y2={b['y2']}")
    else:
        print("\n🚫 İptal edildi veya kare çizilmedi.")

    root.destroy()
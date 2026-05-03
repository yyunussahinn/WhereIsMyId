"""
annotator.py
────────────────────────────────────────────────────────────────
Ekran görüntüsü üzerine mouse ile kırmızı kare çizme penceresi.

v4.4: macOS'ta tk.Button bg rengi sistem tarafından override edildiği için
      Canvas tabanlı renkli butonlar (CBtn) kullanılıyor.

Modül olarak kullanım:
    from annotator import open_annotator
    boxes = open_annotator(parent, image_path)
"""

import tkinter as tk
from PIL import Image, ImageTk
import os
import sys

# ── Renkler ─────────────────────────────────────────────────────────────────
BG_MAIN   = "#F5F0E8"
BG_PANEL  = "#FFFFFF"
BG_INPUT  = "#EDE8DF"
T_MUT     = "#8C7D6A"
BOX_COLOR = "#FF2020"
BOX_WIDTH = 2

# (bg, hover_bg, fg)
BTN_UNDO   = ("#185FA5", "#0C447C", "#FFFFFF")
BTN_CLEAR  = ("#7B1515", "#5a0f0f", "#FFFFFF")
BTN_CANCEL = ("#4A4A4A", "#333333", "#FFFFFF")
BTN_OK_OFF = ("#9E9E9E", "#9E9E9E", "#DDDDDD")  # disabled
BTN_OK_ON  = ("#1a8242", "#145c30", "#FFFFFF")  # enabled

MAX_W = 700
MAX_H = 520


# ── Canvas tabanlı buton sınıfı ───────────────────────────────────────────────
class CBtn:
    """
    macOS Aqua teması tk.Button bg/fg renklerini override eder.
    Canvas + polygon (rounded-rect) ile tamamen özel, her OS'ta renkli buton.
    """

    def __init__(self, parent, text, colors, command,
                 width=120, height=36, font_size=9):
        self._colors  = list(colors)   # [bg, hover, fg]
        self._enabled = True
        self._cmd     = command
        self._w       = width
        self._h       = height

        # parent'ın bg rengini al (canvas şeffaf görünsün)
        try:
            pbg = parent.cget("bg")
        except Exception:
            pbg = BG_MAIN

        self.canvas = tk.Canvas(
            parent,
            width=width, height=height,
            highlightthickness=0,
            bg=pbg,
            bd=0,
        )

        self._rect = self._make_rect(colors[0])
        self._lbl  = self.canvas.create_text(
            width // 2, height // 2,
            text=text,
            fill=colors[2],
            font=("Courier New", font_size, "bold"),
            anchor="center",
        )

        self.canvas.bind("<Enter>",           self._enter)
        self.canvas.bind("<Leave>",           self._leave)
        self.canvas.bind("<ButtonPress-1>",   self._press)
        self.canvas.bind("<ButtonRelease-1>", self._release)

    def _make_rect(self, fill_color):
        w, h, r = self._w, self._h, 7
        # Smooth rounded polygon
        pts = [
            r, 0,    w-r, 0,
            w, 0,    w, r,
            w, h-r,  w, h,
            w-r, h,  r, h,
            0, h,    0, h-r,
            0, r,    0, 0,
            r, 0,
        ]
        return self.canvas.create_polygon(
            pts, smooth=True,
            fill=fill_color, outline="", width=0,
        )

    # ── Durum yönetimi ────────────────────────────────────────────────────────
    def configure(self, state=None, colors=None):
        if colors is not None:
            self._colors = list(colors)
        if state is not None:
            self._enabled = (state == "normal")
        self._refresh()

    def _refresh(self):
        if self._enabled:
            self.canvas.itemconfigure(self._rect, fill=self._colors[0])
            self.canvas.itemconfigure(self._lbl,  fill=self._colors[2])
            self.canvas.configure(cursor="hand2")
        else:
            self.canvas.itemconfigure(self._rect, fill=BTN_OK_OFF[0])
            self.canvas.itemconfigure(self._lbl,  fill=BTN_OK_OFF[2])
            self.canvas.configure(cursor="arrow")

    # ── Hover / tıklama ───────────────────────────────────────────────────────
    def _enter(self, _):
        if self._enabled:
            self.canvas.itemconfigure(self._rect, fill=self._colors[1])

    def _leave(self, _):
        if self._enabled:
            self.canvas.itemconfigure(self._rect, fill=self._colors[0])

    def _press(self, _):
        if self._enabled:
            self.canvas.itemconfigure(self._rect, fill=self._colors[1])

    def _release(self, _):
        if self._enabled:
            self.canvas.itemconfigure(self._rect, fill=self._colors[0])
            self._cmd()

    # ── Layout delegasyonu ────────────────────────────────────────────────────
    def pack(self, **kw):
        self.canvas.pack(**kw)

    def grid(self, **kw):
        self.canvas.grid(**kw)

    def place(self, **kw):
        self.canvas.place(**kw)


# ── Ana fonksiyon ─────────────────────────────────────────────────────────────
def open_annotator(parent, image_path: str) -> list:
    result = []

    # Görüntü yükle
    pil_orig = Image.open(image_path).convert("RGB")
    orig_w, orig_h = pil_orig.size
    scale  = min(MAX_W / orig_w, MAX_H / orig_h, 1.0)
    disp_w = int(orig_w * scale)
    disp_h = int(orig_h * scale)
    pil_disp = pil_orig.resize((disp_w, disp_h), Image.LANCZOS)

    # Pencere
    win = tk.Toplevel(parent)
    win.title("Annotation — Elementleri İşaretle")
    win.configure(bg=BG_MAIN)
    win.resizable(True, True)
    win.protocol("WM_DELETE_WINDOW", win.destroy)

    # Başlık
    hdr = tk.Frame(win, bg=BG_PANEL, height=40)
    hdr.pack(fill="x")
    hdr.pack_propagate(False)
    tk.Label(hdr, text="📍  ELEMENT ANNOTATION",
             font=("Courier New", 11, "bold"),
             bg=BG_PANEL, fg="#000000").pack(side="left", padx=16)
    tk.Label(hdr, text="Mouse ile elementleri kare içine alın",
             font=("Courier New", 9),
             bg=BG_PANEL, fg=T_MUT).pack(side="left", padx=4)

    # Canvas alanı
    canvas_frame = tk.Frame(win, bg="#2C2416")
    canvas_frame.pack(padx=10, pady=(6, 4), fill="both", expand=True)

    v_scroll = tk.Scrollbar(canvas_frame, orient="vertical")
    h_scroll = tk.Scrollbar(canvas_frame, orient="horizontal")
    v_scroll.pack(side="right", fill="y")
    h_scroll.pack(side="bottom", fill="x")

    canvas = tk.Canvas(
        canvas_frame,
        width=min(disp_w, MAX_W), height=min(disp_h, MAX_H),
        cursor="crosshair", highlightthickness=0,
        yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set,
        scrollregion=(0, 0, disp_w, disp_h),
    )
    canvas.pack(side="left", fill="both", expand=True)
    v_scroll.config(command=canvas.yview)
    h_scroll.config(command=canvas.xview)

    tk_img = ImageTk.PhotoImage(pil_disp)
    canvas.tk_img = tk_img
    canvas.create_image(0, 0, anchor="nw", image=tk_img)

    # Info bar
    info_var = tk.StringVar(value="0 kare çizildi")
    info_bar = tk.Frame(win, bg=BG_INPUT, height=24)
    info_bar.pack(fill="x", padx=10)
    info_bar.pack_propagate(False)
    tk.Label(info_bar, textvariable=info_var,
             font=("Courier New", 8), bg=BG_INPUT, fg=T_MUT,
             anchor="w").pack(side="left", padx=8)
    tk.Label(info_bar,
             text=f"Ölçek: {scale:.2f}x  |  Orijinal: {orig_w}×{orig_h}px",
             font=("Courier New", 8), bg=BG_INPUT, fg=T_MUT,
             ).pack(side="right", padx=8)

    # Buton çubuğu
    btn_bar = tk.Frame(win, bg=BG_MAIN)
    btn_bar.pack(fill="x", padx=10, pady=8)

    left_f  = tk.Frame(btn_bar, bg=BG_MAIN)
    left_f.pack(side="left")
    right_f = tk.Frame(btn_bar, bg=BG_MAIN)
    right_f.pack(side="right")

    # ── State ─────────────────────────────────────────────────────────────────
    rects      = []
    drag_start = [None]
    tmp_rect   = [None]

    def update_info():
        n = len(rects)
        info_var.set(
            "0 kare çizildi" if n == 0
            else f"{n} element işaretlendi  —  Onaylamak için butona bas"
        )
        if n > 0:
            btn_confirm.configure(state="normal", colors=BTN_OK_ON)
        else:
            btn_confirm.configure(state="disabled", colors=BTN_OK_OFF)

    def renumber():
        for i, (_, lid, _) in enumerate(rects):
            canvas.itemconfigure(lid, text=str(i + 1))

    # Mouse olayları
    def on_press(e):
        drag_start[0] = (canvas.canvasx(e.x), canvas.canvasy(e.y))
        tmp_rect[0] = canvas.create_rectangle(
            *drag_start[0], *drag_start[0],
            outline=BOX_COLOR, width=BOX_WIDTH, dash=(4, 2))

    def on_drag(e):
        if tmp_rect[0] and drag_start[0]:
            x0, y0 = drag_start[0]
            canvas.coords(tmp_rect[0], x0, y0,
                          canvas.canvasx(e.x), canvas.canvasy(e.y))

    def on_release(e):
        if not drag_start[0]:
            return
        x0, y0 = drag_start[0]
        x1, y1 = canvas.canvasx(e.x), canvas.canvasy(e.y)
        if abs(x1 - x0) < 10 or abs(y1 - y0) < 10:
            canvas.delete(tmp_rect[0])
            tmp_rect[0] = drag_start[0] = None
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
            font=("Courier New", 9, "bold"))
        rects.append((rid, lid, {
            "x1": int(cx0 / scale), "y1": int(cy0 / scale),
            "x2": int(cx1 / scale), "y2": int(cy1 / scale),
        }))
        drag_start[0] = None
        update_info()

    canvas.bind("<ButtonPress-1>",   on_press)
    canvas.bind("<B1-Motion>",       on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    canvas.bind("<MouseWheel>",
                lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

    # Aksiyonlar
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
        result.extend(box for _, _, box in rects)
        win.destroy()

    def cancel():
        win.destroy()

    # Butonlar
    CBtn(left_f, "↩  Geri Al", BTN_UNDO, undo,
         width=130, height=40, font_size=9).pack(side="left", padx=(8, 8))
    CBtn(left_f, "✕  Temizle", BTN_CLEAR, clear,
         width=130, height=40, font_size=9).pack(side="left", padx=(8, 8))

    CBtn(left_f, "İptal", BTN_CANCEL, cancel,
         width=90, height=40, font_size=9).pack(side="left", padx=(8, 8))

    btn_confirm = CBtn(left_f, "✓  Onayla  →  Raporu Oluştur",
                       BTN_OK_OFF, confirm,
                       width=260, height=40, font_size=10)
    btn_confirm.pack(side="left", padx=(8, 0))
    btn_confirm.configure(state="disabled", colors=BTN_OK_OFF)
    btn_confirm.pack(side="left")

    # Pencere boyutu
    extra_h = 40 + 24 + 60 + 20
    win_w   = min(disp_w, MAX_W) + 30
    win_h   = min(disp_h, MAX_H) + extra_h
    win.geometry(f"{win_w}x{win_h}")
    win.minsize(700, 650)

    win.transient(parent)
    win.grab_set()
    win.focus_set()

    win.update_idletasks()
    pw = parent.winfo_rootx() + parent.winfo_width()  // 2
    ph = parent.winfo_rooty() + parent.winfo_height() // 2
    win.geometry(f"{win_w}x{win_h}+{pw - win_w//2}+{ph - win_h//2}")

    parent.wait_window(win)
    return result


# ── Standalone test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) >= 2 else "/tmp/test.png"
    if not os.path.exists(path):
        print(f"❌ Dosya bulunamadı: {path}")
        sys.exit(1)
    root = tk.Tk()
    root.title("Test")
    root.geometry("1x1+0+0")
    boxes = open_annotator(root, path)
    print(f"✅ {len(boxes)} kare" if boxes else "🚫 İptal")
    root.destroy()
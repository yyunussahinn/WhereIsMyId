"""
Where is My Id — GUI  v4.0
──────────────────────────────────────────────────────────────
Özellikler:
  1. Platform toggle  → yalnızca ilgili ayar paneli görünür
                        (Blacklist sadece Android'de)
  2. Build Summary    → dosya gezginiyle Excel seç + ayrı Çalıştır butonu
  3. Branding         → "Where is My Id"
  4. Profil sistemi   → iOS / Android için ayrı adlandırılmış profil
                        (kaydet / yeni / sil)
  5. Sayfa adı        → footer'daki kutucuğa önceden girilir,
                        script başladığında otomatik gönderilir
  7. Profil isimleri  → PIA iOS, KZR Android vb.

Gereksinimler:
  pip install customtkinter pillow
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import subprocess, threading, sys, os, json
from datetime import datetime

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── Palet ────────────────────────────────────────────────────────────────────
ACCENT        = "#000000"
ACCENT_DK     = "#D4A820"
ACCENT_IOS    = "#185FA5"
ACCENT_IOS_DK = "#0C447C"
BG_MAIN       = "#F5F0E8"
BG_PANEL      = "#FFFFFF"
BG_CARD       = "#F5F0E8"
BG_INPUT      = "#EDE8DF"
T_PRI         = "#2C2416"
T_MUT         = "#8C7D6A"
C_OK          = "#2D6A2D"
C_ERR         = "#A32020"
C_WRN         = "#8C6A10"
C_INF         = "#185FA5"

# ── Fontlar ──────────────────────────────────────────────────────────────────
FT  = ("Courier New", 18, "bold")
FL  = ("Courier New", 11, "bold")
FS  = ("Courier New", 10)
FLG = ("Courier New", 10)
FB  = ("Courier New",  9, "bold")

_BASE       = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(_BASE, "gui_config.json")

# ── Varsayılan profil verileri ────────────────────────────────────────────────
_D_IOS = {
    "device_name": "iPhone 16", "platform_version": "18.6",
    "bundle_id":   "test.com.hitit.pia",
    "udid":        "AD21A917-5271-4DF1-8C5D-E64A0DE8EAD9",
}
_D_AND = {
    "device_name":  "ce04171418dee0010c", "platform_version": "9",
    "app_package":  "test.com.piac.thepiaapp.android",
    "app_activity": "com.piamobile.MainActivity",
}
DEFAULT_CFG = {
    "platform": "ios", "output_format": "word+excel",
    "output_dir": "", "appium_server": "http://127.0.0.1:4723",
    "document_sections": ["unique", "undefined", "duplicate", "missing"],
    "blacklist_ids": ["statusBarBackground","content","action_bar_root","navigationBarBackground"],
    "ios_profiles":           {"PIA iOS":     _D_IOS.copy()},
    "android_profiles":       {"PIA Android": _D_AND.copy()},
    "active_ios_profile":     "PIA iOS",
    "active_android_profile": "PIA Android",
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            cfg = {**DEFAULT_CFG, **data}
            cfg.setdefault("ios_profiles",     {"PIA iOS":     _D_IOS.copy()})
            cfg.setdefault("android_profiles", {"PIA Android": _D_AND.copy()})
            return cfg
        except Exception:
            pass
    return json.loads(json.dumps(DEFAULT_CFG))


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def write_config_py(cfg, path):
    platform = cfg["platform"]
    if platform == "ios":
        pname = cfg.get("active_ios_profile", "")
        p = cfg["ios_profiles"].get(pname, _D_IOS)
        plat = (
            'IOS = {\n'
            f'    "device_name":      "{p["device_name"]}",\n'
            f'    "platform_version": "{p["platform_version"]}",\n'
            f'    "bundle_id":        "{p["bundle_id"]}",\n'
            f'    "udid":             "{p["udid"]}",\n'
            '    "no_reset":         True,\n}\nANDROID = {}\n'
        )
    else:
        pname = cfg.get("active_android_profile", "")
        p = cfg["android_profiles"].get(pname, _D_AND)
        plat = (
            'ANDROID = {\n'
            f'    "device_name":      "{p["device_name"]}",\n'
            f'    "platform_version": "{p["platform_version"]}",\n'
            f'    "app_package":      "{p["app_package"]}",\n'
            f'    "app_activity":     "{p["app_activity"]}",\n'
            '    "no_reset":         True,\n}\nIOS = {}\n'
        )
    bl  = json.dumps(cfg.get("blacklist_ids", []))
    sec = json.dumps(cfg.get("document_sections", []))
    od  = cfg.get("output_dir", "").replace("\\", "/")
    txt = (
        f'# WHERE IS MY ID — config.py  ({datetime.now():%d.%m.%Y %H:%M})\n'
        f'PLATFORM = "{platform}"\nBLACKLIST_IDS = {bl}\n'
        f'OUTPUT_FORMAT = "{cfg["output_format"]}"\nDOCUMENT_SECTIONS = {sec}\n'
        f'OUTPUT_DIR = "{od}"\nAPPIUM_SERVER = "{cfg["appium_server"]}"\n{plat}'
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(txt)


# ════════════════════════════════════════════════════════════════════════════
#  YARDIMCI WİDGET'LAR
# ════════════════════════════════════════════════════════════════════════════

class SecHdr(ctk.CTkFrame):
    """İnce çizgili bölüm başlığı."""
    def __init__(self, parent, title, color=None, **kw):
        super().__init__(parent, fg_color="transparent", **kw)
        c = color or ACCENT
        ctk.CTkFrame(self, height=1, fg_color=c, corner_radius=0).pack(
            side="left", fill="x", expand=True, pady=8)
        ctk.CTkLabel(self, text=f"  {title}  ", font=FB,
                     text_color=c, fg_color="transparent").pack(side="left")
        ctk.CTkFrame(self, height=1, fg_color=c, corner_radius=0).pack(
            side="left", fill="x", expand=True, pady=8)


class LE(ctk.CTkFrame):
    """Label + Entry yatay satırı, opsiyonel klasör/dosya browse."""
    def __init__(self, parent, label, var, ph="",
                 browse_dir=False, browse_file=False, **kw):
        super().__init__(parent, fg_color="transparent", **kw)
        ctk.CTkLabel(self, text=label, font=FS, text_color=T_MUT,
                     width=155, anchor="w").pack(side="left")
        ctk.CTkEntry(self, textvariable=var, placeholder_text=ph,
                     fg_color=BG_INPUT, border_color="#D8D0C0",
                     text_color=T_PRI, font=FS, corner_radius=6
                     ).pack(side="left", fill="x", expand=True, padx=(4, 0))
        if browse_dir:
            ctk.CTkButton(self, text="📁", width=30, height=26,
                          fg_color=BG_CARD, hover_color=BG_INPUT,
                          font=FS, corner_radius=6,
                          command=lambda: self._pick(var, "dir")
                          ).pack(side="left", padx=(4, 0))
        if browse_file:
            ctk.CTkButton(self, text="📂", width=30, height=26,
                          fg_color=BG_CARD, hover_color=BG_INPUT,
                          font=FS, corner_radius=6,
                          command=lambda: self._pick(var, "file")
                          ).pack(side="left", padx=(4, 0))

    def _pick(self, var, kind):
        p = (filedialog.askdirectory() if kind == "dir"
             else filedialog.askopenfilename(
                 filetypes=[("Excel", "*.xlsx *.xls"), ("Tümü", "*.*")]))
        if p:
            var.set(p)


class Badge(ctk.CTkLabel):
    _S = {
        "idle":    (ACCENT_DK, "○  HAZIR"),
        "running": (ACCENT_DK, "◉  ÇALIŞIYOR"),
        "ok":      ("green", "✓  TAMAMLANDI"),
        "error":   ("red", "✗  HATA"),
    }
    def __init__(self, parent, **kw):
        super().__init__(parent, font=FB, corner_radius=8, padx=12, pady=4, **kw)
        self.set("idle")

    def set(self, s):
        col, txt = self._S.get(s, self._S["idle"])
        self.configure(fg_color=col, text=txt, text_color="#FFFFFF")


# ════════════════════════════════════════════════════════════════════════════
#  PROFİL PANELİ
# ════════════════════════════════════════════════════════════════════════════

class ProfilePanel(ctk.CTkFrame):
    """Adlandırılmış profil kaydet/yükle/sil paneli."""

    def __init__(self, parent, platform, profiles, active, on_change=None, **kw):
        super().__init__(parent, fg_color="transparent", **kw)
        self.platform   = platform
        self._profiles  = dict(profiles)
        self._active    = (active if active in profiles
                           else (list(profiles)[0] if profiles else ""))
        self._on_change = on_change

        self.v_profile = tk.StringVar(value=self._active)
        self.v_device  = tk.StringVar()
        self.v_version = tk.StringVar()
        if platform == "ios":
            self.v_bundle = tk.StringVar()
            self.v_udid   = tk.StringVar()
        else:
            self.v_package  = tk.StringVar()
            self.v_activity = tk.StringVar()

        self._build()
        self._load(self._active)

    def _build(self):
        col = ACCENT_IOS if self.platform == "ios" else ACCENT

        # Profil satırı
        row = ctk.CTkFrame(self, fg_color="#EDE8DF", corner_radius=8)
        row.pack(fill="x", padx=14, pady=(0, 4))
        ctk.CTkLabel(row, text="Profil:", font=FS,
                     text_color=T_MUT, width=50, anchor="w").pack(side="left", padx=(10,0), pady=8)
        self.dd = ctk.CTkOptionMenu(
            row, values=self._names(), variable=self.v_profile,
            fg_color=BG_INPUT, button_color=BG_CARD,
            button_hover_color=BG_PANEL, text_color=T_PRI,
            font=FS, dropdown_fg_color=BG_CARD,
            corner_radius=6, command=self._select, width=200)
        self.dd.pack(side="left", padx=(4, 8), pady=8)
        for txt, tc, cb in [("💾", col, self._save),
                             ("＋",   C_OK,  self._new),
                             ("✕",     C_ERR, self._delete)]:
            ctk.CTkButton(row, text=txt, width=40, height=26,
                          fg_color=BG_INPUT, hover_color=BG_PANEL,
                          text_color=tc, font=FS, corner_radius=6,
                          command=cb).pack(side="left", padx=(0, 4), pady=8)

        # Alan girişleri
        ff = ctk.CTkFrame(self, fg_color="transparent")
        ff.pack(fill="x")
        if self.platform == "ios":
            for lbl, var, ph in [
                ("Device Name",      self.v_device,  "iPhone 16"),
                ("Platform Version", self.v_version, "18.6"),
                ("Bundle ID",        self.v_bundle,  "com.app.bundle"),
                ("UDID",             self.v_udid,    "AD21A917-..."),
            ]:
                LE(ff, lbl, var, ph).pack(fill="x", padx=14, pady=2)
        else:
            for lbl, var, ph in [
                ("Device Name",      self.v_device,   "device_serial"),
                ("Platform Version", self.v_version,  "9"),
                ("App Package",      self.v_package,  "com.app.package"),
                ("App Activity",     self.v_activity, "com.app.MainActivity"),
            ]:
                LE(ff, lbl, var, ph).pack(fill="x", padx=14, pady=2)

    def _names(self):
        return list(self._profiles.keys()) or ["(boş)"]

    def _load(self, name):
        d = self._profiles.get(name, {})
        self.v_device.set(d.get("device_name", ""))
        self.v_version.set(d.get("platform_version", ""))
        if self.platform == "ios":
            self.v_bundle.set(d.get("bundle_id", ""))
            self.v_udid.set(d.get("udid", ""))
        else:
            self.v_package.set(d.get("app_package", ""))
            self.v_activity.set(d.get("app_activity", ""))

    def _to_dict(self):
        if self.platform == "ios":
            return {"device_name": self.v_device.get(),
                    "platform_version": self.v_version.get(),
                    "bundle_id":  self.v_bundle.get(),
                    "udid":       self.v_udid.get()}
        return {"device_name":  self.v_device.get(),
                "platform_version": self.v_version.get(),
                "app_package":  self.v_package.get(),
                "app_activity": self.v_activity.get()}

    def _notify(self):
        if self._on_change:
            self._on_change(self._profiles, self._active)

    def _select(self, name):
        self._active = name
        self._load(name)
        self._notify()

    def _save(self):
        name = self.v_profile.get()
        if not name or name == "(boş)":
            return
        self._profiles[name] = self._to_dict()
        self._active = name
        self.dd.configure(values=self._names())
        self._notify()
        messagebox.showinfo("Kaydedildi", f'"{name}" profili kaydedildi.')

    def _new(self):
        name = simpledialog.askstring(
            "Yeni Profil", "Profil adı girin\n(örnek: PIA iOS, KZR Android):",
            parent=self.winfo_toplevel())
        if not name or not name.strip():
            return
        name = name.strip()
        if name in self._profiles:
            messagebox.showwarning("Uyarı", f'"{name}" zaten mevcut.')
            return
        self._profiles[name] = self._to_dict()
        self._active = name
        self.v_profile.set(name)
        self.dd.configure(values=self._names())
        self._notify()

    def _delete(self):
        name = self.v_profile.get()
        if len(self._profiles) <= 1:
            messagebox.showwarning("Uyarı", "En az bir profil kalmalı.")
            return
        if not messagebox.askyesno("Sil", f'"{name}" silinsin mi?'):
            return
        del self._profiles[name]
        first = list(self._profiles)[0]
        self._active = first
        self.v_profile.set(first)
        self.dd.configure(values=self._names())
        self._load(first)
        self._notify()

    def get_active(self): return self._active
    def get_data(self):   return self._profiles.get(self._active, {})
    def get_all(self):    return self._profiles


# ════════════════════════════════════════════════════════════════════════════
#  ANA UYGULAMA
# ════════════════════════════════════════════════════════════════════════════

class App(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        self._proc   = None
        self._pn_ev  = threading.Event()
        self._pn_ans = ""
        self._ow_ev  = threading.Event()  # overwrite confirm
        self._ow_ans = True               # default

        self.title("Where is My Id")
        self.geometry("1160x840")
        self.minsize(980, 680)
        self.configure(fg_color="#F5F0E8")

        self._mk_vars()
        self._mk_ui()
        self._apply_cfg()

    # ── Tkinter değişkenleri ─────────────────────────────────────────────────
    def _mk_vars(self):
        self.v_platform      = tk.StringVar(value="ios")
        self.v_out_fmt       = tk.StringVar(value="word+excel")
        self.v_out_dir       = tk.StringVar()
        self.v_appium        = tk.StringVar()
        self.v_blacklist     = tk.StringVar()
        self.v_summary_xl    = tk.StringVar()
        self.v_sec_unique    = tk.BooleanVar(value=True)
        self.v_sec_undefined = tk.BooleanVar(value=True)
        self.v_sec_duplicate = tk.BooleanVar(value=True)
        self.v_sec_missing   = tk.BooleanVar(value=True)

    def _apply_cfg(self):
        c = self.cfg
        self.v_platform.set(c["platform"])
        self.v_out_fmt.set(c["output_format"])
        self.v_out_dir.set(c["output_dir"])
        self.v_appium.set(c["appium_server"])
        self.v_blacklist.set(", ".join(c.get("blacklist_ids", [])))
        secs = c.get("document_sections", [])
        self.v_sec_unique.set("unique" in secs)
        self.v_sec_undefined.set("undefined" in secs)
        self.v_sec_duplicate.set("duplicate" in secs)
        self.v_sec_missing.set("missing" in secs)
        # Platform toggle AFTER UI is built
        self._toggle_platform(c["platform"], init=True)

    # ── UI inşa ──────────────────────────────────────────────────────────────
    def _mk_ui(self):
        self._mk_header()
        self._mk_footer()   # pack(side=bottom) → önce footer
        self._mk_body()

    def _mk_header(self):
        hdr = ctk.CTkFrame(self, fg_color="white", corner_radius=0, height=54)
        hdr.pack(fill="x", side="top")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="WHERE IS MY ID",
                     font=FT, text_color="black").pack(side="left", padx=20)
        ctk.CTkLabel(hdr, text="mobile accessibility reporter",
                     font=FS, text_color="black").pack(side="left", padx=4)
        self.badge = Badge(hdr)
        self.badge.pack(side="right", padx=20)
        ctk.CTkLabel(hdr, text="v4.0", font=FB, text_color="black").pack(side="right", padx=4)

    def _mk_footer(self):
        foot = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=0, height=66)
        foot.pack(fill="x", side="bottom")
        foot.pack_propagate(False)

        # Sol: aktif profil etiketi + CALISTIR / DURDUR
        lf = ctk.CTkFrame(foot, fg_color="transparent")
        lf.pack(side="left", padx=(12, 0), pady=10)

        self.lbl_prof = ctk.CTkLabel(lf, text="", font=FS, text_color=T_MUT)
        self.lbl_prof.pack(side="left", padx=(4, 12))

        self.btn_run = ctk.CTkButton(
            lf, text="▶  CALISTIR", font=FL, height=44, width=150,
            fg_color="#1a8242",hover_color="#1a8242",
            text_color="#FFFFFF", corner_radius=8,
            command=self._run_checker)
        self.btn_run.pack(side="left", padx=(0, 6))

        self.btn_stop = ctk.CTkButton(
            lf, text="■  DURDUR", font=FL, height=44, width=120,
            fg_color="#7B1515", hover_color="#7B1515",
            text_color="#FFFFFF", corner_radius=8,
            command=self._stop_proc)
        self.btn_stop.pack(side="left")
        self.btn_stop.configure(state="disabled")

        # Sağ: Excel seç + Build Summary
        rf = ctk.CTkFrame(foot, fg_color="transparent")
        rf.pack(side="right", padx=12, pady=10)

        sb = ctk.CTkFrame(rf, fg_color="#F5F0E8", corner_radius=8,
                          border_width=1, border_color="#D8D0C0")
        sb.pack(side="right")
        ctk.CTkLabel(sb, text="Excel:", font=FS,
                     text_color="#8C7D6A").pack(side="left", padx=(10, 4), pady=8)
        self.xl_entry = ctk.CTkEntry(
            sb, textvariable=self.v_summary_xl,
            placeholder_text="dosya secin...",
            fg_color="#EDE8DF", border_color="#D8D0C0",
            text_color="#1a8242", font=FS, width=220, corner_radius=6)
        self.xl_entry.pack(side="left", pady=8)
        ctk.CTkButton(sb, text="📂", width=30, height=28,
                      fg_color="#EDE8DF", hover_color="#D8D0C0",
                      font=FS, corner_radius=6,
                      command=self._pick_excel).pack(side="left", padx=(4, 4), pady=8)
        self.btn_summary = ctk.CTkButton(
            sb, text="📊  Merge Sheets", font=FL, height=36, width=155,
            fg_color="#1a8242", hover_color="#1a8242",
            text_color="#FFFFFF", corner_radius=6,
            command=self._run_summary)
        self.btn_summary.pack(side="left", padx=(0, 8), pady=8)

    def _mk_body(self):
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=12, pady=(8, 4))
        body.columnconfigure(0, weight=0)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left = ctk.CTkScrollableFrame(body, width=430, fg_color="#FFFFFF",
                                       corner_radius=10,
                                       scrollbar_button_color="#D8D0C0")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self._mk_config(left)

        right = ctk.CTkFrame(body, fg_color="#F5F0E8", corner_radius=10)
        right.grid(row=0, column=1, sticky="nsew")
        self._mk_log(right)

    # ── Config paneli ─────────────────────────────────────────────────────────
    def _mk_config(self, p):
        pad = dict(padx=14, pady=3)

        # Platform toggle
        SecHdr(p, "PLATFORM").pack(fill="x", **pad)
        pf = ctk.CTkFrame(p, fg_color="#EDE8DF", corner_radius=8)
        pf.pack(fill="x", padx=14, pady=(0, 8))
        self.btn_ios = ctk.CTkButton(
            pf, text="🍎  iOS", font=FL, height=38, corner_radius=7,
            fg_color=ACCENT_IOS, hover_color=ACCENT_IOS_DK, text_color=BG_MAIN,
            command=lambda: self._toggle_platform("ios"))
        self.btn_ios.pack(side="left", expand=True, fill="x", padx=(6, 3), pady=6)
        self.btn_and = ctk.CTkButton(
            pf, text="🤖  Android", font=FL, height=38, corner_radius=7,
            fg_color=BG_INPUT, hover_color="#E8E0D0", text_color=T_MUT,
            command=lambda: self._toggle_platform("android"))
        self.btn_and.pack(side="left", expand=True, fill="x", padx=(3, 6), pady=6)

        # Genel ayarlar
        SecHdr(p, "GENEL AYARLAR").pack(fill="x", **pad)
        LE(p, "Appium Server", self.v_appium,
           "http://127.0.0.1:4723").pack(fill="x", padx=14, pady=3)
        LE(p, "Cikti Klasoru", self.v_out_dir,
           "/path/to/output", browse_dir=True).pack(fill="x", padx=14, pady=3)
        fr = ctk.CTkFrame(p, fg_color="transparent")
        fr.pack(fill="x", padx=14, pady=3)
        ctk.CTkLabel(fr, text="Cikti Formati", font=FS,
                     text_color=T_MUT, width=155, anchor="w").pack(side="left")
        ctk.CTkOptionMenu(
            fr, values=["word+excel", "excel", "word"],
            variable=self.v_out_fmt,
            fg_color=BG_INPUT, button_color=BG_CARD,
            button_hover_color=BG_PANEL, text_color=T_PRI,
            font=FS, dropdown_fg_color=BG_CARD, corner_radius=6
        ).pack(side="left", fill="x", expand=True, padx=(4, 0))

        # Rapor bölümleri
        SecHdr(p, "RAPOR BOLUMLERI").pack(fill="x", **pad)
        sf = ctk.CTkFrame(p, fg_color="#EDE8DF", corner_radius=8)
        sf.pack(fill="x", padx=14, pady=(0, 8))
        for lbl, var, col in [
            ("Unique ID",    self.v_sec_unique,    C_OK),
            ("Undefined ID", self.v_sec_undefined, C_WRN),
            ("Duplicate",    self.v_sec_duplicate, "#C8A060"),
            ("Missing ID",   self.v_sec_missing,   C_ERR),
        ]:
            ctk.CTkCheckBox(sf, text=lbl, variable=var, font=FS,
                            text_color=T_PRI, fg_color="white", hover_color="white",
                            checkmark_color="#1a8242", border_color="#B0A898"
                            ).pack(anchor="w", padx=12, pady=4)

        # iOS profil paneli
        self.ios_hdr = SecHdr(p, "IOS AYARLARI", color=ACCENT)
        self.ios_hdr.pack(fill="x", **pad)
        self.ios_panel = ProfilePanel(
            p, "ios",
            profiles=self.cfg.get("ios_profiles", {"PIA iOS": _D_IOS.copy()}),
            active=self.cfg.get("active_ios_profile", "PIA iOS"),
            on_change=self._ios_changed)
        self.ios_panel.pack(fill="x", pady=(0, 6))

        # Android profil paneli
        self.and_hdr = SecHdr(p, "ANDROID AYARLARI", color=ACCENT)
        self.and_hdr.pack(fill="x", **pad)
        self.and_panel = ProfilePanel(
            p, "android",
            profiles=self.cfg.get("android_profiles", {"PIA Android": _D_AND.copy()}),
            active=self.cfg.get("active_android_profile", "PIA Android"),
            on_change=self._and_changed)
        self.and_panel.pack(fill="x", pady=(0, 6))

        # Blacklist (sadece Android'de görünür)
        self.bl_hdr = SecHdr(p, "BLACKLIST ID'LER")
        self.bl_hdr.pack(fill="x", **pad)
        self.bl_frame = ctk.CTkFrame(p, fg_color="transparent")
        self.bl_frame.pack(fill="x", padx=14, pady=(0, 10))
        ctk.CTkLabel(self.bl_frame, text="Virgülle ayir:",
                     font=FS, text_color=T_MUT).pack(anchor="w")
        ctk.CTkEntry(self.bl_frame, textvariable=self.v_blacklist,
                     fg_color=BG_INPUT, border_color="#D8D0C0",
                     text_color=T_PRI, font=FS, corner_radius=6
                     ).pack(fill="x", pady=(2, 0))

    # ── Log paneli ────────────────────────────────────────────────────────────
    def _mk_log(self, p):
        p.rowconfigure(1, weight=1)
        p.rowconfigure(2, weight=0)
        p.columnconfigure(0, weight=1)
        hdr = ctk.CTkFrame(p, fg_color="white", corner_radius=0, height=36)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        ctk.CTkLabel(hdr, text="KONSOL CIKTISI",
                     font=FB, text_color="green").pack(side="left", padx=14)
        ctk.CTkButton(hdr, text="Temizle", font=FS, width=70, height=24,
                      fg_color="#7B1515", hover_color="#7B1515",
                      text_color="white", corner_radius=6,
                      command=self._clear_log).pack(side="right", padx=10, pady=5)
        self.log_box = ctk.CTkTextbox(
            p, fg_color="#FAFAF7", text_color=T_PRI,
            font=FLG, corner_radius=0, wrap="word",
            scrollbar_button_color="#D8D0C0")
        self.log_box.grid(row=1, column=0, sticky="nsew")
        for tag, col in [("ok", C_OK), ("err", C_ERR),
                          ("warn", C_WRN), ("info", C_INF), ("dim", T_MUT)]:
            self.log_box._textbox.tag_config(tag, foreground=col)

        # Sayfa adi input frame (runtime gosterilir)
        self.page_input_frame = ctk.CTkFrame(p, fg_color=BG_CARD, corner_radius=0, height=50)
        self.page_input_frame.grid(row=2, column=0, sticky="ew")
        self.page_input_frame.grid_propagate(False)
        self.page_input_frame.grid_remove()   # baslangicta gizli
        p.rowconfigure(2, weight=0)

        ctk.CTkLabel(self.page_input_frame, text="Sayfa adi:",
                     font=FL, text_color="black").pack(side="left", padx=(14,6), pady=10)
        self.v_page = tk.StringVar()
        pe = ctk.CTkEntry(self.page_input_frame, textvariable=self.v_page,
                          placeholder_text="login, book_flight",
                          fg_color=BG_INPUT, border_color="green",
                          text_color=T_PRI, font=FL, width=200, corner_radius=6)
        pe.pack(side="left", pady=10)
        pe.bind("<Return>", lambda e: self._submit_page())
        ctk.CTkButton(self.page_input_frame, text="Gonder",
                      font=FL, height=32, width=90,
                      fg_color="green", hover_color="green",
                      text_color=BG_MAIN, corner_radius=6,
                      command=self._submit_page).pack(side="left", padx=10, pady=10)

        # Uzerine yazma onay frame (runtime gosterilir)
        self.ow_frame = ctk.CTkFrame(p, fg_color="#FEF6E4", corner_radius=0, height=50)
        self.ow_frame.grid(row=3, column=0, sticky="ew")
        self.ow_frame.grid_propagate(False)
        self.ow_frame.grid_remove()
        p.rowconfigure(3, weight=0)
        self.ow_label = ctk.CTkLabel(self.ow_frame, text="",
                                      font=FL, text_color="#8C6A10")
        self.ow_label.pack(side="left", padx=(14, 12), pady=10)
        ctk.CTkButton(self.ow_frame, text="✓  Evet (Uzerine Yaz)",
                      font=FL, height=32, width=190,
                      fg_color="#2D6A2D", hover_color="#2D6A2D",
                      text_color="white", corner_radius=6,
                      command=lambda: self._submit_overwrite(True)
                      ).pack(side="left", pady=10)
        ctk.CTkButton(self.ow_frame, text="✗  Hayir (Iptal)",
                      font=FL, height=32, width=150,
                      fg_color="#A32020", hover_color="#A32020",
                      text_color="white", corner_radius=6,
                      command=lambda: self._submit_overwrite(False)
                      ).pack(side="left", padx=(8, 0), pady=10)

    # ── Platform toggle ───────────────────────────────────────────────────────
    def _toggle_platform(self, pf, init=False):
        self.v_platform.set(pf)
        if pf == "ios":
            self.btn_ios.configure(fg_color=ACCENT_IOS, text_color=BG_MAIN,
                                   hover_color=ACCENT_IOS_DK)
            self.btn_and.configure(fg_color=BG_INPUT,   text_color=T_MUT,
                                   hover_color="#E8E0D0")
            if not init:
                self.ios_hdr.pack(fill="x", padx=14, pady=3)
                self.ios_panel.pack(fill="x", pady=(0, 6))
            self.and_hdr.pack_forget()
            self.and_panel.pack_forget()
            self.bl_hdr.pack_forget()
            self.bl_frame.pack_forget()
        else:
            self.btn_and.configure(fg_color=ACCENT_DK,    text_color=BG_MAIN,
                                   hover_color=ACCENT_DK)
            self.btn_ios.configure(fg_color=BG_INPUT,  text_color=T_MUT,
                                   hover_color="#E8E0D0")
            self.ios_hdr.pack_forget()
            self.ios_panel.pack_forget()
            if not init:
                self.and_hdr.pack(fill="x", padx=14, pady=3)
                self.and_panel.pack(fill="x", pady=(0, 6))
                self.bl_hdr.pack(fill="x", padx=14, pady=3)
                self.bl_frame.pack(fill="x", padx=14, pady=(0, 10))
        self._upd_label()

    def _ios_changed(self, profiles, active):
        self.cfg["ios_profiles"] = profiles
        self.cfg["active_ios_profile"] = active
        self._upd_label()

    def _and_changed(self, profiles, active):
        self.cfg["android_profiles"] = profiles
        self.cfg["active_android_profile"] = active
        self._upd_label()

    def _upd_label(self):
        pf = self.v_platform.get()
        if pf == "ios":
            self.lbl_prof.configure(
                text=f"iOS  |  {self.ios_panel.get_active()}", text_color=ACCENT_IOS)
        else:
            self.lbl_prof.configure(
                text=f"Android  |  {self.and_panel.get_active()}", text_color=ACCENT)

    # ── Log yardımcıları ──────────────────────────────────────────────────────
    def _log(self, text, tag=""):
        def _d():
            self.log_box.configure(state="normal")
            ts = datetime.now().strftime("%H:%M:%S")
            self.log_box._textbox.insert("end", f"[{ts}] {text}\n", tag or "")
            self.log_box._textbox.see("end")
            self.log_box.configure(state="disabled")
        self.after(0, _d)

    def _clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def _classify(self, line):
        l = line.lower()
        if any(k in l for k in ("kaydedildi", "tamamlandi", "tamamlandt")): return "ok"
        if any(k in l for k in ("hata", "error", "traceback", "exception", "failed")): return "err"
        if any(k in l for k in ("warning", "uyar")): return "warn"
        if any(k in l for k in ("driver", "appium", "baslatilyior", "baslatil")): return "info"
        return ""

    # ── Config toplama / doğrulama ────────────────────────────────────────────
    def _collect(self):
        secs = [k for k, v in [("unique",    self.v_sec_unique),
                                 ("undefined", self.v_sec_undefined),
                                 ("duplicate", self.v_sec_duplicate),
                                 ("missing",   self.v_sec_missing)] if v.get()]
        bl = [x.strip() for x in self.v_blacklist.get().split(",") if x.strip()]
        return {
            "platform":               self.v_platform.get(),
            "output_format":          self.v_out_fmt.get(),
            "output_dir":             self.v_out_dir.get(),
            "appium_server":          self.v_appium.get(),
            "document_sections":      secs,
            "blacklist_ids":          bl,
            "ios_profiles":           self.ios_panel.get_all(),
            "active_ios_profile":     self.ios_panel.get_active(),
            "android_profiles":       self.and_panel.get_all(),
            "active_android_profile": self.and_panel.get_active(),
        }

    def _validate(self, cfg):
        if not cfg["output_dir"]:         return "Cikti klasoru bos olamaz."
        if not cfg["document_sections"]:  return "En az bir rapor bolumu secilmeli."
        if cfg["platform"] == "ios":
            if not cfg["ios_profiles"].get(
                    cfg["active_ios_profile"], {}).get("bundle_id"):
                return "iOS Bundle ID bos olamaz."
        else:
            if not cfg["android_profiles"].get(
                    cfg["active_android_profile"], {}).get("app_package"):
                return "Android App Package bos olamaz."
        return None

    def _set_busy(self, busy):
        if busy:
            self.btn_run.configure(state="disabled", fg_color="#D8D0C0", text_color="#8C7D6A")
            self.btn_stop.configure(state="normal")
            self.btn_summary.configure(state="disabled")
            self.badge.set("running")
        else:
            self.btn_run.configure(state="normal", fg_color="#1a8242", text_color="#FFFFFF")
            self.btn_stop.configure(state="disabled")
            self.btn_summary.configure(state="normal")

    # ── Excel seç ────────────────────────────────────────────────────────────
    def _pick_excel(self):
        path = filedialog.askopenfilename(
            title="Excel Dosyasi Sec",
            filetypes=[("Excel", "*.xlsx *.xls"), ("Tumu", "*.*")],
            initialdir=self.v_out_dir.get() or _BASE)
        if path:
            self.v_summary_xl.set(path)

    # ── Checker çalıştır ──────────────────────────────────────────────────────
    def _run_checker(self):
        cfg = self._collect()
        err = self._validate(cfg)
        if err:
            messagebox.showerror("Eksik Bilgi", err)
            return

        save_config(cfg)
        self.cfg = cfg
        write_config_py(cfg, os.path.join(_BASE, "config.py"))

        platform = cfg["platform"]
        script   = ("element_checker_ios.py" if platform == "ios"
                    else "element_checker_android.py")
        spath    = os.path.join(_BASE, script)
        if not os.path.exists(spath):
            messagebox.showerror("Hata", f"Script bulunamadi:\n{spath}")
            return

        self._clear_log()
        active = cfg[f"active_{platform}_profile"]
        self._log(f"Platform: {platform.upper()}  |  Profil: {active}", "info")
        self._log("-" * 60, "dim")
        self._set_busy(True)
        self._pn_ev.clear()
        self.page_input_frame.grid_remove()

        threading.Thread(
            target=self._stream,
            args=([sys.executable, spath], _BASE, self._done_checker),
            daemon=True).start()

    def _show_page_input(self):
        self.v_page.set("")
        self.page_input_frame.grid(row=2, column=0, sticky="ew")
        for w in self.page_input_frame.winfo_children():
            if isinstance(w, ctk.CTkEntry):
                w.focus_set()
                break

    def _hide_page_input(self):
        self.page_input_frame.grid_remove()

    def _submit_page(self):
        name = self.v_page.get().strip()
        if not name:
            self._log("Saypa adi bos olamaz!", "warn")
            return
        self._pn_ans = name
        self._pn_ev.set()

    def _show_overwrite(self, label_text):
        self.ow_label.configure(text=label_text)
        self.ow_frame.grid(row=3, column=0, sticky="ew")

    def _hide_overwrite(self):
        self.ow_frame.grid_remove()

    def _submit_overwrite(self, yes: bool):
        self._ow_ans = yes
        self._ow_ev.set()

    # ── Build Summary çalıştır ────────────────────────────────────────────────
    def _run_summary(self):
        xl = self.v_summary_xl.get().strip()
        if not xl:
            messagebox.showwarning("Excel Sec", "Once bir Excel dosyasi secin.")
            return
        if not os.path.exists(xl):
            messagebox.showerror("Hata", f"Dosya bulunamadi:\n{xl}")
            return

        spath = os.path.join(_BASE, "build_summary.py")
        if not os.path.exists(spath):
            messagebox.showerror("Hata", f"build_summary.py bulunamadi:\n{spath}")
            return

        # build_summary.py'nin EXCEL_FILE sabitini override etmek için
        # argüman ya da env var ile geçebiliriz.
        # Basit yaklaşım: script içine argparse eklemek yerine
        # burada geçici bir wrapper env var kullanalım.
        cfg = self._collect()
        save_config(cfg)
        self.cfg = cfg

        self._clear_log()
        self._log(f"Excel: {os.path.basename(xl)}", "info")
        self._log("build_summary.py baslatiliyor...", "info")
        self._log("-" * 60, "dim")
        self._set_busy(True)

        threading.Thread(
            target=self._stream,
            args=([sys.executable, spath], _BASE, self._done_summary),
            kwargs={"xl_override": xl},
            daemon=True).start()

    # ── Subprocess stream (karakter tabanlı) ──────────────────────────────────
    def _stream(self, cmd, cwd, done_cb, xl_override=None):
        """
        stdout karakteri karakter okur.
        Sayfa adi sorusu gelince GUI input frame gosterilir,
        kullanici girince event ile devam edilir.
        """
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        if xl_override:
            env["WIMID_EXCEL_FILE"] = xl_override

        try:
            self._proc = subprocess.Popen(
                [cmd[0], "-u"] + cmd[1:], cwd=cwd,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE, text=True, encoding="utf-8",
                errors="replace", bufsize=0, env=env,
            )
            buf = ""

            page_asked = False   # sayfa adi sorusu bir kez sorulur

            def _normalize(s):
                # Turkce i/I karakterlerini ASCII'ye esle, trigger eslesmesi icin
                return s.replace("\u0131", "i").replace("\u0130", "i").lower()

            def _is_page_prompt(text):
                n = _normalize(text)
                # Tam olarak input() sorusu: "sayfa adi gir" icermeli
                # Cikti satirlari ("Sayfa adi : test2") "gir" icermez
                return "sayfa adi gir" in n or "sayfa ad" in n and "gir" in n

            def handle(line):
                nonlocal page_asked
                low = line.lower()
                norm = _normalize(line)

                if not page_asked and _is_page_prompt(line):
                    page_asked = True
                    self._log(line, "warn")
                    self.after(0, self._show_page_input)
                    self._pn_ev.clear()
                    self._pn_ev.wait(timeout=120)
                    answer = self._pn_ans
                    self.after(0, self._hide_page_input)
                    self._log(f"-> Sayfa adi: {answer}", "info")
                    self._proc.stdin.write(answer + "\n")
                    self._proc.stdin.flush()
                    return

                if "uezerine yazmak istiyor musunuz" in norm or "[e/h]" in low:
                    # Kisa etiket: parantez icini al, max 60 karakter
                    import re as _re
                    m = _re.search(r"'([^']+)'", line)
                    short = m.group(1) if m else line
                    short = short[:60] + ("..." if len(short) > 60 else "")
                    self.after(0, lambda s=short: self._show_overwrite(f"Uzerine yazilsin mi?  {s}"))
                    self._ow_ev.clear()
                    self._ow_ev.wait(timeout=60)
                    answer = "e" if self._ow_ans else "h"
                    self.after(0, self._hide_overwrite)
                    self._proc.stdin.write(answer + "\n")
                    self._proc.stdin.flush()
                    self._log(f"-> Uzerine yazma: {'Evet' if self._ow_ans else 'Hayir'}", "info" if self._ow_ans else "warn")
                    return

                self._log(line, self._classify(line))

            while True:
                ch = self._proc.stdout.read(1)
                if ch == "":
                    break
                if ch == "\n":
                    line = buf.rstrip()
                    buf  = ""
                    if line:
                        handle(line)
                else:
                    buf += ch
                    # Buffer'da prompt tespiti: sadece henuz sorulmadiysa
                    # ve tam "gir" kelimesi de geldiyse tetikle
                    if not page_asked:
                        nb = _normalize(buf)
                        if "sayfa adi gir" in nb:
                            handle(buf.strip())
                            buf = ""
                    # e/h sorusu buffer tespiti
                    if "[e/h]:" in buf.lower():
                        handle(buf.strip())
                        buf = ""

            if buf.strip():
                self._log(buf.strip(), self._classify(buf))

            self._proc.wait()
            done_cb(self._proc.returncode)

        except Exception as ex:
            self._log(f"HATA: {ex}", "err")
            self.after(0, lambda: done_cb(-1))
        finally:
            self._proc = None

    def _done_checker(self, rc):
        self.after(0, lambda: self._set_busy(False))
        self._log("-" * 60, "dim")
        if rc == 0:
            self._log("Script basariyla tamamlandi.", "ok")
            self.after(0, lambda: self.badge.set("ok"))
        else:
            self._log(f"Script hatayla sonlandi (exit code: {rc})", "err")
            self.after(0, lambda: self.badge.set("error"))

    def _done_summary(self, rc):
        self.after(0, lambda: self._set_busy(False))
        self._log("-" * 60, "dim")
        if rc == 0:
            self._log("build_summary.py tamamlandi.", "ok")
            self.after(0, lambda: self.badge.set("ok"))
        else:
            self._log(f"build_summary.py hatayla sonlandi (exit code: {rc})", "err")
            self.after(0, lambda: self.badge.set("error"))

    def _stop_proc(self):
        if self._proc:
            self._proc.terminate()
            self._log("Process durduruldu.", "warn")
        self._set_busy(False)
        self.badge.set("idle")
        self._pn_ev.set()   # deadlock onlemek icin event'i serbest birak
        self._ow_ev.set()   # overwrite event da serbest
        self.after(0, self._hide_page_input)
        self.after(0, self._hide_overwrite)

    def on_close(self):
        if self._proc:
            self._proc.terminate()
        save_config(self._collect())
        self.destroy()


# ════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
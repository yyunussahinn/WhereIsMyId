"""
smart_tab.py
────────────────────────────────────────────────────────────────
"Akıllı Tarama" sekmesi.

app.py içindeki CTkTabview'a şöyle eklenir:
    from smart_tab import SmartTab
    tab = tabview.add("🎯  Akıllı Tarama")
    SmartTab(tab, app_cfg_ref).pack(fill="both", expand=True)

app_cfg_ref: App instance'ına referans (profil, output_dir vb. için)
"""

import customtkinter as ctk
import tkinter as tk
import threading
import os
from datetime import datetime

# ── Palet (app.py ile aynı) ──────────────────────────────────────────────────
ACCENT        = "#000000"
ACCENT_IOS    = "#185FA5"
ACCENT_IOS_DK = "#0C447C"
ACCENT_DK     = "#D4A820"
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

FT  = ("Courier New", 18, "bold")
FL  = ("Courier New", 11, "bold")
FS  = ("Courier New", 10)
FLG = ("Courier New", 10)
FB  = ("Courier New",  9, "bold")


class SmartTab(ctk.CTkFrame):

    def __init__(self, parent, app_ref, **kw):
        super().__init__(parent, fg_color=BG_MAIN, **kw)
        self.app = app_ref          # App instance → profil, output_dir vs.
        self._proc_thread = None
        self._running     = False
        self._all_elements   = []
        self._screenshot_path = ""

        self._build()

    # ── UI ──────────────────────────────────────────────────────────────────
    def _build(self):
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # Sol panel
        left = ctk.CTkScrollableFrame(
            self, width=300, fg_color=BG_PANEL, corner_radius=10,
            scrollbar_button_color="#D8D0C0")
        left.grid(row=0, column=0, sticky="nsew", padx=(8, 6), pady=8)
        self._build_left(left)

        # Sağ panel (log)
        right = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10)
        right.grid(row=0, column=1, sticky="nsew", padx=(0, 8), pady=8)
        self._build_right(right)

    def _build_left(self, p):
        pad = dict(padx=14, pady=3)

        # Platform toggle
        self._sec("PLATFORM", p).pack(fill="x", **pad)
        pf = ctk.CTkFrame(p, fg_color=BG_INPUT, corner_radius=8)
        pf.pack(fill="x", padx=14, pady=(0, 8))

        self.v_platform = tk.StringVar(value=self.app.v_platform.get())

        self.btn_ios = ctk.CTkButton(
            pf, text="🍎  iOS", font=FL, height=36, corner_radius=7,
            fg_color=ACCENT_IOS, hover_color=ACCENT_IOS_DK, text_color=BG_MAIN,
            command=lambda: self._set_platform("ios"))
        self.btn_ios.pack(side="left", expand=True, fill="x", padx=(6,3), pady=6)

        self.btn_and = ctk.CTkButton(
            pf, text="🤖  Android", font=FL, height=36, corner_radius=7,
            fg_color=BG_INPUT, hover_color="#E8E0D0", text_color=T_MUT,
            command=lambda: self._set_platform("android"))
        self.btn_and.pack(side="left", expand=True, fill="x", padx=(3,6), pady=6)

        # Profil bilgisi (app.py'den okur)
        self._sec("AKTİF PROFİL", p).pack(fill="x", **pad)
        self.lbl_profile = ctk.CTkLabel(
            p, text="", font=FS, text_color=C_INF,
            fg_color=BG_INPUT, corner_radius=6)
        self.lbl_profile.pack(fill="x", padx=14, pady=(0, 8), ipady=6)
        self._update_profile_label()

        ctk.CTkLabel(p, text="Profil ayarları için 'Tam Tarama' sekmesini kullanın.",
                     font=("Courier New", 9), text_color=T_MUT,
                     wraplength=240).pack(padx=14, pady=(0, 10))

        # Çıktı klasörü
        self._sec("ÇIKTI", p).pack(fill="x", **pad)
        fr = ctk.CTkFrame(p, fg_color="transparent")
        fr.pack(fill="x", padx=14, pady=(0, 6))
        ctk.CTkLabel(fr, text="Klasör:", font=FS,
                     text_color=T_MUT, width=70, anchor="w").pack(side="left")
        ctk.CTkLabel(fr, textvariable=self.app.v_out_dir,
                     font=FS, text_color=T_PRI,
                     wraplength=180, anchor="w").pack(side="left", padx=(4, 0))

        # Bilgi kutusu
        self._sec("NASIL ÇALIŞIR?", p).pack(fill="x", **pad)
        info = (
            "1. 'Bağlan & Görüntü Al' butonuna bas\n"
            "2. Annotation penceresinde elementleri\n"
            "   kırmızı kare içine al\n"
            "3. 'Onayla' butonuna bas\n"
            "4. Sayfa adını gir → Rapor hazır"
        )
        ctk.CTkLabel(p, text=info, font=FS, text_color=T_MUT,
                     justify="left", anchor="w",
                     fg_color=BG_INPUT, corner_radius=6
                     ).pack(fill="x", padx=14, pady=(0, 10), ipady=8, ipadx=8)

        # Bağlan butonu
        self.btn_connect = ctk.CTkButton(
            p, text="📱  Bağlan & Görüntü Al",
            font=FL, height=44, corner_radius=8,
            fg_color=ACCENT_IOS, hover_color=ACCENT_IOS_DK,
            text_color="#FFFFFF",
            command=self._run_connect)
        self.btn_connect.pack(fill="x", padx=14, pady=(8, 4))

        self.btn_stop = ctk.CTkButton(
            p, text="■  Durdur",
            font=FL, height=36, corner_radius=8,
            fg_color="#7B1515", hover_color="#7B1515",
            text_color="#FFFFFF", state="disabled",
            command=self._stop)
        self.btn_stop.pack(fill="x", padx=14, pady=(0, 8))

    def _build_right(self, p):
        p.rowconfigure(1, weight=1)
        p.rowconfigure(2, weight=0)
        p.rowconfigure(3, weight=0)
        p.columnconfigure(0, weight=1)

        # Log başlığı
        hdr = ctk.CTkFrame(p, fg_color=BG_PANEL, corner_radius=0, height=36)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        ctk.CTkLabel(hdr, text="KONSOL ÇIKTISI",
                     font=FB, text_color="green").pack(side="left", padx=14)
        ctk.CTkButton(hdr, text="Temizle", font=FS, width=70, height=24,
                      fg_color="#7B1515", hover_color="#7B1515",
                      text_color="white", corner_radius=6,
                      command=self._clear_log).pack(side="right", padx=10, pady=5)

        # Log kutusu
        self.log_box = ctk.CTkTextbox(
            p, fg_color="#FAFAF7", text_color=T_PRI,
            font=FLG, corner_radius=0, wrap="word",
            scrollbar_button_color="#D8D0C0")
        self.log_box.grid(row=1, column=0, sticky="nsew")
        for tag, col in [("ok", C_OK), ("err", C_ERR),
                          ("warn", C_WRN), ("info", C_INF), ("dim", T_MUT)]:
            self.log_box._textbox.tag_config(tag, foreground=col)

        # Sayfa adı input (gizli, akış sırasında gösterilir)
        self.page_frame = ctk.CTkFrame(p, fg_color=BG_CARD,
                                        corner_radius=0, height=52)
        self.page_frame.grid(row=2, column=0, sticky="ew")
        self.page_frame.grid_propagate(False)
        self.page_frame.grid_remove()

        ctk.CTkLabel(self.page_frame, text="Sayfa adı:",
                     font=FL, text_color="black").pack(side="left", padx=(14, 6), pady=10)
        self.v_page = tk.StringVar()
        pe = ctk.CTkEntry(self.page_frame, textvariable=self.v_page,
                           placeholder_text="login, checkin ...",
                           fg_color=BG_INPUT, border_color="green",
                           text_color=T_PRI, font=FL, width=200, corner_radius=6)
        pe.pack(side="left", pady=10)
        pe.bind("<Return>", lambda e: self._submit_page())

        ctk.CTkButton(self.page_frame, text="▶  Raporu Oluştur",
                      font=FL, height=34, width=160,
                      fg_color="green", hover_color="green",
                      text_color=BG_MAIN, corner_radius=6,
                      command=self._submit_page).pack(side="left", padx=10, pady=10)

    # ── Yardımcılar ──────────────────────────────────────────────────────────
    def _sec(self, title, parent):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        ctk.CTkFrame(f, height=1, fg_color=ACCENT,
                     corner_radius=0).pack(side="left", fill="x", expand=True, pady=8)
        ctk.CTkLabel(f, text=f"  {title}  ", font=FB,
                     text_color=ACCENT, fg_color="transparent").pack(side="left")
        ctk.CTkFrame(f, height=1, fg_color=ACCENT,
                     corner_radius=0).pack(side="left", fill="x", expand=True, pady=8)
        return f

    def _set_platform(self, pf):
        self.v_platform.set(pf)
        if pf == "ios":
            self.btn_ios.configure(fg_color=ACCENT_IOS, text_color=BG_MAIN,
                                   hover_color=ACCENT_IOS_DK)
            self.btn_and.configure(fg_color=BG_INPUT, text_color=T_MUT,
                                   hover_color="#E8E0D0")
        else:
            self.btn_and.configure(fg_color=ACCENT_DK, text_color=BG_MAIN,
                                   hover_color=ACCENT_DK)
            self.btn_ios.configure(fg_color=BG_INPUT, text_color=T_MUT,
                                   hover_color="#E8E0D0")
        self._update_profile_label()

    def _update_profile_label(self):
        pf = self.v_platform.get()
        if pf == "ios":
            name = self.app.ios_panel.get_active()
            prof = self.app.ios_panel.get_data()
            info = f"iOS  •  {name}\n{prof.get('bundle_id','')}"
        else:
            name = self.app.and_panel.get_active()
            prof = self.app.and_panel.get_data()
            info = f"Android  •  {name}\n{prof.get('app_package','')}"
        self.lbl_profile.configure(text=info)

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

    def _set_busy(self, busy: bool):
        if busy:
            self.btn_connect.configure(state="disabled",
                                        fg_color="#D8D0C0", text_color="#8C7D6A")
            self.btn_stop.configure(state="normal")
        else:
            self.btn_connect.configure(state="normal",
                                        fg_color=ACCENT_IOS, text_color="#FFFFFF")
            self.btn_stop.configure(state="disabled")

    # ── Ana akış ─────────────────────────────────────────────────────────────
    def _run_connect(self):
        """Appium bağlantısı + screenshot thread'i başlat."""
        pf = self.v_platform.get()
        if pf == "ios":
            profile = self.app.ios_panel.get_data()
            if not profile.get("bundle_id"):
                self._log("❌ iOS Bundle ID boş!", "err")
                return
        else:
            profile = self.app.and_panel.get_data()
            if not profile.get("app_package"):
                self._log("❌ Android App Package boş!", "err")
                return

        output_dir = self.app.v_out_dir.get().strip()
        if not output_dir:
            self._log("❌ Çıktı klasörü boş!", "err")
            return

        self._clear_log()
        self._set_busy(True)
        self._log(f"Platform: {pf.upper()}  |  Appium bağlanıyor...", "info")
        self._log("-" * 50, "dim")

        # Screenshot path
        ss_dir  = os.path.join(output_dir, f"screenshots_{pf}")
        os.makedirs(ss_dir, exist_ok=True)
        ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
        ss_path = os.path.join(ss_dir, f"smart_{ts}.png")

        self._running = True
        self._proc_thread = threading.Thread(
            target=self._connect_worker,
            args=(pf, profile, self.app.v_appium.get(), ss_path),
            daemon=True)
        self._proc_thread.start()

    def _connect_worker(self, platform, profile, appium_server, ss_path):
        """Thread: Appium bağlan, screenshot al, elementleri topla."""
        try:
            from smart_checker import connect_and_capture

            elements, detected_page = connect_and_capture(
                platform=platform,
                profile=profile,
                appium_server=appium_server,
                screenshot_path=ss_path,
                log_cb=self._log,
            )

            self._all_elements    = elements
            self._screenshot_path = ss_path
            self._detected_page   = detected_page

            self._log("", "")
            self._log("📸 Ekran görüntüsü hazır. Annotation penceresi açılıyor...", "ok")

            # GUI thread'inde annotation penceresini aç
            self.after(300, lambda: self._open_annotation(ss_path))

        except Exception as ex:
            self._log(f"❌ HATA: {ex}", "err")
            self.after(0, lambda: self._set_busy(False))

    def _open_annotation(self, ss_path):
        """Annotation penceresini aç, kutular onaylanınca sayfa adı iste."""
        from annotator import open_annotator

        self._log("✏️  Elementleri işaretleyin ve 'Onayla' butonuna basın.", "warn")

        # Ana pencereyi bul
        root = self.winfo_toplevel()
        boxes = open_annotator(root, ss_path)

        if not boxes:
            self._log("🚫 Annotation iptal edildi.", "warn")
            self._set_busy(False)
            return

        self._boxes = boxes
        self._log(f"✅ {len(boxes)} kutu işaretlendi.", "ok")

        # Sayfa adı inputunu göster
        self.v_page.set("")
        self.page_frame.grid(row=2, column=0, sticky="ew")

        # Entry'e focus ver
        for w in self.page_frame.winfo_children():
            if isinstance(w, ctk.CTkEntry):
                w.focus_set()
                break

    def _submit_page(self):
        """Sayfa adı girildi → rapor üret."""
        page_name = self.v_page.get().strip()
        if not page_name:
            self._log("⚠️  Sayfa adı boş olamaz!", "warn")
            return

        self.page_frame.grid_remove()
        self._log(f"📄 Sayfa adı: {page_name}", "info")
        self._log("🔄 Elementler eşleştiriliyor...", "info")

        threading.Thread(
            target=self._report_worker,
            args=(page_name,),
            daemon=True).start()

    def _report_worker(self, page_name):
        """Thread: filter + rapor üret."""
        try:
            from claude_filter import filter_elements_by_boxes
            from smart_checker import generate_reports

            pf         = self.v_platform.get()
            output_dir = self.app.v_out_dir.get().strip()
            output_fmt = self.app.v_out_fmt.get()

            # API key var mı kontrol et
            use_vision = bool(os.environ.get("ANTHROPIC_API_KEY", "").strip()
                              or os.path.exists(
                                  os.path.join(os.path.dirname(
                                      os.path.abspath(__file__)), ".anthropic_key")))

            if not use_vision:
                self._log("ℹ️  API key bulunamadı → sadece koordinat eşleştirme.", "warn")

            filtered = filter_elements_by_boxes(
                all_elements=self._all_elements,
                boxes=self._boxes,
                screenshot_path=self._screenshot_path,
                use_vision=use_vision,
            )

            self._log(f"🎯 {len(filtered)} element raporda yer alacak.", "info")
            self._log("📝 Rapor oluşturuluyor...", "info")

            generate_reports(
                elements=filtered,
                page_name=page_name,
                output_dir=output_dir,
                platform=pf,
                screenshot_path=self._screenshot_path,
                output_fmt=output_fmt,
                log_cb=self._log,
            )

            self._log("-" * 50, "dim")
            self._log("✅ Tamamlandı!", "ok")

        except Exception as ex:
            import traceback
            self._log(f"❌ HATA: {ex}", "err")
            self._log(traceback.format_exc(), "err")
        finally:
            self.after(0, lambda: self._set_busy(False))

    def _stop(self):
        self._running = False
        self._set_busy(False)
        self._log("■ Durduruldu.", "warn")
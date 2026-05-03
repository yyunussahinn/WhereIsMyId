"""
smart_tab.py — v4.2
────────────────────────────────────────────────────────────────
Smart Tarama mantık sınıfı.

v4.2'de UI paneli app.py'ye taşındı.
Bu sınıf yalnızca Appium bağlantısı, annotation ve rapor üretimi
iş mantığını barındırır; app.py'deki log kutusu ve page frame'e bağlanır.

Kullanım (app.py içinde):
    self._smart_tab_ref = SmartTab(self)
    self._smart_tab_ref.bind_to_log(self.smart_log_box)
    self._smart_tab_ref.bind_page_frame(frame, var, submit_cb)
"""

import threading
import os
from datetime import datetime


class SmartTab:

    def __init__(self, app_ref):
        self.app = app_ref       # App instance → profil, output_dir, platform vb.
        self._running         = False
        self._all_elements    = []
        self._screenshot_path = ""
        self._detected_page   = ""
        self._boxes           = []

        # Bağlanan widget'lar (app.py tarafından set edilir)
        self._log_box    = None
        self._page_frame = None
        self._page_var   = None
        self._submit_cb  = None

    # ── Bağlama ──────────────────────────────────────────────────────────────
    def bind_to_log(self, log_box):
        self._log_box = log_box

    def bind_page_frame(self, frame, var, submit_cb):
        self._page_frame = frame
        self._page_var   = var
        self._submit_cb  = submit_cb

    # ── Log ──────────────────────────────────────────────────────────────────
    def _log(self, text, tag=""):
        if not self._log_box:
            return
        def _d():
            self._log_box.configure(state="normal")
            ts = datetime.now().strftime("%H:%M:%S")
            self._log_box._textbox.insert("end", f"[{ts}] {text}\n", tag or "")
            self._log_box._textbox.see("end")
            self._log_box.configure(state="disabled")
        self.app.after(0, _d)

    # ── Dış çağrılar ─────────────────────────────────────────────────────────
    def run_connect_from_footer(self):
        """Footer'daki 'BAĞLAN & GÖRÜNTÜ AL' butonundan çağrılır."""
        self._run_connect()

    def submit_page(self, page_name: str):
        """app.py'deki sayfa adı inputu onaylandığında çağrılır."""
        if not page_name:
            self._log("⚠️  Sayfa adı boş olamaz!", "warn")
            return
        if self._page_frame:
            self.app.after(0, self._page_frame.grid_remove)
        self._log(f"📄 Sayfa adı: {page_name}", "info")
        self._log("🔄 Elementler eşleştiriliyor...", "info")
        threading.Thread(
            target=self._report_worker,
            args=(page_name,),
            daemon=True).start()

    def stop(self):
        self._running = False
        self.app.after(0, lambda: self.app._set_busy(False))
        self._log("■ Durduruldu.", "warn")

    # ── Bağlan & Görüntü Al ───────────────────────────────────────────────────
    def _run_connect(self):
        pf = self.app.v_platform.get()
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

        # Log kutusunu temizle
        if self._log_box:
            self.app.after(0, lambda: (
                self._log_box.configure(state="normal"),
                self._log_box.delete("1.0", "end"),
                self._log_box.configure(state="disabled")
            ))

        self.app.after(0, lambda: self.app._set_busy(True))
        self._log(f"Platform: {pf.upper()}  |  Appium bağlanıyor...", "info")
        self._log("-" * 50, "dim")

        ss_dir  = os.path.join(output_dir, f"screenshots_{pf}")
        os.makedirs(ss_dir, exist_ok=True)
        ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
        ss_path = os.path.join(ss_dir, f"smart_{ts}.png")

        self._running = True
        threading.Thread(
            target=self._connect_worker,
            args=(pf, profile, self.app.v_appium.get(), ss_path),
            daemon=True).start()

    def _connect_worker(self, platform, profile, appium_server, ss_path):
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

            self.app.after(300, lambda: self._open_annotation(ss_path))

        except Exception as ex:
            self._log(f"❌ HATA: {ex}", "err")
            self.app.after(0, lambda: self.app._set_busy(False))

    def _open_annotation(self, ss_path):
        from annotator import open_annotator

        self._log("✏️  Elementleri işaretleyin ve 'Onayla' butonuna basın.", "warn")

        root  = self.app
        boxes = open_annotator(root, ss_path)

        if not boxes:
            self._log("🚫 Annotation iptal edildi.", "warn")
            self.app.after(0, lambda: self.app._set_busy(False))
            return

        self._boxes = boxes
        self._log(f"✅ {len(boxes)} kutu işaretlendi.", "ok")

        # Sayfa adı inputunu göster
        if self._page_var:
            self._page_var.set("")
        if self._page_frame:
            self.app.after(0, lambda: self._page_frame.grid(row=2, column=0, sticky="ew"))

    def _report_worker(self, page_name: str):
        try:
            from claude_filter import filter_elements_by_boxes
            from smart_checker import generate_reports

            pf         = self.app.v_platform.get()
            output_dir = self.app.v_out_dir.get().strip()

            # Çıktı formatını app'tan al
            cfg = self.app._collect()
            output_fmt = self._build_fmt(cfg)

            # Document sections
            document_sections = cfg.get("document_sections", ["unique", "undefined", "duplicate", "missing"])

            use_vision = bool(
                os.environ.get("ANTHROPIC_API_KEY", "").strip()
                or os.path.exists(os.path.join(
                    os.path.dirname(os.path.abspath(__file__)), ".anthropic_key"))
            )

            if not use_vision:
                self._log("ℹ️  API key bulunamadı → sadece koordinat eşleştirme.", "warn")

            filtered = filter_elements_by_boxes(
                all_elements=self._all_elements,
                boxes=self._boxes,
                screenshot_path=self._screenshot_path,
                use_vision=use_vision,
            )

            self._log(f"🎯 {len(filtered)} element raporda yer alacak.", "info")

            # AI Suggestion ekle
            import shared as sh
            filtered = sh.enrich_with_ai(filtered, pf)

            self._log("📝 Rapor oluşturuluyor...", "info")

            generate_reports(
                elements=filtered,
                page_name=page_name,
                output_dir=output_dir,
                platform=pf,
                screenshot_path=self._screenshot_path,
                output_fmt=output_fmt,
                document_sections=document_sections,
                log_cb=self._log,
            )

            self._log("-" * 50, "dim")
            self._log("✅ Tamamlandı!", "ok")
            self.app.after(0, lambda: self.app.badge.set("ok"))

        except Exception as ex:
            import traceback
            self._log(f"❌ HATA: {ex}", "err")
            self._log(traceback.format_exc(), "err")
            self.app.after(0, lambda: self.app.badge.set("error"))
        finally:
            self.app.after(0, lambda: self.app._set_busy(False))

    @staticmethod
    def _build_fmt(cfg) -> str:
        parts = []
        if cfg.get("output_word"):  parts.append("word")
        if cfg.get("output_excel"): parts.append("excel")
        if cfg.get("output_json"):  parts.append("json")
        return "+".join(parts) if parts else "word"
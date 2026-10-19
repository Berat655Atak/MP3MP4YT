"""
MP3MP4YT - Başlangıç ve Kütüphane Güncelleme Ekranı (Splash Loader)
Uygulama açılırken bağımlılıkları denetler, gerekirse günceller ve ana pencereye akıcı geçiş sağlar.
"""

import queue
import threading
import time
import customtkinter as ctk
from core.storage import load_config
from core.updater import check_ytdlp_update, perform_ytdlp_upgrade, get_installed_ytdlp_version
from ui.theme import Theme

class SplashLoader:
    def __init__(self, root: ctk.CTk, on_complete):
        self.root = root
        self.on_complete = on_complete
        self.queue = queue.Queue()
        
        # Tema ayarını erkenden uygula
        config = load_config()
        saved_theme = config.get("theme", "dark")
        ctk.set_appearance_mode(saved_theme)

        # Başlangıç pencere boyut ve ekran ortalama
        self.width = 460
        self.height = 230
        self.root.title("MP3MP4YT - Başlatılıyor")
        
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = max(0, (sw - self.width) // 2)
        y = max(0, (sh - self.height) // 2)
        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")
        self.root.resizable(False, False)
        self.root.configure(fg_color=Theme.COLOR_BG)

        self._build_ui()
        self.root.after(40, self._process_queue)
        threading.Thread(target=self._worker_check, daemon=True).start()

    def _build_ui(self):
        self.frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Başlık Bölümü
        header_row = ctk.CTkFrame(self.frame, fg_color="transparent")
        header_row.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            header_row,
            text="🎬 MP3MP4YT",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=20, weight="bold"),
            text_color=Theme.COLOR_TEXT
        ).pack(side="left")

        ctk.CTkLabel(
            header_row,
            text="YouTube İndirici",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11),
            text_color=Theme.COLOR_TEXT_MUTED
        ).pack(side="left", padx=(10, 0), pady=(4, 0))

        # Kontrol Kartı
        card = ctk.CTkFrame(
            self.frame,
            fg_color=Theme.COLOR_CARD,
            corner_radius=Theme.RADIUS_CARD,
            border_width=1,
            border_color=Theme.COLOR_CARD_BORDER
        )
        card.pack(fill="both", expand=True)

        card_inner = ctk.CTkFrame(card, fg_color="transparent")
        card_inner.pack(fill="both", expand=True, padx=16, pady=16)

        self.status_label = ctk.CTkLabel(
            card_inner,
            text="⏳ yt-dlp ve kütüphaneler denetleniyor...",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11, weight="bold"),
            text_color=Theme.COLOR_TEXT,
            anchor="w"
        )
        self.status_label.pack(fill="x", pady=(4, 8))

        # İlerleme Çubuğu
        self.progress_bar = ctk.CTkProgressBar(
            card_inner,
            height=6,
            corner_radius=3,
            progress_color=Theme.COLOR_ACCENT,
            fg_color=Theme.COLOR_INPUT_BG,
            mode="indeterminate"
        )
        self.progress_bar.pack(fill="x", pady=(0, 10))
        self.progress_bar.start()

        # Alt Bilgi Metni
        curr_ver = get_installed_ytdlp_version()
        self.info_label = ctk.CTkLabel(
            card_inner,
            text=f"Mevcut yt-dlp: v{curr_ver}",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=10),
            text_color=Theme.COLOR_TEXT_MUTED,
            anchor="w"
        )
        self.info_label.pack(fill="x")

    def _worker_check(self):
        try:
            has_update, latest_ver, installed_ver = check_ytdlp_update(timeout=2.5)
            if has_update:
                self.queue.put(("status", f"⬇ Yeni sürüm bulundu (v{latest_ver}), güncelleniyor...", Theme.COLOR_TEXT))
                success, msg = perform_ytdlp_upgrade()
                if success:
                    new_ver = get_installed_ytdlp_version()
                    self.queue.put(("status", f"✔ yt-dlp v{new_ver} sürümüne güncellendi!", Theme.COLOR_SUCCESS))
                else:
                    self.queue.put(("status", "⚠ Güncelleme atlandı, başlatılıyor...", Theme.COLOR_TEXT_MUTED))
            else:
                self.queue.put(("status", "✔ Tüm bileşenler güncel, uygulama başlatılıyor...", Theme.COLOR_SUCCESS))
        except Exception:
            self.queue.put(("status", "Sistem hazır, başlatılıyor...", Theme.COLOR_TEXT))

        time.sleep(0.35)
        self.queue.put(("done", None, None))

    def _process_queue(self):
        try:
            while True:
                msg_type, text, color = self.queue.get_nowait()
                if msg_type == "status":
                    self.status_label.configure(text=text)
                    if color:
                        self.status_label.configure(text_color=color)
                elif msg_type == "done":
                    try:
                        self.progress_bar.stop()
                    except Exception:
                        pass
                    self.frame.destroy()
                    self.on_complete(self.root)
                    return
        except queue.Empty:
            pass

        if self.frame.winfo_exists():
            self.root.after(50, self._process_queue)

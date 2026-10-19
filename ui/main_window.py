"""
MP3MP4YT - Modern Arayüz ve Görsel Deneyim Katmanı
Windows 11 Fluent + YouTube Dark Mode tasarım felsefesiyle güçlendirilmiş,
mikro etkileşimler, yumuşak geçişler ve akıcı animasyonlar sunan ana pencere.
"""

import io
import os
import re
import threading
import urllib.request
import customtkinter as ctk
from PIL import Image
import yt_dlp
from yt_dlp.utils import download_range_func

from core.utils import (
    format_duration, is_valid_url, get_ffmpeg_path,
    format_bytes, parse_time_str, show_windows_notification,
    reveal_in_explorer, open_file
)
from core.storage import (
    load_history, add_history_item, delete_history_item,
    clear_all_history, load_config, save_config
)
from core.updater import (
    check_ytdlp_update, perform_ytdlp_upgrade, get_installed_ytdlp_version
)
from ui.theme import Theme
from ui.animations import (
    AnimationManager, ease_out_cubic, ease_out_back, interpolate_color
)
from ui.toast import ToastManager

class YouTubeDownloaderApp:
    def __init__(self, root: ctk.CTk):
        self.root = root
        self.root.title("MP3MP4YT - Modern YouTube İndirici")
        self._set_window_geometry(560, 240)
        self.root.resizable(False, False)
        self.root.configure(fg_color=Theme.COLOR_BG)

        # Kullanıcı yapılandırmasını yükle ve tema ayarlarını uygula
        self.config = load_config()
        saved_theme = self.config.get("theme", "dark")
        ctk.set_appearance_mode(saved_theme)
        Theme.set_reduce_animations(self.config.get("reduce_animations", False))

        # Temel durum değişkenleri
        self.current_video_info = None
        self.available_resolutions = []
        self.resolution_size_map = {}
        self.audio_size_estimate = 0
        self.active_thumbnail_image = None
        self.current_url = ""
        self._debounce_id = None
        self._restore_timer = None
        self.cancel_download = False
        self.selected_playlist_indices = None
        self.current_download_base = None
        self.last_downloaded_file = None

        # İş parçacığı ve animasyon durum takipçileri
        self.is_downloading = False
        self._fetch_id = 0
        self.active_tab = "downloader"
        self._current_progress_val = 0.0

        # Form ve girdi değişkenleri
        self.url_var = ctk.StringVar()
        self.url_var.trace_add("write", self._on_url_input_changed)

        saved_format = self.config.get("last_format", "mp4")
        self.format_var = ctk.StringVar(value=saved_format)
        self.quality_var = ctk.StringVar()

        saved_dir = self.config.get("download_dir", os.path.join(os.path.expanduser("~"), "Downloads"))
        self.download_dir_var = ctk.StringVar(value=saved_dir)

        # Gelişmiş seçenekler ve tercihler
        self.clip_enabled_var = ctk.BooleanVar(value=False)
        self.clip_start_var = ctk.StringVar(value="00:00")
        self.clip_end_var = ctk.StringVar(value="00:00")
        self.subtitles_var = ctk.BooleanVar(value=self.config.get("subtitles_enabled", False))
        self.cookies_var = ctk.StringVar(value=self.config.get("cookies_browser", "Kapalı"))
        self.reduce_motion_var = ctk.BooleanVar(value=Theme.is_reduced_motion())
        self.theme_var = ctk.StringVar(value="🌙 Koyu" if saved_theme == "dark" else "☀️ Açık")
        saved_sub_lang = self.config.get("default_subtitle_lang", "tr")
        self.default_sub_lang_var = ctk.StringVar(value=saved_sub_lang)

        self._build_main_layout()
        self._reset_preview()

        # Pano odağı dinleyicisi
        self.root.bind("<FocusIn>", self._on_focus_in)

    def _set_window_geometry(self, width: int, height: int):
        """Pencereyi ekran boyutuna göre otomatik ortalayarak boyutlandırır."""
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = max(0, (sw - width) // 2)
        y = max(25, (sh - height) // 2 - 20)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _build_main_layout(self):
        """Üst sekme menüsünü ve ana içerik alanlarını kurar."""
        # Üst Gezinti Çubuğu
        self.nav_container = ctk.CTkFrame(self.root, fg_color="transparent")
        self.nav_container.pack(fill="x", padx=Theme.SPACE_XL, pady=(Theme.SPACE_LG, Theme.SPACE_SM))

        self.tab_selector = ctk.CTkSegmentedButton(
            self.nav_container,
            values=["🔗 İndirici", "📂 İndirilenler", "⚙️ Ayarlar"],
            command=self._on_tab_changed,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12, weight="bold"),
            selected_color=Theme.COLOR_ACCENT,
            selected_hover_color=Theme.COLOR_ACCENT_HOVER,
            unselected_color=Theme.COLOR_CARD,
            unselected_hover_color=Theme.COLOR_CARD_BORDER,
            text_color=Theme.COLOR_TEXT,
            corner_radius=Theme.RADIUS_CHIP,
            height=34
        )
        self.tab_selector.set("🔗 İndirici")
        self.tab_selector.pack(fill="x")

        # Üç Ana Sayfa Konteyneri
        self.downloader_container = ctk.CTkFrame(self.root, fg_color="transparent")
        self.downloader_container.pack(fill="both", expand=True)

        self.history_container = ctk.CTkFrame(self.root, fg_color="transparent")
        self.settings_container = ctk.CTkFrame(self.root, fg_color="transparent")

        self._build_downloader_ui()
        self._build_history_ui()
        self._build_settings_ui()

    def _on_tab_changed(self, selected_tab: str):
        """Sekmeler arası geçişi yumuşakça yönetir."""
        if "İndirici" in selected_tab:
            self.active_tab = "downloader"
            self.history_container.pack_forget()
            self.settings_container.pack_forget()
            self.downloader_container.pack(fill="both", expand=True)

            if self.current_video_info:
                self._set_window_geometry(560, 700)
            else:
                self._set_window_geometry(560, 240)
        elif "İndirilenler" in selected_tab:
            self.active_tab = "history"
            self.downloader_container.pack_forget()
            self.settings_container.pack_forget()
            self.history_container.pack(fill="both", expand=True)
            self._set_window_geometry(560, 700)
            self._render_history_list()
        elif "Ayarlar" in selected_tab:
            self.active_tab = "settings"
            self.downloader_container.pack_forget()
            self.history_container.pack_forget()
            self.settings_container.pack(fill="both", expand=True)
            self._set_window_geometry(560, 700)

    def _build_downloader_ui(self):
        """İndirici sekmesindeki girdi alanlarını ve kart yapılarını kurar."""
        # Başlık ve Alt Metin
        header_frame = ctk.CTkFrame(self.downloader_container, fg_color="transparent")
        header_frame.pack(fill="x", padx=Theme.SPACE_XL, pady=(Theme.SPACE_XS, Theme.SPACE_SM))

        title_row = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_row.pack(fill="x")

        ctk.CTkLabel(
            title_row,
            text="🎬 MP3MP4YT",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=18, weight="bold"),
            text_color=Theme.COLOR_TEXT
        ).pack(side="left")

        # Animasyonları Azalt Seçeneği (Hızlı / Sade Mod)
        self.reduce_motion_check = ctk.CTkCheckBox(
            title_row,
            text="⚡ Hızlı Mod",
            variable=self.reduce_motion_var,
            command=self._on_reduce_motion_toggled,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=10),
            text_color=Theme.COLOR_TEXT_MUTED,
            fg_color=Theme.COLOR_ACCENT,
            hover_color=Theme.COLOR_ACCENT_HOVER,
            corner_radius=4,
            width=18,
            height=18
        )
        self.reduce_motion_check.pack(side="right")

        ctk.CTkLabel(
            header_frame,
            text="Hızlı, Akıllı ve Güvenli YouTube İndirici",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11),
            text_color=Theme.COLOR_TEXT_MUTED
        ).pack(anchor="w", pady=(1, 0))

        # URL Giriş Kutusu (Odak Parıltısı ve Shake Destekli)
        self.url_container_frame = ctk.CTkFrame(self.downloader_container, fg_color="transparent")
        self.url_container_frame.pack(fill="x", padx=Theme.SPACE_XL, pady=Theme.SPACE_XS)

        self.url_entry = ctk.CTkEntry(
            self.url_container_frame,
            textvariable=self.url_var,
            placeholder_text="YouTube video veya oynatma listesi linkini yapıştırın...",
            height=40,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12),
            corner_radius=Theme.RADIUS_INPUT,
            fg_color=Theme.COLOR_INPUT_BG,
            border_color=Theme.COLOR_INPUT_BORDER,
            border_width=1,
            text_color=Theme.COLOR_TEXT,
            placeholder_text_color=Theme.COLOR_TEXT_MUTED
        )
        self.url_entry.pack(fill="x")
        self.url_entry.focus_set()

        # Giriş kutusu odak (Focus Glow) efektleri
        self.url_entry.bind("<FocusIn>", self._on_entry_focus_in)
        self.url_entry.bind("<FocusOut>", self._on_entry_focus_out)

        # ---------------------------------------------------------------------
        # KART 1: Video Önizleme Kartı (Elevation Layer 2)
        # ---------------------------------------------------------------------
        self.preview_card = ctk.CTkFrame(
            self.downloader_container,
            fg_color=Theme.COLOR_CARD,
            corner_radius=Theme.RADIUS_CARD,
            border_width=1,
            border_color=Theme.COLOR_CARD_BORDER
        )

        preview_content = ctk.CTkFrame(self.preview_card, fg_color="transparent")
        preview_content.pack(fill="x", padx=Theme.SPACE_MD, pady=Theme.SPACE_MD)

        # Kapak Görseli ve Yükleniyor Göstergesi
        self.thumbnail_frame = ctk.CTkFrame(
            preview_content,
            width=140,
            height=80,
            corner_radius=Theme.RADIUS_INPUT,
            fg_color=Theme.COLOR_INPUT_BG
        )
        self.thumbnail_frame.pack(side="left", padx=(0, Theme.SPACE_MD))
        self.thumbnail_frame.pack_propagate(False)

        self.thumbnail_label = ctk.CTkLabel(
            self.thumbnail_frame,
            text="[Görsel]",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11),
            text_color=Theme.COLOR_TEXT_MUTED
        )
        self.thumbnail_label.pack(expand=True)

        # Sağ Metin Detayları
        info_box = ctk.CTkFrame(preview_content, fg_color="transparent")
        info_box.pack(side="left", fill="both", expand=True)

        self.video_title_label = ctk.CTkLabel(
            info_box,
            text="",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12, weight="bold"),
            text_color=Theme.COLOR_TEXT,
            wraplength=310,
            anchor="w",
            justify="left"
        )
        self.video_title_label.pack(fill="x", anchor="w")

        self.video_detail_label = ctk.CTkLabel(
            info_box,
            text="",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11),
            text_color=Theme.COLOR_TEXT_MUTED,
            anchor="w",
            justify="left"
        )
        self.video_detail_label.pack(fill="x", anchor="w", pady=(2, 4))

        self.playlist_btn = ctk.CTkButton(
            info_box,
            text="📑 Oynatma Listesini Düzenle",
            command=self._open_playlist_window,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11, weight="bold"),
            fg_color=Theme.COLOR_SECONDARY_BTN,
            hover_color=Theme.COLOR_SECONDARY_HOVER,
            text_color=Theme.COLOR_TEXT,
            corner_radius=Theme.RADIUS_CHIP,
            height=28
        )

        # ---------------------------------------------------------------------
        # KART 2: Format ve Kalite Seçimi
        # ---------------------------------------------------------------------
        self.options_card = ctk.CTkFrame(
            self.downloader_container,
            fg_color=Theme.COLOR_CARD,
            corner_radius=Theme.RADIUS_CARD,
            border_width=1,
            border_color=Theme.COLOR_CARD_BORDER
        )

        options_inner = ctk.CTkFrame(self.options_card, fg_color="transparent")
        options_inner.pack(fill="x", padx=Theme.SPACE_MD, pady=Theme.SPACE_MD)

        format_row = ctk.CTkFrame(options_inner, fg_color="transparent")
        format_row.pack(fill="x")

        ctk.CTkRadioButton(
            format_row,
            text="MP4 (Video)",
            variable=self.format_var,
            value="mp4",
            command=self.on_format_changed,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12),
            text_color=Theme.COLOR_TEXT,
            fg_color=Theme.COLOR_ACCENT,
            hover_color=Theme.COLOR_ACCENT_HOVER
        ).pack(side="left", padx=(0, 16))

        ctk.CTkRadioButton(
            format_row,
            text="MP3 (Ses)",
            variable=self.format_var,
            value="mp3",
            command=self.on_format_changed,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12),
            text_color=Theme.COLOR_TEXT,
            fg_color=Theme.COLOR_ACCENT,
            hover_color=Theme.COLOR_ACCENT_HOVER
        ).pack(side="left", padx=16)

        ctk.CTkRadioButton(
            format_row,
            text="M4A (Orijinal Ses)",
            variable=self.format_var,
            value="m4a",
            command=self.on_format_changed,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12),
            text_color=Theme.COLOR_TEXT,
            fg_color=Theme.COLOR_ACCENT,
            hover_color=Theme.COLOR_ACCENT_HOVER
        ).pack(side="left", padx=16)

        quality_row = ctk.CTkFrame(options_inner, fg_color="transparent")
        quality_row.pack(fill="x", pady=(10, 0))

        ctk.CTkLabel(
            quality_row,
            text="Kalite / Çözünürlük:",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11, weight="bold"),
            text_color=Theme.COLOR_TEXT
        ).pack(side="left", padx=(0, 10))

        self.quality_combobox = ctk.CTkComboBox(
            quality_row,
            variable=self.quality_var,
            state="readonly",
            height=32,
            corner_radius=Theme.RADIUS_CHIP,
            fg_color=Theme.COLOR_INPUT_BG,
            border_color=Theme.COLOR_INPUT_BORDER,
            button_color=Theme.COLOR_SECONDARY_BTN,
            button_hover_color=Theme.COLOR_SECONDARY_HOVER,
            dropdown_fg_color=Theme.COLOR_CARD,
            text_color=Theme.COLOR_TEXT,
            dropdown_text_color=Theme.COLOR_TEXT,
            width=340
        )
        self.quality_combobox.pack(side="left", fill="x", expand=True)

        # ---------------------------------------------------------------------
        # KART 3: Ek Seçenekler (Kırpma, Altyazı, Çerezler)
        # ---------------------------------------------------------------------
        self.adv_card = ctk.CTkFrame(
            self.downloader_container,
            fg_color=Theme.COLOR_CARD,
            corner_radius=Theme.RADIUS_CARD,
            border_width=1,
            border_color=Theme.COLOR_CARD_BORDER
        )

        adv_inner = ctk.CTkFrame(self.adv_card, fg_color="transparent")
        adv_inner.pack(fill="x", padx=Theme.SPACE_MD, pady=Theme.SPACE_MD)

        adv_row1 = ctk.CTkFrame(adv_inner, fg_color="transparent")
        adv_row1.pack(fill="x", pady=(0, 6))

        self.clip_check = ctk.CTkCheckBox(
            adv_row1,
            text="✂️ Zaman Aralığı (Kırp):",
            variable=self.clip_enabled_var,
            command=self._on_clip_toggled,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11),
            text_color=Theme.COLOR_TEXT,
            fg_color=Theme.COLOR_ACCENT,
            hover_color=Theme.COLOR_ACCENT_HOVER,
            corner_radius=4
        )
        self.clip_check.pack(side="left", padx=(0, 8))

        self.clip_start_entry = ctk.CTkEntry(
            adv_row1,
            textvariable=self.clip_start_var,
            width=65,
            height=28,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11),
            corner_radius=Theme.RADIUS_CHIP,
            fg_color=Theme.COLOR_INPUT_BG,
            border_color=Theme.COLOR_INPUT_BORDER,
            justify="center",
            state="disabled"
        )
        self.clip_start_entry.pack(side="left", padx=2)

        ctk.CTkLabel(adv_row1, text="-", font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11), text_color=Theme.COLOR_TEXT_MUTED).pack(side="left", padx=2)

        self.clip_end_entry = ctk.CTkEntry(
            adv_row1,
            textvariable=self.clip_end_var,
            width=65,
            height=28,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11),
            corner_radius=Theme.RADIUS_CHIP,
            fg_color=Theme.COLOR_INPUT_BG,
            border_color=Theme.COLOR_INPUT_BORDER,
            justify="center",
            state="disabled"
        )
        self.clip_end_entry.pack(side="left", padx=2)

        ctk.CTkLabel(
            adv_row1,
            text="(Örn: 01:15 - 03:40)",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=10),
            text_color=Theme.COLOR_TEXT_MUTED
        ).pack(side="left", padx=8)

        adv_row2 = ctk.CTkFrame(adv_inner, fg_color="transparent")
        adv_row2.pack(fill="x")

        self.subtitles_check = ctk.CTkCheckBox(
            adv_row2,
            text="💬 Altyazı Ekle",
            variable=self.subtitles_var,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11),
            text_color=Theme.COLOR_TEXT,
            fg_color=Theme.COLOR_ACCENT,
            hover_color=Theme.COLOR_ACCENT_HOVER,
            corner_radius=4
        )
        self.subtitles_check.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(adv_row2, text="🍪 Çerez:", font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11), text_color=Theme.COLOR_TEXT).pack(side="left", padx=(0, 6))

        self.cookies_combobox = ctk.CTkComboBox(
            adv_row2,
            variable=self.cookies_var,
            values=["Kapalı", "Chrome", "Edge", "Firefox", "Brave"],
            state="readonly",
            height=28,
            width=110,
            corner_radius=Theme.RADIUS_CHIP,
            fg_color=Theme.COLOR_INPUT_BG,
            border_color=Theme.COLOR_INPUT_BORDER,
            button_color=Theme.COLOR_SECONDARY_BTN,
            button_hover_color=Theme.COLOR_SECONDARY_HOVER,
            dropdown_fg_color=Theme.COLOR_CARD,
            text_color=Theme.COLOR_TEXT,
            dropdown_text_color=Theme.COLOR_TEXT
        )
        self.cookies_combobox.pack(side="left")

        # ---------------------------------------------------------------------
        # KART 4: İlerleme Çubuğu ve Aksiyon Bölümü
        # ---------------------------------------------------------------------
        self.bottom_frame = ctk.CTkFrame(self.downloader_container, fg_color="transparent")

        self.progress_bar = ctk.CTkProgressBar(
            self.bottom_frame,
            height=8,
            corner_radius=4,
            progress_color=Theme.COLOR_ACCENT,
            fg_color=Theme.COLOR_INPUT_BG
        )
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", pady=(0, 8))

        buttons_row = ctk.CTkFrame(self.bottom_frame, fg_color="transparent")
        buttons_row.pack(fill="x")

        self.download_btn = ctk.CTkButton(
            buttons_row,
            text="İNDİR",
            command=self.start_download_action,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=13, weight="bold"),
            height=42,
            corner_radius=Theme.RADIUS_INPUT,
            fg_color=Theme.COLOR_ACCENT,
            hover_color=Theme.COLOR_ACCENT_HOVER,
            text_color="#FFFFFF"
        )
        self.download_btn.pack(side="left", fill="both", expand=True)

        self.cancel_btn = ctk.CTkButton(
            buttons_row,
            text="✕",
            command=self.cancel_download_action,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=14, weight="bold"),
            height=42,
            width=42,
            corner_radius=Theme.RADIUS_INPUT,
            fg_color=Theme.COLOR_SECONDARY_BTN,
            hover_color=Theme.COLOR_DANGER,
            text_color=Theme.COLOR_TEXT
        )

        # Durum ve Tamamlanma Hızlı Eylem Butonları
        self.action_links_frame = ctk.CTkFrame(self.downloader_container, fg_color="transparent")
        self.status_label = ctk.CTkLabel(
            self.downloader_container,
            text="",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11),
            text_color=Theme.COLOR_TEXT_MUTED
        )
        self.status_label.pack(pady=2)

        self.root.bind("<Return>", self.start_download_action)

    def _build_history_ui(self):
        """İndirilenler geçmişi sekmesini kurar."""
        head = ctk.CTkFrame(self.history_container, fg_color="transparent")
        head.pack(fill="x", padx=Theme.SPACE_XL, pady=(10, 8))

        ctk.CTkLabel(
            head,
            text="İndirilen Dosyalar Geçmişi",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=14, weight="bold"),
            text_color=Theme.COLOR_TEXT
        ).pack(side="left")

        ctk.CTkButton(
            head,
            text="🗑️ Tümünü Temizle",
            command=self._on_clear_history_clicked,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11),
            fg_color=Theme.COLOR_SECONDARY_BTN,
            hover_color=Theme.COLOR_DANGER,
            text_color=Theme.COLOR_TEXT,
            corner_radius=Theme.RADIUS_CHIP,
            height=28
        ).pack(side="right")

        self.hist_scroll_frame = ctk.CTkScrollableFrame(
            self.history_container,
            fg_color="transparent",
            corner_radius=Theme.RADIUS_CARD
        )
        self.hist_scroll_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))

    def _render_history_list(self):
        """Geçmiş listesini diskten okur ve kartlar halinde listeler."""
        for widget in self.hist_scroll_frame.winfo_children():
            widget.destroy()

        items = load_history()
        if not items:
            empty_frame = ctk.CTkFrame(self.hist_scroll_frame, fg_color="transparent")
            empty_frame.pack(pady=60)

            ctk.CTkLabel(
                empty_frame,
                text="📂",
                font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=36),
                text_color=Theme.COLOR_TEXT_MUTED
            ).pack(pady=(0, 6))

            ctk.CTkLabel(
                empty_frame,
                text="Henüz indirilmiş bir dosya bulunmuyor.\nİndirdiğiniz videolar burada listelenecektir.",
                font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12),
                text_color=Theme.COLOR_TEXT_MUTED,
                justify="center"
            ).pack()
            return

        for item in items:
            card = ctk.CTkFrame(
                self.hist_scroll_frame,
                fg_color=Theme.COLOR_CARD,
                corner_radius=Theme.RADIUS_CHIP,
                border_width=1,
                border_color=Theme.COLOR_CARD_BORDER
            )
            card.pack(fill="x", pady=4, padx=4)

            # Hover parıltı efekti
            def _on_enter(e, c=card):
                AnimationManager.animate_color(c, "border_color", Theme.COLOR_CARD_BORDER, Theme.COLOR_CARD_BORDER_HOVER, duration_ms=160)
            def _on_leave(e, c=card):
                AnimationManager.animate_color(c, "border_color", Theme.COLOR_CARD_BORDER_HOVER, Theme.COLOR_CARD_BORDER, duration_ms=160)
            
            card.bind("<Enter>", _on_enter)
            card.bind("<Leave>", _on_leave)

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=12, pady=10)

            info_col = ctk.CTkFrame(inner, fg_color="transparent")
            info_col.pack(side="left", fill="both", expand=True)

            title_text = item.get("title", "İsimsiz Video")
            ctk.CTkLabel(
                info_col,
                text=title_text,
                font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12, weight="bold"),
                text_color=Theme.COLOR_TEXT,
                anchor="w",
                wraplength=320,
                justify="left"
            ).pack(fill="x")

            meta_str = f"Format: {item.get('format')} ({item.get('quality')})  |  Boyut: {item.get('size')}  |  {item.get('date')}"
            ctk.CTkLabel(
                info_col,
                text=meta_str,
                font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=10),
                text_color=Theme.COLOR_TEXT_MUTED,
                anchor="w"
            ).pack(fill="x", pady=(2, 0))

            btn_col = ctk.CTkFrame(inner, fg_color="transparent")
            btn_col.pack(side="right", padx=(6, 0))

            filepath = item.get("filepath", "")

            ctk.CTkButton(
                btn_col,
                text="📁",
                command=lambda p=filepath: reveal_in_explorer(p),
                font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11),
                fg_color=Theme.COLOR_SECONDARY_BTN,
                hover_color=Theme.COLOR_SECONDARY_HOVER,
                text_color=Theme.COLOR_TEXT,
                corner_radius=Theme.RADIUS_CHIP,
                width=34,
                height=30
            ).pack(side="left", padx=2)

            ctk.CTkButton(
                btn_col,
                text="▶",
                command=lambda p=filepath: open_file(p),
                font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11),
                fg_color=Theme.COLOR_SECONDARY_BTN,
                hover_color=Theme.COLOR_SECONDARY_HOVER,
                text_color=Theme.COLOR_TEXT,
                corner_radius=Theme.RADIUS_CHIP,
                width=34,
                height=30
            ).pack(side="left", padx=2)

            ctk.CTkButton(
                btn_col,
                text="✕",
                command=lambda i=item.get("id"): self._on_delete_history_item(i),
                font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11),
                fg_color=Theme.COLOR_SECONDARY_BTN,
                hover_color=Theme.COLOR_DANGER,
                text_color=Theme.COLOR_TEXT_MUTED,
                corner_radius=Theme.RADIUS_CHIP,
                width=34,
                height=30
            ).pack(side="left", padx=2)

    def _on_delete_history_item(self, item_id: str):
        delete_history_item(item_id)
        self._render_history_list()
        ToastManager.show(self.root, "Kayıt geçmişten silindi.", toast_type="info", duration_ms=2500)

    def _on_clear_history_clicked(self):
        clear_all_history()
        self._render_history_list()
        ToastManager.show(self.root, "Tüm indirme geçmişi temizlendi.", toast_type="info", duration_ms=2500)

    def _build_settings_ui(self):
        """Ayarlar sekmesini ve yapılandırma kartlarını kurar."""
        head = ctk.CTkFrame(self.settings_container, fg_color="transparent")
        head.pack(fill="x", padx=Theme.SPACE_XL, pady=(10, 8))

        ctk.CTkLabel(
            head,
            text="⚙️ Tercihler ve Ayarlar",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=15, weight="bold"),
            text_color=Theme.COLOR_TEXT
        ).pack(anchor="w")

        ctk.CTkLabel(
            head,
            text="Uygulama görünümünü, indirme yollarını ve varsayılan seçenekleri yönetin.",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11),
            text_color=Theme.COLOR_TEXT_MUTED
        ).pack(anchor="w", pady=(1, 0))

        settings_scroll = ctk.CTkScrollableFrame(
            self.settings_container,
            fg_color="transparent",
            corner_radius=Theme.RADIUS_CARD
        )
        settings_scroll.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # -------------------------------------------------------------
        # KART 1: Görünüm ve Tema (Koyu / Açık Mod)
        # -------------------------------------------------------------
        theme_card = ctk.CTkFrame(
            settings_scroll,
            fg_color=Theme.COLOR_CARD,
            corner_radius=Theme.RADIUS_CARD,
            border_width=1,
            border_color=Theme.COLOR_CARD_BORDER
        )
        theme_card.pack(fill="x", pady=6)

        theme_inner = ctk.CTkFrame(theme_card, fg_color="transparent")
        theme_inner.pack(fill="x", padx=Theme.SPACE_MD, pady=Theme.SPACE_MD)

        theme_text_col = ctk.CTkFrame(theme_inner, fg_color="transparent")
        theme_text_col.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(
            theme_text_col,
            text="🎨 Uygulama Teması",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12, weight="bold"),
            text_color=Theme.COLOR_TEXT,
            anchor="w"
        ).pack(fill="x")

        ctk.CTkLabel(
            theme_text_col,
            text="Karanlık veya aydınlık arayüz görünümünü seçin.",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=10),
            text_color=Theme.COLOR_TEXT_MUTED,
            anchor="w"
        ).pack(fill="x", pady=(2, 0))

        self.theme_segmented = ctk.CTkSegmentedButton(
            theme_inner,
            values=["🌙 Koyu", "☀️ Açık"],
            variable=self.theme_var,
            command=self._on_theme_changed,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11, weight="bold"),
            selected_color=Theme.COLOR_ACCENT,
            selected_hover_color=Theme.COLOR_ACCENT_HOVER,
            unselected_color=Theme.COLOR_INPUT_BG,
            unselected_hover_color=Theme.COLOR_CARD_BORDER,
            text_color=Theme.COLOR_TEXT,
            corner_radius=Theme.RADIUS_CHIP,
            height=32
        )
        self.theme_segmented.pack(side="right")

        # -------------------------------------------------------------
        # KART 2: İndirme Klasörü Konumu
        # -------------------------------------------------------------
        dir_card = ctk.CTkFrame(
            settings_scroll,
            fg_color=Theme.COLOR_CARD,
            corner_radius=Theme.RADIUS_CARD,
            border_width=1,
            border_color=Theme.COLOR_CARD_BORDER
        )
        dir_card.pack(fill="x", pady=6)

        dir_inner = ctk.CTkFrame(dir_card, fg_color="transparent")
        dir_inner.pack(fill="x", padx=Theme.SPACE_MD, pady=Theme.SPACE_MD)

        ctk.CTkLabel(
            dir_inner,
            text="📁 Varsayılan İndirme Klasörü",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12, weight="bold"),
            text_color=Theme.COLOR_TEXT,
            anchor="w"
        ).pack(fill="x")

        ctk.CTkLabel(
            dir_inner,
            text="İndirilen tüm video ve ses dosyaları bu dizine kaydedilir.",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=10),
            text_color=Theme.COLOR_TEXT_MUTED,
            anchor="w"
        ).pack(fill="x", pady=(2, 6))

        dir_path_box = ctk.CTkFrame(
            dir_inner,
            fg_color=Theme.COLOR_INPUT_BG,
            corner_radius=Theme.RADIUS_CHIP,
            border_width=1,
            border_color=Theme.COLOR_INPUT_BORDER
        )
        dir_path_box.pack(fill="x", pady=(0, 8))

        self.settings_dir_label = ctk.CTkLabel(
            dir_path_box,
            textvariable=self.download_dir_var,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11),
            text_color=Theme.COLOR_TEXT,
            anchor="w"
        )
        self.settings_dir_label.pack(fill="x", padx=10, pady=6)

        dir_btns_row = ctk.CTkFrame(dir_inner, fg_color="transparent")
        dir_btns_row.pack(fill="x")

        ctk.CTkButton(
            dir_btns_row,
            text="📁 Klasör Değiştir",
            command=self.select_download_folder,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11, weight="bold"),
            fg_color=Theme.COLOR_ACCENT,
            hover_color=Theme.COLOR_ACCENT_HOVER,
            text_color="#FFFFFF",
            corner_radius=Theme.RADIUS_CHIP,
            height=30
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            dir_btns_row,
            text="↗ Klasörü Aç",
            command=lambda: reveal_in_explorer(self.download_dir_var.get()),
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11),
            fg_color=Theme.COLOR_SECONDARY_BTN,
            hover_color=Theme.COLOR_SECONDARY_HOVER,
            text_color=Theme.COLOR_TEXT,
            corner_radius=Theme.RADIUS_CHIP,
            height=30
        ).pack(side="left")

        # -------------------------------------------------------------
        # KART 3: Altyazı Dili Tercihi
        # -------------------------------------------------------------
        sub_card = ctk.CTkFrame(
            settings_scroll,
            fg_color=Theme.COLOR_CARD,
            corner_radius=Theme.RADIUS_CARD,
            border_width=1,
            border_color=Theme.COLOR_CARD_BORDER
        )
        sub_card.pack(fill="x", pady=6)

        sub_inner = ctk.CTkFrame(sub_card, fg_color="transparent")
        sub_inner.pack(fill="x", padx=Theme.SPACE_MD, pady=Theme.SPACE_MD)

        sub_text_col = ctk.CTkFrame(sub_inner, fg_color="transparent")
        sub_text_col.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(
            sub_text_col,
            text="💬 Varsayılan Altyazı Dili",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12, weight="bold"),
            text_color=Theme.COLOR_TEXT,
            anchor="w"
        ).pack(fill="x")

        ctk.CTkLabel(
            sub_text_col,
            text="Altyazı ekleme seçeneği açıkken öncelikle aranacak dil.",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=10),
            text_color=Theme.COLOR_TEXT_MUTED,
            anchor="w"
        ).pack(fill="x", pady=(2, 0))

        lang_map = {
            "tr": "Türkçe (tr)",
            "en": "İngilizce (en)",
            "all": "Tüm Diller (Tümü)",
            "auto": "Orijinal / Otomatik"
        }
        current_lang = self.config.get("default_subtitle_lang", "tr")
        current_display = lang_map.get(current_lang, "Türkçe (tr)")

        self.sub_lang_combobox = ctk.CTkComboBox(
            sub_inner,
            values=["Türkçe (tr)", "İngilizce (en)", "Tüm Diller (Tümü)", "Orijinal / Otomatik"],
            command=self._on_sub_lang_changed,
            state="readonly",
            height=30,
            width=150,
            corner_radius=Theme.RADIUS_CHIP,
            fg_color=Theme.COLOR_INPUT_BG,
            border_color=Theme.COLOR_INPUT_BORDER,
            button_color=Theme.COLOR_SECONDARY_BTN,
            button_hover_color=Theme.COLOR_SECONDARY_HOVER,
            dropdown_fg_color=Theme.COLOR_CARD,
            text_color=Theme.COLOR_TEXT,
            dropdown_text_color=Theme.COLOR_TEXT
        )
        self.sub_lang_combobox.set(current_display)
        self.sub_lang_combobox.pack(side="right")

        # -------------------------------------------------------------
        # KART 4: Sistem ve Motor Bilgileri
        # -------------------------------------------------------------
        info_card = ctk.CTkFrame(
            settings_scroll,
            fg_color=Theme.COLOR_CARD,
            corner_radius=Theme.RADIUS_CARD,
            border_width=1,
            border_color=Theme.COLOR_CARD_BORDER
        )
        info_card.pack(fill="x", pady=6)

        info_inner = ctk.CTkFrame(info_card, fg_color="transparent")
        info_inner.pack(fill="x", padx=Theme.SPACE_MD, pady=Theme.SPACE_MD)

        ctk.CTkLabel(
            info_inner,
            text="ℹ️ Sistem ve Motor Bilgisi",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12, weight="bold"),
            text_color=Theme.COLOR_TEXT,
            anchor="w"
        ).pack(fill="x")

        yt_ver_str = get_installed_ytdlp_version()
        ffmpeg_bin = get_ffmpeg_path()
        ffmpeg_status = "✔ Kurulu & Aktif" if ffmpeg_bin else "✕ Bulunamadı"

        tech_row = ctk.CTkFrame(info_inner, fg_color="transparent")
        tech_row.pack(fill="x", pady=(6, 8))

        self.tech_info_label = ctk.CTkLabel(
            tech_row,
            text=f"yt-dlp: v{yt_ver_str}   |   FFmpeg: {ffmpeg_status}",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=10),
            text_color=Theme.COLOR_TEXT_MUTED,
            anchor="w"
        )
        self.tech_info_label.pack(fill="x")

        btn_row = ctk.CTkFrame(info_inner, fg_color="transparent")
        btn_row.pack(fill="x", pady=(2, 0))

        self.update_btn = ctk.CTkButton(
            btn_row,
            text="🔄 yt-dlp Güncelle",
            command=self._on_manual_update_clicked,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11, weight="bold"),
            fg_color=Theme.COLOR_ACCENT,
            hover_color=Theme.COLOR_ACCENT_HOVER,
            text_color="#FFFFFF",
            corner_radius=Theme.RADIUS_CHIP,
            height=30
        )
        self.update_btn.pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_row,
            text="🗑️ Tüm Geçmişi Temizle",
            command=self._on_clear_history_clicked,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11),
            fg_color=Theme.COLOR_SECONDARY_BTN,
            hover_color=Theme.COLOR_DANGER,
            text_color=Theme.COLOR_TEXT,
            corner_radius=Theme.RADIUS_CHIP,
            height=30
        ).pack(side="left")

    def _on_manual_update_clicked(self):
        self.update_btn.configure(state="disabled", text="⏳ Kontrol Ediliyor...")
        ToastManager.show(self.root, "yt-dlp güncellemeleri denetleniyor...", toast_type="info", duration_ms=2500)

        def _bg_check():
            has_update, latest_ver, installed_ver = check_ytdlp_update(timeout=4.0)
            if has_update:
                self.root.after(0, lambda: self.update_btn.configure(text="⬇ Güncelleniyor..."))
                self.root.after(0, lambda: ToastManager.show(self.root, f"v{latest_ver} bulundu, güncelleniyor...", toast_type="info", duration_ms=3000))
                success, msg = perform_ytdlp_upgrade()
                if success:
                    new_ver = get_installed_ytdlp_version()
                    ffmpeg_bin = get_ffmpeg_path()
                    ffmpeg_status = "✔ Kurulu & Aktif" if ffmpeg_bin else "✕ Bulunamadı"
                    self.root.after(0, lambda: self.tech_info_label.configure(text=f"yt-dlp: v{new_ver}   |   FFmpeg: {ffmpeg_status}"))
                    self.root.after(0, lambda: ToastManager.show(self.root, f"✔ yt-dlp v{new_ver} sürümüne güncellendi!", toast_type="success", duration_ms=3500))
                else:
                    self.root.after(0, lambda: ToastManager.show(self.root, f"Hata: {msg[:40]}", toast_type="danger", duration_ms=3500))
            else:
                self.root.after(0, lambda: ToastManager.show(self.root, f"yt-dlp zaten en güncel sürümde (v{installed_ver}).", toast_type="info", duration_ms=3000))

            self.root.after(0, lambda: self.update_btn.configure(state="normal", text="🔄 yt-dlp Güncelle"))

        threading.Thread(target=_bg_check, daemon=True).start()

    def _on_theme_changed(self, value: str):
        mode = "dark" if "Koyu" in value else "light"
        ctk.set_appearance_mode(mode)
        save_config({"theme": mode})
        ToastManager.show(
            self.root,
            f"Tema değiştirildi: {'Karanlık' if mode == 'dark' else 'Aydınlık'} Mod",
            toast_type="info",
            duration_ms=2500
        )

    def _on_sub_lang_changed(self, value: str):
        code_map = {
            "Türkçe (tr)": "tr",
            "İngilizce (en)": "en",
            "Tüm Diller (Tümü)": "all",
            "Orijinal / Otomatik": "auto"
        }
        lang_code = code_map.get(value, "tr")
        self.default_sub_lang_var.set(lang_code)
        save_config({"default_subtitle_lang": lang_code})
        ToastManager.show(
            self.root,
            f"Varsayılan altyazı dili güncellendi: {value}",
            toast_type="info",
            duration_ms=2500
        )

    def _on_entry_focus_in(self, event):
        """URL kutusuna odaklanıldığında parlak kırmızı kenarlık animasyonu."""
        AnimationManager.animate_color(
            self.url_entry, "border_color",
            Theme.COLOR_INPUT_BORDER, Theme.COLOR_INPUT_BORDER_FOCUS,
            duration_ms=Theme.TIME_HOVER
        )

    def _on_entry_focus_out(self, event):
        """URL kutusundan çıkıldığında kenarlık rengini normale döndürür."""
        AnimationManager.animate_color(
            self.url_entry, "border_color",
            Theme.COLOR_INPUT_BORDER_FOCUS, Theme.COLOR_INPUT_BORDER,
            duration_ms=Theme.TIME_HOVER
        )

    def _on_reduce_motion_toggled(self):
        val = self.reduce_motion_var.get()
        Theme.set_reduce_animations(val)
        save_config({"reduce_animations": val})
        msg = "Hızlı Mod açık (Animasyonlar kapatıldı)" if val else "Animasyonlar ve görsel efektler açıldı"
        ToastManager.show(self.root, msg, toast_type="info", duration_ms=2500)

    def _on_clip_toggled(self):
        state = "normal" if self.clip_enabled_var.get() else "disabled"
        self.clip_start_entry.configure(state=state)
        self.clip_end_entry.configure(state=state)

    def _on_focus_in(self, event):
        if self.is_downloading or self.active_tab != "downloader":
            return
        if event.widget != self.root:
            return
        try:
            clipboard_content = self.root.clipboard_get().strip()
            if is_valid_url(clipboard_content) and self.url_var.get() != clipboard_content:
                self.url_var.set(clipboard_content)
        except Exception:
            pass

    def _on_url_input_changed(self, *args):
        if self._debounce_id:
            self.root.after_cancel(self._debounce_id)
            self._debounce_id = None

        if self._restore_timer:
            try:
                self.root.after_cancel(self._restore_timer)
            except Exception:
                pass
            self._restore_timer = None

        url = self.url_var.get().strip()

        # Yeni link girildiği an önceki indirme barını, sayaçları ve aksiyon butonlarını anında sıfırla
        self.progress_bar.set(0)
        self._current_progress_val = 0.0
        self._hide_action_links()
        self.current_url = ""

        if not url:
            self._reset_preview()
            self.status_label.configure(text="")
            return

        if not is_valid_url(url):
            self._reset_preview()
            self.status_label.configure(text="Hata: Geçersiz YouTube linki!", text_color=Theme.COLOR_DANGER)
            # Geçersiz bağlantıda hafif yatay sallanma (shake) efekti
            AnimationManager.animate_shake(self.url_entry, self.url_container_frame, base_padx=Theme.SPACE_XL)
            ToastManager.show(self.root, "Geçersiz YouTube bağlantısı!", toast_type="danger", duration_ms=3000)
            return

        # Önceki video verilerini temizle ki eski videonun bilgileri ekranda asılı kalmasın
        self.current_video_info = None
        self.available_resolutions = []
        self.resolution_size_map = {}
        self.audio_size_estimate = 0
        self.active_thumbnail_image = None
        self.playlist_btn.pack_forget()

        # Kartları kademeli olarak ekrana yerleştir ve pencereyi genişlet
        self._show_panels_staggered()
        self._set_window_geometry(560, 700)

        self.thumbnail_label.configure(text="⏳ Yükleniyor...", image=None)
        self.video_title_label.configure(text="Video bilgileri taranıyor...")
        self.video_detail_label.configure(text="Lütfen bekleyin...")
        self.status_label.configure(text="")
        self.download_btn.configure(state="disabled", text="⏳ BİLGİLER ALINIYOR...", fg_color=Theme.COLOR_SECONDARY_BTN, text_color=Theme.COLOR_TEXT_MUTED)
        AnimationManager.stop_pulse("download_btn_pulse")

        self._fetch_id += 1
        current_fetch_id = self._fetch_id
        self._debounce_id = self.root.after(250, lambda: self._trigger_auto_fetch(url, current_fetch_id))

    def _show_panels_staggered(self):
        """Kartların sırayla hafif gecikmelerle belirmesini sağlar."""
        panels = [
            self.preview_card,
            self.options_card,
            self.adv_card,
            self.bottom_frame
        ]

        # Eğer zaten ekrandalarsa tekrar pack animasyonu tetikleme
        if all(p.winfo_ismapped() for p in panels):
            return

        if Theme.is_reduced_motion():
            for p in panels:
                p.pack(fill="x", padx=Theme.SPACE_XL, pady=4)
        else:
            for idx, panel in enumerate(panels):
                delay = idx * 50
                self.root.after(delay, lambda p=panel: p.pack(fill="x", padx=Theme.SPACE_XL, pady=4))

    def _reset_preview(self):
        self._fetch_id += 1
        AnimationManager.stop_pulse("download_btn_pulse")
        self.current_video_info = None
        self.current_url = ""
        self.available_resolutions = []
        self.resolution_size_map = {}
        self.audio_size_estimate = 0
        self.active_thumbnail_image = None
        self.video_title_label.configure(text="")
        self.video_detail_label.configure(text="")
        self.playlist_btn.pack_forget()
        self.thumbnail_label.configure(text="", image=None)

        self.preview_card.pack_forget()
        self.options_card.pack_forget()
        self.adv_card.pack_forget()
        self.bottom_frame.pack_forget()
        self._hide_action_links()

        self.progress_bar.set(0)
        self._current_progress_val = 0.0
        self.clip_enabled_var.set(False)
        self.clip_start_var.set("00:00")
        self.clip_end_var.set("00:00")

        if self.active_tab == "downloader":
            self._set_window_geometry(560, 240)

        self.on_format_changed()

    def _trigger_auto_fetch(self, url: str, fetch_id: int):
        if url == self.current_url and self.current_video_info is not None:
            self._set_button_ready()
            return

        threading.Thread(
            target=self._fetch_info_thread,
            args=(url, fetch_id),
            daemon=True
        ).start()

    def _fetch_info_thread(self, url: str, fetch_id: int):
        try:
            is_playlist_only = "playlist?list=" in url and "watch?v=" not in url
            ydl_options = {
                "skip_download": True,
                "nocheckcertificate": True,
                "noplaylist": not is_playlist_only,
                "quiet": True,
                "no_warnings": True,
                "socket_timeout": 8,
                "retries": 1,
            }

            if is_playlist_only:
                ydl_options["extract_flat"] = "in_playlist"

            cookies_browser = self.cookies_var.get()
            if cookies_browser != "Kapalı":
                ydl_options["cookiesfrombrowser"] = (cookies_browser.lower(),)

            with yt_dlp.YoutubeDL(ydl_options) as ydl:
                info = ydl.extract_info(url, download=False)

            if fetch_id != self._fetch_id:
                return

            if not info:
                raise ValueError("Video bilgisi alınamadı.")

            thumbnail_url = info.get("thumbnail")
            is_playlist = info.get("_type") == "playlist"
            entries = info.get("entries", []) if is_playlist else []

            if not thumbnail_url and is_playlist and entries:
                first = entries[0]
                thumbnail_url = first.get("thumbnail") or (first.get("thumbnails", [{}])[0].get("url") if first.get("thumbnails") else None)

            image_data = None
            if thumbnail_url:
                try:
                    req = urllib.request.Request(thumbnail_url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=3.0) as response:
                        image_data = response.read()
                except Exception:
                    image_data = None

            formats = info.get("formats", [])
            resolutions_set = set()
            res_size_map = {}
            best_audio_size = 0

            for fmt in formats:
                if fmt.get("vcodec") == "none" and fmt.get("acodec") != "none":
                    a_size = fmt.get("filesize") or fmt.get("filesize_approx") or 0
                    if a_size > best_audio_size:
                        best_audio_size = a_size

            for fmt in formats:
                height = fmt.get("height")
                vcodec = fmt.get("vcodec", "")
                if height and vcodec != "none" and height >= 144:
                    resolutions_set.add(height)
                    v_size = fmt.get("filesize") or fmt.get("filesize_approx") or 0
                    total_est = v_size + best_audio_size if v_size > 0 else 0
                    if height not in res_size_map or total_est > res_size_map[height]:
                        res_size_map[height] = total_est

            resolutions = sorted(list(resolutions_set), reverse=True)

            self.root.after(0, lambda: self._apply_fetched_info(
                url, info, resolutions, res_size_map, best_audio_size, image_data, fetch_id
            ))

        except Exception as exc:
            err_msg = str(exc)
            if fetch_id == self._fetch_id:
                self.root.after(0, lambda: self._handle_fetch_error(err_msg))

    def _apply_fetched_info(self, url: str, info: dict, resolutions: list, res_size_map: dict, best_audio_size: int, image_data: bytes | None, fetch_id: int):
        if fetch_id != self._fetch_id:
            return

        self.current_video_info = info
        self.current_url = url
        self.available_resolutions = resolutions
        self.resolution_size_map = res_size_map
        self.audio_size_estimate = best_audio_size

        title = info.get("title", "Bilinmeyen Başlık")
        channel = info.get("uploader") or info.get("channel") or "Bilinmeyen Kanal"
        is_playlist = info.get("_type") == "playlist"

        if is_playlist:
            entries = info.get("entries", [])
            duration_str = f"{len(entries)} Video"
            video_type = "Oynatma Listesi"
            self.selected_playlist_indices = list(range(len(entries)))
            self.playlist_btn.pack(fill="x", pady=(4, 0))
            detail_text = f"Tür: {video_type}  |  Kanal: {channel}\nİçerik: {duration_str}"
        else:
            duration = info.get("duration")
            duration_str = format_duration(duration)
            video_type = "Video"
            self.selected_playlist_indices = None
            self.playlist_btn.pack_forget()
            detail_text = f"Tür: {video_type}  |  Kanal: {channel}  |  Süre: {duration_str}"

            if duration:
                self.clip_end_var.set(duration_str)

        self.video_title_label.configure(text=title)
        self.video_detail_label.configure(text=detail_text)

        # Kapak Görselini yumuşakça oluştur
        if image_data:
            try:
                raw_image = Image.open(io.BytesIO(image_data))
                photo = ctk.CTkImage(light_image=raw_image, dark_image=raw_image, size=(140, 80))
                self.active_thumbnail_image = photo
                self.thumbnail_label.configure(image=photo, text="")
            except Exception:
                self.thumbnail_label.configure(text="[Kapak Yüklenemedi]", image=None)
        else:
            self.thumbnail_label.configure(text="[Kapak Yok]", image=None)

        self.on_format_changed()
        self.status_label.configure(text="")
        self._set_button_ready()

    def _set_button_ready(self):
        """İndir butonunu hazır duruma getirir ve yumuşak parıltı (breathing pulse) başlatır."""
        self.download_btn.configure(state="normal", text="İNDİR", fg_color=Theme.COLOR_ACCENT, text_color="#FFFFFF")
        AnimationManager.start_pulse(
            self.download_btn,
            prop_name="fg_color",
            color_a=Theme.COLOR_ACCENT,
            color_b=Theme.COLOR_ACCENT_HOVER,
            pulse_id="download_btn_pulse",
            cycle_ms=Theme.TIME_PULSE
        )

    def _handle_fetch_error(self, err_msg: str = ""):
        AnimationManager.stop_pulse("download_btn_pulse")
        self.current_video_info = None
        self.download_btn.configure(state="disabled", text="✕ Video Alınamadı", fg_color=Theme.COLOR_SECONDARY_BTN, text_color=Theme.COLOR_TEXT_MUTED)
        self.thumbnail_label.configure(text="✕", image=None)
        self.playlist_btn.pack_forget()

        if "unavailable" in err_msg.lower():
            self.video_title_label.configure(text="Video Kullanılamıyor")
            self.video_detail_label.configure(text="Bu video YouTube üzerinde gizli veya silinmiş.")
            self.status_label.configure(text="Hata: Video kullanılamıyor!", text_color=Theme.COLOR_DANGER)
            ToastManager.show(self.root, "Bu video YouTube üzerinde kullanılamıyor!", toast_type="danger", duration_ms=3500)
        else:
            self.video_title_label.configure(text="Video Bilgisi Alınamadı")
            self.video_detail_label.configure(text="Bağlantıyı kontrol edip tekrar deneyin.")
            self.status_label.configure(text="Hata: Video bilgileri taranamadı!", text_color=Theme.COLOR_DANGER)
            ToastManager.show(self.root, "Video bilgileri alınamadı!", toast_type="danger", duration_ms=3000)

        self.on_format_changed()

    def on_format_changed(self):
        fmt = self.format_var.get()
        duration = (self.current_video_info.get("duration") or 0) if self.current_video_info else 0

        if fmt == "mp4":
            values = []
            if self.available_resolutions:
                for h in self.available_resolutions:
                    sz = self.resolution_size_map.get(h, 0)
                    sz_str = f" (~{format_bytes(sz)})" if sz > 0 else ""
                    values.append(f"{h}p{sz_str}")
            else:
                values = ["En İyi Kalite", "1080p", "720p", "480p", "360p"]
            self.quality_combobox.configure(values=values)
            self.quality_combobox.set(values[0])
            self.subtitles_check.configure(state="normal")
        elif fmt == "mp3":
            sz_320 = format_bytes((duration * 320 * 1000) / 8) if duration else None
            sz_192 = format_bytes((duration * 192 * 1000) / 8) if duration else None
            sz_128 = format_bytes((duration * 128 * 1000) / 8) if duration else None

            v320 = f"320 kbps (Yüksek Kalite)" + (f" (~{sz_320})" if sz_320 else "")
            v192 = f"192 kbps (Standart)" + (f" (~{sz_192})" if sz_192 else "")
            v128 = f"128 kbps (Düşük Boyut)" + (f" (~{sz_128})" if sz_128 else "")

            values = [v320, v192, v128]
            self.quality_combobox.configure(values=values)
            self.quality_combobox.set(v192)
            self.subtitles_check.configure(state="disabled")
        else:
            sz_m4a = format_bytes(self.audio_size_estimate) if self.audio_size_estimate > 0 else None
            m4a_label = "Orijinal Kalite (AAC/M4A)" + (f" (~{sz_m4a})" if sz_m4a else "")
            self.quality_combobox.configure(values=[m4a_label])
            self.quality_combobox.set(m4a_label)
            self.subtitles_check.configure(state="disabled")

    def _open_playlist_window(self):
        if not self.current_video_info or self.current_video_info.get("_type") != "playlist":
            return

        entries = self.current_video_info.get("entries", [])
        if not entries:
            return

        win = ctk.CTkToplevel(self.root)
        win.title("Oynatma Listesi Seçimi")
        win.geometry("440x540")
        win.configure(fg_color=Theme.COLOR_BG)
        win.transient(self.root)
        win.grab_set()

        head = ctk.CTkFrame(win, fg_color="transparent")
        head.pack(fill="x", padx=16, pady=(14, 6))

        ctk.CTkLabel(
            head,
            text=f"Listeden İndirilecek Videolar ({len(entries)})",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=13, weight="bold"),
            text_color=Theme.COLOR_TEXT
        ).pack(anchor="w")

        quick_frame = ctk.CTkFrame(win, fg_color="transparent")
        quick_frame.pack(fill="x", padx=16, pady=4)

        def select_all():
            for var in self._temp_vars:
                var.set(True)

        def deselect_all():
            for var in self._temp_vars:
                var.set(False)

        ctk.CTkButton(
            quick_frame,
            text="Tümünü Seç",
            command=select_all,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11),
            fg_color=Theme.COLOR_SECONDARY_BTN,
            hover_color=Theme.COLOR_SECONDARY_HOVER,
            corner_radius=Theme.RADIUS_CHIP,
            height=28
        ).pack(side="left", fill="x", expand=True, padx=(0, 4))

        ctk.CTkButton(
            quick_frame,
            text="Tümünü Kaldır",
            command=deselect_all,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11),
            fg_color=Theme.COLOR_SECONDARY_BTN,
            hover_color=Theme.COLOR_SECONDARY_HOVER,
            corner_radius=Theme.RADIUS_CHIP,
            height=28
        ).pack(side="right", fill="x", expand=True, padx=(4, 0))

        scroll_frame = ctk.CTkScrollableFrame(win, fg_color=Theme.COLOR_CARD, corner_radius=Theme.RADIUS_CHIP)
        scroll_frame.pack(fill="both", expand=True, padx=16, pady=8)

        self._temp_vars = []
        for i, entry in enumerate(entries):
            var = ctk.BooleanVar(value=(i in self.selected_playlist_indices))
            self._temp_vars.append(var)

            title = entry.get("title", f"Video {i+1}")
            ctk.CTkCheckBox(
                scroll_frame,
                text=f"{i+1}. {title}",
                variable=var,
                font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11),
                text_color=Theme.COLOR_TEXT,
                fg_color=Theme.COLOR_ACCENT,
                hover_color=Theme.COLOR_ACCENT_HOVER,
                corner_radius=4
            ).pack(anchor="w", pady=4)

        def save_selection():
            self.selected_playlist_indices = [i for i, var in enumerate(self._temp_vars) if var.get()]
            win.destroy()
            ToastManager.show(self.root, f"{len(self.selected_playlist_indices)} video seçildi.", toast_type="info", duration_ms=2500)

        ctk.CTkButton(
            win,
            text="Seçimi Kaydet",
            command=save_selection,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12, weight="bold"),
            fg_color=Theme.COLOR_ACCENT,
            hover_color=Theme.COLOR_ACCENT_HOVER,
            text_color="#FFFFFF",
            corner_radius=Theme.RADIUS_INPUT,
            height=36
        ).pack(fill="x", padx=16, pady=(4, 14))

    def select_download_folder(self):
        selected_dir = ctk.filedialog.askdirectory(
            title="İndirme Klasörünü Seçin",
            initialdir=self.download_dir_var.get()
        )
        if selected_dir:
            self.download_dir_var.set(selected_dir)
            save_config({"download_dir": selected_dir})
            ToastManager.show(self.root, "İndirme klasörü güncellendi.", toast_type="info", duration_ms=2500)

    def progress_hook(self, data: dict):
        if self.cancel_download:
            raise Exception("İndirme iptal edildi")

        filename = data.get("filename")
        if filename:
            self.current_download_base = os.path.splitext(filename)[0]

        status = data.get("status")
        if status == "downloading":
            total_bytes = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            downloaded_bytes = data.get("downloaded_bytes") or 0
            speed = data.get("speed") or 0.0

            self.root.after(0, lambda: self._update_progress_ui(downloaded_bytes, total_bytes, speed))
        elif status == "finished":
            self.root.after(0, self._on_download_finished_ui)

    def _update_progress_ui(self, downloaded_bytes: int, total_bytes: int, speed: float):
        speed_mb = speed / (1024 * 1024) if speed else 0.0

        if total_bytes > 0:
            target_pct = downloaded_bytes / total_bytes
            
            # Değer değişimi ani değil, yumuşak number-tween ile akar
            AnimationManager.animate_number(
                self.progress_bar,
                setter_fn=self.progress_bar.set,
                start_val=self._current_progress_val,
                end_val=target_pct,
                duration_ms=200,
                easing_fn=ease_out_cubic
            )
            self._current_progress_val = target_pct

            total_mb = total_bytes / (1024 * 1024)
            down_mb = downloaded_bytes / (1024 * 1024)
            pct_100 = target_pct * 100
            
            self.download_btn.configure(text=f"İNDİRİLİYOR… %{pct_100:.0f}")
            self.status_label.configure(
                text=f"%{pct_100:.1f} | {down_mb:.1f}MB / {total_mb:.1f}MB | {speed_mb:.1f} MB/s",
                text_color=Theme.COLOR_SUCCESS
            )
        else:
            self.status_label.configure(
                text=f"İndiriliyor... | Hız: {speed_mb:.1f} MB/s",
                text_color=Theme.COLOR_SUCCESS
            )

    def _on_download_finished_ui(self):
        self.progress_bar.set(1.0)
        self._current_progress_val = 1.0
        self.download_btn.configure(text="DÖNÜŞTÜRÜLÜYOR…")
        self.status_label.configure(text="Dosya işleniyor ve kaydediliyor...", text_color=Theme.COLOR_TEXT_MUTED)

    def cancel_download_action(self):
        if self.cancel_download:
            return
        self.cancel_download = True
        self.cancel_btn.configure(state="disabled")
        self.status_label.configure(text="İptal ediliyor, lütfen bekleyin...", text_color=Theme.COLOR_DANGER)

    def start_download_action(self, event=None):
        if self.download_btn.cget("state") == "disabled":
            return

        url = self.url_var.get().strip()
        if not is_valid_url(url):
            return

        # Zaman aralığı doğrulaması
        if self.clip_enabled_var.get():
            start_sec = parse_time_str(self.clip_start_var.get())
            end_sec = parse_time_str(self.clip_end_var.get())
            if start_sec is None or end_sec is None or end_sec <= start_sec:
                ToastManager.show(self.root, "Hata: Bitiş süresi başlangıçtan büyük olmalıdır!", toast_type="danger")
                AnimationManager.animate_shake(self.clip_start_entry, self.adv_card, base_padx=Theme.SPACE_XL)
                return

        is_playlist = self.current_video_info and self.current_video_info.get("_type") == "playlist"
        if is_playlist and self.selected_playlist_indices is not None and not self.selected_playlist_indices:
            self.status_label.configure(text="Hata: İndirilecek video seçilmedi!", text_color=Theme.COLOR_DANGER)
            ToastManager.show(self.root, "İndirilecek video seçilmedi!", toast_type="danger")
            return

        # Animasyonlu parıltıyı durdur ve indirme durumunu başlat
        AnimationManager.stop_pulse("download_btn_pulse")
        self._hide_action_links()
        self.is_downloading = True
        self.cancel_download = False
        self._current_progress_val = 0.0

        self.cancel_btn.pack(side="right", padx=(6, 0))
        self.download_btn.configure(state="disabled", text="⏳ BAŞLATILIYOR...", fg_color=Theme.COLOR_SECONDARY_BTN, text_color=Theme.COLOR_TEXT_MUTED)
        self.cancel_btn.configure(state="normal", fg_color=Theme.COLOR_SECONDARY_BTN)
        self.progress_bar.set(0)
        self.status_label.configure(text="İndirme hazırlanıyor...", text_color=Theme.COLOR_TEXT_MUTED)

        save_config({
            "last_format": self.format_var.get(),
            "cookies_browser": self.cookies_var.get(),
            "subtitles_enabled": self.subtitles_var.get()
        })

        threading.Thread(target=self._download_thread, daemon=True).start()

    def _download_thread(self):
        try:
            url = self.url_var.get().strip()
            selected_format = self.format_var.get()
            selected_quality = self.quality_var.get()
            target_dir = self.download_dir_var.get()

            if not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)

            is_playlist = self.current_video_info and self.current_video_info.get("_type") == "playlist"
            if is_playlist:
                output_template = os.path.join(target_dir, "%(playlist_title)s", "%(title)s.%(ext)s")
            else:
                output_template = os.path.join(target_dir, "%(title)s.%(ext)s")

            ffmpeg_path = get_ffmpeg_path()

            common_opts = {
                "outtmpl": output_template,
                "progress_hooks": [self.progress_hook],
                "match_filter": lambda info, *args, **kwargs: "İptal edildi" if self.cancel_download else None,
                "nocheckcertificate": True,
                "socket_timeout": 20,
                "retries": 5,
                "fragment_retries": 5,
                "http_chunk_size": 10485760,
            }

            if not is_playlist:
                common_opts["noplaylist"] = True

            if ffmpeg_path:
                common_opts["ffmpeg_location"] = ffmpeg_path

            cookies_browser = self.cookies_var.get()
            if cookies_browser != "Kapalı":
                common_opts["cookiesfrombrowser"] = (cookies_browser.lower(),)

            # Zaman aralığı kesme
            if self.clip_enabled_var.get():
                start_sec = parse_time_str(self.clip_start_var.get())
                end_sec = parse_time_str(self.clip_end_var.get())
                if start_sec is not None and end_sec is not None and end_sec > start_sec:
                    common_opts["download_ranges"] = download_range_func(None, [(start_sec, end_sec)])
                    common_opts["force_keyframes_at_cuts"] = True

            if selected_format == "mp4":
                height_match = re.search(r"(\d+)p", selected_quality)
                if ffmpeg_path:
                    if height_match:
                        h = height_match.group(1)
                        format_query = f"bestvideo[height<={h}]+bestaudio/best[height<={h}]/best"
                    else:
                        format_query = "bestvideo+bestaudio/best"

                    ydl_opts = {
                        **common_opts,
                        "format": format_query,
                        "merge_output_format": "mp4",
                    }
                else:
                    # FFmpeg tespit edilemediyse birleştirme gerektirmeyen tek parça en iyi akışı indir
                    ydl_opts = {
                        **common_opts,
                        "format": "best[ext=mp4]/best",
                    }

                if self.subtitles_var.get():
                    ydl_opts["writesubtitles"] = True          # Kanal sahibinin yüklediği resmi altyazılar
                    ydl_opts["writeautomaticsub"] = True       # YouTube'un otomatik oluşturduğu altyazılar
                    
                    sub_lang = self.default_sub_lang_var.get() or self.config.get("default_subtitle_lang", "tr")
                    if sub_lang == "tr":
                        ydl_opts["subtitleslangs"] = ["tr.*", "tr", "en.*", "en"]
                    elif sub_lang == "en":
                        ydl_opts["subtitleslangs"] = ["en.*", "en", "tr.*", "tr"]
                    elif sub_lang == "all":
                        ydl_opts["subtitleslangs"] = ["all"]
                    else:
                        ydl_opts["subtitleslangs"] = [sub_lang, "en"]

                    ydl_opts["subtitlesformat"] = "best"
                    ydl_opts["embedsubtitles"] = True

            elif selected_format == "m4a":
                ydl_opts = {
                    **common_opts,
                    "format": "bestaudio[ext=m4a]/bestaudio/best",
                }
                if ffmpeg_path:
                    ydl_opts["postprocessors"] = [
                        {"key": "FFmpegMetadata", "add_metadata": True},
                        {"key": "EmbedThumbnail", "already_have_thumbnail": False}
                    ]
                    ydl_opts["writethumbnail"] = True
            else:
                bitrate = "192"
                if "320" in selected_quality:
                    bitrate = "320"
                elif "128" in selected_quality:
                    bitrate = "128"

                if ffmpeg_path:
                    ydl_opts = {
                        **common_opts,
                        "format": "bestaudio/best",
                        "postprocessors": [
                            {
                                "key": "FFmpegExtractAudio",
                                "preferredcodec": "mp3",
                                "preferredquality": bitrate,
                            },
                            {"key": "FFmpegMetadata", "add_metadata": True},
                            {"key": "EmbedThumbnail", "already_have_thumbnail": False}
                        ],
                        "writethumbnail": True,
                    }
                else:
                    # FFmpeg yoksa MP3 dönüştürme yapılamaz; orijinal sesi doğrudan indir
                    ydl_opts = {
                        **common_opts,
                        "format": "bestaudio/best",
                    }

            if is_playlist and self.selected_playlist_indices is not None:
                items_str = ",".join(str(i + 1) for i in self.selected_playlist_indices)
                ydl_opts["playlist_items"] = items_str

            self.current_download_base = None

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if not info:
                    raise ValueError("Video indirilemedi!")

            if self.cancel_download:
                raise Exception("İndirme iptal edildi")

            if self.current_download_base:
                for ext in [".webp", ".jpg"]:
                    f = self.current_download_base + ext
                    if os.path.exists(f):
                        try:
                            os.remove(f)
                        except Exception:
                            pass

            downloaded_file = self._find_downloaded_file(info, target_dir, selected_format)
            self.last_downloaded_file = downloaded_file

            file_size_str = "Bilinmiyor"
            if downloaded_file and os.path.exists(downloaded_file):
                file_size_str = format_bytes(os.path.getsize(downloaded_file))

            video_title = info.get("title", "İndirilen Video")
            add_history_item(
                title=video_title,
                url=url,
                media_format=selected_format,
                quality=selected_quality.split("(")[0].strip(),
                size_str=file_size_str,
                filepath=downloaded_file or target_dir
            )

            show_windows_notification("MP3MP4YT", f"'{video_title}' başarıyla indirildi!")
            self.root.after(0, lambda: self._show_success_animation(video_title, downloaded_file))

        except Exception as exc:
            error_message = str(exc)
            self.root.after(0, lambda: self._handle_download_error(error_message))

        finally:
            self.is_downloading = False

    def _find_downloaded_file(self, info: dict, target_dir: str, target_ext: str) -> str | None:
        title = info.get("title", "")
        clean_title = re.sub(r'[\\/*?:"<>|]', "", title)

        if self.current_download_base:
            for ext in [f".{target_ext}", ".mp4", ".mp3", ".m4a"]:
                candidate = self.current_download_base + ext
                if os.path.exists(candidate):
                    return candidate

        if os.path.exists(target_dir):
            for file in os.listdir(target_dir):
                if file.startswith(clean_title[:15]):
                    return os.path.join(target_dir, file)

        return None

    def _cleanup_download_artifacts(self):
        if not self.current_download_base:
            return
        for ext in [".part", ".ytdl", ".webm", ".m4a", ".mp4", ".mp3", ".webp", ".jpg"]:
            f = self.current_download_base + ext
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass

    def _handle_download_error(self, error_message: str):
        AnimationManager.stop_pulse("download_btn_pulse")
        if "İndirme iptal edildi" in error_message:
            self.status_label.configure(text="Bilgi: İndirme iptal edildi.", text_color=Theme.COLOR_TEXT)
            ToastManager.show(self.root, "İndirme iptal edildi.", toast_type="info")
        else:
            self.status_label.configure(text=f"Hata: {error_message[:65]}", text_color=Theme.COLOR_DANGER)
            ToastManager.show(self.root, "İndirme sırasında bir hata oluştu!", toast_type="danger")

        self._cleanup_download_artifacts()
        self.cancel_btn.pack_forget()
        self.download_btn.configure(state="normal", text="İNDİR", fg_color=Theme.COLOR_ACCENT, text_color="#FFFFFF")
        self.progress_bar.set(0)

    def _show_success_animation(self, title: str, downloaded_path: str | None):
        """İndirme bitişinde renk geçişi ve eylem butonlarının akıcı gösterimi."""
        self.cancel_btn.pack_forget()
        
        # Buton rengini yumuşakça SUCCESS yeşiline çek
        AnimationManager.animate_color(
            self.download_btn,
            prop_name="fg_color",
            start_color=Theme.COLOR_ACCENT,
            end_color=Theme.COLOR_SUCCESS,
            duration_ms=Theme.TIME_TRANSITION
        )
        self.download_btn.configure(state="normal", text="✔ TAMAMLANDI", text_color="#FFFFFF")
        self.progress_bar.set(1.0)
        self.status_label.configure(text="İndirme başarıyla tamamlandı!", text_color=Theme.COLOR_SUCCESS)

        # Uygulama içi modern toast bildirimi
        ToastManager.show(self.root, f"'{title[:28]}' başarıyla indirildi!", toast_type="success")

        # 3.5 saniye sonra İNDİR butonunu tekrar hazır durumuna döndür
        self._restore_timer = self.root.after(3500, self._restore_download_button)
        self._show_action_links(downloaded_path)

    def _restore_download_button(self):
        self._restore_timer = None
        self.progress_bar.set(0)
        self._current_progress_val = 0.0
        if not self.is_downloading and self.current_video_info:
            AnimationManager.animate_color(
                self.download_btn,
                prop_name="fg_color",
                start_color=Theme.COLOR_SUCCESS,
                end_color=Theme.COLOR_ACCENT,
                duration_ms=Theme.TIME_TRANSITION,
                on_complete=self._set_button_ready
            )
            self.download_btn.configure(text="İNDİR")
        elif not self.is_downloading:
            self.download_btn.configure(state="disabled", text="İNDİR", fg_color=Theme.COLOR_SECONDARY_BTN, text_color=Theme.COLOR_TEXT_MUTED)

    def _show_action_links(self, filepath: str | None):
        """Tamamlanınca çıkan 'Dosyayı Aç' ve 'Klasörde Göster' butonlarını gösterir."""
        self._hide_action_links()

        path = filepath or self.download_dir_var.get()
        self.action_links_frame.pack(pady=(Theme.SPACE_XS, Theme.SPACE_SM))

        btn_open = ctk.CTkButton(
            self.action_links_frame,
            text="▶ Dosyayı Aç",
            command=lambda: open_file(path),
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11, weight="bold"),
            fg_color=Theme.COLOR_SECONDARY_BTN,
            hover_color=Theme.COLOR_SECONDARY_HOVER,
            text_color=Theme.COLOR_TEXT,
            corner_radius=Theme.RADIUS_CHIP,
            height=30
        )
        btn_open.pack(side="left", padx=Theme.SPACE_XS)

        btn_reveal = ctk.CTkButton(
            self.action_links_frame,
            text="📁 Klasörde Göster",
            command=lambda: reveal_in_explorer(path),
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11, weight="bold"),
            fg_color=Theme.COLOR_SECONDARY_BTN,
            hover_color=Theme.COLOR_SECONDARY_HOVER,
            text_color=Theme.COLOR_TEXT,
            corner_radius=Theme.RADIUS_CHIP,
            height=30
        )
        btn_reveal.pack(side="left", padx=Theme.SPACE_XS)

    def _hide_action_links(self):
        for widget in self.action_links_frame.winfo_children():
            widget.destroy()
        self.action_links_frame.pack_forget()

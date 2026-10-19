"""
MP3MP4YT - Tasarım ve Tema Sistemi (Design Tokens)
Windows 11 Fluent + YouTube Dark Mode ilkelerine göre yapılandırılmış renk,
ölçü, tipografi ve animasyon sabitleri.
"""

import os
from typing import Tuple

class Theme:
    # -------------------------------------------------------------------------
    # 1. TEMEL RENK TOKENLARI (Three-tier Elevation)
    # -------------------------------------------------------------------------
    # Katman 1: Ana Pencere ve zemin
    COLOR_BG = ("#F4F5F8", "#0D0E11")
    
    # Katman 2: Kartlar ve paneller (Zeminden bir ton açık)
    COLOR_CARD = ("#FFFFFF", "#16171B")
    COLOR_CARD_BORDER = ("#E2E4E9", "#25272D")
    COLOR_CARD_BORDER_HOVER = ("#CBD0D8", "#34373F")
    
    # Katman 3: Girdiler ve etkileşimli kutular (Karttan bir ton açık)
    COLOR_INPUT_BG = ("#EEF0F4", "#1F2126")
    COLOR_INPUT_BORDER = ("#D2D5DD", "#2F323A")
    COLOR_INPUT_BORDER_FOCUS = "#E11D48"

    # -------------------------------------------------------------------------
    # 2. VURGU VE EYLEM RENKLERİ (Accent & Feedback)
    # -------------------------------------------------------------------------
    COLOR_ACCENT = "#E11D48"
    COLOR_ACCENT_HOVER = "#BE123C"
    COLOR_ACCENT_ACTIVE = "#9F1239"
    COLOR_ACCENT_GRADIENT_START = "#F43F5E"
    COLOR_ACCENT_GRADIENT_END = "#BE123C"
    
    # İkincil eylemler
    COLOR_SECONDARY_BTN = ("#E5E7EB", "#272930")
    COLOR_SECONDARY_HOVER = ("#D1D5DB", "#363942")
    COLOR_SECONDARY_ACTIVE = ("#9CA3AF", "#1E2025")

    # Durum ve Geri Bildirim
    COLOR_SUCCESS = "#22C55E"
    COLOR_SUCCESS_HOVER = "#16A34A"
    COLOR_DANGER = "#EF4444"
    COLOR_DANGER_HOVER = "#DC2626"
    COLOR_WARNING = "#F59E0B"

    # -------------------------------------------------------------------------
    # 3. TİPOGRAFİ RENKLERİ
    # -------------------------------------------------------------------------
    COLOR_TEXT = ("#18191C", "#F4F4F5")         # Ana başlıklar, buton yazıları
    COLOR_TEXT_MUTED = ("#64748B", "#9498A3")   # İkincil detaylar, süre, boyut
    COLOR_TEXT_DIM = ("#94A3B8", "#6B7280")     # İpuçları, pasif elemanlar

    # -------------------------------------------------------------------------
    # 4. YUMUŞAK PARILTI VE DOLGU TONLARI (Türev Tokenlar)
    # -------------------------------------------------------------------------
    ACCENT_SOFT = "#2B161E"        # Kırmızı yumuşak seçim arka planı
    ACCENT_GLOW_HEX = "#4A1220"    # Buton/focus yumuşak halkası
    SUCCESS_SOFT = "#14291E"       # Başarılı arka plan tonu
    DANGER_SOFT = "#2B1618"        # Hata arkalık tonu
    SHIMMER_BASE = "#1F2126"       # Skeleton animasyonu tabanı
    SHIMMER_HIGHLIGHT = "#2D313A"  # Skeleton animasyonu ışık çizgisi

    # -------------------------------------------------------------------------
    # 5. ÖLÇÜLER VE YARIÇAPLAR (Metrics & Radii)
    # -------------------------------------------------------------------------
    RADIUS_CARD = 14               # Kart köşeleri (Fluent card)
    RADIUS_INPUT = 10              # Girdi ve buton köşeleri
    RADIUS_CHIP = 8                # Rozet ve küçük butonlar
    RADIUS_FULL = 999              # Hap şeklinde yuvarlak elemanlar

    # Boşluk ölçeği (Spacing Scale)
    SPACE_XS = 4
    SPACE_SM = 8
    SPACE_MD = 12
    SPACE_LG = 16
    SPACE_XL = 24

    # -------------------------------------------------------------------------
    # 6. TİPOGRAFİ
    # -------------------------------------------------------------------------
    FONT_FAMILY = "Segoe UI"
    
    # -------------------------------------------------------------------------
    # 7. ANİMASYON SÜRELERİ (Milisaniye)
    # -------------------------------------------------------------------------
    TIME_MICRO = 140               # Buton basılma, tik atma
    TIME_HOVER = 180               # Renk ve çerçeve geçişi
    TIME_TRANSITION = 280          # Sekme, modal ve açılır paneller
    TIME_ENTRANCE = 450            # Kartların sırayla girişi
    TIME_PULSE = 2400              # "İNDİR" butonunun hazır nefes alma döngüsü

    # -------------------------------------------------------------------------
    # 8. ERİŞİLEBİLİRLİK: ANİMASYONLARI AZALT AYARI
    # -------------------------------------------------------------------------
    _reduce_animations = False

    @classmethod
    def set_reduce_animations(cls, reduce: bool):
        cls._reduce_animations = bool(reduce)

    @classmethod
    def is_reduced_motion(cls) -> bool:
        return cls._reduce_animations

    @classmethod
    def get_duration(cls, default_duration: int) -> int:
        """Animasyonları azalt ayarı açıksa süreyi 0 yapar, aksi halde orijinal süreyi döner."""
        return 0 if cls._reduce_animations else default_duration

# Geriye uyumluluk için modül seviyesinde değişken atamaları
COLOR_BG = Theme.COLOR_BG
COLOR_CARD = Theme.COLOR_CARD
COLOR_CARD_BORDER = Theme.COLOR_CARD_BORDER
COLOR_INPUT_BG = Theme.COLOR_INPUT_BG
COLOR_INPUT_BORDER = Theme.COLOR_INPUT_BORDER
COLOR_ACCENT = Theme.COLOR_ACCENT
COLOR_ACCENT_HOVER = Theme.COLOR_ACCENT_HOVER
COLOR_SECONDARY_BTN = Theme.COLOR_SECONDARY_BTN
COLOR_SECONDARY_HOVER = Theme.COLOR_SECONDARY_HOVER
COLOR_SUCCESS = Theme.COLOR_SUCCESS
COLOR_DANGER = Theme.COLOR_DANGER
COLOR_TEXT = Theme.COLOR_TEXT
COLOR_TEXT_MUTED = Theme.COLOR_TEXT_MUTED
FONT_FAMILY = Theme.FONT_FAMILY

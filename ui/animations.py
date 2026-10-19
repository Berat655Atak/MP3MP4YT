"""
MP3MP4YT - Mikro Etkileşim ve Animasyon Motoru
Ana iş parçacığını (UI thread) kilitlemeyen, 60 FPS hedefli
easing, renk enterpolasyonu, shake, pulse ve skeleton (shimmer) yöneticisi.
"""

import time
import math
from typing import Callable, Optional, Dict, Any
from ui.theme import Theme

# -----------------------------------------------------------------------------
# 1. MATEMATİKSEL EASING FONKSİYONLARI
# -----------------------------------------------------------------------------
def ease_out_cubic(t: float) -> float:
    """Standart yumuşak duruş eğrisi."""
    return 1.0 - math.pow(1.0 - t, 3)

def ease_in_cubic(t: float) -> float:
    """Çıkışlar için hızlanan eğri."""
    return math.pow(t, 3)

def ease_out_back(t: float, s: float = 1.70158) -> float:
    """Girişler için hafif yaylanmalı (elastic overshoot) eğri."""
    t -= 1.0
    return 1.0 + (s + 1.0) * math.pow(t, 3) + s * math.pow(t, 2)

def linear(t: float) -> float:
    """Doğrusal akış (sürekli dönen shimmer için)."""
    return t

# -----------------------------------------------------------------------------
# 2. RENK ENTERPOLASYONU YARDIMCILARI
# -----------------------------------------------------------------------------
def hex_to_rgb(hex_code) -> tuple[int, int, int]:
    """#RRGGBB metnini veya tema renk demetini (r, g, b) sayısal demetine dönüştürür."""
    if isinstance(hex_code, (tuple, list)):
        import customtkinter as ctk
        mode = ctk.get_appearance_mode().lower()
        hex_code = hex_code[0] if mode == "light" else hex_code[1]
    clean = str(hex_code).lstrip("#")
    if len(clean) == 3:
        clean = "".join([c * 2 for c in clean])
    return int(clean[0:2], 16), int(clean[2:4], 16), int(clean[4:6], 16)

def rgb_to_hex(r: int, g: int, b: int) -> str:
    """(r, g, b) tam sayılarını #RRGGBB formatına çevirir."""
    r = max(0, min(255, int(r)))
    g = max(0, min(255, int(g)))
    b = max(0, min(255, int(b)))
    return f"#{r:02x}{g:02x}{b:02x}"

def interpolate_color(color_start: str, color_end: str, t: float) -> str:
    """İki renk arasında t (0.0 - 1.0) oranına göre ara rengi hesaplar."""
    r1, g1, b1 = hex_to_rgb(color_start)
    r2, g2, b2 = hex_to_rgb(color_end)
    r = r1 + (r2 - r1) * t
    g = g1 + (g2 - g1) * t
    b = b1 + (b2 - b1) * t
    return rgb_to_hex(r, g, b)

# -----------------------------------------------------------------------------
# 3. ANİMASYON YÖNETİCİSİ (AnimationManager)
# -----------------------------------------------------------------------------
class AnimationManager:
    """
    Tkinter/CustomTkinter bileşenleri üzerinde periyodik frame tetiklemeleriyle
    donma yapmayan animasyonları koordine eder.
    """
    _active_pulses: Dict[str, bool] = {}

    @classmethod
    def animate_color(
        cls,
        widget,
        prop_name: str,
        start_color: str,
        end_color: str,
        duration_ms: int = Theme.TIME_HOVER,
        easing_fn: Callable[[float], float] = ease_out_cubic,
        on_complete: Optional[Callable[[], None]] = None
    ):
        """
        Widget üzerindeki bir renk özelliğini (fg_color, border_color vb.)
        belirtilen sürede pürüzsüzce ara renklere dönüştürür.
        """
        # Hareketi azalt ayarı aktifse anında hedef renge ata
        effective_duration = Theme.get_duration(duration_ms)
        if effective_duration == 0:
            try:
                widget.configure(**{prop_name: end_color})
            except Exception:
                pass
            if on_complete:
                on_complete()
            return

        start_time = time.perf_counter()
        dur_sec = effective_duration / 1000.0

        def _step():
            try:
                if not widget.winfo_exists():
                    return
            except Exception:
                return

            elapsed = time.perf_counter() - start_time
            progress = min(1.0, elapsed / dur_sec) if dur_sec > 0 else 1.0
            eased_t = easing_fn(progress)
            current_color = interpolate_color(start_color, end_color, eased_t)

            try:
                widget.configure(**{prop_name: current_color})
            except Exception:
                return

            if progress < 1.0:
                widget.after(16, _step)  # ~60 FPS
            else:
                try:
                    widget.configure(**{prop_name: end_color})
                except Exception:
                    pass
                if on_complete:
                    on_complete()

        _step()

    @classmethod
    def animate_number(
        cls,
        widget,
        setter_fn: Callable[[float], None],
        start_val: float,
        end_val: float,
        duration_ms: int = Theme.TIME_TRANSITION,
        easing_fn: Callable[[float], float] = ease_out_cubic,
        on_complete: Optional[Callable[[], None]] = None
    ):
        """
        Sayısal değerleri (yüzde, progress vb.) ani zıplama olmadan
        yumuşak bir eğriyle hedefe doğru kaydırır.
        """
        effective_duration = Theme.get_duration(duration_ms)
        if effective_duration == 0:
            setter_fn(end_val)
            if on_complete:
                on_complete()
            return

        start_time = time.perf_counter()
        dur_sec = effective_duration / 1000.0

        def _step():
            try:
                if not widget.winfo_exists():
                    return
            except Exception:
                return

            elapsed = time.perf_counter() - start_time
            progress = min(1.0, elapsed / dur_sec) if dur_sec > 0 else 1.0
            eased_t = easing_fn(progress)
            cur = start_val + (end_val - start_val) * eased_t
            
            try:
                setter_fn(cur)
            except Exception:
                return

            if progress < 1.0:
                widget.after(16, _step)
            else:
                setter_fn(end_val)
                if on_complete:
                    on_complete()

        _step()

    @classmethod
    def animate_shake(
        cls,
        widget,
        container_frame,
        base_padx: int = 24,
        amplitude: int = 6,
        duration_ms: int = 280,
        on_complete: Optional[Callable[[], None]] = None
    ):
        """
        Geçersiz link durumunda girdi kutusunu yatayda 3 kez hafifçe sallar.
        """
        if Theme.is_reduced_motion():
            if on_complete:
                on_complete()
            return

        offsets = [amplitude, -amplitude, amplitude * 0.7, -amplitude * 0.7, amplitude * 0.3, 0]
        step_interval = max(16, duration_ms // len(offsets))

        def _run_step(idx: int):
            if idx >= len(offsets):
                try:
                    container_frame.pack_configure(padx=base_padx)
                except Exception:
                    pass
                if on_complete:
                    on_complete()
                return

            offset = offsets[idx]
            try:
                container_frame.pack_configure(padx=(base_padx + int(offset), base_padx - int(offset)))
            except Exception:
                pass

            widget.after(step_interval, lambda: _run_step(idx + 1))

        _run_step(0)

    @classmethod
    def start_pulse(
        cls,
        widget,
        prop_name: str,
        color_a: str,
        color_b: str,
        pulse_id: str,
        cycle_ms: int = Theme.TIME_PULSE
    ):
        """
        Buton boşta ve indirmeye hazırken nazikçe parıldayan (breathing glow)
        sonsuz bir döngü başlatır.
        """
        if Theme.is_reduced_motion():
            return

        cls._active_pulses[pulse_id] = True
        half_cycle = cycle_ms // 2

        def _forward():
            if not cls._active_pulses.get(pulse_id, False):
                return
            cls.animate_color(
                widget, prop_name, color_a, color_b,
                duration_ms=half_cycle,
                easing_fn=ease_out_cubic,
                on_complete=_backward
            )

        def _backward():
            if not cls._active_pulses.get(pulse_id, False):
                return
            cls.animate_color(
                widget, prop_name, color_b, color_a,
                duration_ms=half_cycle,
                easing_fn=ease_out_cubic,
                on_complete=_forward
            )

        _forward()

    @classmethod
    def stop_pulse(cls, pulse_id: str):
        """Devam eden bir parıldama döngüsünü durdurur."""
        cls._active_pulses[pulse_id] = False

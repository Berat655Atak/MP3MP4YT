"""
MP3MP4YT - Modern Toast Bildirim Bileşeni
Ekranın altındaki alana zarifçe yerleşen, aşırı yer kaplamayan,
kompakt ve modern bildirim kartı.
"""

import customtkinter as ctk
from ui.theme import Theme
from ui.animations import AnimationManager, ease_out_cubic

class ToastManager:
    """Uygulama içi dinamik ve kompakt toast bildirimlerini yönetir."""
    _current_toast = None
    _dismiss_job = None

    @classmethod
    def show(
        cls,
        parent_root,
        message: str,
        toast_type: str = "success",
        duration_ms: int = 2800
    ):
        # Önceki zamanlayıcı varsa iptal et
        if cls._dismiss_job and parent_root:
            try:
                parent_root.after_cancel(cls._dismiss_job)
                cls._dismiss_job = None
            except Exception:
                pass

        # Önceki toast varsa temizle
        if cls._current_toast and cls._current_toast.winfo_exists():
            try:
                cls._current_toast.destroy()
            except Exception:
                pass
            cls._current_toast = None

        indicator_color = Theme.COLOR_SUCCESS if toast_type == "success" else (
            Theme.COLOR_DANGER if toast_type == "danger" else (
                Theme.COLOR_ACCENT if toast_type == "info" else Theme.COLOR_WARNING
            )
        )
        icon = "✔" if toast_type == "success" else (
            "✕" if toast_type == "danger" else (
                "ℹ" if toast_type == "info" else "⚠"
            )
        )

        # 32px sabit yükseklik - pack_propagate(False) ile kesinlikle genişlemez
        toast_frame = ctk.CTkFrame(
            parent_root,
            fg_color=Theme.COLOR_CARD,
            corner_radius=Theme.RADIUS_CHIP,
            border_width=1,
            border_color=indicator_color,
            height=32
        )
        toast_frame.pack_propagate(False)
        cls._current_toast = toast_frame

        # Sol durum ikonu
        icon_lbl = ctk.CTkLabel(
            toast_frame,
            text=icon,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12, weight="bold"),
            text_color=indicator_color,
            width=20
        )
        icon_lbl.pack(side="left", padx=(10, 4))

        # Mesaj metni
        msg_lbl = ctk.CTkLabel(
            toast_frame,
            text=message,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11, weight="bold"),
            text_color=Theme.COLOR_TEXT,
            anchor="w"
        )
        msg_lbl.pack(side="left", fill="x", expand=True, padx=(0, 6))

        # Sağ hızlı kapatma butonu
        close_btn = ctk.CTkButton(
            toast_frame,
            text="✕",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=10, weight="bold"),
            text_color=Theme.COLOR_TEXT_MUTED,
            hover_color=Theme.COLOR_CARD_BORDER,
            fg_color="transparent",
            width=22,
            height=22,
            corner_radius=11,
            command=lambda: cls.dismiss(parent_root)
        )
        close_btn.pack(side="right", padx=(0, 6))

        # Hedef koordinatlar (URL kutusunun altındaki boşluğa tam oturur)
        target_rely = 0.94
        start_rely = 1.08

        if Theme.is_reduced_motion():
            toast_frame.place(relx=0.5, rely=target_rely, relwidth=0.92, anchor="s")
        else:
            toast_frame.place(relx=0.5, rely=start_rely, relwidth=0.92, anchor="s")
            AnimationManager.animate_number(
                toast_frame,
                setter_fn=lambda y: toast_frame.place_configure(rely=y) if toast_frame.winfo_exists() else None,
                start_val=start_rely,
                end_val=target_rely,
                duration_ms=Theme.TIME_TRANSITION,
                easing_fn=ease_out_cubic
            )

        # Otomatik kapanma zamanlayıcısı
        cls._dismiss_job = parent_root.after(duration_ms, lambda: cls.dismiss(parent_root))

    @classmethod
    def dismiss(cls, parent_root=None):
        """Bildirimi akıcı şekilde kapatır."""
        toast = cls._current_toast
        if not toast or not toast.winfo_exists():
            cls._current_toast = None
            return

        if cls._dismiss_job and parent_root:
            try:
                parent_root.after_cancel(cls._dismiss_job)
            except Exception:
                pass
            cls._dismiss_job = None

        if Theme.is_reduced_motion():
            try:
                toast.destroy()
            except Exception:
                pass
            cls._current_toast = None
        else:
            AnimationManager.animate_number(
                toast,
                setter_fn=lambda y: toast.place_configure(rely=y) if toast.winfo_exists() else None,
                start_val=0.94,
                end_val=1.08,
                duration_ms=160,
                on_complete=lambda: toast.destroy() if toast.winfo_exists() else None
            )
            cls._current_toast = None

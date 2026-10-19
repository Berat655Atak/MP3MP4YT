import os
import re
import shutil

# Geçersiz veya tek başına YouTube ana sayfası olan adresleri filtrelemek için desenler
INVALID_URL_PATTERNS = [
    r"^https?://(www\.)?youtube\.com/?$",
    r"^https?://youtu\.be/?$",
]

# Geçerli bir video veya oynatma listesi URL'si olup olmadığını denetleyen desen
VIDEO_URL_REGEX = r"(v=|youtu\.be/|shorts/|watch\?|embed/|playlist\?)"

def format_duration(seconds: int | float | None) -> str:
    """
    Saniye cinsinden verilen süreyi HH:MM:SS veya MM:SS formatına dönüştürür.
    """
    if not seconds:
        return "Bilinmiyor"
    minutes, sec = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{sec:02d}"
    return f"{minutes:02d}:{sec:02d}"

def is_valid_url(url: str) -> bool:
    """
    Girilen metnin geçerli bir YouTube video/playlist linki olup olmadığını doğrular.
    """
    if not url:
        return False
    clean_url = url.rstrip("/")
    for pattern in INVALID_URL_PATTERNS:
        if re.match(pattern, clean_url, re.IGNORECASE):
            return False
    if not re.search(VIDEO_URL_REGEX, url):
        return False
    return True

def get_ffmpeg_path() -> str | None:
    """
    FFmpeg çalıştırılabilir dosyasının konumunu otomatik olarak tespit eder.
    Öncelikle projenin 'bin' klasörünü, ardından sistem PATH ortam değişkenini kontrol eder.
    Böylece harici FFmpeg yüklemelerine gerek kalmadan bin/ içine atılan dosyalar da çalışır.
    """
    # Projenin kök dizinini ve bin klasörünü belirle
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bin_dir = os.path.join(base_dir, "bin")

    # Kontrol edilecek olası FFmpeg yolları
    possible_paths = [
        os.path.join(bin_dir, "ffmpeg.exe"),
        os.path.join(bin_dir, "ffmpeg", "bin", "ffmpeg.exe"),
        os.path.join(bin_dir, "ffmpeg"),
    ]

    for path in possible_paths:
        if os.path.isfile(path):
            return path
        elif os.path.isdir(path) and os.path.isfile(os.path.join(path, "ffmpeg.exe")):
            return os.path.join(path, "ffmpeg.exe")

    # Sistem PATH değişkeninde ffmpeg var mı kontrol et
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg

    # imageio_ffmpeg Python paketi mevcutsa otomatik kullan
    try:
        import imageio_ffmpeg
        ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
        if ffmpeg_bin and os.path.isfile(ffmpeg_bin):
            return ffmpeg_bin
    except Exception:
        pass

    return None

def format_bytes(size_bytes: int | float | None) -> str:
    """
    Bayt cinsinden verilen boyutu insan tarafından okunabilir bir formata (MB, GB vb.) dönüştürür.
    """
    if not size_bytes or size_bytes <= 0:
        return "Bilinmiyor"
    
    size = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            if unit in ["MB", "GB", "TB"]:
                return f"{size:.1f} {unit}"
            return f"{int(size)} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"

def parse_time_str(time_str: str) -> float | None:
    """
    '01:30', '1:25:40' veya doğrudan '90' gibi zaman metinlerini saniyeye dönüştürür.
    Hatalı veya boş girdilerde None döndürür.
    """
    if not time_str or not time_str.strip():
        return None
    
    clean = time_str.strip()
    parts = clean.split(":")
    try:
        if len(parts) == 1:
            val = float(parts[0])
            return val if val >= 0 else None
        elif len(parts) == 2:
            mins, secs = float(parts[0]), float(parts[1])
            return mins * 60 + secs
        elif len(parts) == 3:
            hrs, mins, secs = float(parts[0]), float(parts[1]), float(parts[2])
            return hrs * 3600 + mins * 60 + secs
    except (ValueError, TypeError):
        return None
    return None

def show_windows_notification(title: str, message: str):
    """
    Windows üzerinde sesli bildirim verir ve arka planda hafif bir toast uyarısı çıkarır.
    Arayüz akışını kilitlememek için ayrı bir thread'de yürütülür.
    """
    import threading
    def _worker():
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass

        try:
            import subprocess
            # Güvenli karakter kaçışı
            safe_title = title.replace('"', '`"').replace("'", "''")
            safe_msg = message.replace('"', '`"').replace("'", "''")
            
            ps_cmd = f"""
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
            $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
            $textNodes = $template.GetElementsByTagName("text")
            $textNodes.Item(0).AppendChild($template.CreateTextNode('{safe_title}')) > $null
            $textNodes.Item(1).AppendChild($template.CreateTextNode('{safe_msg}')) > $null
            $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("MP3MP4YT")
            $notification = [Windows.UI.Notifications.ToastNotification]::new($template)
            $notifier.Show($notification)
            """
            subprocess.run(
                ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_cmd],
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                timeout=6
            )
        except Exception:
            pass

    threading.Thread(target=_worker, daemon=True).start()

def reveal_in_explorer(filepath: str):
    """
    Dosyanın bulunduğu klasörü Windows Gezgini'nde açar ve ilgili dosyayı seçili hale getirir.
    Dosya bulunamazsa doğrudan ana klasörü açar.
    """
    if not filepath:
        return
    import subprocess
    try:
        norm = os.path.normpath(filepath)
        if os.path.isfile(norm):
            subprocess.run(f'explorer /select,"{norm}"', shell=True)
        elif os.path.isdir(norm):
            subprocess.run(f'explorer "{norm}"', shell=True)
        else:
            parent = os.path.dirname(norm)
            if os.path.exists(parent):
                subprocess.run(f'explorer "{parent}"', shell=True)
    except Exception:
        pass

def open_file(filepath: str):
    """Dosyayı sistemin varsayılan oynatıcısında başlatır."""
    if not filepath or not os.path.exists(filepath):
        return
    try:
        os.startfile(filepath)
    except Exception:
        pass



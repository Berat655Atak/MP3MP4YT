"""
MP3MP4YT - Otomatik Güncelleme ve Kütüphane Bakım Modülü
yt-dlp ve bağımlılıkların sürüm denetimini ve arka plan güncellemesini koordine eder.
"""

import sys
import os
import re
import json
import urllib.request
import subprocess
import yt_dlp

def parse_version_tuple(ver_str: str) -> tuple[int, ...]:
    """Sürüm metnini sayısal demete dönüştürür (örn: '2026.08.19' -> (2026, 8, 19))."""
    if not ver_str:
        return (0,)
    digits = re.findall(r"\d+", str(ver_str))
    return tuple(int(d) for d in digits) if digits else (0,)

def get_installed_ytdlp_version() -> str:
    """Yüklü yt-dlp sürümünü döndürür."""
    try:
        import importlib
        importlib.reload(yt_dlp)
        return getattr(yt_dlp.version, "__version__", "Bilinmiyor")
    except Exception:
        return getattr(yt_dlp.version, "__version__", "Bilinmiyor")

def check_ytdlp_update(timeout: float = 2.5) -> tuple[bool, str, str]:
    """
    PyPI üzerinden yt-dlp'nin en güncel sürümünü kontrol eder.
    Dönüş: (guncelleme_var_mi: bool, guncel_surum: str, kurulu_surum: str)
    """
    installed_ver = get_installed_ytdlp_version()
    try:
        req = urllib.request.Request(
            "https://pypi.org/pypi/yt-dlp/json",
            headers={"User-Agent": "MP3MP4YT-Updater"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as res:
            data = json.loads(res.read().decode("utf-8"))
            latest_ver = data.get("info", {}).get("version", "")
            
            if latest_ver and parse_version_tuple(latest_ver) > parse_version_tuple(installed_ver):
                return True, latest_ver, installed_ver
            return False, latest_ver or installed_ver, installed_ver
    except Exception:
        return False, installed_ver, installed_ver

def perform_ytdlp_upgrade(timeout: int = 90) -> tuple[bool, str]:
    """
    pip aracılığıyla yt-dlp'yi yükseltir (konsol penceresi açmadan).
    Dönüş: (basarili_mi: bool, mesaj: str)
    """
    try:
        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=creation_flags
        )
        if result.returncode == 0:
            new_ver = get_installed_ytdlp_version()
            return True, f"yt-dlp başarıyla güncellendi: v{new_ver}"
        else:
            err = result.stderr.strip() or result.stdout.strip()
            return False, f"Güncelleme yapılamadı: {err[:60]}"
    except Exception as e:
        return False, f"Hata: {str(e)[:60]}"

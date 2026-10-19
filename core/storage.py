import json
import os
import uuid
from datetime import datetime

# Proje dizinleri ve veri yollarını belirle
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

def _ensure_data_dir():
    """Veri klasörünün mevcut olduğundan emin olur."""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)

def load_history() -> list[dict]:
    """
    Kaydedilmiş indirme geçmişini okur.
    Dosya yoksa veya bozulmuşsa boş bir liste döner.
    """
    _ensure_data_dir()
    if not os.path.exists(HISTORY_FILE):
        return []
    
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []

def save_history(history: list[dict]) -> bool:
    """İndirme geçmişi listesini JSON formatında diske yazar."""
    _ensure_data_dir()
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def add_history_item(title: str, url: str, media_format: str, quality: str, size_str: str, filepath: str) -> dict:
    """
    Yeni bir tamamlanan indirme kaydı ekler ve güncel listeyi kaydeder.
    En yeni kayıt listenin en başına eklenir.
    """
    history = load_history()
    item = {
        "id": str(uuid.uuid4())[:8],
        "title": title,
        "url": url,
        "format": media_format.upper(),
        "quality": quality,
        "size": size_str,
        "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "filepath": filepath
    }
    history.insert(0, item)
    save_history(history)
    return item

def delete_history_item(item_id: str) -> bool:
    """Belirtilen kimliğe (id) sahip indirme kaydını listeden siler."""
    history = load_history()
    filtered = [item for item in history if item.get("id") != item_id]
    if len(filtered) != len(history):
        return save_history(filtered)
    return False

def clear_all_history() -> bool:
    """Tüm indirme geçmişini sıfırlar."""
    return save_history([])

def load_config() -> dict:
    """
    Kullanıcının son tercihlerini (klasör, format, çerez seçimi vb.) okur.
    """
    _ensure_data_dir()
    default_config = {
        "download_dir": os.path.join(os.path.expanduser("~"), "Downloads"),
        "last_format": "mp4",
        "last_quality": "En İyi Kalite",
        "cookies_browser": "Kapalı",
        "subtitles_enabled": False,
        "reduce_animations": False,
        "theme": "dark",
        "default_subtitle_lang": "tr"
    }

    if not os.path.exists(CONFIG_FILE):
        return default_config

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                default_config.update(data)
    except Exception:
        pass

    # Kayıtlı klasör bu sistemde mevcut değilse yerel Downloads klasörüne dön
    saved_dir = default_config.get("download_dir", "")
    if not saved_dir or not os.path.exists(saved_dir):
        default_config["download_dir"] = os.path.join(os.path.expanduser("~"), "Downloads")

    return default_config

def save_config(config_data: dict) -> bool:
    """Kullanıcı tercihlerini diske kaydeder."""
    _ensure_data_dir()
    try:
        current = load_config()
        current.update(config_data)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(current, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

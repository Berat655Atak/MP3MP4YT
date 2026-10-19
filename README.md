<div align="center">

# 🎬 MP3MP4YT
### Modern, Akıllı ve Hızlı YouTube Medya İndirici

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![yt-dlp](https://img.shields.io/badge/Engine-yt--dlp-red?logo=youtube&logoColor=white)](https://github.com/yt-dlp/yt-dlp)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white)](https://www.microsoft.com/windows)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

*Reklamsız, sade, koyu temalı ve gelişmiş özelliklerle donatılmış masaüstü YouTube indiricisi.*

</div>

---

## 🌟 Öne Çıkan Özellikler

- **🎞️ Çoklu Format ve Çözünürlük Desteği:**
  - **MP4 (Video):** 1080p, 720p, 480p ve 360p seçenekleri.
  - **MP3 (Stüdyo Kalitesi):** 320 kbps, 192 kbps ve 128 kbps seçenekleri (kapak görseli ve ID3 etiketleri otomatik gömülür).
  - **M4A (Orijinal Ses - ⚡ Ultra Hızlı):** FFmpeg dönüştürme süresi beklemeden doğrudan YouTube'un ham AAC ses akışını 2-3 saniyede kayıpsız çeker.

- **📏 Tahmini Dosya Boyutu Göstergesi:**
  - Kalite seçim menüsünde her çözünürlük ve ses formatının yaklaşık boyutu listelenir (Örn: `1080p (~142 MB)`, `MP3 320 kbps (~9.5 MB)`).

- **✂️ Klip Kırpma / Zaman Aralığı (Clip Downloader):**
  - Uzun bir videonun veya podcast'in yalnızca istediğiniz kısmını (`01:15 - 03:40`) tüm videoyu indirmeden doğrudan kesip kaydeder.

- **💬 Altyazı Desteği:**
  - Türkçe ve orijinal dildeki altyazıları otomatik olarak MP4 videosunun içine gömer.

- **🍪 Tarayıcı Çerezleri (Cookies) Entegrasyonu:**
  - YouTube'un bot korumasına takılan, oturum gerektiren veya yaş kısıtlamalı videoları tek tıkla **Chrome, Edge, Firefox veya Brave** çerezleriyle sorunsuz indirir.

- **📂 İndirilenler (Geçmiş) Sekmesi:**
  - Daha önce indirilen tüm videoların adı, boyutu, formatı ve indirilme tarihi yerel olarak saklanır.
  - **📁 Klasörde Göster:** İlgili dosyayı Windows Gezgini'nde seçili halde açar.
  - **▶️ Oynat:** Dosyayı varsayılan medya oynatıcınızda doğrudan başlatır.

- **📋 Otomatik Pano (Clipboard) Algılama:**
  - YouTube linki kopyalayıp programa döndüğünüzde linki anında algılar ve taramaya başlar.

- **📑 Oynatma Listesi (Playlist) Yöneticisi:**
  - Playlist içindeki videoları listeler; **"Tümünü Seç"** ve **"Tümünü Kaldır"** butonlarıyla istediğiniz videoları filtreleyip klasörlenmiş olarak indirir.

- **🔔 Windows Bildirimi ve Ses:**
  - İndirme tamamlandığında sesli uyarı verir ve Windows Toast bildirim kartı gösterir.

- **🧹 Otomatik Temizlik:**
  - İptal edilen veya tamamlanan indirmelerden sonra geride kalan `.part`, `.ytdl`, `.webp` gibi geçici kalıntı dosyaları anında temizler.

---

## 📁 Proje Mimarisi

```text
MP3MP4YT/
├── core/            # Temel motor, yardımcı fonksiyonlar ve yerel depolama
│   ├── storage.py   # İndirme geçmişi (history.json) ve ayarların yönetimi
│   └── utils.py     # URL doğrulama, FFmpeg tespiti, boyut hesaplama ve bildirimler
├── ui/              # Modern koyu tema arayüz bileşenleri
│   ├── main_window.py # Sekmeler, önizleme kartları, indirme ve geçmiş UI
│   └── styles.py    # Renk paleti ve font tanımları
├── bin/             # Harici FFmpeg motoru için ayrılmış alan
├── data/            # Yerel yapılandırma ve geçmiş verileri
├── requirements.txt # Gerekli Python bağımlılıkları
├── README.md        # Proje dokümantasyonu
└── MP3MP4YT.pyw     # Konsolsuz doğrudan uygulama başlatıcı
```

---

## 🚀 Kurulum ve Çalıştırma

### Gereksinimler
- **Python 3.10** veya daha yeni bir sürüm
- **FFmpeg** *(Sistem PATH'inde tanımlı olabilir ya da doğrudan projenin `bin/` klasörüne `ffmpeg.exe` atılabilir)*

### 1. Kütüphaneleri Yükleyin
```bash
pip install -r requirements.txt
```

### 2. Uygulamayı Başlatın
- **Windows için Pratik Yöntem:** `MP3MP4YT.pyw` dosyasına çift tıklayın (siyah konsol ekranı olmadan açılır).
- **Terminalden Başlatmak İçin:**
  ```bash
  python MP3MP4YT.pyw
  ```

---

## ⚙️ Yapılandırma ve İpuçları

1. **FFmpeg Konumu:** Bilgisayarınızda global FFmpeg kurulu değilse, indirdiğiniz `ffmpeg.exe` dosyasını `MP3MP4YT/bin/` içine koymanız yeterlidir; uygulama otomatik olarak tanıyacaktır.
2. **Kayıpsız Hızlı Ses:** Hızlı ve işlemciyi yormayan bir ses indirme istiyorsanız format olarak **M4A (Orijinal Ses)** seçeneğini tercih edebilirsiniz.
3. **Zaman Aralığı Formatı:** Kırpma alanına `01:30` (1 dakika 30 saniye) veya `01:15:00` (1 saat 15 dakika) biçiminde giriş yapabilirsiniz.

---

## 📄 Lisans
Bu proje [MIT Lisansı](LICENSE) kapsamında açık kaynak olarak sunulmaktadır.

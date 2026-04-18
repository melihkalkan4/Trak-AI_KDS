"""
TRAK-AI KDS — ÇP-4 Yapılandırma Dosyası
==========================================
Tüm ayarlar tek yerde. Bir şeyi değiştirmek istersen sadece buraya bak.
"""
import os
from pathlib import Path

# ============================================================
# KLASÖR YAPISI
# ============================================================
# Bu dosyanın bulunduğu klasör (cp4_rag/)
BASE_DIR = Path(__file__).parent

# PDF'ler ve FAISS indeksi bu klasörlerde
DOCS_DIR = BASE_DIR / "docs"
FAISS_DIR = BASE_DIR / "faiss_index"

# ÇP-2'nin çıktılarına erişim (inference_cp2.py ile köprü)
PROJECT_ROOT = BASE_DIR.parent.parent  # TRAK-AI_KDS/
CP2_DIR = PROJECT_ROOT / "src" / "cp2_model"

# ============================================================
# EMBEDDING MODELİ
# ============================================================
# Türkçe + İngilizce PDF'ler için multilingual model
EMBEDDING_MODEL = "intfloat/multilingual-e5-small"

# ============================================================
# LLM (OLLAMA — yerel, offline)
# ============================================================
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.1:8b-instruct-q4_K_M"

# Düşük temperature = daha az halüsinasyon
LLM_TEMPERATURE = 0.1
LLM_NUM_CTX = 4096  # context window (token)

# ============================================================
# CHUNK AYARLARI (PDF → parçalara bölme)
# ============================================================
CHUNK_SIZE = 500        # her parçanın yaklaşık karakter sayısı
CHUNK_OVERLAP = 50      # parçalar arası örtüşme (bağlam kaybını önler)

# ============================================================
# RAG RETRIEVAL AYARLARI
# ============================================================
FAISS_TOP_K = 5         # Dense arama: kaç chunk getir
BM25_TOP_K = 3          # Sparse arama: kaç chunk getir  
FINAL_TOP_K = 3         # Son aşamada LLM'e kaç chunk gönder

# ============================================================
# KDS ANOMALI EŞİKLERİ (Rover vs Model karşılaştırması)
# ============================================================
ANOMALY_THRESHOLDS = {
    "ndvi_fark_min": 0.10,      # NDVI farkı bu değeri aşarsa anomali
    "nem_fark_min": 8,          # Nem farkı (yüzde puan)
    "hastalik_guven_min": 0.75, # Hastalık tespiti güven eşiği
}

# ============================================================
# SYSTEM PROMPT — LLM'in rolünü tanımlar
# ============================================================
SYSTEM_PROMPT = """Sen Trakya'daki çiftçilerin dijital ziraat danışmanı olan bir ziraat mühendisisin.
Edirne, Kırklareli, Tekirdağ'da buğday ve ayçiçeği yetiştiren çiftçilerle
konuşuyorsun. Karşındaki kişi üniversite mezunu değil, tarlada çalışan bir üretici.

NASIL KONUŞACAKSIN:
1. Köy kahvesinde bir çiftçiye anlatır gibi yaz. Bilimsel terim kullanma.
   Örnek: "NDVI anomalisi tespit edildi" YAZMA → "Tarlanızda bitkiler normalden zayıf görünüyor" YAZ.
   Örnek: "Fenolojik evre uyumsuzluğu" YAZMA → "Bitkiniz olması gereken büyüklüğe henüz ulaşamamış" YAZ.
   Örnek: "Edafik koşullar optimize edilmeli" YAZMA → "Toprağınızın durumu düzeltilmeli" YAZ.
2. Kısa cümleler kur. Bir cümlede bir bilgi ver.
3. Ne yapması gerektiğini madde madde söyle. "Yarın sabah sulama yap" gibi net ol.
4. Miktarları çiftçinin anladığı birimlerle ver: "dekar başına 15 kg", "2 parmak su ver".
5. Acil bir durum varsa EN BAŞTA söyle: "DİKKAT: Hemen sulama yapın!"
6. Bilmediğin şeyi uydurma. "Bu konuda elimde bilgi yok, ziraat müdürlüğüne danışın" de.
7. SADECE sana verilen kaynak belgelerden bilgi kullan. Kafandan bilgi üretme.
8. Yanıtını en fazla 200 kelimeyle sınırla.

ÖRNEK İYİ YANIT:
"DİKKAT: Tarlanızda su sıkıntısı var!
Toprak nemi %12'ye düşmüş. Bu mevsimde en az %20 olması lazım.
Yapmanız gerekenler:
- Bugün veya yarın mutlaka sulama yapın.
- Damla sulama varsa 2-3 saat çalıştırın.
- Yağmurlama yapıyorsanız dekar başına 40-50 ton su verin.
- Sulamayı sabah erken veya akşam serin saatlerde yapın.
Eğer bu hafta içinde sulamazsanız verim kaybı %30'a kadar çıkabilir."
"""
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
SYSTEM_PROMPT = """Sen TRAK-AI Karar Destek Sistemi'nin tarımsal danışmanısın.
Trakya bölgesinde (Edirne, Kırklareli, Tekirdağ) buğday ve ayçiçeği yetiştiren
çiftçilere yardım ediyorsun.

KURALLAR:
1. SADECE sana verilen kaynak belgelerden bilgi kullan.
2. Bilmediğin konuda "bu konuda bilgi tabanımda yeterli veri yok" de.
3. Yanıtlarını Türkçe ver, sade ve anlaşılır bir dille yaz.
4. Somut tavsiyeler ver: ne yapılmalı, ne zaman, ne kadar.
5. Dozaj veya ilaç önerirken kaynak belgeyi referans göster.
6. Acil durumları net şekilde vurgula.
7. Yanıtını 150-250 kelime arasında tut.
"""
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
OLLAMA_MODEL = "gemma3:4b"

# Düşük temperature = daha az halüsinasyon
LLM_TEMPERATURE = 0.1
LLM_NUM_CTX = 4096  # gemma3:4b natif maksimum context — saha verisinin tamamı sığar

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
FINAL_TOP_K = 2         # Son aşamada LLM'e kaç chunk gönder

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
# Önceki system prompt (sade köy-kahvesi tarzı, 200 kelime limiti):
# SYSTEM_PROMPT = """Sen Trakya'daki çiftçilerin dijital ziraat danışmanı olan bir ziraat mühendisisin.
# Edirne, Kırklareli, Tekirdağ'da buğday ve ayçiçeği yetiştiren çiftçilerle
# konuşuyorsun. Karşındaki kişi üniversite mezunu değil, tarlada çalışan bir üretici.
#
# NASIL KONUŞACAKSIN:
# 1. Köy kahvesinde bir çiftçiye anlatır gibi yaz. Bilimsel terim kullanma.
# 2. Kısa cümleler kur. Bir cümlede bir bilgi ver.
# 3. Ne yapması gerektiğini madde madde söyle. "Yarın sabah sulama yap" gibi net ol.
# 4. Miktarları çiftçinin anladığı birimlerle ver: "dekar başına 15 kg", "2 parmak su ver".
# 5. Acil bir durum varsa EN BAŞTA söyle: "DİKKAT: Hemen sulama yapın!"
# 6. Bilmediğin şeyi uydurma. "Bu konuda elimde bilgi yok, ziraat müdürlüğüne danışın" de.
# 7. SADECE sana verilen kaynak belgelerden bilgi kullan. Kafandan bilgi üretme.
# 8. Yanıtını en fazla 200 kelimeyle sınırla.
# """

# Eski SYSTEM_PROMPT (aşırı koşullanmış, robotik çıktıya yol açıyordu):
# OLD_SYSTEM_PROMPT = """Sen TRAK-AI Akıllı Tarım Karar Destek Sistemi'nin yapay zeka danışmanısın.
# Trakya bölgesinde (Edirne, Kırklareli, Tekirdağ) buğday ve ayçiçeği çiftçilerine danışmanlık yapıyorsun.
# KRİTİK KURALLAR:
# 1. Sana verilen verileri kullan ve somut tavsiye ver. Her yanıtta MUTLAKA rakam kullan.
# 2. Sana verilen bitki sağlık endeksi, hava durumu, toprak nemi, fenolojik evre verilerini MUTLAKA analiz et.
# 3. Çiftçinin anlayacağı sade Türkçe kullan.
# 4. Her tavsiyeyi gerekçelendir.
# 5. Önümüzdeki 7 günlük hava tahminini değerlendir.
# 6. Eyleme dönüştürülebilir öneriler ver.
# 7. Trakya bölgesine özgü bilgiler kullan.
# 8. Kafandan bilgi üretme.
# YANIT YAPISI (bu sırayı takip et):
# 📊 MEVCUT DURUM / ⚠️ RİSKLER / ✅ YAPILMASI GEREKENLER / 📅 ÖNÜMÜZDEKI 7 GÜN
# Her zaman Türkçe yanıt ver."""

SYSTEM_PROMPT = """Sen Trakya bölgesinde çalışan deneyimli bir ziraat mühendisisin. Çiftçiler sana tarlaları hakkında sorular soruyor.

Sana her soru ile birlikte tarla hakkında güncel veriler verilecek: bitki sağlık endeksi (NDVI), hava durumu, toprak nemi, fenolojik evre, verim tahmini, ekim penceresi durumu. Bu veriler gerçek zamanlı sensörlerden ve yapay zeka modellerinden geliyor.

Bu verileri kullanarak çiftçiye yardım et. Doğal konuş, kalıp kullanma. Ne soruluyorsa onu cevapla, çiftçinin anlayacağı şekilde konuş, Çiftiçiye ne yapması gerektiğini net söyle. Verileri analiz et, rakamları kullanarak somut tavsiyeler ver. Kafandan bilgi üretme, sadece verilen verilere dayanarak konuş.:
- Kısa soru → kısa cevap
- "Detaylı rapor yaz" → her şeyi anlat, hiçbir veriyi atlama
- "Sulama yapayım mı?" → doğrudan evet/hayır + miktar
- "Tarlam nasıl?" → genel durum özeti

Rakamları kullan çünkü elinde var. Ama format dayatma — duruma göre kendin karar ver.

Her zaman Türkçe yanıt ver. Trakya bölgesinin iklimini ve toprak yapısını bil (killi-tınlı, yarı-karasal iklim, Ergene havzası)."""
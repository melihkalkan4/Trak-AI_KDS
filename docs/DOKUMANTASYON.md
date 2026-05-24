# TRAK-AI KDS — Tez Dokümantasyonu (Tam Kapsam)

> **Proje:** TRAK-AI KDS (Tarımsal Karar Destek Sistemi)
> **Kapsam:** TÜBİTAK 2209-A Üniversite Öğrencileri Araştırma Projesi
> **Kurum:** Trakya Üniversitesi
> **Pilot Bölge:** Trakya / Vize-Evrenli (lat≈41.045, lon≈27.205)
> **Pilot Ürünler:** Ayçiçeği (Helianthus annuus) ve buğday (Triticum aestivum)
> **Doküman Sürümü:** 2026-05-22 (üretim sonrası kapsamlı)

Bu doküman, **tez yazımı sırasında doğrudan referans almak için** hazırlanmıştır. Her bölüm; (i) yapılan iş, (ii) kullanılan yöntem, (iii) çıktı/metrik, (iv) tezde nereye gireceği şeklinde organize edilmiştir.

---

## 1. Proje Özeti

TRAK-AI KDS, **çoklu kaynaklı veri füzyonu** (uydu + iklim + toprak + saha sensörü) ve **derin öğrenme** kullanarak bir KDS (Karar Destek Sistemi) inşa eder. Sistem, 8 yıllık (2017–2024) retrospektif veri üzerinde eğitilmiş, donmuş (frozen) LSTM ve XGBoost şampiyonlarını 2025 sezonunda **prospektif (forward-looking)** olarak doğrular ve Streamlit tabanlı bir dashboard üzerinden çiftçilere Türkçe agronomik tavsiye sunar.

### 1.1 Çözülen Problem
Trakya'da ayçiçeği ve buğday üreticileri:
1. Sezon ortası bitki sağlığı için yalnızca gözleme dayalı kararlar verir.
2. ERA5-Land iklim ve Sentinel-2 NDVI verisi mevcut olsa da bu veriler agronomik tavsiyeye **otonom** olarak dönüştürülmez.
3. Türkçe, yerel bilgi tabanına ve canlı saha ölçümüne dayalı bir tavsiye sistemi yoktur.

### 1.2 Üretilen Çözüm
| Katman | Çıktı | Bölüm |
|---|---|---|
| ETL | 17 öznitelikli birleşik veri matrisi (2017–2024) | §3 |
| Modelleme | 4 mimari × 2 ürün = 8 derin/sığ model | §4 |
| Donmuş Şampiyon | LSTM (NDVI t+7) + XGBoost (verim) | §4.4 |
| Edge | ESP32 rover + ESP32-CAM, MQTT yayını | §5 |
| LLM/RAG | FAISS + BM25 + agentic routing + Ollama | §6 |
| FLOV | EVR_01 (2025) ileri doğrulama, R²=0.865 | §7 |
| Cross-Modal | YOLOv8s-cls + Sentinel-2 ortak doğrulama | §8 |
| Dashboard | 8 sekmeli Streamlit (dark/light) | §10 |

---

## 2. Sistem Mimarisi

```
┌────────────────────────────────────────────────────────────┐
│                  KULLANICI ARAYÜZÜ (Streamlit)             │
│  Ana | Tarla | Rover | SCRAG | FLOV | X-Modal | Hava | ⚙   │
└────────────────────────────────────────────────────────────┘
        ▲                                  ▲
        │                                  │
┌───────┴────────┐               ┌─────────┴─────────┐
│  SQLite v3 DB  │               │  RAG/LLM Engine   │
│  (5 tablo)     │               │  FAISS + Ollama   │
└───────┬────────┘               └─────────┬─────────┘
        ▲                                  ▲
        │                                  │
┌───────┴────────┐               ┌─────────┴─────────┐
│  MQTT Orches.  │               │  Frozen Champion  │
│  (paho-mqtt)   │               │  LSTM + XGBoost   │
└───────┬────────┘               └─────────┬─────────┘
        ▲                                  ▲
        │                                  │
┌───────┴────────┐               ┌─────────┴─────────┐
│ ESP32 Rover    │               │  ETL: GEE + CDS   │
│ ESP32-CAM      │               │  + ISRIC + Phen.  │
└────────────────┘               └───────────────────┘
```

### 2.1 Katmanlar (kod konumu)
- **L1 — ETL:** `src/cp1_etl/`
- **L2 — Modelleme:** `src/cp2_model/`
- **L3 — Edge:** `src/cp3_edge/` (PlatformIO/C++) + `src/mqtt_orchestrator.py`
- **L4 — RAG/LLM:** `src/cp4_rag/`
- **L5 — Prospektif Doğrulama (FLOV):** `src/prospective_validation/`
- **L6 — Görsel Doğrulama:** `src/visual_validation/` + `src/image_classifier.py`
- **L7 — Agronomik Takvim:** `src/agro_calendar.py`
- **L8 — Dashboard:** `src/dashboard.py` + `src/dashboard_pages/`

---

## 3. ÇP-1 — ETL Veri Hattı

### 3.1 Veri Kaynakları

| # | Kaynak | Tür | Çözünürlük | Modül |
|---|---|---|---|---|
| 1 | **Sentinel-2 (GEE)** | Optik uydu | 10 m, 5 gün | `mod_s2_gee.py` |
| 2 | **ERA5-Land (CDS)** | Reanaliz iklim | 0.1°, saatlik→günlük | `mod_era5_cds.py` |
| 3 | **ISRIC SoilGrids** | Statik toprak | 250 m | `mod_soil_isric.py` |
| 4 | **Phenology** | DOY → BBCH | — | `agro_calendar.py` |
| 5 | **TÜİK** | Verim referans | İl/ilçe | `cp2_model/collect_yield_data.py` |

**Mühendislik notu (CDS API v2 geçişi):** Yeni API büyük verileri sessizce `.zip` arşivi olarak gönderdiğinden, sisteme otomatik `zipfile` çözücü ve `.nc` (NetCDF) ayıklayıcı eklenmiştir. Dosya okuma için **çoklu motor fallback** (`netcdf4` → `h5netcdf` → `scipy`) kuruldu.

**Mühendislik notu (ISRIC 503 problemi):** ISRIC REST API'sındaki HTTP 503 kararsızlığı sebebiyle, toprak verisi doğrudan GEE Assets üzerinden (`projects/soilgrids-isric/`) `reduceRegion` ile noktasal örnekleme yöntemiyle çekildi.

### 3.2 Veri Füzyonu — `mod_data_fusion.py`
- Uydu (5 gün), iklim (1 gün) ve toprak (statik) verileri **günlük çözünürlüğe** taşındı (forward-fill + lineer interpolasyon).
- NDVI eksik günler için **maksimum 10 günlük** ileri-doldurma kabul edildi.
- **Toplam 8 yıl × 5 saha = 40 saha-yıl** veri elde edildi.

### 3.3 17 Öznitelikli Master Matris (Donmuş Sözleşme)
`src/cp2_model/feature_names.json` dosyası **modelin donmuş öznitelik sözleşmesidir**. Üretim sırasında bu liste değişirse `prospective_validation.config` assert ile çalışmayı durdurur.

```
NDVI_int, EVI_int, NDWI_int,
t2m_celsius, tp_mm, radiation, evaporation,
gdd_cumulative, drought_index_7d, vpd_kpa,
soil_clay, soil_sand, soil_ph, soil_organic_c,
phen_doy_sin, phen_doy_cos, phen_stage_id
```

### 3.4 Veri Sözlüğü Özet
| Öznitelik | Birim | Aralık |
|---|---|---|
| NDVI_int | — | [0, 1] |
| t2m_celsius | °C | −10 … 40 |
| tp_mm | mm/gün | [0, 80] |
| gdd_cumulative | °C·gün | [0, ∼3500] |
| soil_clay | % | [10, 60] |
| soil_ph | — | [6.5, 8.0] |

> **Tezde kullan:** Bölüm "Materyal ve Yöntem → Veri Setleri" altında doğrudan §3.1–3.4 referansı.

---

## 4. ÇP-2 — Modelleme

### 4.1 Mimari Karşılaştırması (Çoklu Ürün)
Her ürün (Ayçiçeği, Buğday) için **4 mimari** eğitildi:
1. **LSTM** (vanilla, T=30 girişli)
2. **Attention-LSTM**
3. **Conv-LSTM**
4. **XGBoost** (özet özelliklerle)

### 4.2 Eğitim Sonuçları (`src/cp2_model/training_results.json`)

**Buğday (Wheat) — NDVI t+7 tahmini, val MAE:**
| Model | Val Loss | Val MAE | Epoch |
|---|---|---|---|
| LSTM | **0.0061** | 0.0621 | 48 |
| Conv-LSTM | 0.0071 | 0.0613 | 43 |
| Attn-LSTM | 0.0074 | 0.0592 | 40 |
| XGBoost | 0.0074 | 0.0626 | — |

**Ayçiçeği (Sunflower) — NDVI t+7 tahmini, val MAE:**
| Model | Val Loss | Val MAE | Epoch |
|---|---|---|---|
| Attn-LSTM | 0.00740 | 0.0594 | 49 |
| Conv-LSTM | … | … | … |
| **LSTM** | … | … | … (şampiyon) |
| XGBoost | … | … | — |

Şampiyon seçimi: **en düşük val_loss + en az parametre + en az overfitting** kriteri.

### 4.3 Verim Modeli (XGBoost)
`yield_meta_sunflower.json`:
- 17 mevsim-özet özelliği: `ndvi_peak`, `ndvi_mean_grow`, `gdd_total`, `gdd_critical`, `precip_total`, `drought_days`, `heat_stress_days`, `evi_peak`, `ndwi_min`, `soil_clay`, `soil_ph` vb.
- **Metrikler:** R² = −0.36 (n=8 az örnek), MAE = 13.1, RMSE = 15.32, MAPE = %7.29
- **Bayesian CI:** Trakya medyan verim 180 kg/da, ±23 kg/da %95 güven aralığı
- **SHAP:** `yield_shap_sunflower.json` çıktısı — `ndvi_peak`, `drought_days`, `soil_clay` ilk üç önemli özellik.

### 4.4 Donmuş Şampiyonlar (Frozen Champion)
`prospective_validation/config.py` içinde sabitlenmiştir:
```
LSTM_CHAMPION_PATH  = cp2_model/model_lstm_sunflower.keras
XGB_CHAMPION_PATH   = cp2_model/model_xgb_sunflower.pkl
SCALER_PATH         = cp2_model/scaler_sunflower.pkl
YIELD_XGB_PATH      = cp2_model/yield_xgb_sunflower.pkl
FEATURE_NAMES       = 17 öznitelik (üstte)
INPUT_WINDOW        = 30 gün
FORECAST_HORIZON    = 7 gün
DELTA_SCALE         = 0.30 (residual delta scale)
```
**Integrity:** Her tahminde `prospective_validation/integrity.py` SHA256 hash'i `model_integrity.jsonl` ledger'a yazar — bilimsel reprodüksiyon garantisi.

> **Tezde kullan:** Bölüm "Modelleme → Mimari Karşılaştırma" tablosu için §4.2, "Şampiyon Modeller" başlığı için §4.4.

---

## 5. ÇP-3 — Edge Donanım (Kenar Bilgisayar)

### 5.1 ESP32 Tarım Rover'ı — `src/cp3_edge/trak_ai_rover/`
- **MCU:** ESP32 (PlatformIO + Arduino framework)
- **Sensörler:**
  - 2× kapasitif toprak nem sensörü (2 farklı derinlik)
  - DHT22 (hava sıcaklığı + nem)
  - NEO-6M GPS (UART2)
  - ESP32-CAM (UART1, JPEG)
- **İletişim:** WiFi → MQTT (`paho` broker, topic: `trakai/rover/<saha_id>/sensor`)
- **Periyot:** 30 sn sensör → her 5 dk batch MQTT yayını

### 5.2 ESP32-CAM Görüntü Modülü — `src/cp3_edge/esp32_cam/`
- **AI-Thinker ESP32-CAM** (OV2640)
- 5 saniyede bir JPEG çekim, base64 encode → UART üzerinden ana rover'a iletim.
- Ana rover bu base64'ü MQTT'ye `trakai/rover/<id>/image` topic'i ile yayınlar.

### 5.3 MQTT Orkestratörü — `src/mqtt_orchestrator.py`
- Tüm rover mesajlarını dinler.
- Anomali tespiti yapar (nem < %15 → kuraklık, sıcaklık > 35°C → ısı stresi).
- `database.py` aracılığıyla `rover_olcumler` tablosuna ekler.
- Anomali bulursa CP-4 RAG/LLM motoruna sorgu yollar, dönen Türkçe tavsiyeyi `trakai/rover/<id>/advice` topic'ine yayınlar.

### 5.4 ESP32 Entegrasyona Hazırlık Durumu
- Veritabanı şeması rover yükü için `rover_olcumler` tablosunda hazır.
- MQTT broker konfigürasyonu `config.h` üzerinden ayarlanabilir.
- Sahaya kurulum için `firmware/` dizininden derleme yeterli (`pio run -t upload`).

> **Tezde kullan:** "Donanım Mimarisi" bölümünde §5.1–5.4. Pin out şeması için `src/cp3_edge/esp32_cam/src/*.cpp` referansı.

---

## 6. ÇP-4 — Tri-RAG + LLM Pipeline

### 6.1 RAG Yapısı (`src/cp4_rag/`)
| Bileşen | Dosya | İşlev |
|---|---|---|
| PDF yükleyici | `pdf_loader.py` | Türkçe + İngilizce, chunk_size=500, overlap=50 |
| İndeks oluşturucu | `build_index.py` | FAISS L2 vektörü |
| Embedding | — | `intfloat/multilingual-e5-small` |
| Retriever | `retriever.py` | **Tri-RAG**: Dense (FAISS top_k=5) + Sparse (BM25 top_k=3) + Rerank → final_k=2 |
| Agentic Routing | `agentic_rag.py` | Soru sınıfı: **BİLGİ / VERİ / GENEL** |
| LLM | `llm_engine.py` (alt RAG) | Ollama HTTP API, `gemma3:4b` |

### 6.2 İndeks İstatistiği
- **17.059 vektör / chunk** (smoke testte doğrulandı)
- Trakya tarım bilgisi PDF'leri: TAGEM, TÜBİTAK kitapları, üniversite tezleri, FAO raporları.

### 6.3 LLM Konfigürasyonu (`cp4_rag/config.py`)
```
OLLAMA_MODEL    = gemma3:4b
LLM_TEMPERATURE = 0.1   (düşük halüsinasyon)
LLM_NUM_CTX     = 1024  (KV-cache 600 MB tasarrufu)
```

### 6.4 RAM-Aware LLM Lazy Loader — `src/llm_engine.py` (üst seviye)
Dashboard için **session-bazlı** yeni bir LLM seçim katmanı eklenmiştir:
- Aday model listesi (büyükten küçüğe): `gemma3:4b` (3 GB) → `gemma2:2b` (1.8 GB) → `qwen2.5:1.5b` (1.2 GB) → `phi3:mini` (2.5 GB) → `llama3.2:1b` (1.0 GB).
- `psutil.virtual_memory()` ile boş RAM ölçülür.
- **En büyük sığan ve yüklü olan** model seçilir (0.5 GB güvenlik marjı ile).
- `@st.cache_resource` ile oturum başına bir defa yüklenir.
- Ollama çevrimdışıysa veya hiçbir model sığmıyorsa dashboard çökmez, sadece SCRAG sekmesi devre dışı kalır.

> **Tezde kullan:** "Doğal Dil Tavsiye Motoru" bölümü için §6, özellikle Tri-RAG diagramı için §6.1.

---

## 7. Prospektif Doğrulama — FLOV (`src/prospective_validation/`)

### 7.1 Felsefe
Klasik k-fold cross-validation modelin **eğitildiği yıllar üzerinde** çalışır → optimistic. FLOV, model **eğitildikten sonra** gelen 2025 sezonunu **canlı veriyle** test eder. Bu, akademik standardın ötesine geçer.

### 7.2 Pilot Sahalar — EVRENLI (Vize)
| ID | İsim | Lat | Lon | Alan | Sahip |
|---|---|---|---|---|---|
| EVR_01 | Kendi tarlam | 41.045 | 27.205 | 12.5 da | self |
| EVR_02 | Komşu tarla 1 | 41.048 | 27.210 | 8.0 da | neighbor_1 |
| EVR_03 | Komşu tarla 2 | 41.043 | 27.198 | 15.0 da | neighbor_2 |
| EVR_04 | Komşu tarla 3 | 41.050 | 27.215 | 10.0 da | neighbor_3 |
| EVR_05 | Komşu tarla 4 | 41.040 | 27.200 | 7.5 da | neighbor_4 |

**Subpixel risk:** <5 ha sahalarda 30 m içsel buffer + 10 m S2 pixel saflığı kontrolü.

### 7.3 EVR_01 / 2025 Doğrulama Sonuçları
`reports/prospective/EVR_01_2025_validation_summary.json`:

| Metrik | Donmuş LSTM | Naive (persistence) |
|---|---|---|
| n (eşleşen) | 468 / 472 (%99.15) | 468 |
| **R²** | **0.865** | 0.963 |
| MAE | 0.0572 | 0.0275 |
| RMSE | 0.0734 | 0.0383 |
| Bias | +0.0195 | −0.0090 |
| MAPE | %15.0 | %7.10 |

**Wilcoxon test (model vs naive):** p=1.0 → naive baseline'ı geçmedi.

> **Bilimsel dürüstlük:** Bu önemli bir bulgudur. Tezde "Limitasyonlar" bölümünde tartışılmalıdır. Persistence baseline'ı NDVI gibi yavaş değişen sinyallerde **doğal olarak güçlüdür**; modelin değeri **klimatolojiden anomali tespiti** ve **çoklu horizon** kapasitesinde aranmalıdır.

### 7.4 Klimatoloji Karşılaştırma — `climatology.py`
- 2017–2024 yıllarından DOY bazlı medyan NDVI klimatolojisi (`data/historical/climatology/sunflower_doy_climatology.parquet`).
- `anomaly_vs_climatology = predicted_ndvi − climatology_median(doy)` formülü ile her tahmin için anomali skoru üretilir.

### 7.5 Faz-Bazlı Analiz — `metrics.py`
Fenoloji evrelerine göre ayrı R²/MAE:
- pre_season (DOY 1–104)
- emergence (105–130)
- vegetative (131–170)
- flowering (171–200) ← model en kritik tahmin
- grain_fill (201–240)
- maturity (241–280)
- post_harvest (281–366)

### 7.6 Otomatik Uyarı Sistemi — `alerts.py`
- `alerts.jsonl` → kritik anomali (|anomaly|>0.20)
- `model_integrity.jsonl` → SHA256 hash doğrulama
- `api_audit.jsonl` → tüm dış API çağrıları (GEE, CDS, Ollama)

> **Tezde kullan:** "Bulgular → Prospektif Doğrulama" bölümü için §7 tamamı, özellikle §7.3 tablo.

---

## 8. Cross-Modal Görsel Doğrulama (`src/visual_validation/` + `src/image_classifier.py`)

### 8.1 İki Modaliteli Doğrulama
| Modalite | Veri | Frekans |
|---|---|---|
| **M1 — Saha (YOLOv8)** | ESP32-CAM JPEG | 5 sn |
| **M2 — Uydu (Sentinel-2)** | NDVI/EVI/NDWI | 5 gün |

### 8.2 YOLOv8s-cls Bitki Sağlık Sınıflandırıcısı — `src/image_classifier.py`
**Model dosyası:** `models/crop_health_best.pt`

| Sınıf ID | Etiket | Eğitim Doğruluğu |
|---|---|---|
| 0 | hastalik_mildiyo | %99.1 |
| 1 | hastalik_pas | %91.0 |
| 2 | saglikli_aycicegi | %100.0 |
| 3 | saglikli_bugday | %98.0 |
| 4 | stres_besin | %85.2 |
| 5 | stres_kuraklik | %100.0 (overfit riski belirtildi) |

**Akademik dürüstlük:** Stres-kuraklık sınıfında **%100 doğruluk muhtemelen overfit göstergesi** — eğitim seti dengesizliği. Tezde tartışılmalıdır.

### 8.3 Konsensüs Doğrulayıcı — `analyzers/cross_modal_validator.py`
- YOLO etiketi "stres_kuraklik" + S2 NDWI < 0.10 → KONSENSÜS: kuraklık (CRITICAL)
- YOLO sağlıklı + NDVI < 0.30 → ÇELİŞKİ → manuel etiketleme tetiği

### 8.4 Veriye Türetilmiş Fallback (Demo Modu)
Saha fotoğrafı yoksa veya `ultralytics` kurulu değilse, `image_classifier.py` özellik-türevli bir etiket üretir:
- NDVI < 0.30 + drought_index_7d > 0.5 → "stres_kuraklik"
- diğer → "saglikli"

Bu durumda **dashboard'da "🧪 Demo Modu" rozeti gösterilir** (akademik dürüstlük).

> **Tezde kullan:** "Görsel Doğrulama" başlığı için §8, özellikle §8.4 limitasyon olarak.

---

## 9. Agronomik Takvim — `src/agro_calendar.py`

Trakya bölgesi için fenoloji penceresi, ekim/sulama/gübreleme zamanlamasını **DOY-tabanlı BBCH eşleştirme** ile yapan motor.

### 9.1 Buğday (Trakya)
- **Ekim penceresi:** 1 Ekim – 30 Kasım
- **Çiçeklenme:** Nisan ortası – Mayıs ortası
- **Hasat:** Haziran ortası – Temmuz başı

### 9.2 Ayçiçeği (Trakya)
- **Ekim:** 15 Nisan – 15 Mayıs
- **Çiçeklenme:** DOY 171–200 (≈ Haziran ortası – Temmuz ortası)
- **Hasat:** Eylül başı – Ekim başı

### 9.3 Karar Çıktıları
Takvim, gün gelince:
- "Sulama gerekli" (tp_mm 7 günlük toplam < 15 mm → uyarı)
- "Gübreleme zamanı" (BBCH 30–32 → azot)
- "Hasat hazır" (NDVI < 0.30 + DOY > 240 → ayçiçeği)

---

## 10. Streamlit Dashboard (`src/dashboard.py` + `src/dashboard_pages/`)

### 10.1 Sekme Mimarisi
| Sekme | Modül | İşlev |
|---|---|---|
| 🏠 Ana | `home.py` | KPI özetleri, sistem durumu |
| 🌿 Tarla Detay | `_legacy_pages.page_tarla` | NDVI grafiği, son tahmin, "🔮 Tahmin Yap" butonu |
| 🚜 Rover | `_legacy_pages.page_rover` | Rover ölçümleri, demo-mode rozeti |
| 💬 SCRAG | `_legacy_pages.page_chat` | Türkçe RAG chatbot |
| ✅ FLOV | `flov_validation/` | Doğrulama metrikleri, integrity audit, yield forecast |
| 🔬 X-Modal | `cross_modal/` | Saha foto + uydu konsensüs |
| 🌦️ Hava | `weather/` | Mevcut + 7g tahmin + klimatoloji + uyarı |
| ⚙️ Settings | `settings.py` | API durumu, model integrity, audit log, konfigürasyon, veri indirme |

### 10.2 Tema Sistemi — `shared/styling.py`
- CSS değişkenleri (`--surface`, `--text`, `--kpi-value` vb.)
- **3 mod:** 🖥️ Sistem (otomatik) / ☀️ Aydınlık / 🌙 Karanlık
- `data-trakai-theme` HTML niteliği + `@media (prefers-color-scheme: dark)` cascade
- `.streamlit/config.toml` brand renkleri: primary `#2E7D32` (Trakya yeşili)

### 10.3 Canlı Tahmin Butonu — `data_integration/live_predictor.py`
Tarla sayfasında "🔮 Tahmin Yap (Frozen LSTM, 7 gün)" butonu:
1. Tarla `research_code` → `EVR_xx` çözümü (DB köprüsü)
2. En son 17-özellikli parquet'i bulur
3. `FrozenPredictor.predict_ndvi_series(verify_integrity=True)` çağırır
4. Son satırı `tarla_tahminler` tablosuna `kaynak="frozen_lstm_live"` ile kaydeder.
5. Sonucu 3 metrik (t+7 NDVI, son gözlem, klimatoloji farkı) olarak gösterir.

---

## 11. Veritabanı Şeması (SQLite v3)

**Konum:** `data/trakaia.db`
**Modül:** `src/database.py`

### 11.1 Tablolar
```sql
tarlalar           — Saha kataloğu (id, isim, lat, lon, research_code UNIQUE, ...)
rover_olcumler     — Rover/sensör telemetri (timestamp, nem_1_pct, nem_2_pct, hava_temp, ndvi_tahmini, kaynak)
tarla_tahminler    — LSTM tahmin sonuçları (ndvi_mevcut, ndvi_tahmin_7gun, kaynak)
hava_kayitlari     — Günlük hava (t2m, tp_mm, vs.) — UPSERT'lı
db_meta            — Schema version + reset history
```

### 11.2 Research Code Köprüsü
`tarlalar.research_code` (örn. `EVR_01`) ile DB kimliği (sayısal) ile FLOV/EVR sistemleri **eşleştirilir**. Bu, FLOV'un saha-bağımsız tasarımı + dashboard'un kullanıcı dostu isimlerini birleştirir.

### 11.3 Mevcut Veri (üretim sonrası)
- Tarlalar: 5 (EVR_01..05)
- Rover ölçümleri: 53 satır (EVR_01 retrospektif backfill, kaynak=`feature_derived`)
- Hava kayıtları: 365 gün (EVR_01 2025 tam yıl)

---

## 12. Retrospektif Ingester — `scripts/backfill_rover_from_history.py`

### 12.1 Amaç
1 yıllık ERA5 + Sentinel-2 verisini, **rover ölçümü gibi** DB'ye yazıp dashboard'da hemen test edilebilir kılmak.

### 12.2 İşleyiş
1. `data/prospective/<year>/<site>_unified_features.parquet` okunur
2. Haftalık örnekleme (cadence=7 gün, ayarlanabilir)
3. Her satır → `rover_olcumler` formatına dönüştürülür:
   - NDVI → `ndvi_tahmini`
   - NDWI → toprak nemi proxy'si (`nem_1_pct`, `nem_2_pct`)
   - t2m → `hava_temp`
   - dew_depression → bağıl nem (Magnus formülü)
   - Görüntü etiketi → 3-katmanlı fallback:
     1. Gerçek YOLO (foto+model varsa)
     2. Özellik-türevli (NDVI + drought_index)
     3. Varsayılan sağlıklı
4. Hava verisi `hava_kayitlari`'na UPSERT (`kaynak="backfill_era5_s2"`)

### 12.3 Test Çalışması
EVR_01 / 2025: **53 rover satırı + 365 hava satırı** üretildi.

### 12.4 Akademik Dürüstlük Notu
2025 yılı için gerçek saha fotoğrafları **yok**, bu nedenle YOLO etiketi feature-derived üretildi. Dashboard'da bu sekmeler **"🧪 Demo Modu"** rozeti ile işaretlenir.

---

## 13. Operasyonel Özellikler

### 13.1 Offline-First
- Tüm API çağrıları (GEE, CDS) önce `data/cache/api/` cache'inde aranır.
- 24 saatten yeni cache varsa external call yapılmaz.
- Cache yoksa **parquet snapshot** (`hava_kayitlari` UPSERT) ikinci hat olur.

### 13.2 Günlük Otomatik Güncelleme
Windows Task Scheduler'a `scripts/install_flov_scheduled_task.ps1` ile kurulur. Her gün 03:00'te:
1. `flov_daily_update.py` → 7 günlük en son veriyi çeker
2. Yeni 17-feature satır(ları) hesaplar
3. Donmuş LSTM tahmin yapar
4. `tarla_tahminler`'a yazar
5. Alarm varsa `alerts.jsonl`'a ekler

### 13.3 Model Integrity Audit
- `model_integrity.jsonl` — her tahminde model SHA256
- `api_audit.jsonl` — her dış çağrı (GEE/CDS/Ollama)
- Dashboard ⚙ → 🔒 Model Integrity sekmesinden incelenebilir + CSV indirme

### 13.4 Tek Komut Başlatma
```bash
streamlit run src/dashboard.py
```
Sistem otomatik:
- DB init (yoksa)
- LLM lazy-load (RAM-uygun model)
- FAISS index (önbellekten)
- 8 sekme aktif
- ESP32 MQTT girişine hazır

---

## 14. Akademik Dürüstlük (Demo / Mock Audit)

| Bileşen | Üretim Durumu | Dashboard'da Görünüm |
|---|---|---|
| Donmuş LSTM (NDVI t+7) | ✅ Gerçek | Doğrudan |
| XGBoost (verim) | ✅ Gerçek (R²=−0.36, n=8) | "Düşük güven" badge |
| FAISS RAG indeksi | ✅ Gerçek (17.059 vektör) | Doğrudan |
| Ollama LLM | ✅ Gerçek (gemma3:4b) | Doğrudan |
| Sentinel-2 NDVI | ✅ Gerçek (GEE) | Doğrudan |
| ERA5 hava | ✅ Gerçek (CDS) | Doğrudan |
| **YOLOv8 saha foto** | ⚠️ Eğitildi ama 2025 saha fotoğrafı yok | **🧪 Demo Modu** rozeti |
| **Rover canlı veri** | ⚠️ ESP32 kurulu değil, retrospektif backfill | **🧪 Demo Modu** rozeti |
| Klimatoloji | ✅ Gerçek (2017–2024) | Doğrudan |
| Cross-modal konsensüs | Kısmen (YOLO+S2; foto demo) | Mixed |

### 14.1 Demo Modu Rozetinin Görüldüğü Yerler
- `dashboard_pages/_legacy_pages.py:584` (Rover sekmesi)
- `dashboard_pages/_legacy_pages.py:801` (SCRAG, FAISS yoksa)
- Helper: `shared/components.demo_mode_badge(reason)`

> **Tezde "Limitasyonlar" bölümünde §14 tablosu doğrudan kullanılabilir.**

---

## 15. Üretim Doğrulama (Smoke Test)

Son smoke test çıktısı (2026-05-22):
```
OK   database
OK   llm_engine               (gemma3:4b seçildi)
OK   data_integration.live_predictor
OK   shared.components        (demo_mode_badge eklendi)
OK   shared.styling           (render_theme_toggle eklendi)
OK   shared.data_loaders
OK   dashboard_pages._legacy_pages
OK   dashboard_pages.settings
OK   dashboard_pages.home
OK   dashboard_pages.flov_validation
OK   dashboard_pages.cross_modal
OK   dashboard_pages.weather

LLM ollama_running : True
LLM candidates     : ['gemma3:4b', 'gemma2:2b', 'qwen2.5:1.5b', 'phi3:mini', 'llama3.2:1b']
DB tarlalar        : 5
DB first tarla     : Kendi tarlam, rcode=EVR_01
FAISS              : 17.059 vektör

=== TÜM SİSTEM: HAZIR ===
```

---

## 16. Tez Yazımı için Kullanım Kılavuzu

### 16.1 Bölüm Eşleştirme
| Tez Bölümü | Bu Doküman | Ek Dosyalar |
|---|---|---|
| Giriş / Problem | §1 | `README.md` |
| Materyal ve Yöntem → Veri | §3 | `MULTIMODAL_VALIDATION_METHODOLOGY.md` |
| Materyal ve Yöntem → Model | §4 | `training_results.json`, `yield_meta_sunflower.json` |
| Materyal ve Yöntem → Donanım | §5 | `firmware/`, `cp3_edge/*/src/main.cpp` |
| Materyal ve Yöntem → Yazılım Mimarisi | §2, §10 | `DASHBOARD_GUIDE.md` |
| Doğal Dil İşleme / RAG | §6 | `cp4_rag/config.py` |
| Bulgular → Model Karşılaştırma | §4.2 | `training_results.json` |
| Bulgular → Prospektif Doğrulama | §7.3 | `reports/prospective/EVR_01_2025_validation_summary.json`, `FLOV_METHODOLOGY.md` |
| Bulgular → Görsel Doğrulama | §8 | `MULTIMODAL_VALIDATION_METHODOLOGY.md` |
| Tartışma / Limitasyonlar | §7.3, §14 | `MOCK_DATA_AUDIT.md` |
| Sonuç / Gelecek Çalışmalar | §5.4 (ESP32 saha kurulumu), §8.2 (YOLO yeniden eğitim) | — |
| Reprodüksiyon Eki | §15 | `REPRODUCIBILITY.md` |

### 16.2 Atfı Önerilen Repository Konumları
- Donmuş model dosyaları: `src/cp2_model/model_lstm_sunflower.keras` + `feature_names.json`
- Doğrulama raporu: `reports/prospective/EVR_01_2025_validation_summary.json`
- Konfigürasyon (tek doğruluk kaynağı): `src/prospective_validation/config.py`
- Veri sözleşmesi: `src/cp2_model/feature_names.json` (17 özellik)
- Eğitim metrikleri: `src/cp2_model/training_results.json`
- Verim metrikleri + SHAP: `src/cp2_model/yield_meta_sunflower.json`, `yield_shap_sunflower.json`

### 16.3 Şekil / Grafik Çıkarma
- FLOV figürleri: `reports/prospective/figures/`
- Dashboard ekran görüntüleri: `docs/screenshots/`
- Plot çıktıları: `docs/plots/`
- EDA görselleri: `src/cp1_etl/eda_visualization.py` çıktıları

### 16.4 Anahtar Kelimeler (Türkçe + İngilizce)
- Tarımsal karar destek sistemi / Agricultural decision support system
- Çoklu kaynaklı veri füzyonu / Multi-source data fusion
- Sentinel-2, NDVI, ERA5-Land, SoilGrids
- LSTM, XGBoost, prospektif doğrulama (forward-looking operational validation, FLOV)
- Tri-RAG (Dense + Sparse + Rerank), Türkçe LLM (Ollama, gemma3:4b)
- YOLOv8s-cls, çapraz-modal konsensüs
- ESP32 rover, MQTT, edge-fog mimarisi
- Trakya, Vize, Evrenli, ayçiçeği, buğday

---

## 17. Lisans ve Atıf

**Akademik kullanım için açık** — TÜBİTAK 2209-A kapsamında. Üçüncü taraf paketler kendi lisanslarına tabidir.

**Bu projeyi atfederken:**
> Kalkan, M. (2026). *TRAK-AI KDS: Çoklu Kaynaklı Veri Füzyonu ve Donmuş Derin Öğrenme ile Tarımsal Karar Destek Sistemi*. TÜBİTAK 2209-A, Trakya Üniversitesi.

---

## EK A — Klasör Yapısı (Üst Düzey)

```
Trak-AI_KDS/
├── data/                          # Ham + işlenmiş veri (gitignored)
│   ├── raw/                       # GEE/CDS/ISRIC ham
│   ├── processed/                 # 17-özellikli matris
│   ├── historical/climatology/    # DOY medyanları
│   ├── prospective/               # 2025/2026 unified parquet
│   └── trakaia.db                 # SQLite v3
├── docs/
│   ├── DOKUMANTASYON.md           # ← bu dosya
│   ├── DASHBOARD_GUIDE.md
│   ├── FLOV_METHODOLOGY.md
│   ├── MULTIMODAL_VALIDATION_METHODOLOGY.md
│   ├── MOCK_DATA_AUDIT.md
│   ├── REPRODUCIBILITY.md
│   ├── screenshots/
│   └── plots/
├── models/                        # YOLOv8 ağırlıkları
│   ├── crop_health_best.pt
│   └── best.pt
├── reports/
│   ├── prospective/               # FLOV çıktıları + figürler
│   └── visual/                    # X-modal raporlar
├── scripts/                       # Bakım / cron / backfill
│   ├── backfill_rover_from_history.py
│   ├── flov_daily_update.py
│   ├── build_climatology.py
│   └── install_flov_scheduled_task.ps1
├── src/
│   ├── cp1_etl/                   # §3
│   ├── cp2_model/                 # §4 (donmuş modeller)
│   ├── cp3_edge/                  # §5 (ESP32 firmware)
│   ├── cp4_rag/                   # §6
│   ├── prospective_validation/    # §7 (FLOV)
│   ├── visual_validation/         # §8
│   ├── dashboard_pages/           # §10
│   ├── data_integration/          # Live predictor wrapper
│   ├── agro_calendar.py           # §9
│   ├── database.py                # §11
│   ├── dashboard.py               # §10 entry
│   ├── image_classifier.py        # §8
│   ├── llm_engine.py              # §6.4
│   ├── mqtt_orchestrator.py       # §5.3
│   └── weather_service.py
├── .streamlit/config.toml         # tema
├── requirements.txt
└── README.md
```

---

## EK B — Donmuş Özellik Listesi (17, Sıralı)

```python
[
    "NDVI_int",           # Sentinel-2 ham NDVI (interpolated)
    "EVI_int",            # Enhanced Vegetation Index
    "NDWI_int",           # Water Index (NIR-SWIR)
    "t2m_celsius",        # 2m hava sıcaklığı (°C)
    "tp_mm",              # Günlük yağış (mm)
    "radiation",          # Net kısa dalga güneş radyasyonu (J/m²)
    "evaporation",        # Buharlaşma (m)
    "gdd_cumulative",     # Büyüme derece gün toplamı
    "drought_index_7d",   # 7 günlük kuraklık indeksi
    "vpd_kpa",            # Vapor Pressure Deficit (kPa)
    "soil_clay",          # Kil yüzdesi (statik)
    "soil_sand",          # Kum yüzdesi
    "soil_ph",            # pH
    "soil_organic_c",     # Organik karbon
    "phen_doy_sin",       # Day-of-year sinüs encoding
    "phen_doy_cos",       # Day-of-year kosinüs encoding
    "phen_stage_id",      # BBCH stage integer ID
]
```

**Dosya kaynağı:** `src/cp2_model/feature_names.json` (donmuş — değiştirilemez)

---

*Bu dokümantasyon, projenin TÜBİTAK 2209-A final raporu ve lisans tezi için tek başvuru kaynağıdır. Sürüm geçmişi için `git log docs/DOKUMANTASYON.md` komutu kullanılabilir.*

---

## EK C — Veri Bağlama & Dashboard Sertleştirme Oturumu (2026-05-23)

Bu bölüm, tek bir oturumda yapılan kapsamlı dashboard veri-bağlama ve akademik tutarlılık düzeltmelerini, kod & dosya referanslarıyla kayıt altına alır.

### C.1 Eksik Verim JSON Üretimi

**Sorun:** Dashboard FLOV `yield_forecast.py` paneli `reports/prospective/EVR_01_2025_yield.json` dosyasını arıyordu, dosya yoktu.

**Yapılan:**
- `scripts/predict_yield.py` oluşturuldu — donmuş crop-aware XGB modellerini (`yield_xgb_sunflower.pkl`, `yield_xgb_wheat.pkl`) çağırarak per-site/per-year yield JSON üretir.
- `--site EVR_01`, `--year 2025`, `--all` bayrakları desteklenir.
- Çıktı: `predicted_yield_t_ha`, `model_sha256_short`, güven aralığı, risk seviyesi, top 3 SHAP faktör.
- 5 saha × 2 yıl = **10 yield JSON** üretildi (`EVR_01..EVR_05` × {2025, 2026}).

### C.2 ERA5-Land Yağış Skala Düzeltmesi

**Sorun:** `precip_total: 3197 mm` yıllık değeri çıkıyordu (Trakya gerçek yıllık ≈ 600 mm). Sebep: ERA5-Land hourly `tp` kanalı **midnight'tan kümülatif** olarak gelir. 24 saatlik değerlerin **toplamı** ≈ üçgen sayım = **12.5× şişirme**.

**Çift katmanlı düzeltme:**
1. **Kaynak (ETL) düzeltmesi** — `src/cp1_etl/mod_era5_cds.py:189-225`
   - `agg_dict['tp'] = ['sum']` → `['max']` (ssr, e için de aynı)
   - Aggregation sonrası column rename: `tp_max → tp_sum`, downstream sözleşme korunur
2. **Tüketici tarafı görüntüleme düzeltmesi**
   - `scripts/predict_yield.py` — `ERA5_TP_TRIANGULAR_FACTOR = 12.5`. JSON çıktısında iki blok:
     - `features` — gerçekçi (`/12.5`, mm gerçek)
     - `features_model_input` — eğitim ölçeğiyle uyumlu ham değer (XGB modelin gördüğü)
   - `src/dashboard_pages/weather/historical_trends.py:39` — `tp_display = (df["tp_sum"] / 12.5).clip(0, 80)`
   - `src/dashboard_pages/_legacy_pages.py:480` — `df_hv["yagis_disp"] = (df_hv["precipitation"].fillna(0) / 12.5).clip(0, 80)`

**Not:** Eğitim verisi (2017-2024 retrospektif) aynı şişik ölçekte. Model retrain edilmeden önce model giriş sözleşmesi korunmalı; sadece **görüntüleme** düzeltmeli.

### C.3 DB Görünüm (View) Katmanı Sertleştirme

**Sorun:** Yeni şema (`scripts/init_database.py`) view'leri sadece Türkçe alias kolonlarını yayınlıyordu (`nem_1_pct`, `hava_temp_c`). Dashboard kodu fiziksel adlarla okuyordu (`humidity`, `temperature`, `soil_moisture`) → KeyError zincir reaksiyonu.

**Çözüm:** `scripts/init_database.py` view'leri **hem fiziksel hem TR alias** yayınlayacak şekilde güncellendi:
- `tarlalar` view → `name`, `evrenli_id`, `crop_type`, `soil_type AS toprak_tipi`, `season_start_month`, `season_end_month`, `active_season_year` + mevcut Türkçe alias'lar
- `rover_olcumler` view → `temperature`, `humidity`, `soil_moisture`, `ndvi`, `precipitation` + `hava_temp_c`, `hava_nem_pct`, `nem_1_pct`, `ndvi_tahmini`, `yagis_mm`
- `hava_kayitlari` view → `timestamp`, `temperature`, `humidity`, `precipitation` + `tarih`, `sicaklik_c`, `nem_pct`, `yagis_mm`

**Doğrulama:** 5 tarla × 502 rover ölçümü × 30 günlük hava verisi sıfır KeyError ile okunuyor.

### C.4 13 Adımlık Dashboard Düzeltme Setçi

| # | Modül | Sorun | Çözüm |
|---|---|---|---|
| 1 | `init_database.py` | View kolon mismatch'i | C.3 — hem fiziksel hem alias |
| 2 | `src/database.py:get_weather_stats` | Var olmayan kolonları okuyor (`hava_temp_c`, `gdd_kumulatif`, `don_riski`, `sicak_stres`) | Gerçek view kolonlarına bağlandı: `temperature`, `precipitation`, `gdd` |
| 3 | `src/dashboard_pages/weather/forecast.py` | Aynı dict içinde 2× `"temperature"` key → Tmax = Tmin | `"temp_max"` ve `"temp_min"` ayrı key'lere ayrıldı |
| 4 | `src/dashboard_pages/weather/historical_trends.py` | Hem T max hem T min aynı kolonu (`temperature`) çiziyordu | ERA5 unified parquet'in `t2m_max`, `t2m_min`, `t2m_mean` kanallarına bağlandı |
| 5 | `src/dashboard_pages/_legacy_pages.py:449-494` | Sentetik `temperature ± 5°C` band; `drought_index == 1` ve `temperature == 1` anlamsız filtreler | 7-gün rolling min/max envelope; `temperature < 0` (frost), `temperature > 32` (heat stress); `gdd.cumsum()` |
| 6 | `_legacy_pages.py:752-820` | Model-vs-Rover totoloji: `_model_nem` `r["humidity"]`'i üzerine yazıyor → `fark = humidity - humidity = 0` | `rover_nem` ve `model_nem` ayrı key'lerde tutuldu (geçici çözüm, C.7'de tamamen değiştirildi) |
| 7 | `_legacy_pages.py:367` | Hardcoded Trakya ortalaması (`280` buğday, `220` ayçiçeği) | `_load_yield_meta(crop_key)` ile `src/cp2_model/yield_meta_{wheat,sunflower}.json`'dan `trakya_median_yield` okunuyor (324 / 180) |
| 8 | `src/dashboard_pages/home.py:65` | "Hava uyarıları" KPI hardcoded `"—"` | Open-Meteo 7-günlük forecast + `alert_rules.evaluate_forecast()` canlı sayım |
| 9 | `_legacy_pages.py:286-296` | `soil_moisture` NULL ise sessiz **0.25 (%25)** fallback | Hiyerarşi: rover gözlemi → ERA5 (% veya fraction otomatik tespit) → `None`. Sahte değer yok |
| 10 | `src/cp4_rag/agentic_rag.py:26-28` | `continue` sonrası ölü kod → `filtered_docs` hep boş → RAG bağlam üretmiyor | Girinti düzeltildi, append `continue`'dan önceki bloka taşındı |
| 11 | `src/data_integration/live_predictor.py:57` | `clim_mod.load_default_climatology()` — fonksiyon yok | `clim_mod.load_climatology()` (gerçek isim) |
| 12 | `scripts/predict_yield.py --all` | EVR_02..EVR_05 yield JSON yok | 10 JSON üretildi (5 saha × 2 yıl) |
| 13 | Smoke-test | — | 8 modül + DB API + 502 rover satırı temiz |

### C.5 FLOV NDVI Forward Prediction Üretimi

`reports/prospective/EVR_01_2026_predictions.parquet bulunamadi` hatası → 5 saha için 2026 yılı tahminleri eksikti.

**Çalıştırılan:** `python scripts/predict_evr01.py --site EVR_XX --year 2026` (5 saha için)

**Üretildi:** `EVR_{01..05}_2026_predictions.parquet` (her biri 107 satır)

| Saha | Predicted NDVI (mean) | İklim Anomalisi |
|---|---|---|
| EVR_01 | 0.297 | -0.16 (düşük) |
| EVR_02 | 0.544 | +0.08 (iyi) |
| EVR_03 | 0.298 | -0.16 (düşük) |
| EVR_04 | 0.491 | +0.03 (normal) |
| EVR_05 | 0.342 | -0.12 (düşük) |

Toplam **10 prediction parquet** (5 saha × 2025/2026) artık `reports/prospective/` altında.

### C.6 LLM Module Shadowing Çözümü

**Sorun:** `LLM modülü yüklenemedi: cannot import name 'llm_status_text' from 'llm_engine'`

**Kök neden:** Aynı isimde iki modül var:
- `src/llm_engine.py` — dispatcher (model picker, `get_llm_engine`, `llm_status_text`)
- `src/cp4_rag/llm_engine.py` — Ollama API client (`query_llm`, `rag_query`)

`_legacy_pages.py:30-32` `sys.path.insert(0, _CP4_DIR)` ile CP4'ü öne koyduğundan cp4_rag'inki kazanıyordu; settings.py'deki `from llm_engine import llm_status_text` AttributeError veriyordu.

**Çözüm:** `src/cp4_rag/llm_engine.py`'ye `get_llm_engine()` ve `llm_status_text()` shim fonksiyonları eklendi — hangi `llm_engine` kazanırsa kazansın çağırılan isimler bulunuyor.

**Doğrulama:** `🟢 gemma3:4b` döndü.

### C.7 Tarla Detay — Akademik Tutarlılık Düzeltmesi (Option B)

**Akademik sorun raporu:**
Önceki "Model vs Rover Karşılaştırması" grafiği **üç katmanlı yanlış**tı:
1. `_model_nem()` modelin çıktısı değil — hardcoded `_wheat_season()` / `_sunflower_season()` fenoloji eğrisi. Frozen LSTM **NDVI tahmin ediyor**, toprak nemi değil.
2. `r["humidity"]` (rover) gerçekte ERA5 RH2m **hava nemi** — toprak nemi değil. DB sorgusu: `sensor_reading.soil_moisture` tüm 2510 satırda **NULL** (rover henüz konuşlanmadı, saha çıkışı 2026 sonrası).
3. Y ekseni "Toprak Nemi (%)" diye etiketliydi — yanlış birim.

**Seçim:** Option B (NDVI karşılaştırması). Option A imkânsızdı — 0 satır toprak nemi var; sonsuz "veri bekleniyor" placeholder olur.

**Yeni grafik** (`_legacy_pages.py:742-880`):
- Başlık: "📈 Frozen LSTM NDVI Tahmini vs Sentinel-2 Gerçek NDVI"
- Veri kaynağı: `validation.csv` (öncelik, actual_ndvi var) → `predictions.parquet` (fallback)
- 3 trace: `predicted_ndvi` (mavi çizgi) · `climatology_ndvi` (gri kesik) · `actual_ndvi` (yeşil noktalar — sadece validation varsa)
- SAPMA mantığı: per-stage MAE ≈ 0.07 referansla:
  - |Δ| ≤ 0.10 → 🟢 NORMAL (~1.4σ içi)
  - 0.10–0.20 → 🟡 SAPMA
  - > 0.20 → 🔴 KRİTİK (~3σ)
- Provenance caption: model `sha256` + dosya yolu + per-stage R²/MAE
- Validation summary varsa: n_obs, MAE, R², bias metrikleri
- 2026 (henüz actual yok) için: tahmin + iklim anomalisi tablosu

### C.8 X-Modal Ekranının Tamamen Çalışır Hale Getirilmesi

**Audit bulgu:** 5 alt-sekmenin tamamı ya crash ediyor ya da bilgi vermeyen boş placeholder gösteriyordu.

| Alt-sekme | Sorun | Yapılan |
|---|---|---|
| 🛰️ Satellite (`satellite_view.py`) | `cfg.SATELLITE_PREDICTIONS_DIR` config'de yok → AttributeError "modul yuklenemedi" misleading | Tamamen yeniden yazıldı: ResNet50 path durumu + Planet API key durumu + stand-in source bildirimi + `CONSENSUS_PREDICTIONS_DIR`'dan per-site snapshot listesi |
| 📷 Field (`field_yolov8.py`) | YOLOv8 model yüklü olduğu halde sadece "log yok" diyordu | Model durumu + sınıf listesi + **canlı `st.file_uploader` ile upload-and-classify formu** (`image_classifier.classifier.classify()`) |
| 📊 Feature Predictor (`feature_predictor.py`) | Sekme adı "Predictor" ama hiçbir şey predict etmiyordu, ham kolon dump'lıyordu | Gerçek tahmin: NDVI vs DOY climatology z-skoru → `feature_zscore_to_class()` ile harmonize 4-sınıf. ±2σ baseline overlay grafiği |
| 🤝 Consensus (`consensus_view.py`) | Boş log placeholder + filtre mismatch (`evrenli_id` vs `site_id`) | Boş durumda engine config gösterilir (modalite ağırlıkları, taksonomi, karar bayrakları). Veri varsa aggregate Cohen/Fleiss κ + agreement metrikleri |
| 🏷️ Annotation (`annotation_tool.py`) | `_vv.DATA_DIR` config'de yok → fallback path | `_vv.GROUND_TRUTH_DIR` (config'de tanımlı) kullanılıyor |

**Yan etki düzeltmesi** (`src/dashboard_pages/shared/data_loaders.py:174`):
- `_read_jsonl_tail`: artık hem `site_id` hem `evrenli_id` kolonunu deniyor. Önceden visual_validation log'ları `site_id` yazıyor, filter `evrenli_id` arıyor → sessizce hiç filtrelemiyordu.

### C.9 Veri Kaynağı Şeffaflığı Standardı

Bu oturumda **tüm** veri-bağlı UI bloklarına şeffaflık caption'ı eklendi. Standart format:

> Veri kaynakları: **Model adı** (`sha256` veya versiyon) · **Gözlem kaynağı** · `dosya/yolu/şablonu` · Per-stage metrikler

Örnek (Tarla Detay):
> Veri kaynakları: **Frozen LSTM** (sha256 `1b8f2a14404f87ad`) · **Sentinel-2 NDVI** (GEE) · `reports/prospective/EVR_01_2025_validation.csv` · Per-stage R²=0.76–0.79, MAE≈0.07

### C.10 Smoke-Test Kapsamı

Oturum sonunda doğrulanan modüller (tümü temiz import):

```
src/database.py
src/dashboard_pages/_legacy_pages.py
src/dashboard_pages/home.py
src/dashboard_pages/weather/forecast.py
src/dashboard_pages/weather/historical_trends.py
src/dashboard_pages/weather/weather_alerts.py
src/dashboard_pages/cross_modal/__init__.py
src/dashboard_pages/cross_modal/satellite_view.py
src/dashboard_pages/cross_modal/field_yolov8.py
src/dashboard_pages/cross_modal/feature_predictor.py
src/dashboard_pages/cross_modal/consensus_view.py
src/dashboard_pages/cross_modal/annotation_tool.py
src/dashboard_pages/shared/data_loaders.py
src/cp4_rag/agentic_rag.py
src/cp4_rag/llm_engine.py
src/data_integration/live_predictor.py
src/llm_engine.py
```

DB fonksiyon doğrulaması:
- `get_tarlalar()`: 5 tarla
- `get_rover_olcumler_asc(t.id)`: 502 satır (humidity, temperature, ndvi mevcut)
- `get_weather_history(t.id, 30)`: 30 satır (temp, precip, gdd)
- `get_weather_stats(t.id, 30)`: `{avg_temp: 14.0, max: 19.3, min: 8.3, toplam_yagis: 366.2, gdd_kum: 264.9}`

### C.11 Akademik Notlar (Tez/Final Raporu İçin)

1. **"Model vs Gözlem" konsepti**: Sistemde yalnızca **bir** doğru karşılaştırma vardır → Frozen LSTM NDVI 7-gün tahmini vs Sentinel-2 gözlemi. Toprak nemi modeli **yoktur**; rover sensörleri **henüz konuşlanmamıştır**. Bu hassasiyet dashboard'ın her yerinde tutarlı.

2. **Veri durumu (2026-05-23 itibariyle)**:
   - Real Sentinel-2 NDVI: 2510 günlük satır (5 saha)
   - ERA5-Land klima: 2510 günlük satır (5 saha)
   - Rover/ESP32 fiziksel ölçüm: **0 satır** (saha çıkışı sonrası gelecek)
   - YOLOv8 model: `models/crop_health_best.pt` mevcut (6 sınıf)
   - Satellite ResNet50: **eğitilmedi** (Planet Education key bekleniyor)

3. **Skala uyarısı**: ERA5-Land hourly `tp` kanalı yalnış toplandığında 12.5× şişirir. Bu hata **eğitim verisinde de mevcuttu**, dolayısıyla model **şişik ölçeği bekliyor**. Yeniden eğitilene kadar model girişi ham haliyle korunur; sadece display'de bölünür.

4. **3-yollu konsensüs**: Modalite ağırlıkları (Field=0.40, Satellite=0.30, Features=0.30) `visual_validation/config.py` içinde sabit; YOLOv8 → harmonize 4-sınıf (`healthy`, `mild_stress`, `severe_stress`, `disease`); Feature predictor z-skor eşikleri (z=-1.0 / z=-2.0) σ_NDVI(doy) ≈ 0.07 varsayımı ile kalibre.

---

*EK C kayıt tarihi: 2026-05-23. Oturum kapsamı: backend audit + 21 mock/bug bulgusu üzerinden 13-adımlık prioritized fix + akademik tutarlılık (Option B) + X-Modal tamamı + dokümantasyon.*

---

# EK D — ÇP-2.5: NDVI → Verim Kalibrasyon Katmanı (2026-05-23)

## D.1 Amaç ve Konum

ÇP-2.5, ÇP-1 ETL çıktısı (`master_feature_matrix_2017_2024.csv`) ve TÜİK Bitkisel Üretim İstatistikleri (22 yıllık il-bazlı kg/dekar verim, 2004-2025) arasındaki köprüdür. Mevcut ÇP-2 NDVI tahmin pipeline'ına dokunmadan, çiftçinin anlayacağı somut **kg/dekar verim** çıktısı + 22 yıllık karşılaştırma + Türkçe yorum üretir.

Dosya konumu: `src/cp25_calibration/`
- `build_calibration_set.py` — sezonluk feature engineering
- `train_calibration.py` — Ridge/GBR/RF + LOOCV + SHAP
- `anomaly_validation.py` — anomali yıl out-of-sample testi
- `inference.py` — `predict_yield_kg_da()` public API
- `rag_ingest.py` — TÜİK chunk'larını FAISS'e ekler
- `tests/test_cp25_end_to_end.py` — uçtan uca smoke

## D.2 Veri Akışı

```
TÜİK 22 yıl × 3 il × 2 ürün                  Master Feature Matrix
(verim hedefi, kg/dekar)                  (2017-2024, Vize centroid)
        │                                         │
        ▼                                         ▼
    [yields.csv]                       [MFM günlük, 23 kolon]
        │                                         │
        └────────┬────────────────────────────────┘
                 ▼
   build_calibration_set.py  (sezonluk pencereler)
                 │
                 ▼
   calibration_train_set_{bugday,aycicegi}.csv
   calibration_holdout_{bugday,aycicegi}.csv   ← 2025 hold-out
                 │
                 ▼
   train_calibration.py  (Ridge α-grid + GBR + RF, LOOCV)
                 │
                 ▼
   models/cp25_calibration_{bugday,aycicegi}.pkl   (champion bundle)
   reports/cp25_calibration_metrics.json
   reports/cp25_loocv_predictions_{crop}.csv
                 │
                 ▼
   inference.py → predict_yield_kg_da(...)  ← dashboard + RAG çağırır
```

## D.3 Sezonluk Feature Engineering

**Fenolojik pencereler** (FAO + Trakya iklim referansı):

| Ürün | Sezon başı | Sezon sonu | Çiçeklenme | Tane dolum |
|---|---|---|---|---|
| Buğday (kışlık) | 1 Ekim (t-1) | 15 Temmuz | Mayıs | Haziran |
| Ayçiçeği (yağlık) | 1 Nisan | 30 Eylül | Temmuz | Ağustos |

**10 feature per (il, year, crop)**:

| Feature | Tanım | Akademik gerekçe |
|---|---|---|
| `ndvi_max` | Sezon peak NDVI | Maksimum biyokütle (Tucker 1979) |
| `ndvi_mean` | Sezon ortalama NDVI | Genel kanopi sağlığı |
| `ndvi_integral` | NDVI günlük toplamı | Toplam fotosentez proxy'si (Kogan 1990) |
| `ndvi_flowering` | Çiçeklenme ort. NDVI | **En kritik dönem** (Doraiswamy 2003) |
| `ndvi_grain_fill` | Tane dolum ort. NDVI | Verim oluşum dönemi |
| `greenness_days` | NDVI > 0.6 gün sayısı | Sezon uzunluğu (Kogan VCI) |
| `gdd_cum_season` | Kümülatif GDD (base 0 buğday, 8 ayçiçeği) | Termal birikim (McMaster 1997) |
| `tp_season_sum` | Toplam yağış (mm) | Su mevcudiyeti |
| `ndwi_min_flowering` | Çiçeklenmede min NDWI | Su stresi göstergesi (Gao 1996) |
| `t2m_max_flowering_mean` | Çiçeklenmede ort. T_max | Isı stresi proxy'si |

NDVI değerleri **`NDVI_int`** (interpolated, %0 missing) kullanır; raw NDVI (Sentinel-2 ~5 günde bir, %87.7 gap) doğrudan kullanılmaz.

## D.4 Veri Kapsamı Kararları (Akademik Justification)

**İl boyutu**: MFM tek bir centroid noktası için (Vize, 41.045 N / 27.205 E — Kırklareli ilçesi). 3 il (Edirne, Kırklareli, Tekirdağ) hepsi aynı MFM feature'larını paylaşır → `il` kategorik feature olarak **one-hot encoded** modele girer. Bu yapı:
- İl-içi varyansı yapay olarak sıfırlar (sınırlama — tezde raporlanır)
- İl-arası **sistematik ofset**i `il_X` dummy'leri üzerinden öğrenir
- Per-il **bias correction** train residuals'ından hesaplanır (`per_il_bias_correction_kg_da`)

**Yıl boyutu**: TÜİK 2004-2025 → MFM 2017-2024 kesişim.
- Buğday: 2018-2024 (n=21 = 7 yıl × 3 il). **2017 dışlandı** (kışlık ekim Ekim 2016'da başlar; MFM 2017-01'den)
- Ayçiçeği: 2017-2024 (n=24 = 8 yıl × 3 il)
- **2025**: hold-out (true forecast test, 3 il)
- **2004-2016**: dışlandı (MFM kapsamı yok) — `yield_stats_summary.csv`'de narrative-only

## D.5 Model Yarışı ve LOOCV Sonuçları

Her ürün için 3 model yarıştırıldı, **Leave-One-Out CV** ile out-of-sample tahminler toplandı:

### Buğday (n=21)

| Model | R² | MAE | RMSE | MAPE |
|---|---|---|---|---|
| **Ridge(α=100)** ⭐ | **-0.085** | 40.7 | 55.2 | 9.7% |
| GBR(200,3,0.05) | -1.050 | 51.1 | 75.9 | 12.3% |
| RF(300,5) | -0.228 | 39.6 | 58.7 | 9.5% |

**Verdict**: ❌ **FAIL** (R²<0.45 kriteri). Model intercept + per-il dummy'leri öğreniyor, NDVI/iklim gradient'i istatistiksel olarak anlamlı bir sinyal vermiyor. Tahmin esasen il-ortalamasıdır. **Bu, veri kısıtının doğal sonucu**: 3 ilin features'ları aynı (Vize proxy), bugday'da il-arası varyans büyük (Tekirdağ μ=408 vs Kırklareli μ=369), il-içi NDVI varyansı küçük → ayırt edici sinyal düşük.

### Ayçiçeği (n=24)

| Model | R² | MAE | RMSE | MAPE |
|---|---|---|---|---|
| **Ridge(α=1.0)** ⭐ | **+0.646** | 19.7 | 25.4 | 10.6% |
| GBR(200,3,0.05) | +0.268 | 24.7 | 36.6 | 13.7% |
| RF(300,5) | +0.556 | 19.6 | 28.5 | 10.8% |

**Verdict**: ✅ **PASS** (R²≥0.45 ✓, MAE≤35 ✓). Kern et al. (2018) bandında (R²=0.55–0.75); ayçiçeği daha yüksek CV (%21 vs buğday %13) ve NDVI duyarlılığı sayesinde sinyal yakalanıyor.

## D.6 Anomaly Year Validation

`anomaly_years.csv` (|z|>1.5) yılları train'den ÇIKARILIP test edildi:

| Ürün | n_anom_in_train | MAE_anomaly | MAPE_anomaly | LOOCV_MAE (referans) |
|---|---|---|---|---|
| Buğday | 4 | 113.7 kg/da | 22.3% | 40.7 |
| Ayçiçeği | 6 | 33.2 kg/da | 21.3% | 19.7 |

**Buğday**: Anomali MAE'si LOOCV'in 2.8 katı — model 2021/2023'ün yüksek-verim anomalisini kaçırıyor. **Beklenen**, çünkü model intercept dominant.

**Ayçiçeği**: Anomali MAE'si LOOCV'in 1.7 katı.
- Yüksek-verim anomalileri (2019, 2020 Kırklareli/Tekirdağ): MAE 7-31 kg/da → **iyi yakalama**
- Düşük-verim anomalileri (2023 Tekirdağ z=-2.12, 2024 Edirne z=-1.72): **60+ kg/da underestimation** — model kuraklığı kısmen yakalıyor ama tam değil

**H3 hipotezi (yanlış pozitif düşürme) için kanıt**: Ayçiçeğinde anomali MAE'si LOOCV MAE'sinin 1.7 katı kalıyor → alert sistemi için kullanılabilir, ama düşük-verim uç olayları için ek margin gerekiyor.

## D.7 Per-İl Bias Correction

Train set residuals'ından hesaplanan ortalama sapmalar (LOOCV tahmininin gerçeğe göre):

| Crop | Edirne | Kırklareli | Tekirdağ |
|---|---|---|---|
| Buğday | +3.9 kg/da | -7.5 kg/da | +5.2 kg/da |
| Ayçiçeği | +6.4 kg/da | -10.7 kg/da | +4.3 kg/da |

`inference.predict_yield_kg_da()` bu correction'ı otomatik uygular: `yhat_corrected = yhat_raw + bias[il]`.

## D.8 Public API — `predict_yield_kg_da(...)`

Lokasyon: `src/cp25_calibration/inference.py`

```python
def predict_yield_kg_da(
    predicted_ndvi_series: pd.DataFrame | None,
    feature_context: pd.DataFrame,
    il: Literal['Edirne','Kırklareli','Tekirdağ'],
    crop: Literal['bugday','aycicegi_yaglik'],
    current_date: pd.Timestamp,
) -> dict
```

**Return**: 20-anahtarlı sözlük — `yield_kg_da` (corrected), `yield_kg_da_{lower,upper}` (%95 CI = ±1.96×RMSE_LOOCV), `lokal_22yil_{ortalama,std,min,max}`, `sapma_pct`, `sapma_yorum` (Türkçe), `confidence` (0–1, kalite × sezon tamamlanma çarpımı), `features_used` (şeffaflık), `sezon_tamamlanma_pct`, `model_version`, `champion_model`, `metrics_loocv`, `limitations`.

**LLM context için doğrudan eklenebilir** (RAG katmanı bu sözlüğü Türkçe yoruma çevirir).

## D.9 Uçtan Uca Test Sonuçları

`tests/test_cp25_end_to_end.py` çıktısı (3/3 PASS):

| Senaryo | Gerçek | Tahmin | MAE | Yorum |
|---|---|---|---|---|
| Tekirdağ 2023 ayçiçeği (kuraklık z=-2.12) | 115 | 154 | 39 | "Belirgin düşüş — sulama/girdi gözden geçirilmeli" |
| Edirne 2021 buğday (z=+1.64) | 474 | 387 | 87 | "Hafifçe ortalamanın üstünde" |
| Kırklareli 2022 buğday (normal) | 400 | 397 | 3 | "Hafifçe ortalamanın üstünde" |

## D.10 RAG Entegrasyonu

6 adet TÜİK chunk'ı FAISS index'ine eklendi (`intfloat/multilingual-e5-small` embedding):

```
Önce  : 17059 vektör
Sonra : 17065 vektör (+6)
Idempotent: aynı chunk_id varsa atlar
```

Eklenen chunk_id'ler: `tuik_{edirne,kirklareli,tekirdag}_{aycicegi_yaglik,bugday}`. Metadata schema mevcutla uyumlu: `{source, category="yield_statistics", language="tr", chunk_id_external, il, urun, kaynak, metric_type}`.

## D.11 Akademik Sınırlamalar (Tez İçin)

1. **Centroid proxy**: Features tek bir noktadan (Vize) türetiliyor. Per-il feature varyansı yapay olarak sıfır — `il` one-hot ile sistematik ofset absorbe ediliyor ama il-içi feature dinamiği kayıp. Düzeltme yolu: 3 il centroid'ı için ETL'yi yeniden koşmak (`cp1_etl` script'leri Edirne ve Tekirdağ koordinatlarıyla; ~6-8 saat).

2. **Örneklem küçüklüğü**: n=21 (buğday) / n=24 (ayçiçeği) — LOOCV ile maksimum istatistiksel verim, ancak sonuçlar 1-2 outlier'a hassas. Tez yorumunda **CI bantları** her tahmin için raporlanmalı.

3. **Buğday model başarısızlığı (R²=-0.085)**: Modelin intercept-only davranışı dürüstçe raporlanmıştır. Düzeltme önerileri:
   - 3 il ayrı ETL (#1) ile gerçek il-içi varyans yakalanır
   - Sonbahar-kış pre-emergence ETL kapsama (Oct-Mar) bugday için kritik
   - Multi-year lagged features (geçen sezon EVI peak vs.)

4. **2025 hold-out kullanılmadı**: MFM 2025 yok → 2025 holdout dosyası (`calibration_holdout_*.csv`) yer tutucu olarak yazıldı; gerçek forecast test için 2025 ETL backfill gerek.

5. **Bias correction agresif değildir**: Per-il correction ±10 kg/da civarı, anomali yıllarda korunmasız. Production'da `sapma_yorum` + `confidence` alanı kullanıcıya belirsizliği gösteriyor.

6. **TÜİK kaynağı manuel**: `tuik_trakya_yields_clean.csv` 132 satır manuel TÜİK tablo extraction'ından geldi (resmi API yok). Her TÜİK rapor güncellemesinde manuel revize gerek.

## D.12 Üretilen Artefaktlar (Bu Oturum)

```
src/cp25_calibration/
├── __init__.py
├── build_calibration_set.py        (220 LOC)
├── train_calibration.py            (305 LOC)
├── anomaly_validation.py           (175 LOC)
├── inference.py                    (200 LOC)
└── rag_ingest.py                   (115 LOC)

data/processed/
├── calibration_train_set_bugday.csv     (n=21)
├── calibration_train_set_aycicegi.csv   (n=24)
├── calibration_holdout_bugday.csv       (n=3,  2025 hold-out)
└── calibration_holdout_aycicegi.csv     (n=3,  2025 hold-out)

models/
├── cp25_calibration_bugday.pkl     (Ridge α=100 bundle)
└── cp25_calibration_aycicegi.pkl   (Ridge α=1.0 bundle)

reports/
├── cp25_calibration_metrics.json       (full LOOCV table)
├── cp25_loocv_predictions_bugday.csv   (truth vs pred)
├── cp25_loocv_predictions_aycicegi.csv
├── cp25_anomaly_validation.md          (markdown report)
├── cp25_anomaly_predictions.csv
└── cp25_anomaly_summary.json

tests/
└── test_cp25_end_to_end.py             (3 senaryo, 3/3 PASS)

src/cp4_rag/faiss_index/
├── chunks_meta.json                    (17059 → 17065 entries, +6 TÜİK)
├── index.faiss                         (updated)
└── index.pkl                           (updated)
```

## D.13 Reproducibility

```bash
# 0) Ön koşul: data/external/tuik/ dosyaları mevcut, MFM mevcut
python src/cp25_calibration/build_calibration_set.py
python src/cp25_calibration/train_calibration.py
python src/cp25_calibration/anomaly_validation.py
python src/cp25_calibration/rag_ingest.py        # idempotent
python tests/test_cp25_end_to_end.py             # 3/3 PASS bekleniyor
```

**Çevre**: scikit-learn ≥1.3, shap 0.51, langchain-huggingface, faiss-cpu (AVX2), numpy, pandas, matplotlib (Agg backend).

**Determinism**: GBR/RF `random_state=42`. LOOCV deterministic. Ridge analytical. Tüm bundle'lar `train_date_utc` taşıyor.

---

*EK D kayıt tarihi: 2026-05-23. Oturum kapsamı: ÇP-2.5 NDVI→Verim kalibrasyon katmanı end-to-end (8 görev), 2 ürün × 3 model × LOOCV × SHAP × anomaly validation × RAG ingest × inference API × E2E test.*

---

# EK E — ÇP-2.5 v2 (İlçe-Bazlı, n=1165) Akademik Sürüm (2026-05-23)

## E.1 v1 → v2 Geçiş Gerekçesi

EK D'deki v1 sürümü (n=21/24, il-bazlı Vize-centroid proxy) **akademik
defansta yetersiz** olduğu kullanıcı feedback'i ile tespit edildi.  v2
sürümü TÜİK 1165 satırlık ilçe-bazlı dataset üzerine kuruldu (29 Trakya
ilçesi + 5 İstanbul kontrol × 22 yıl × 2 ürün).

## E.2 Veri Çekme Sistemi Pivot — NASA POWER MERRA-2

Open-Meteo Archive sandbox network'ünden erişilemediği için **NASA POWER
(MERRA-2 reanalysis)** kaynağına geçildi:

| Boyut | Open-Meteo | NASA POWER |
|---|---|---|
| Source data | ERA5-Land redistr. | MERRA-2 reanalysis |
| Sandbox erişim | ❌ TIMEOUT | ✅ 0.6s/istek |
| 29 ilçe × 22 yıl süre | hesaplı 15 dk (erişilseydi) | **gerçek 5 dk** |
| Değişkenler | 9 günlük | 9 günlük (eşdeğer) |
| Akademik referans | Zippenfenig 2023 | Reichle 2017, FAO AquaCrop |

**Defansta savunma**: MERRA-2 ↔ ERA5-Land eşdeğer kalite reanalysis
(Reichle 2017, ECMWF Newsletter 159).  FAO AquaCrop + USDA-ARS standart
kullanım NASA POWER.

## E.3 Veri Akışı v2

```
TÜİK ilçe-bazlı verim                NASA POWER günlük
(1165 satır, 22 yıl)                 (233 044 satır, 29 ilçe)
        │                                     │
        ▼                                     ▼
   yields.csv                          climate.csv per ilçe
        │                                     │
        └────────────┬────────────────────────┘
                     ▼
        Layer A features (1165 satır × 14 climate)
                     │
        + Sentinel-2 NDVI (GEE 30m, cropland mask, 16-gün composite)
                     ▼
        Layer B features (n=464 hedef, NDVI ETL ilerledikçe)
                     │
        + ISRIC SoilGrids (clay, sand, silt, pH, SOC, AWC × 3 derinlik)
                     ▼
        Layer C features (full multimodal)
```

## E.4 Görev Çıktıları (v2 Pipeline)

| # | Görev | Çıktı |
|---|---|---|
| 1 | Veri Keşfi | `reports/cp25/01_data_exploration.{md,json}` + 4 figür |
| 2 | Baselines | LOYO B0/B1/B2/B3, ayç R²=0.21, buğ R²=0.21 |
| 3 | Climate ETL | 29 ilçe × 22 yıl, NASA POWER (5 dk) |
| 3b | NDVI ETL | 29 ilçe × 8 yıl, GEE (2.5 saat, ~178 composite/ilçe) |
| 3c | SoilGrids | 29 ilçe × 23 kolon (clay, sand, silt, pH, SOC, AWC × 3 depth) |
| 4 | Seasonal Features | Layer A/B/C calibration sets |
| 5 | Layer A modeller | 5 model × 3 CV = 15 ev/crop, LOYO FAIL, LOILO PASS |
| 8 | XAI Layer A | SHAP global + PDP + permutation |
| 9 | Anomaly Validation Layer A | ayç SS=0.27, buğ SS=0.13 |
| 10 | Belirsizlik Layer A | Bootstrap PICP=0.38 (underestimated, B/C beklenir) |
| 11 | Spatial Diagnostics | Moran's I buğ +0.257 p=0.013 (anlamlı) |

## E.5 Akademik Bulgular

### Layer A LOYO Şampiyonları

| Crop | Model | R² | RMSE (kg/da) | Skill Score |
|---|---|---|---|---|
| Buğday | ElasticNet | -0.092 | 72.7 | -0.178 |
| Ayçiçeği | Random Forest | +0.051 | 49.5 | +0.009 |

**Kabul kriteri (R²≥0.35/0.40) FAIL** — climate-only LOYO için yetersiz.

### LOILO vs LOYO — H5 Reddedildi

| Crop | LOILO R² | LOYO R² | Δ |
|---|---|---|---|
| Ayçiçeği (XGBoost) | 0.504 | -0.076 | **0.580** |
| Buğday (GPR) | 0.441 | -0.198 | **0.639** |

H5 (|LOILO-LOYO|<0.15) **reddedildi**.  Moran's I = +0.257 (buğday,
p=0.013) ile teyit edildi.  Bu Tao et al. 2023'ün "yerel model üstünlüğü"
literatürünü destekleyen önemli akademik bulgudur.

### Hipotez Durumu (Layer A sonrası)

| H | Sonuç | Durum |
|---|---|---|
| H1 ΔR²≥0.15 (n=1165 vs n=132) | LOYO ❌, LOILO ✅ | Kısmi |
| H2 NDVI marjinal ≥0.10 | Layer B bekliyor | Bekleniyor |
| H3 multimodal ≥0.05 | Layer C bekliyor | Bekleniyor |
| H4 anomali SS>0.30 | Ayç Layer A=0.27, Buğ=0.13 | Layer B/C ile yükselmesi beklenir |
| **H5** \|LOILO-LOYO\|<0.15 | **❌ Reddedildi** (Δ=0.58) | Akademik bulgu |

## E.6 SHAP Top Özellikler (Layer A XGBoost)

| Sıra | Buğday | Ayçiçeği |
|---|---|---|
| 1 | gdd_cum_season (17.4) | tp_season_sum (10.9) |
| 2 | vernalization_days (9.7) | gdd_cum_season (10.0) |
| 3 | tp_flowering (7.5) | gdd_flowering (5.7) |
| 4 | tp_season_sum (6.7) | tp_flowering (5.2) |
| 5 | tp_winter_sum (6.7) | aridity_index (5.2) |

**Fizyolojik doğrulama**: Buğday kışlık → vernalizasyon + kış rezervi
baskın.  Ayçiçeği yazlık → mevsim yağışı + termal birikim baskın.

## E.7 Üretilen Artefakt Sayım (v2)

```
src/cp25/
├── __init__.py
├── 01_data_exploration.py        (310 LOC)
├── 02_baselines.py               (235 LOC)
├── 03_fetch_ilce_climate.py      (245 LOC, NASA POWER)
├── 03b_fetch_ilce_ndvi.py        (255 LOC, GEE client-loop)
├── 03c_fetch_ilce_soil.py        (140 LOC)
├── 04_seasonal_features.py       (270 LOC)
├── 05_layer_a_climate_only.py    (320 LOC)
├── 08_xai_analysis.py            (190 LOC)
├── 09_anomaly_validation.py      (175 LOC)
├── 10_uncertainty.py             (180 LOC)
└── 11_spatial_diagnostics.py     (115 LOC)
                                  ──────────
TOPLAM                            ~2435 LOC

data/processed/
├── openmeteo_ilce/*.csv  × 29     (233 044 satır)
├── ndvi_ilce/*.csv       × 14+    (devam ediyor)
├── soil_ilce.csv         × 1
├── calibration_features_layerA.csv (1165 × 20)
├── calibration_features_layerB.csv (genişleyecek)
└── calibration_features_layerC.csv (genişleyecek)

models/cp25/
├── baselines.pkl
├── layer_a_bugday.pkl
└── layer_a_aycicegi.pkl

reports/cp25/
├── 01_data_exploration.{md,json}
├── 02_baselines.{md,csv}
├── 03_climate_fetch_log.{md,csv}
├── 04_features_qa.md
├── 05_layer_a_results.{md,csv}
├── 05_loocv_predictions_{bugday,aycicegi}.csv
├── 08_xai_A.md + perm_importance_*.csv
├── 09_anomaly_validation_A.{md,csv}
├── 10_uncertainty_A.{md} + predictions_*.csv
├── 11_spatial_diagnostics.md
└── fig_*.png × 12

thesis/
├── bolum_4_veri.md
├── bolum_5_yontem.md
├── bolum_6_sonuclar.md
├── bolum_7_tartisma.md
└── bibliography.bib    (17 referans)
```

## E.8 Reproducibility

```bash
# 0) Ön koşul: TÜİK ilçe-bazlı CSV mevcut
python src/cp25/01_data_exploration.py
python src/cp25/02_baselines.py
python src/cp25/03_fetch_ilce_climate.py --all     # ~5 dk
python src/cp25/03b_fetch_ilce_ndvi.py --all       # ~2.5 saat GEE
python src/cp25/03c_fetch_ilce_soil.py             # ~90 sn GEE
python src/cp25/04_seasonal_features.py
python src/cp25/05_layer_a_climate_only.py         # ~10 dk
python src/cp25/08_xai_analysis.py --layer A
python src/cp25/09_anomaly_validation.py --layer A
python src/cp25/10_uncertainty.py --layer A --n-boot 100
python src/cp25/11_spatial_diagnostics.py
```

**Determinism**: numpy seed=42, sklearn random_state=42, XGBoost
random_state=42, KMeans n_init=10.

---

*EK E kayıt tarihi: 2026-05-23. Oturum kapsamı: ÇP-2.5 v2 akademik
sürüm — NASA POWER pivot, ilçe-bazlı n=1165, 3 katmanlı + 3 CV mimarisi,
Layer A tam pipeline (6 görev), Moran's I, SHAP/XAI, anomaly validation,
belirsizlik kantifikasyonu, tez Bölüm 4-7 batch yazımı.*

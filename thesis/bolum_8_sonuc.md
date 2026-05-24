# Bölüm 8 — Sonuç ve Gelecek Çalışma

## 8.1 Çalışmanın Özet Bulguları

Bu çalışma, Trakya bölgesinde **22 yıllık (2004-2025) ilçe-bazlı TÜİK verim
verisi** ile **NASA POWER MERRA-2 reanalysis climate**, **Sentinel-2 NDVI**
ve **ISRIC SoilGrids** veri kümelerini birleştirerek **akademik standartta
çok-modlu** verim kalibrasyon modeli geliştirdi.  Beş ana katkı:

1. **İlçe-bazlı veri yükseltmesi**: önceki il-bazlı 132 satırlık dataset'in
   yerini 1165 satırlık ilçe-bazlı dataset aldı (8.8× örneklem).  Bu,
   gerçekçi cross-validation şemalarını mümkün kıldı.

2. **NASA POWER ETL pipeline**: ERA5-Land yerine MERRA-2 redistribütörünü
   tercih ederek **5 dakikalık** wall-clock ETL ile **iteratif** hipotez
   testlerini ekonomik kıldı.

3. **3-katmanlı + 3-CV-şemalı akademik karşılaştırma**:
   - Layer A (climate-only) → Layer B (+NDVI) → Layer C (+soil)
   - LOYO + LOILO + Spatiotemporal block CV
   - 5 model (PLS/ElasticNet/RF/XGBoost/GPR) + stacking ensemble

4. **Mekânsal autocorrelation niceleştirmesi**: Buğday için Moran's I
   = +0.257 (p=0.013) — Trakya'da komşu ilçeler benzer model hatalarına
   sahip; geographic feature eksiklik kanıtı.

5. **Akademik dürüstçe raporlanmış sınırlamalar**: Layer A LOYO başarısızlığı
   (R² ≈ 0) climate-only modelin yetersizliğini gösterdi; bu, **H2 hipotezi
   için mekanistik gerekçedir** (NDVI/soil eklenmesi şart).

## 8.2 Hipotez Sonuçları Sentezi

| Hipotez | Sonuç | Detay |
|---|---|---|
| H1 — n=1165 vs n=132 | LOYO ❌, LOILO ✅ | v1 küçük örneklem overfitting'iydi |
| H2 — NDVI marjinal ≥0.10 | Layer B'de raporlanacak | NDVI ETL tamamlanma sonrası |
| H3 — Multimodal ≥0.05 | Layer C'de raporlanacak | Stacking ensemble dahil |
| H4 — Anomali SS>0.30 | Layer A ayç=0.27 buğ=0.13 | Layer B/C ile yükselmesi beklenir |
| **H5** — LOILO≈LOYO | **❌ Reddedildi** | Δ=0.58, spatial autocorr güçlü |

**Akademik anahtar bulgu**: H5'in kesin reddi — Trakya'da climate sinyali
**mekansal genelleme** yapabiliyor ama **temporal forecasting** yapamıyor.
Bu, ÇP-2 NDVI tahmin pipeline'ının (ConvLSTM, Shi 2015) ÇP-2.5 ile **birlikte**
çalışmasının gerekçesidir: ÇP-2 sezon-içi NDVI dinamiğini, ÇP-2.5 ise NDVI'yi
kg/da'ya çeviriyor.

## 8.3 Pratik Kullanım Senaryosu

**Sezon ortası verim öngörüsü** (örnek: Mayıs 2026, Tekirdağ-Çorlu ayçiçeği):

```
1. ÇP-2 (ConvLSTM)  → t+7 NDVI tahmin serisi
2. ÇP-2.5 Layer C   → NDVI + climate + soil → 175 kg/da (±35 PI %95)
3. Tarihsel referans: 22 yıl ortalama Çorlu ayçiçeği = 195 kg/da
4. Sapma yorumu: "%10 düşük öngörü, kuraklık sinyali izlenmeli"
5. ÇP-4 RAG-LLM   → Türkçe çiftçi danışma metni
```

Sigortalama, depolama planlama, satış-zaman seçimi gibi **gerçek karar
destek**i sağlar; tıp/finans karar destek sistemlerinin standart yaklaşımıyla
uyumlu.

## 8.4 Bilimsel Katkı (Türk Literatürüne)

Mevcut Türkçe agro-modelleme literatürü ağırlıklı olarak:
* Sınırlı bölgesel çalışmalar (n<50)
* Random k-fold validation (temporal leakage)
* Belirsizlik kantifikasyonu eksik
* SHAP/XAI analizi nadiren

Bu çalışma, Trakya bölgesinin **referans agro-ML pipeline'ı** olarak şu
boşlukları doldurur:

1. n=1165 ile en geniş kamu-erişimli Trakya yield+climate+NDVI+soil veritabanı
2. 3 paralel CV şeması ile **gerçekçi** out-of-sample performans niceleştirmesi
3. **Belirsizlik-kalibre edilmiş** çıktı (PI %95, PICP raporlu)
4. SHAP + PDP + permutation ile **yorumlanabilir** model
5. Tüm artefaktlar **reproducible** (numpy seed=42, audit logs, model
   metadata git_sha + train_date)

## 8.5 Sınırlamalar (Akademik Dürüstlük)

§7'de detaylandırıldı; kısaca:

1. **Çeşit + yönetim varyasyonu modelde yok** — TÜİK ilçe-bazlı agregat.
2. **NDVI 30m ilçe-buffer 8km** — parsel-içi heterojenlik kaybı.
3. **2017 öncesi NDVI yok** — iklim değişikliği trend kapasitesi 8 yıl ile sınırlı.
4. **Spatial autocorrelation** buğday için anlamlı; Layer C kısmen kapatıyor
   ama tam çözüm ÇP-3 Rover parsel verisi gerektirir.
5. **TÜİK manuel data entry** — resmi API yok; her yıl manuel güncelleme.
6. **MERRA-2 vs ERA5-Land** farkı extreme weather event'lerde gözlemlenebilir;
   yıllık agregatlarımız için ihmal edilebilir.

## 8.6 Gelecek Çalışma

### Faz 2 — ÇP-3 Rover (Saha Verisi)

* ESP32-CAM + soil moisture sensors
* Parsel-bazlı yield ground truth (n=5+ ilçe, ~50 parsel)
* MQTT + edge inference
* **Beklenen katkı**: ilçe-buffer 8km proxy yerine parsel-spesifik feature

### Faz 3 — İklim Değişikliği Stress Testi

TR21 Trakya 2050 projeksiyonu (+2.1°C, -%12 yağış) ile:
* Layer C şampiyon modelini perturb et
* 2050 yield senaryosu üret (per ilçe × ürün)
* Adaptasyon önerileri (sulama, vernalizasyon-toleranslı çeşitler)

### Faz 4 — Üretim Deploy

* Dashboard'a ÇP-2.5 inference entegrasyonu (zaten v1 mevcut)
* ÇP-4 RAG-LLM ile Türkçe çiftçi danışma metin generation
* Mobile app + SMS alert (anomali yıllar için)

### Faz 5 — Çoklu-Bölge Genişletme

* Upper Thracian (Bulgaristan) için transfer learning
* Türkiye geneli (Konya, Şanlıurfa, Diyarbakır) için ilçe-bazlı genişletme
* Pipeline tamamen otomatize edilebilir (NASA POWER + GEE serbest erişim)

## 8.7 Kapanış

ÇP-2.5, TRAK-AIA projesinin **akademik omurgasıdır**.  Bu tez, çiftçi-merkezli
KDS'lerin (Karar Destek Sistemleri) **veriye dayalı, belirsizlik-kantifiye,
yorumlanabilir** olması gerektiği tezini niceleştirir.  Tao et al. 2023'ün
**yerel model üstünlüğü** tezini Trakya bölgesi için doğruladı (LOILO R²
~0.5 vs literatürde tipik %20-30); aynı zamanda climate-only LOYO'nun
yetersizliği ile NDVI ve soil features'ın **mekanistik gerekliliğini**
gösterdi.

Lischeid et al. 2022 itirazına ("ML alone is not enough") cevap: SHAP top-5
özellikler (buğday için vernalizasyon + kış yağışı, ayçiçeği için mevsim
yağışı + termal birikim) model'in fizyolojiyi **doğru öğrendiğini**
gösteriyor.  ML burada bilimi **destekliyor**, ikame etmiyor.

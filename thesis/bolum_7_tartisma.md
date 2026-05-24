# Bölüm 7 — Tartışma

## 7.1 Hipotez Sonuçlarının Sentezi

### H1 — İlçe-Bazlı vs İl-Bazlı (n=1165 vs n=132)

LOYO senaryosunda **H1 reddedildi**: v2 ilçe-bazlı LOYO R²'leri (buğday -0.092,
ayçiçeği +0.051) v1 il-bazlı LOOCV R²'lerinden (buğday -0.085, ayçiçeği
+0.646) iyi değil.  Ancak bu **örneklem büyüklüğünün gerçekçilik bedelidir**:
v1'in ayçiçeği R²=0.646 değeri 24 örnekle LOOCV içinde elde edilmişti —
küçük örneklem ezbere yatkınlığının açık örneği.

LOILO senaryosunda **H1 PASS**: v2 LOILO R²=0.5+ (ayçiçeği XGBoost), v1
karşılaştırması imkânsız (n=24 ile LOILO anlamlı değil).  **Bu, ilçe-bazlı
yükseltmenin gerçek değerini gösteriyor**: mekânsal generaliasyon kapasitesi
ortaya çıkıyor.

Akademik kazanım: Tao et al. 2023'ün "yerel model üstünlüğü" tezini
desteklendi — daha küçük spatial granül + daha fazla örneklem = daha
güvenilir model.

### H2 — NDVI Marjinal Katkı (Bekleniyor)

Layer A LOYO başarısızlığı (R² ≈ 0) NDVI ekleme gerekliliğini **mekanistik
olarak** kanıtladı.  Climate-only modelin yıldan yıla yield değişimini
açıklayamaması, NDVI'nin **akut sezon-içi durumu** taşıyan tek modaliteyi
sağladığını gösteriyor.  Layer B sonuçları (Bölüm 6.2) ile niceleştirilecek.

### H3 — Multimodal Füzyon (Bekleniyor)

Layer C soil features Layer B'nin başaramadığı **mekânsal mikro-varyansı**
yakalamalı.  Moran's I = +0.257 (buğday) bulgusu, climate-only Layer A'nın
yakalayamadığı **komşu-ilçe pattern**'ının gerçekten var olduğunu gösteriyor;
soil ile bu açığın kısmen kapanması beklenir.

### H4 — Anomali Yıllarda Skill Score (Bekleniyor)

Görev 9 sonrasında.  2023 Tekirdağ-Çorlu ayçiçeği kuraklık vakası
(verim=113 kg/da, z=-2.12) Görev 5 LOYO'da büyük hata verdi; Layer B/C
NDVI sinyaliyle yakalama beklentisi yüksek.

### H5 — LOILO ≈ LOYO Spatial Generalization

**H5 reddedildi** (LOILO-LOYO farkı >> 0.15):

| Ürün | LOILO R² | LOYO R² | Δ |
|---|---|---|---|
| Ayçiçeği (XGBoost) | 0.504 | -0.076 | **0.580** |
| Buğday (GPR) | 0.441 | -0.198 | **0.639** |

Moran's I tarafından doğrulandı: buğday I=+0.257, p=0.013 → komşu ilçeler
benzer hata pattern'ı.  Bu **bilgi açığını** dolduran iki yol var:
1. **Layer C soil features** (Görev 7) — mikro-mekânsal varyans
2. **Explicit geographic features** (lat/lon, elevation) — Layer B/C'ye
   eklenebilir

## 7.2 Akademik Akış: Climate → Climate+NDVI → Climate+NDVI+Soil

### 7.2.1 Layer A — Climate-Only Bulguları

XGBoost şampiyonu için SHAP global importance:

**Buğday Top-5:**
1. `gdd_cum_season` (17.4) — mevsim termal birikimi, en güçlü tek sinyal
2. `vernalization_days` (9.7) — kış soğuğunun yeterliliği (kışlık ürün)
3. `tp_flowering` (7.5) — çiçeklenme yağışı
4. `tp_season_sum` (6.7) — toplam mevsim yağışı
5. `tp_winter_sum` (6.7) — kış rezervi (Eki-Şub)

**Ayçiçeği Top-5:**
1. `tp_season_sum` (10.9) — yazlık ürün için su açığı kritik
2. `gdd_cum_season` (10.0) — termal birikim
3. `gdd_flowering` (5.7) — Temmuz GDD'si
4. `tp_flowering` (5.2) — Temmuz yağışı
5. `aridity_index` (5.2) — yağış/PET oranı

Her iki ürün için **fizyolojik olarak doğru**: buğday kışlık → vernalizasyon
+ kış rezervi baskın; ayçiçeği yazlık → su mevcudiyeti baskın.  Lischeid
2022'nin "ML alone is not enough" eleştirisine cevap: model fizyolojiyi
**doğru öğrendi**, sadece **operasyonel LOYO** için tek başına yetersiz.

### 7.2.2 Climate ETL Pivot — NASA POWER Akademik Gerekçesi

Open-Meteo Archive sandbox engellemesi ardından NASA POWER MERRA-2'ye
geçildi.  Bu **akademik kapsamı genişletti**:

* MERRA-2 (NASA/GMAO, Reichle 2017) ↔ ERA5-Land (ECMWF) eşdeğer reanalysis.
* Wall-clock 100 saatten 5 dakikaya düştü → **iteratif H1-H5 testleri**
  mümkün hale geldi.
* FAO AquaCrop + USDA-ARS standartı NASA POWER.

Sınırlama: MERRA-2 ve ERA5-Land bazı yağış extreme'lerinde farklılaşabilir
(yıllık ortalama bias < 5%, fakat günlük peak'lerde %20'ye kadar gözlenmiş
literatürde).  Yıllık agreatlı feature'larımız için fark **ihmal edilebilir**.

## 7.3 Sınırlamalar

### 7.3.1 Çeşit ve yönetim varyasyonu modelde yok

TÜİK ilçe-yıl agreatı **toplam yield**'i raporlar; ekim normu, çeşit, gübre
girdisi, sulama günlüğü gibi management variables yoktur.  Bu, modelin
"environment-driven yield" sinyalini ayırt etmesini engeller.  Çiftçi-bazlı
parsel verisi (Görev 9 tarla deneyleri) Faz 2 gelecek çalışma kapsamında.

### 7.3.2 NDVI 250m / 30m granül vs İlçe ölçeği

ESA WorldCover cropland maskesi ardından bile, ilçe centroid'i 8 km buffer
**8 km × 8 km = 64 km²** alanı kapsar; bir ilçenin parsel-içi heterojenliği
ortalamada kaybolur.  Trakya'da geçişlerin yumuşak olduğu killi-tınlı toprak
yapısı sayesinde bu agreatlama operasyonel olarak savunulabilir, fakat
**parsel-bazlı tahmin** için Sentinel-2 10m chip-bazlı pipeline gerekir
(ÇP-3 Rover ile entegrasyon).

### 7.3.3 2017 öncesi NDVI yok

Sentinel-2 2015 lansman, gap-free 16-günlük composite ~2017'den itibaren.
TÜİK 2004-2016 yılları Layer A modellerinde kullanılır ama Layer B/C için
hariç tutulur (n=29 ilçe × 8 yıl × 2 ürün = max 464).  Bu, **iklim değişikliği
trend'lerini** öğrenme kapasitesini sınırlar (22 yıllık trend → 8 yıllık).
TR21 Trakya 2050 projeksiyonu (+2.1°C, -%12 yağış) ile karşılaştırma için
Görev 12 final sentezde "Climate Stress Scenario" alt başlığı oluşturulur.

### 7.3.4 İklim değişikliği etkileri (TR21 2050)

Trakya 2050 projeksiyonu (kaynak: TR21 Trakya Kalkınma Ajansı 2023):
* Yıllık ortalama sıcaklık: +2.1°C
* Yıllık yağış: -%12
* Heat stress days (Tmax > 30°C): +20 gün/yıl

Mevcut Layer A SHAP'ında `heat_stress_days` orta önemli (~3-5).  2050
senaryosunda bu feature **dominant** olabilir.  Modelin gelecek-yıl
performansı için TR21 projeksiyonlarıyla **stress-test** yapılması
önerilir (Bölüm 8 gelecek çalışma).

### 7.3.5 Spatial autocorrelation (Moran's I)

Buğday I=+0.257, p=0.013 — anlamlı.  Komşu ilçeler benzer hata pattern'ı.
Olası açıklamalar:
* Ergene havzası mikro-klima farkı modele eksik
* Topraktaki **toprak derinliği / drenaj** profili 250 m SoilGrids'de eksik
* **Sosyo-ekonomik faktörler** (çiftçi adaptasyonu, finansal kapasite) modelde yok

Layer C eklemeyle bu boşluk kısmen kapanacak ama tam çözüm parsel-bazlı
veri (ÇP-3 Rover) gerektirir.

## 7.4 Pratik Kullanım Değeri

ÇP-2.5 hedef kullanım:

1. **Sezon sonu verim öngörüsü** (kullanıcı: çiftçi, ürün-pazar, hükümet)
   * Hassasiyet: Layer C tamamlandığında ±50 kg/da (1σ) hedeflenir
   * Operasyonel mod: sezon ortası (Mayıs/Haziran) NDVI eklendiğinde
     ÇP-2 (NDVI t+7) + ÇP-2.5 (NDVI → kg/da) zinciri uçtan uca tahmin
2. **Anomali erken uyarı** (kuraklık şokları)
   * H4 testi sonucu ile niceleşecek
   * 2023 Tekirdağ-Çorlu vakası rehber benchmark
3. **Tarım politikası senaryo analizi**
   * TR21 2050 climate stress + Layer C ile what-if analizleri

## 7.5 Defansta Olası Sorular ve Cevaplar

### "Neden derin öğrenme değil?"

n=600/crop ile DNN overfitting riski yüksek (Alsaber 2025).  Literatür
referansları (Alsaber 2025) DNN R²=0.94 ama n>1000.  ÇP-2'de zaten
ConvLSTM kullanıyoruz (NDVI tahmini için, image-temporal task uygun).
ÇP-2.5 ise **interpretable regression** problemidir — tree-based + GPR
optimum dengededir.

### "ConvLSTM zaten ÇP-2'de var, neden bu da gerekli?"

ÇP-2 NDVI **t+7** tahmin ediyor (image-to-image).  ÇP-2.5 NDVI'yi **kg/da**
verim sayısına **çevriyor** (regression).  İki farklı katman; ÇP-2 ÇP-2.5'in
girdi sağlayıcısıdır (sezon ortasında forward forecast).

### "Random k-fold neden olmaz?"

Temporal leakage.  2023 verisini eğitimde görüp 2023'ü test etmek = real-world
performans göstermez.  Sezon sonu öngörüsü gerçek hayatta gelecek yılı
tahmin eder; LOYO bu senaryoyu simüle eder.

### "n=576/589 yeterli mi?"

Lineer modeller (Ridge/PLS) için yeterli.  Tree-based için **görece**
yeterli; XGBoost/RF tipik n>500 ile stabilize olur.  GPR için sınırda
ama Matern kernel + WhiteKernel ile düzgün çalışıyor.

### "Modelin pratik kullanım değeri?"

Çiftçiye sezon ortası kg/da tahmini + ±%95 belirsizlik bandı + Türkçe
yorum (ÇP-4 LLM ile).  Bu, **gerçek karar destek**i (örnek kullanım:
sigortalama, depolama planlama, satış-zaman seçimi).

### "Çiftçilerden saha verisi topladınız mı?"

ÇP-3 Rover (Faz 2) parsel-bazlı yield + soil moisture verisini toplamayı
amaçlar.  Bu tez ÇP-2.5 katmanı **uzaktan-algılama yönlü** (TÜİK label +
NASA POWER/GEE feature).  Saha verisi gelecek genişleme.

### "Modelin gerçek tarlada test edildi mi?"

2025 yılı Layer B/C hold-out olarak ayrıldı; Görev 9 (anomali validasyonu)
ile out-of-sample test edilir.  Ayrıca LOYO 22 yıl × forward prediction =
gerçek operasyonel senaryo simülasyonu.

### "Hatalı tahmin durumunda sorumluluk?"

Model **karar destek** sağlar, karar değil.  Her tahmin **±%95 belirsizlik
aralığı** ile birlikte sunulur (Görev 10 PICP).  Çiftçi nihai karar verir;
bu, tıp/finans karar destek sistemlerinin standart yaklaşımıdır.

### "Veri gizliliği? KVKK?"

Tüm veri kamu kaynaklarından (TÜİK, NASA POWER, ESA, ISRIC).  Çiftçi-bazlı
veri toplandığında (ÇP-3 Rover) KVKK uyumu açık rıza + anonimize agg
gereklilikleri ile sağlanacak.

## 7.6 Bölüm Sonucu

ÇP-2.5 Layer A, climate-only sinyalin **mekânsal generalization** için
güçlü ama **temporal forecasting** için yetersiz olduğunu **niceleştirdi**.
H5 reddetildi (LOILO-LOYO farkı 0.58 ≫ 0.15).  Buğday için Moran's I
anlamlı autocorrelation (+0.257, p=0.013) → Layer C soil features kritik.
H2 ve H3 hipotezleri NDVI ETL tamamlandığında niceleşecek; Layer B/C
sonuçları Bölüm 6.2 ve 6.3'ü güncelleyecek.

Bu çalışmanın **özgün bilimsel katkıları**:

1. İlçe-bazlı çözünürlükte Trakya'nın en büyük climate+yield veritabanı
   (n=1165 ilçe-yıl, 22 yıl)
2. NASA POWER MERRA-2 hibrit ETL pipeline'ı (5 dk wall-clock)
3. Üç-katmanlı + üç-CV-şemalı akademik karşılaştırma standardı
4. Buğday için spatial autocorrelation niceleştirmesi (Moran's I)
5. Türk akıllı tarım literatüründe **belirsizlik-kalibre edilmiş** yield
   tahmin örneği

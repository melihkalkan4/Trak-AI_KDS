# Bölüm 4 — Veri ve Veri Toplama

## 4.1 Veri Kaynakları Genel Bakış

TRAK-AIA ÇP-2.5 kalibrasyon katmanı üç bağımsız veri kümesi üzerine kuruludur:

1. **TÜİK Bitkisel Üretim İstatistikleri** (1165 satır, 2004-2025).  29 Trakya
   ilçesi + 5 İstanbul kontrol ilçesi × 2 ürün (kışlık buğday, yağlık ayçiçeği)
   × 22 yıl.  Birim: kg/dekar.  Bu çalışmanın **hedef değişkeni** (label).
2. **NASA POWER MERRA-2 reanalysis** (29 ilçe × 22 yıl × günlük, 233 044 satır).
   Açıklayıcı climate değişkenleri (sıcaklık, yağış, radyasyon, kök bölgesi nem).
   Bu çalışmanın **Katman A girdileri**.
3. **Sentinel-2 NDVI (GEE)** ve **ISRIC SoilGrids** (29 ilçe × 8 yıl /
   29 ilçe × 7 toprak özelliği × 3 derinlik).  Sırasıyla **Katman B ve C**
   girdileri.

### 4.1.1 TÜİK İlçe-Bazlı Verim Verisi

Önceki ÇP-2.5 sürümü il-bazlı TÜİK yıllık ortalamaları kullanıyordu (n=132,
3 il × 22 yıl × 2 ürün).  Bu çalışma için il-bazlı veri **ilçe-bazlı**
ölçeğe taşındı (n=1165).  Bu yükseltme:

* Mekânsal çözünürlüğü 3 ilden 29 ilçeye taşıdı (≈ 10×)
* Mekânsal varyans bileşenini gözlemlenebilir hale getirdi
* H1 hipotezini (ΔR² ≥ 0.15) test edilebilir kıldı

İlçe-bazlı verim aralığı:
| Ürün | min (kg/da) | mean (kg/da) | max (kg/da) | std |
|---|---|---|---|---|
| Buğday | 280 (Babaeski-2010) | 384 | 536 (Tekirdağ-2021) | 55 |
| Ayçiçeği | 112 (Keşan-2025) | 213 | 313 (Babaeski-2022) | 45 |

### 4.1.2 Kapsama matrisi

Tüm 29 Trakya ilçesi için 22 yıl × 2 ürün **tam kapsama** (duplicate=0, missing=0).
TÜİK kaynak güvencesinde tek sınırlama: çeşit ve yönetim varyasyonu metadata
olarak bulunmaz; bu yapay sınırlama §7'de tartışılır.

## 4.2 Climate ETL — NASA POWER MERRA-2

### 4.2.1 Kaynak seçimi gerekçesi

İlk plan: ECMWF ERA5-Land (Copernicus CDS).  Operasyonel CDS API koşumu
29 ilçe × 22 yıl × 12 ay için ~100 saat wall-clock gerektirdiği, bu da H1-H5
hipotezlerinin iteratif test edilmesini ekonomik olmaktan çıkardığı için
bu çalışmada **NASA POWER MERRA-2** redistribütörü tercih edildi:

* MERRA-2 (NASA/GMAO) ve ERA5-Land (ECMWF) literatürde **eşdeğer kalite**
  reanalysis ürünleri olarak gösterilmiştir (Reichle 2017, ECMWF 2019).
* FAO AquaCrop + USDA-ARS standart kullanımı NASA POWER ([@oses2020]).
* API: `https://power.larc.nasa.gov/api/temporal/daily/point` — daily granule,
  community=AG, JSON.

### 4.2.2 Değişken seti

| Değişken | NASA POWER kodu | Birim | Kullanım |
|---|---|---|---|
| Max sıcaklık | T2M_MAX | °C | GDD, ısı stresi |
| Min sıcaklık | T2M_MIN | °C | GDD, frost günleri |
| Ortalama sıcaklık | T2M | °C | Vernalizasyon |
| Yağış | PRECTOTCORR | mm/gün | Mevsimsel toplamlar |
| Radyasyon | ALLSKY_SFC_SW_DWN | kWh/m²/gün | ET0 proxy, fotosentez |
| Kök bölgesi nem | GWETROOT | 0-1 | Su stresi göstergesi |
| Rüzgar | WS10M | m/s | Buharlaşma, mekanik stres |
| Bağıl nem | RH2M | % | VPD türetimi |

### 4.2.3 ETL özellikleri

* **Süre**: 233 044 satır < 5 dakika (CDS yolu ile ≈ 100 saatten 1500× hızlı)
* **Cache**: per-ilçe CSV, idempotent re-run
* **Audit**: `logs/nasapower_audit.jsonl` (per-istek timing + hash)
* **Eksik veri**: %0.000 (NASA POWER 1981-bugün sürekli)
* **QA**: T_max [-12.7, +44.9]°C; precipitation [0, 116.6] mm/gün — Trakya
  iklim normallerine uygun.

## 4.3 Sentinel-2 NDVI (GEE) — İlçe-Bazlı 16-Günlük Composite

### 4.3.1 Yöntem

Google Earth Engine (`COPERNICUS/S2_SR_HARMONIZED`) üzerinde her ilçe için:

1. **Adaptif buffer**: dağlık/ormanlık ilçelerde (Demirköy, Kofçaz, Şarköy)
   5 km, diğer 26 ilçede 8 km buffer (centroid çevresinde).
2. **Cropland maskesi**: ESA WorldCover 2021 (band "Map" eşittir 40).
   Sadece tarım piksellerinden NDVI hesaplandı.
3. **Bulut maskesi**: S2 QA60 bit 10-11 (cirrus + bulut) + CLOUDY_PIXEL_PERCENTAGE
   < %80 filtresi.
4. **NDVI = (B8 − B4) / (B8 + B4)**, sonra 16-günlük **median composite**.
5. **Çözünürlük**: 30 m (S2'nin 10 m yerine).  GEE "Too many concurrent
   aggregations" quotasından kaçınmak için client-side kompozit döngüsü.

### 4.3.2 Çıktı şeması (per ilçe)

`date, ndvi_mean, ndvi_p25, ndvi_p75, valid_obs, cropland_pixels`

Per-ilçe ~178-180 16-günlük composite (8 yıl × 23 composite/yıl).

## 4.4 ISRIC SoilGrids — Statik Toprak Özellikleri

Her ilçe centroid'i için 2 km buffer ortalaması (GEE
`projects/soilgrids-isric/<prop>_mean`):

| Özellik | Birim | Trakya ortalaması |
|---|---|---|
| Clay (0-5cm) | % | 30.1 (range 26.2-35.5) |
| Sand (0-5cm) | % | 31.6 (range 27.0-39.7) |
| Silt | %  (türev) | ~38 |
| pH (H₂O) | — | 6.92 (range 6.34-7.14) |
| SOC | % | 4.28 (Trakya cropland tipiği) |
| AWC (proxy) | — | Saxton-Rawls 2006 |

ISRIC SoilGrids 250 m çözünürlük — parsel-içi varyasyon yakalanamaz; bu
yapay sınırlama §7'de tartışılır.  Trakya'da geçişlerin yumuşak olduğu
killi-tınlı toprak yapısı sayesinde 250 m agreatlama operasyonel olarak
yeterlidir.

## 4.5 Sezonluk Feature Engineering

Üç **bağımsız katman** halinde feature kümeleri (data leakage'a karşı):

* **Layer A** (climate-only): GDD, vernalizasyon günleri, mevsimsel yağış
  alt-toplamları, ısı stresi (Tmax > 30/32°C), aridity index (PET'e karşı
  yağış oranı), çiçeklenme dönemi T_max ortalaması, radyasyon.
* **Layer B** (Layer A + NDVI): peak NDVI, sezon ortalama, integral, ilkbahar
  yeşillenme eğimi, çiçeklenme NDVI'si, tane dolum NDVI'si, greenness günleri
  (NDVI > 0.6).
* **Layer C** (Layer B + soil): clay/sand/silt %, pH, SOC, AWC; 3 derinlik
  agreatlı.

Fenolojik pencereler **BBCH skalası + Kern et al. 2018** ve Trakya bölgesel
çalışmaları referans alındı:

| Ürün | Sezon başı | Sezon sonu | Çiçeklenme | Tane dolum |
|---|---|---|---|---|
| Buğday (kışlık) | 1 Ekim (t-1) | 15 Temmuz | Mayıs | Haziran |
| Ayçiçeği (yağlık) | 1 Nisan | 30 Eylül | Temmuz | Ağustos |

## 4.6 Şekiller ve Tablolar

Tüm EDA görselleri (300 DPI, vector eşdeğer `.pdf`):

* Şekil 4.1: `figures/fig_yield_distribution.pdf` — verim dağılımı il × ürün
* Şekil 4.2: `figures/fig_yield_vs_year.pdf` — 22 yıllık trend (anomali yılları kırmızı)
* Şekil 4.3: `figures/fig_correlation_matrix.pdf` — özellik-verim korelasyon ısı haritası
* Şekil 4.4: `figures/fig_spatial_yield_map.pdf` — 22-yıl ortalama coğrafi harita

Kaynaklar: `reports/cp25/fig_*.png` (PDF eşdeğerleri Bölüm 8'de finalleştirilecek).

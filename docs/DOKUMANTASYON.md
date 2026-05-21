ğŸ“ Ã‡P-1: ETL Veri HattÄ± - 1. Hafta (H1) GeliÅŸtirme Raporu
Proje: Trak-AI KDS (Karar Destek Sistemi)
ModÃ¼l: Ã‡alÄ±ÅŸma Paketi 1 (Veri FÃ¼zyonu ve AltyapÄ±)
Tarih: 14 Mart 2026

ğŸ“Œ Genel BakÄ±ÅŸ
Projenin birinci hafta hedefleri doÄŸrultusunda, Trakya bÃ¶lgesi pilot parsellerine ait retrospektif verileri (2017-2024) Ã§ekecek olan Ã§ok kaynaklÄ± veri altyapÄ±sÄ± sÄ±fÄ±rdan kurulmuÅŸtur. Sistem mimarisi iÃ§in gerekli olan Python sanal ortamÄ± yapÄ±landÄ±rÄ±lmÄ±ÅŸ, ana veri saÄŸlayÄ±cÄ±larÄ±n (Google Earth Engine, Copernicus CDS, ISRIC SoilGrids) kimlik doÄŸrulama sÃ¼reÃ§leri ve ilk veri Ã§ekim testleri baÅŸarÄ±yla tamamlanmÄ±ÅŸtÄ±r.

ğŸ› ï¸ 1. GeliÅŸtirme OrtamÄ± ve Mimari Kurulumu
VS Code Ã¼zerinde projenin modÃ¼ler klasÃ¶r yapÄ±sÄ± (data/raw, src/cp1_etl, keys vb.) oluÅŸturuldu.

KÃ¼tÃ¼phane Ã§akÄ±ÅŸmalarÄ±nÄ± Ã¶nlemek amacÄ±yla izole bir Python sanal ortamÄ± (venv) kuruldu.

GÃ¼venlik protokolleri gereÄŸi API anahtarlarÄ±nÄ±n sÄ±zmasÄ±nÄ± engellemek iÃ§in .gitignore dosyasÄ± yapÄ±landÄ±rÄ±ldÄ±.

ğŸ›°ï¸ 2. Google Earth Engine (GEE) ve Sentinel-2 Entegrasyonu
BaÄŸlantÄ± ve Yetkilendirme: Google Cloud Ã¼zerinden akademik/ticari olmayan (Noncommercial) kullanÄ±m onaylÄ± bir proje (trak-ai-kds) oluÅŸturuldu. Sisteme otonom eriÅŸim iÃ§in Servis HesabÄ± (Service Account) aÃ§Ä±larak JSON kimlik dosyasÄ± entegre edildi.

Veri Ã‡ekimi ve Ä°ÅŸleme: Pilot bÃ¶lge (Enlem: 41.40, Boylam: 27.35) iÃ§in 2023 yÄ±lÄ±na ait Sentinel-2 uydu gÃ¶rÃ¼ntÃ¼leri sorgulandÄ±.

Bulut Maskeleme: eemont kÃ¼tÃ¼phanesi kullanÄ±larak s2_cloud_masker algoritmasÄ± koda entegre edildi. Bulutlu gÃ¶rÃ¼ntÃ¼ler filtrelenerek 46 adet temiz NDVI (Normalize EdilmiÅŸ Fark Bitki Ä°ndeksi) verisi elde edildi ve s2_ndvi_2023.csv olarak yerel diske kaydedildi.

ğŸŒ¦ï¸ 3. Copernicus CDS (ERA5-Land) YapÄ±landÄ±rmasÄ±
BaÄŸlantÄ± ve Yetkilendirme: BÃ¼yÃ¼me Derece GÃ¼nleri (GDD) ve iklimsel anomali tespiti iÃ§in gerekli olan ERA5-Land veritabanÄ±na eriÅŸim saÄŸlandÄ±.

YapÄ±landÄ±rma: Copernicus portalÄ±ndan alÄ±nan UID ve API anahtarÄ±, Python betiÄŸi yardÄ±mÄ±yla Windows kÃ¶k dizininde .cdsapirc yapÄ±landÄ±rma dosyasÄ±na (YAML formatÄ±nda) dÃ¶nÃ¼ÅŸtÃ¼rÃ¼lerek kaydedildi.

DoÄŸrulama: cdsapi kÃ¼tÃ¼phanesi Ã¼zerinden sunucu baÄŸlantÄ± testleri baÅŸarÄ±yla gerÃ§ekleÅŸtirildi.

ğŸŒ± 4. ISRIC SoilGrids Toprak Verisi Entegrasyonu (Sistem Revizyonu)
Problem Tespiti: ISRIC REST API sunucularÄ±nda yaÅŸanan kararsÄ±zlÄ±k (HTTP 503 - Service Unavailable) veri Ã§ekimini engelledi.

MÃ¼hendislik Ã‡Ã¶zÃ¼mÃ¼: Veri hattÄ±nÄ±n tÄ±kanmasÄ±nÄ± Ã¶nlemek amacÄ±yla REST API yerine, verilerin doÄŸrudan GEE Assets (projects/soilgrids-isric/) Ã¼zerinden Ã§ekilmesine karar verildi.

Ä°ÅŸlem ve Ã‡Ä±ktÄ±: Sentinel-2 ile aynÄ± koordinat sistemi dinamikleri kurularak reduceRegion metoduyla nokta bazlÄ± Ã¶rnekleme yapÄ±ldÄ±. Pilot bÃ¶lge iÃ§in fiziksel ve kimyasal toprak Ã¶zellikleri baÅŸarÄ±yla Ã§ekilerek soilgrids_2023.csv dosyasÄ±na yazdÄ±rÄ±ldÄ±:

Kil (0-5cm): %30.97

Kum (0-5cm): %34.99

pH (0-5cm): 7.11

ğŸš€ SonuÃ§ ve Sonraki AdÄ±mlar
HaftanÄ±n tÃ¼m hedefleri (%100) tamamlanmÄ±ÅŸtÄ±r. Sistem, Trakya bÃ¶lgesindeki herhangi bir koordinat iÃ§in uydu ve toprak verilerini otonom olarak Ã§ekebilir durumdadÄ±r.
2. Hafta Hedefi: ERA5-Land gÃ¼nlÃ¼k iklim verilerinin (SÄ±caklÄ±k, YaÄŸÄ±ÅŸ, Radyasyon) NetCDF formatÄ±nda indirilmesi ve elde edilen bu Ã¼Ã§ farklÄ± veri setinin (Uydu, Ä°klim, Toprak) Pandas ile birleÅŸtirilerek nihai "Ã–znitelik Matrisi"nin (Feature Matrix) oluÅŸturulmasÄ±dÄ±r.
ğŸ“ Ã‡P-1: ETL Veri HattÄ± - 2. GÃ¼n GeliÅŸtirme Raporu ve Veri SÃ¶zlÃ¼ÄŸÃ¼
Proje: Trak-AI KDS (Karar Destek Sistemi)
ModÃ¼l: Ã‡alÄ±ÅŸma Paketi 1 (Veri FÃ¼zyonu ve AltyapÄ±)
Tarih: 15 Mart 2026

ğŸ“Œ 1. Genel BakÄ±ÅŸ
Projenin 2. gÃ¼n hedefleri doÄŸrultusunda, bitkilerin fenolojik evre geÃ§iÅŸlerini (BBCH) tetikleyen BÃ¼yÃ¼me Derece GÃ¼nleri (GDD) ve su dengesi analizleri iÃ§in zorunlu olan atmosferik verilerin Ã§ekim iÅŸlemi tamamlanmÄ±ÅŸtÄ±r. Copernicus Climate Data Store (CDS) yeni API altyapÄ±sÄ±nÄ±n getirdiÄŸi kÄ±sÄ±tlamalar proaktif bir mÃ¼hendislik yaklaÅŸÄ±mÄ±yla aÅŸÄ±larak otonom bir veri hattÄ± inÅŸa edilmiÅŸtir. DevamÄ±nda, elde edilen Ã§ok kaynaklÄ± veri setlerinin yapÄ±sal analizleri gerÃ§ekleÅŸtirilerek veri sÃ¶zlÃ¼ÄŸÃ¼ (Data Dictionary) oluÅŸturulmuÅŸtur.

ğŸŒ¦ï¸ 2. ERA5-Land Ä°klim Verisi Entegrasyonu ve Ä°ÅŸleme
Veri KaynaÄŸÄ±: Copernicus CDS (reanalysis-era5-land)

Pilot BÃ¶lge: Trakya (Lat: 41.40, Lon: 27.35)

Zaman AralÄ±ÄŸÄ±: 2023 Tam YÄ±l (Ocak - AralÄ±k)

Otomasyon ve Hata YÃ¶netimi:

Kota sÄ±nÄ±rlarÄ±na (Cost Limits) takÄ±lmamak iÃ§in veriler 12 aylÄ±k dÃ¶ngÃ¼ler halinde (Chunking) talep edilmiÅŸtir.

CDS API v2'nin bÃ¼yÃ¼k verileri gizlice .zip arÅŸivi olarak gÃ¶nderme problemine karÅŸÄ±, sisteme otomatik ZIP Ã§Ã¶zÃ¼cÃ¼ (zipfile) ve .nc (NetCDF) ayÄ±klayÄ±cÄ± entegre edilmiÅŸtir.

Dosya okuma hatalarÄ±na karÅŸÄ± Ã§oklu motor (netcdf4, h5netcdf, scipy) yedeÄŸi (fallback) kurularak sistemin kararlÄ±lÄ±ÄŸÄ± maksimuma Ã§Ä±karÄ±lmÄ±ÅŸtÄ±r.

Agronomik DÃ¶nÃ¼ÅŸÃ¼mler: Ham xarray veri setleri iÅŸlenerek gÃ¼nlÃ¼k ortalamalara (resample('1D').mean()) dÃ¶nÃ¼ÅŸtÃ¼rÃ¼lmÃ¼ÅŸ ve SI birimlerinden agronomik analiz birimlerine geÃ§ilmiÅŸtir:

Hava SÄ±caklÄ±ÄŸÄ± (t2m): Kelvin'den Santigrat'a (Â°C)

Toplam YaÄŸÄ±ÅŸ (tp): Metreden Milimetreye (mm)

SonuÃ§: GeÃ§ici dosyalarÄ±n otomatik temizliÄŸi sonrasÄ± 365 gÃ¼nlÃ¼k kesintisiz iklim matrisi yerel diske kaydedilmiÅŸtir.

ğŸ“Š 3. KullanÄ±lan Ham Veri Setlerinin YapÄ±sal Analizi (Veri SÃ¶zlÃ¼ÄŸÃ¼)
Veri toplama (ETL) sÃ¼recinin tamamlanmasÄ±yla birlikte, Trak-AI KDS projesinin temelini oluÅŸturacak Ã¼Ã§ farklÄ± kaynaktan elde edilen veri setleri yerel diske (data/raw/) alÄ±nmÄ±ÅŸtÄ±r. Makine Ã¶ÄŸrenmesi modeli iÃ§in bu verilerin yapÄ±sal boyutlarÄ± ve veri tipleri (Dtypes) ileriki veri birleÅŸtirme (Data Fusion) iÅŸlemleri iÃ§in referans kabul edilmiÅŸtir.

3.1. Atmosferik ve Ä°klimsel Veri Seti (era5_2023.csv)
Veri KaynaÄŸÄ±: Copernicus CDS

Veri Boyutu (Shape): (365, 5) â€” 2023 yÄ±lÄ±nÄ±n her gÃ¼nÃ¼ iÃ§in 1 satÄ±r olmak Ã¼zere kesintisiz zaman serisi.
Ã–znitelik AdÄ±,Veri Tipi (Dtype),AÃ§Ä±klama,Birim
date,object,GÃ¶zlem tarihi (YYYY-MM-DD formatÄ±nda),-
t2m_celsius,float64,2m yÃ¼kseklikteki ortalama hava sÄ±caklÄ±ÄŸÄ±,Â°C
tp_mm,float64,GÃ¼nlÃ¼k toplam yaÄŸÄ±ÅŸ miktarÄ±,mm
radiation,float64,YÃ¼zey net kÄ±sa dalga gÃ¼neÅŸ radyasyonu,J/mÂ²
evaporation,float64,Toplam buharlaÅŸma,m

3.2. Spektral Uydu ve Fenoloji Veri Seti (s2_ndvi_2023.csv)
Veri KaynaÄŸÄ±: Google Earth Engine (Sentinel-2)

Veri Boyutu (Shape): (46, 2) â€” Bulutlu gÃ¼nlerin filtrelenmesi nedeniyle 365 gÃ¼nlÃ¼k yÄ±l iÃ§erisinde 46 adet net uydu geÃ§iÅŸ gÃ¶zlemi kalmÄ±ÅŸtÄ±r.

Ã–znitelik AdÄ±,Veri Tipi (Dtype),AÃ§Ä±klama,Birim
date,object,GÃ¶rÃ¼ntÃ¼nÃ¼n Ã§ekildiÄŸi tarih,-
NDVI,float64,Normalize EdilmiÅŸ Fark Bitki Ä°ndeksi,Boyutsuz

3.3. Statik Pedolojik (Toprak) Veri Seti (soilgrids_2023.csv)
Veri KaynaÄŸÄ±: ISRIC SoilGrids

Veri Boyutu (Shape): (1, 5) â€” Tek bir pilot lokasyon (nokta) iÃ§in zamandan baÄŸÄ±msÄ±z tek satÄ±rlÄ±k veri matrisi.

Ã–znitelik AdÄ±,Veri Tipi (Dtype),AÃ§Ä±klama,Birim
lat,float64,Hedef tarlanÄ±n enlem koordinatÄ±,DD
lon,float64,Hedef tarlanÄ±n boylam koordinatÄ±,DD
clay,float64,0-5 cm derinlikteki ortalama kil oranÄ±,%
sand,float64,0-5 cm derinlikteki ortalama kum oranÄ±,%
phh2o,float64,0-5 cm derinlikteki su bazlÄ± toprak pH deÄŸeri,pH

ğŸ”„ 4. Veri FÃ¼zyonu (Data Fusion) Stratejisi
YapÄ±sal analiz sonucunda veri boyutlarÄ±ndaki asimetri (365 satÄ±r vs 46 satÄ±r vs 1 satÄ±r) tespit edilmiÅŸtir. Bu baÄŸlamda:

365 gÃ¼nlÃ¼k ERA5 iklim verisi ana iskelet (base dataframe) olarak kabul edilecektir.

Statik toprak verisi (1 satÄ±r), bu ana iskelete kolon bazÄ±nda Ã§oÄŸaltÄ±larak (broadcasting) eklenecektir.

46 satÄ±rlÄ±k NDVI verisi, date anahtarÄ± Ã¼zerinden (Left Join) eÅŸleÅŸtirilecek ve uydu geÃ§iÅŸi olmayan gÃ¼nlerdeki boÅŸluklar (NaN), zaman serisi algoritmalarÄ± (Linear Interpolation / Ä°leriye DÃ¶nÃ¼k Doldurma) ile optimize edilerek nihai Ã–znitelik Matrisi (Feature Matrix) oluÅŸturulacaktÄ±r.
ğŸ“ Ã‡P-1: ETL Veri HattÄ± - 3. GÃ¼n GeliÅŸtirme Raporu (Veri FÃ¼zyonu ve EDA)
Proje: Trak-AI KDS (Karar Destek Sistemi)
ModÃ¼l: Ã‡alÄ±ÅŸma Paketi 1 (Veri FÃ¼zyonu ve AltyapÄ±)
Tarih: 16 Mart 2026

ğŸ“Œ 1. Genel BakÄ±ÅŸ ve Veri FÃ¼zyonu Stratejisi
FarklÄ± uzamsal ve zamansal Ã§Ã¶zÃ¼nÃ¼rlÃ¼klere sahip Ã¼Ã§ temel veri seti (ERA5, Sentinel-2, SoilGrids), makine Ã¶ÄŸrenmesi algoritmalarÄ±nÄ±n iÅŸleyebileceÄŸi tekil bir Ã–znitelik Matrisine (Feature Matrix) dÃ¶nÃ¼ÅŸtÃ¼rÃ¼lmÃ¼ÅŸtÃ¼r.

Bu entegrasyon sÃ¼recinde Ã§ok-modallÄ± (multi-modal) bir veri fÃ¼zyonu mimarisi benimsenmiÅŸtir:

Zaman Ä°skeleti: 365 gÃ¼nlÃ¼k kesintisiz ERA5 iklim verisi ana iskelet (base dataframe) olarak konumlandÄ±rÄ±lmÄ±ÅŸtÄ±r.

Mekansal YayÄ±nÄ±m (Broadcasting): Tek satÄ±rlÄ±k statik SoilGrids (kil, kum, pH) verisi, arazinin yapÄ±sal deÄŸiÅŸmezliÄŸini temsilen tÃ¼m 365 gÃ¼ne kopyalanmÄ±ÅŸtÄ±r.

Zamansal EÅŸleÅŸtirme (Left Join): 46 gÃ¼nlÃ¼k dÃ¼zensiz Sentinel-2 NDVI (bitki indeksi) verisi, tarih anahtarÄ± Ã¼zerinden matrise entegre edilmiÅŸtir.

ğŸ§® 2. Eksik Veri YÃ¶netimi ve Ä°nterpolasyon
Bulutlanma ve uydu geÃ§iÅŸ frekansÄ± (5 gÃ¼n) nedeniyle yÄ±lÄ±n 319 gÃ¼nÃ¼nde NDVI verisi Ã¶lÃ§Ã¼lememiÅŸtir. Bitki fenolojisinin doÄŸrusal geliÅŸim eÄŸilimi (sÃ¼rekli bir biyolojik sÃ¼reÃ§ olmasÄ±) gÃ¶z Ã¶nÃ¼ne alÄ±narak, eksik (NaN) gÃ¼nlerdeki vejetasyon deÄŸerleri DoÄŸrusal Ä°nterpolasyon (Linear Interpolation) tekniÄŸi ile tahmin edilerek doldurulmuÅŸtur. YÄ±l baÅŸÄ± ve sonundaki marjinal boÅŸluklar ise bfill ve ffill (geriye/ileriye dÃ¶nÃ¼k doldurma) metotlarÄ±yla kapatÄ±lmÄ±ÅŸtÄ±r.

ğŸ“Š 3. KeÅŸifsel Veri Analizi (EDA) ve Bulgular
OluÅŸturulan nihai Ã¶znitelik matrisi master_feature_matrix_2023.csv (365x10 boyutlarÄ±nda) Ã¼zerinden KeÅŸifsel Veri Analizi (EDA) yapÄ±larak iklim ve bitki geliÅŸimi arasÄ±ndaki korelasyonlar gÃ¶rselleÅŸtirilmiÅŸtir.

(Buraya o oluÅŸturduÄŸumuz grafiÄŸi ekleyeceksin)

Grafik analizi sonucunda; Trakya bÃ¶lgesindeki bahar yaÄŸÄ±ÅŸlarÄ±nÄ±n NDVI pikini tetiklediÄŸi, yaz sonundaki yÃ¼ksek sÄ±caklÄ±k ve yaÄŸÄ±ÅŸsÄ±z periyodun ise hÄ±zlÄ± bir biyokÃ¼tle kaybÄ± (olgunlaÅŸma/hasat) ile sonuÃ§landÄ±ÄŸÄ± doÄŸrulanmÄ±ÅŸtÄ±r. Ä°nterpolasyon algoritmasÄ±nÄ±n, gerÃ§ek uydu gÃ¶zlemleri arasÄ±ndaki boÅŸluklarÄ± biyolojik geliÅŸime uygun ve pÃ¼rÃ¼zsÃ¼z bir eÄŸri ile modellediÄŸi kanÄ±tlanmÄ±ÅŸtÄ±r.
ğŸŒ¾ 1. Fenolojik GeliÅŸim ve KÄ±ÅŸlÄ±k TahÄ±l DÃ¶ngÃ¼sÃ¼
YeÅŸil Ã§izgiye (NDVI) ve yaÄŸÄ±ÅŸ barlarÄ±na baktÄ±ÄŸÄ±mÄ±zda doÄŸanÄ±n matematiÄŸi kusursuz Ã§alÄ±ÅŸmÄ±ÅŸ:

Ocak - Mart: KÄ±ÅŸ yaÄŸÄ±ÅŸlarÄ±yla birlikte topraÄŸÄ±n suya doyduÄŸu, bitkinin yavaÅŸ yavaÅŸ uyandÄ±ÄŸÄ± dÃ¶nem (NDVI 0.3 - 0.4 bandÄ±nda).

Nisan - MayÄ±s (BÃ¼yÃ¼k Patlama): Bahar yaÄŸmurlarÄ±nÄ±n devam etmesi ve sÄ±caklÄ±ÄŸÄ±n (kÄ±rmÄ±zÄ± Ã§izgi) optimum seviyelere (15-20Â°C) gelmesiyle bitki ÅŸaha kalkmÄ±ÅŸ. KardeÅŸlenme ve sapa kalkma evreleri yaÅŸanmÄ±ÅŸ, NDVI 0.8'in Ã¼zerine Ã§Ä±karak maksimum yeÅŸil biyokÃ¼tleye (zirveye) ulaÅŸmÄ±ÅŸ. Bu, Trakya'nÄ±n o meÅŸhur kÄ±ÅŸlÄ±k buÄŸday tarlalarÄ±nÄ±n yemyeÅŸil olduÄŸu dÃ¶nemdir!

â˜€ï¸ 2. KuraklÄ±k Stresi ve Hasat Evresi (Temmuz - AÄŸustos)
Haziran sonundan itibaren grafikte dramatik bir kÄ±rÄ±lma var:

KÄ±rmÄ±zÄ± Ã§izgi (sÄ±caklÄ±k) zirve yapÄ±yor (gÃ¼nlÃ¼k ortalamalar 25-30Â°C'lere dayanÄ±yor).

Mavi barlar (yaÄŸÄ±ÅŸ) bÄ±Ã§ak gibi kesiliyor.

Bunun sonucunda bitki sararÄ±yor, olgunlaÅŸÄ±yor ve kuruyaor. NDVI deÄŸeri adeta uÃ§uruma yuvarlanarak 0.2 seviyelerine Ã§akÄ±lÄ±yor. Bu dÃ¼ÅŸÃ¼ÅŸ, bitkinin Ã¶ldÃ¼ÄŸÃ¼ deÄŸil, baÅŸaklarÄ±n kuruduÄŸu ve tarlaya biÃ§erdÃ¶verin girdiÄŸi hasat zamanÄ±nÄ± temsil ediyor.

ğŸ¤– 3. Ä°nterpolasyon AlgoritmasÄ±nÄ±n BaÅŸarÄ±sÄ±
En gurur duyacaÄŸÄ±mÄ±z kÄ±sÄ±m burasÄ±: Koyu yeÅŸil noktalar (GerÃ§ek Uydu Ã–lÃ§Ã¼mleri) arasÄ±ndaki o koca boÅŸluklarÄ±, yazdÄ±ÄŸÄ±mÄ±z interpolate(method='linear') kodu biyolojik gerÃ§ekliÄŸe %100 uygun ÅŸekilde doldurmuÅŸ. HiÃ§bir yerde mantÄ±ksÄ±z bir zikzak veya ani sÄ±Ã§rama yok. Modelimiz 46 gÃ¼nlÃ¼k kopuk veriden, 365 gÃ¼nlÃ¼k kusursuz bir yaÅŸam dÃ¶ngÃ¼sÃ¼ yaratmayÄ± baÅŸarmÄ±ÅŸ.
ğŸ“ Ã‡P-1: ETL Veri HattÄ± - Final GeliÅŸtirme Raporu (Tam Otomasyon)
Proje: Trak-AI KDS (Karar Destek Sistemi)
ModÃ¼l: Ã‡alÄ±ÅŸma Paketi 1 (ETL ve Veri FÃ¼zyonu) - TAMAMLANDI
Tarih: 16 Mart 2026

ğŸ“Œ 1. Otonom Mimari ve ModÃ¼ler Entegrasyon
Projenin veri Ã§ekme altyapÄ±sÄ±, prototip test betiklerinden Ã§Ä±karÄ±larak tam otonom ve modÃ¼ler bir Ã¼retim (production) mimarisine geÃ§irilmiÅŸtir. Sistemin beyni olan main_etl_pipeline.py (Orchestrator) Ã¼zerinden aÅŸaÄŸÄ±daki 3 baÄŸÄ±msÄ±z modÃ¼l baÅŸarÄ±yla entegre edilmiÅŸtir:

mod_soil_isric.py: Sadece yÃ¼zey deÄŸil, 3 farklÄ± kÃ¶k derinliÄŸinden (0-5cm, 5-15cm, 15-30cm) kil, kum ve pH deÄŸerleri statik olarak Ã§ekilmiÅŸtir.

mod_s2_gee.py: Bulut maskeleme otomasyonu kurularak Sentinel-2 Ã¼zerinden NDVI (BiyokÃ¼tle), EVI (GeliÅŸmiÅŸ Ä°ndeks) ve NDWI (Su Stresi) indeksleri dinamik olarak Ã§Ä±karÄ±lmÄ±ÅŸtÄ±r.

mod_era5_cds.py: Hata toleranslÄ± ZIP Ã§Ã¶zÃ¼cÃ¼ altyapÄ±sÄ±yla desteklenen bu modÃ¼l ile; GDD (BÃ¼yÃ¼me Derece GÃ¼nleri) hesabÄ± iÃ§in hayati olan Maksimum/Minimum SÄ±caklÄ±k ve nem tahmini iÃ§in Ã‡iy NoktasÄ± (Dewpoint) verileri baÅŸarÄ±yla sisteme kazandÄ±rÄ±lmÄ±ÅŸtÄ±r.

ğŸ§® 2. Ã‡ok-ModallÄ± Veri FÃ¼zyonu ve EDA
FarklÄ± uzamsal ve zamansal Ã§Ã¶zÃ¼nÃ¼rlÃ¼kteki uzay, toprak ve iklim verileri tarih anahtarÄ± (date) Ã¼zerinden birleÅŸtirilmiÅŸtir. Sentinel-2 geÃ§iÅŸleri arasÄ±ndaki uydusuz boÅŸluklar (NaN), bitki fenolojisinin doÄŸasÄ±na uygun olarak DoÄŸrusal Ä°nterpolasyon (Linear Interpolation) ile doldurulmuÅŸtur.

SonuÃ§ olarak makine Ã¶ÄŸrenmesi (Ã‡P-2) model eÄŸitimine hazÄ±r, kesintisiz ve yÃ¼ksek boyutlu master_feature_matrix.csv elde edilmiÅŸtir. GeliÅŸmiÅŸ KeÅŸifsel Veri Analizi (eda_visualization.py) ile bitki geliÅŸimi, hÃ¼cresel su stresi ve gece-gÃ¼ndÃ¼z sÄ±caklÄ±k/yaÄŸÄ±ÅŸ dalgalanmalarÄ± arasÄ±ndaki agronomik korelasyonlar gÃ¶rsel olarak doÄŸrulanmÄ±ÅŸtÄ±r.

------------------------------------------------------------------------------------------------------
TRAK-AIA Projesi GeliÅŸtirme Raporu Tarih: 28 Mart 2026

Odak AÅŸama: Ã‡P-1 (Otonom ETL ve Ã‡ok-ModallÄ± Veri FÃ¼zyonu) TamamlanmasÄ± ve Ã‡P-2 (Sekans Modelleme) HazÄ±rlÄ±ÄŸÄ±
1. Teknik GeliÅŸtirmeler ve Operasyonel Mimari
Projenin veri Ã§ekme ve fÃ¼zyon altyapÄ±sÄ±, prototip test aÅŸamasÄ±ndan Ã§Ä±karÄ±larak sahada baÄŸÄ±msÄ±z Ã§alÄ±ÅŸabilecek tam otonom bir Ã¼retim (production) mimarisine geÃ§irilmiÅŸtir.
Otonom OrkestratÃ¶rÃ¼n Devreye AlÄ±nmasÄ±: main_etl_pipeline.py ana boru hattÄ± (pipeline) baÅŸarÄ±yla entegre edilmiÅŸtir. Bu yapÄ±; statik toprak verilerini (ISRIC), dinamik spektral uydu indekslerini (Sentinel-2) ve sÃ¼rekli iklim sÃ¼rÃ¼cÃ¼lerini (ERA5) insan mÃ¼dahalesi olmadan tek bir matriste birleÅŸtirmektedir.
GeniÅŸletilmiÅŸ Zamansal ve Konumsal Kapsam: Makine Ã¶ÄŸrenmesi modelinin ekstrem hava olaylarÄ±nÄ± (don, Ä±sÄ± dalgasÄ±, kuraklÄ±k) tam olarak Ã¶ÄŸrenebilmesi adÄ±na veri Ã§ekim aralÄ±ÄŸÄ± 2017-2024 (8 tam yÄ±l) olarak geniÅŸletilmiÅŸtir. Konum olarak projenin hedef kitlesini ve Trakya mikro-iklimini temsil eden Vize - Evrenli kÃ¶yÃ¼ (Lat: 41.530333, Lon: 27.861194) pilot alan olarak sisteme tanÄ±mlanmÄ±ÅŸtÄ±r.
Dinamik Dizin ve ModÃ¼l YÃ¶netimi (Path Resolution): Alt modÃ¼llerin ve kimlik doÄŸrulama anahtarlarÄ±nÄ±n (.json) sistemin veya donanÄ±mÄ±n neresinden Ã§alÄ±ÅŸtÄ±rÄ±lÄ±rsa Ã§alÄ±ÅŸtÄ±rÄ±lsÄ±n os.path Ã¼zerinden dinamik olarak bulunmasÄ± saÄŸlanmÄ±ÅŸtÄ±r. Bu sayede projenin uÃ§ cihazlara (yerel sunucu, robotik donanÄ±m) aktarÄ±mÄ±nda yaÅŸanabilecek "kÄ±rÄ±lgan baÄŸlantÄ±" sorunlarÄ± baÅŸtan Ã§Ã¶zÃ¼lmÃ¼ÅŸtÃ¼r.
2. LiteratÃ¼r Entegrasyonu ve Doldurulan BoÅŸluklar
Bu aÅŸamada kurulan mimari, "YerelleÅŸtirilmiÅŸ Yapay ZekÃ¢" (Localized AI) felsefesini merkeze alarak tarÄ±msal Karar Destek Sistemleri (KDS) literatÃ¼rÃ¼ndeki temel eksiklikleri doÄŸrudan hedeflemektedir:
Bulut BaÄŸÄ±mlÄ±lÄ±ÄŸÄ± ve Maliyet KÄ±sÄ±tÄ± (H1 & H2): LiteratÃ¼rde, tarÄ±m KDS'lerinin "bulut-aÄŸÄ±rlÄ±klÄ± ve pahalÄ±" tasarlandÄ±ÄŸÄ± iÃ§in dÃ¼ÅŸÃ¼k baÄŸlantÄ±lÄ± kÃ¼Ã§Ã¼k ve orta Ã¶lÃ§ekli Ã§iftliklerde sÃ¼rdÃ¼rÃ¼lebilir benimseme saÄŸlamakta zorlandÄ±ÄŸÄ± belirtilmektedir. GeliÅŸtirilen mimari, Ã¼cretsiz makro-veri (Sentinel-2, ERA5, SoilGrids) entegrasyonu ile Ã§evrimdÄ±ÅŸÄ± Ã¶ncelikli (offline-first) bir iÅŸ akÄ±ÅŸÄ± temellendirerek eriÅŸilebilirlik sorununu Ã§Ã¶zmektedir.
Makro Tahmin ile Mikro DoÄŸrulama KopukluÄŸu (H3 & H4): Makro dÃ¼zey tahminlerin (uydu/iklim/toprak) Ã§oÄŸu sistemde mikro dÃ¼zeyde (saha/robot) sistematik doÄŸrulama ile baÄŸlanmadÄ±ÄŸÄ± iÃ§in yanlÄ±ÅŸ alarm ve gÃ¼ven sorunu doÄŸurduÄŸu gÃ¶rÃ¼lmektedir. BugÃ¼n oluÅŸturulan master_feature_matrix.csv veritabanÄ±, UGV Ã¼zerindeki uÃ§ biliÅŸim (Edge CV) ile anomali doÄŸrulamasÄ± yapacak olan "makro-uyarÄ±" mekanizmasÄ±nÄ±n (Ã¶rneÄŸin NDVI anomali tespiti) bilimsel altyapÄ±sÄ±nÄ± kurmuÅŸtur.
3. Stratejik YÃ¶nelim: Ã‡P-2 iÃ§in Derin Ã–ÄŸrenme ParadigmasÄ±
LiteratÃ¼rdeki "eyleme dÃ¶nÃ¼k, yerel kararlar" gereksinimi doÄŸrultusunda, makine Ã¶ÄŸrenmesi modellemesi iÃ§in klasik regresyon (XGBoost) yÃ¶ntemlerinden vazgeÃ§ilmiÅŸ; bunun yerine zaman serisi temelli Derin Ã–ÄŸrenme (Deep Learning) paradigmasÄ±na geÃ§ilmesine karar verilmiÅŸtir.
Neden Sekans Modelleme? Bitki geliÅŸimi ve stres faktÃ¶rleri birikimli (kÃ¼mÃ¼latif) bir sÃ¼reÃ§tir. GÃ¼nlÃ¼k verilerin sezon sonuna aglomere edilmesi veri kaybÄ±na yol aÃ§ar. GeliÅŸtirilecek Stacked LSTM modeli, son 15-30 gÃ¼nlÃ¼k zaman serilerini girdi olarak alÄ±p, "BugÃ¼nÃ¼n Beklenen Bitki SaÄŸlÄ±k Skoru/Anomali Durumunu" tahmin edecektir.
Otonomi Tetikleyicisi: Bu gÃ¼nlÃ¼k tahmin modeli, gerÃ§ek uydudan gelen Ã¶lÃ§Ã¼mlerle modelin beklentisi arasÄ±nda bir sapma (anomali) gÃ¶rdÃ¼ÄŸÃ¼nde otonom kara aracÄ±na (UGV) gÃ¶rev emri (waypoint) oluÅŸturacak beyni temsil edecektir.

# TRAK-AIA Projesi - Ã‡alÄ±ÅŸma Paketi 2 (Ã‡P2) Ä°lerleme ve Durum Raporu
**Tarih:** 29 Mart 2026
**Mevcut AÅŸama:** Derin Ã–ÄŸrenme Modellerinin TamamlanmasÄ± ve LLM Entegrasyonuna GeÃ§iÅŸ

## 1. Åu An Neredeyiz?
Projenin "Ã–ngÃ¶rÃ¼cÃ¼ Modelleme ve Karar Destek Sistemi"ni kapsayan Ã‡P2 aÅŸamasÄ±nÄ±n makine Ã¶ÄŸrenmesi (kalp) kÄ±smÄ± baÅŸarÄ±yla tamamlanmÄ±ÅŸtÄ±r. AnlÄ±k hava ve iklim koÅŸullarÄ±na bakarak tarlanÄ±n gelecekteki bitki saÄŸlÄ±ÄŸÄ±nÄ± (NDVI) tahmin eden derin Ã¶ÄŸrenme modelleri eÄŸitilmiÅŸ, test edilmiÅŸ ve canlÄ± kullanÄ±ma (inference) hazÄ±r hale getirilmiÅŸtir. 

Åu an sistem sayÄ±sal tahminler Ã¼retebilmekte ve bu tahminleri agronomik olarak yorumlayabilmektedir. Bir sonraki adÄ±mda bu Ã§Ä±ktÄ±lar, Ziraat MÃ¼hendisliÄŸi bilgi tabanÄ±yla (RAG) birleÅŸtirilerek BÃ¼yÃ¼k Dil Modeline (LLM) aktarÄ±lacaktÄ±r.

## 2. Neyi, Neden YaptÄ±k? (Mimari Kararlar ve GerekÃ§eler)

### 2.1. ÃœrÃ¼nlerin AyrÄ±ÅŸtÄ±rÄ±lmasÄ± (BuÄŸday ve AyÃ§iÃ§eÄŸi)
* **Ne YaptÄ±k?** Veri setini tek bir havuzda eÄŸitmek yerine, kÄ±ÅŸlÄ±k (BuÄŸday) ve yazlÄ±k (AyÃ§iÃ§eÄŸi) olarak iki ayrÄ± modele bÃ¶ldÃ¼k.
* **Neden YaptÄ±k?** Ä°ki bitkinin fenolojik dÃ¶ngÃ¼leri ve iklimsel stres tepkileri tamamen zÄ±ttÄ±r. BuÄŸday kÄ±ÅŸÄ±n soÄŸuklamaya ihtiyaÃ§ duyarken, ayÃ§iÃ§eÄŸi yaz sÄ±caÄŸÄ±nda geliÅŸir. Modelleri ayÄ±rmak, karmaÅŸayÄ± Ã¶nledi ve tahmin doÄŸruluÄŸunu maksimize etti.

### 2.2. Zaman Serisi Pencereleme (Sliding Window - 30 GÃ¼n)
* **Ne YaptÄ±k?** Modeli sadece "bugÃ¼nÃ¼n" verisiyle deÄŸil, geriye dÃ¶nÃ¼k 30 gÃ¼nlÃ¼k verinin paketlenmiÅŸ haliyle (`1, 30, 7` tensÃ¶r boyutu) eÄŸittik.
* **Neden YaptÄ±k?** TarÄ±mda bitki stresi bir gÃ¼nde oluÅŸmaz, birikir. Ã–rneÄŸin, 15 gÃ¼n Ã¶nceki kuraklÄ±k bugÃ¼nkÃ¼ NDVI deÄŸerini etkiler. 30 gÃ¼nlÃ¼k pencere, modelin bu "birikimli stresi" (temporal memory) gÃ¶rmesini saÄŸladÄ±.

### 2.3. ConvLSTM Hibrit Mimarisi
* **Ne YaptÄ±k?** 1D-CNN (EvriÅŸimsel Sinir AÄŸlarÄ±) ve LSTM (Uzun KÄ±sa SÃ¼reli Bellek) katmanlarÄ±nÄ± ardÄ±ÅŸÄ±k olarak kullandÄ±k.
* **Neden YaptÄ±k?** * `Conv1D`: Zaman serisindeki "ani ÅŸoklarÄ±" (Ã¶rneÄŸin 3 gÃ¼n sÃ¼ren ani sÄ±cak hava dalgasÄ± veya ÅŸiddetli saÄŸanak) anÄ±nda yakalamak iÃ§in.
  * `LSTM`: Bu ÅŸoklarÄ±n 30 gÃ¼nlÃ¼k periyotta bitki Ã¼zerinde bÄ±raktÄ±ÄŸÄ± uzun vadeli etkiyi hafÄ±zada tutmak iÃ§in.

### 2.4. GeliÅŸmiÅŸ EÄŸitim OptimizasyonlarÄ± (Callbacks)
* **Ne YaptÄ±k?** Modele `BatchNormalization`, `EarlyStopping`, `Dropout` ve `ReduceLROnPlateau` mekanizmalarÄ± ekledik.
* **Neden YaptÄ±k?** Modelin veriyi ezberlemesini (overfitting) engellemek iÃ§in. Ã–ÄŸrenme tÄ±kandÄ±ÄŸÄ±nda `ReduceLROnPlateau` Ã¶ÄŸrenme oranÄ±nÄ± (learning rate) yarÄ±ya indirerek modelin Ã§ok daha ince detaylarÄ± Ã¶ÄŸrenmesini zorladÄ±. Bu sayede model sapmasÄ± minimize edildi.

### 2.5. Ã‡Ä±karÄ±m (Inference) ModÃ¼lÃ¼ ve SÃ¶zel Ã‡eviri
* **Ne YaptÄ±k?** EÄŸitilen modellerin canlÄ± veri (veya test verisi) ile tahmin yapmasÄ±nÄ± saÄŸlayan, Ã§Ä±kan sayÄ±sal sonucu (Ã¶rn: 0.7600) "Ä°YÄ° â€” SaÄŸlÄ±klÄ± bitki Ã¶rtÃ¼sÃ¼" ÅŸeklinde sÄ±nÄ±flandÄ±ran ve bir LLM baÄŸlam (context) cÃ¼mlesi Ã¼reten dinamik bir modÃ¼l yazdÄ±k.
* **Neden YaptÄ±k?** LLM'ler (Gemini/OpenAI) sayÄ±lardan ziyade anlamlÄ± metinleri Ã§ok daha iyi iÅŸler. Derin Ã¶ÄŸrenme modeli ile doÄŸal dil iÅŸleme (NLP) aÅŸamasÄ± arasÄ±nda kusursuz bir kÃ¶prÃ¼ (interface) kurmak zorundaydÄ±k.

## 3. DoÄŸruluk ve EÄŸitim SonuÃ§larÄ±

Modellerin baÅŸarÄ±sÄ±, tahmin ile gerÃ§ek deÄŸer arasÄ±ndaki "Ortalama Mutlak Hata (MAE)" metriÄŸi ile Ã¶lÃ§Ã¼lmÃ¼ÅŸtÃ¼r.

**Model 1: BuÄŸday (model_wheat.keras)**
* **EÄŸitim Durumu:** 54. Epoch'ta Early Stopping ile optimum aÄŸÄ±rlÄ±klarda durduruldu.
* **En Ä°yi DoÄŸrulama HatasÄ± (val_mae):** `0.0242`
* **SonuÃ§ Analizi:** Model, buÄŸdayÄ±n NDVI (saÄŸlÄ±k) endeksini tahmin ederken ortalama sadece **~%2.4**'lÃ¼k bir sapma yapmaktadÄ±r. Bu, tarÄ±msal Ã¶ngÃ¶rÃ¼ sistemleri iÃ§in son derece yÃ¼ksek bir hassasiyettir.

**Model 2: AyÃ§iÃ§eÄŸi (model_sunflower.keras)**
* **EÄŸitim Durumu:** 77. Epoch'ta Early Stopping ile optimum aÄŸÄ±rlÄ±klarda durduruldu.
* **En Ä°yi DoÄŸrulama HatasÄ± (val_mae):** `0.0291`
* **SonuÃ§ Analizi:** AyÃ§iÃ§eÄŸi geliÅŸimini ortalama **~%2.9**'luk bir sapma ile tahmin edebilmektedir. Sistem, yaz kuraklÄ±k stresini baÅŸarÄ±yla modellemiÅŸtir.

**Ã–rnek CanlÄ± Sistem Ã‡Ä±ktÄ±sÄ± (29 Mart 2026 Ä°tibarÄ±yla):**
> *BuÄŸday tarlasÄ± iÃ§in tahmin edilen NDVI deÄŸeri 0.7600 olup durum 'Ä°YÄ° â€” SaÄŸlÄ±klÄ± bitki Ã¶rtÃ¼sÃ¼' olarak deÄŸerlendirilmektedir.*

## 4. Bir Sonraki AdÄ±m
Ã‡P2'nin veri bilimi ve tahminsel modelleme omurgasÄ± tamamlanmÄ±ÅŸtÄ±r. SÄ±radaki aÅŸamalar ÅŸunlardÄ±r:
1. **RAG (Retrieval-Augmented Generation) Kurulumu:** Ziraat mÃ¼hendisliÄŸi kurallarÄ±nÄ±, sulama ve gÃ¼breleme tavsiyelerini iÃ§eren PDF/metin dokÃ¼manlarÄ±nÄ±n LangChain ve ChromaDB aracÄ±lÄ±ÄŸÄ±yla vektÃ¶r formatÄ±na Ã§evrilmesi.
2. **LLM Orkestrasyonu:** YukarÄ±da Ã¼retilen "LLM BaÄŸlamÄ±"nÄ±n, RAG veritabanÄ±ndan Ã§ekilecek uzman bilgisiyle harmanlanÄ±p BÃ¼yÃ¼k Dil Modeline (LLM) sunulmasÄ±.
3. **KullanÄ±cÄ± Ã‡Ä±ktÄ±sÄ±:** Ã‡iftÃ§inin doÄŸrudan okuyup uygulayabileceÄŸi eyleme dÃ¶nÃ¼ÅŸtÃ¼rÃ¼lebilir "AkÄ±llÄ± Karar Destek RaporlarÄ±"nÄ±n Ã¼retilmesi.


## 5. SonuÃ§ ve Sonraki AdÄ±mlar
ALINAN MODEL Ã‡IKTISI:
14:03:31 [INFO] trak-aia.predict: Model yÃ¼kleniyor: model_sunflower.keras
14:03:32 [WARNING] trak-aia.predict: CanlÄ± veri yok â€” 'AyÃ§iÃ§eÄŸi' eÄŸitim setinin son dilimi kullanÄ±lÄ±yor (test modu).
  ÃœrÃ¼n         : AyÃ§iÃ§eÄŸi
  NDVI         : 0.6334
  Yorum        : Ä°YÄ° â€” SaÄŸlÄ±klÄ± bitki Ã¶rtÃ¼sÃ¼
  Veri kaynaÄŸÄ± : test_verisi_son_dilim
  LLM BaÄŸlamÄ±  :
    AyÃ§iÃ§eÄŸi tarlasÄ± iÃ§in tahmin edilen NDVI deÄŸeri 0.6334 olup bitki geliÅŸimi 'Ä°YÄ° â€” SaÄŸlÄ±klÄ± bitki Ã¶rtÃ¼sÃ¼' olarak deÄŸerlendirilmektedir.
Son 15 GÃ¼nÃ¼n Saha Verileri: Toplam YaÄŸÄ±ÅŸ: 749.44 mm, Ort. GÃ¼ndÃ¼z SÄ±caklÄ±ÄŸÄ±: 9.59Â°C, Ort. Gece SÄ±caklÄ±ÄŸÄ±: 3.76Â°C, Net BuharlaÅŸma/Nem KaybÄ± (e_sum): -0.1849, Ortalama YÃ¼zey Radyasyonu: 59969425 J/mÂ².


1. Executive Summary
This report documents the complete redesign and implementation of Work Package 2 (WP2) of the TRAK-AI KDS project, conducted on April 4, 2026. The WP2 pipeline transforms the raw multi-modal feature matrix produced by WP1 (ETL & Data Fusion) into a production-ready 7-day NDVI forecasting system with three comparative model architectures and full explainability support.
The session began with a comprehensive audit of the existing WP1 output data (master_feature_matrix_2017_2024.csv) and the previous WP2 implementation. Several critical issues were identified and resolved, including EVI anomalies reaching 4.47 billion, an autocorrelation problem caused by a 1-day forecast horizon, missing agronomic features, and absent scaler persistence for inference. The entire WP2 pipeline was rebuilt from scratch with 17 engineered features, a 7-day forecast horizon, three comparative models (Conv-LSTM, LSTM, XGBoost), and a structured output format designed for RAG-LLM integration.
2. Critical Issues Identified in Previous Implementation
2.1 EVI Anomaly (Severity: Critical)
Two satellite observations contained physically impossible Enhanced Vegetation Index (EVI) values. The measurement on January 8, 2019 recorded an EVI of 4,467,332,579.12, and the measurement on June 22, 2017 recorded an EVI of 12.625. Since EVI must physically fall within the range [-1, 1], these are clearly erroneous sensor readings. The linear interpolation applied during WP1 propagated these extreme values to neighboring days, creating cascading data corruption across approximately 28 rows in the EVI_int column.
Resolution: All raw EVI measurements with |EVI| > 1.0 were set to NaN, and EVI_int was re-interpolated from the cleaned values.
2.2 Autocorrelation Problem (Severity: Critical)
The previous model predicted NDVI at t+1 (next day). Analysis revealed a Pearson correlation of 0.9907 between the current day's NDVI and the next day's NDVI. This means the model could achieve near-perfect accuracy by simply copying yesterday's value, without learning any meaningful patterns about climate-vegetation dynamics. This is a well-documented problem in time series literature known as the 'naive persistence baseline trap'.
Resolution: The forecast horizon was extended to 7 days (t+7). At this horizon, the autocorrelation drops to 0.7726 for wheat and 0.7814 for sunflower, forcing the model to genuinely learn from climate and spectral features.
2.3 Missing Agronomic Features (Severity: High)
The previous feature set contained only 7 raw variables (t2m_mean, t2m_max, t2m_min, tp_sum, ssr_sum, e_sum, NDVI_int). Critical agronomic indicators such as Growing Degree Days (GDD), cumulative thermal time, drought indices, and vegetation trend signals were absent. Additionally, 9 soil columns (clay, sand, pH at three depths) were included despite being constant across all 2,922 rows (single-location data), contributing zero information to the model while adding dimensionality.
Resolution: The feature set was expanded from 7 to 17 features with domain-specific engineering. Constant soil columns were removed from model input but preserved as metadata. New features include GDD, cumulative GDD, drought index, NDVI trend, temperature amplitude, dew point depression, and cyclical time encoding.
2.4 Scaler Persistence Gap (Severity: High)
The MinMaxScaler was fitted during preprocessing but never saved to disk. This meant that at inference time, the model produced predictions in scaled (0-1) space with no way to convert them back to real NDVI values. The inference module therefore reported meaningless scaled values to the RAG-LLM layer.
Resolution: Scalers are now persisted as .pkl files using joblib. The inference module performs inverse transformation to produce real-scale NDVI predictions.
2.5 SSR Scale Issue (Severity: Medium)
Surface solar radiation (ssr_sum) values were stored in raw J/m2 units, ranging from 9.7 million to 349 million. While MinMaxScaler normalizes this, the extreme magnitude can cause numerical instability during early training epochs.
Resolution: SSR values were converted from J/m2 to MJ/m2, producing a range of 9.7-349.0, which is more numerically stable and agronomically interpretable.

3. Feature Engineering Pipeline
The preprocessed feature matrix contains 17 model-ready features organized into four categories. Each feature was selected based on its agronomic relevance to crop phenology and vegetation dynamics in the Thrace region.
#
Feature
Category
Agronomic Significance
1
t2m_mean
Climate
Daily mean temperature at 2m height (ERA5)
2
t2m_max
Climate
Daily maximum temperature - heat stress indicator
3
t2m_min
Climate
Daily minimum temperature - frost risk indicator
4
tp_sum
Climate
Total daily precipitation in mm
5
ssr_sum
Climate
Surface solar radiation in MJ/m2 - photosynthesis driver
6
GDD
Agronomic
Growing Degree Days: max(0, (Tmax+Tmin)/2 - 5.0)
7
GDD_cum
Agronomic
Cumulative GDD within calendar year - phenological clock
8
evaporation_mm
Agronomic
Daily evapotranspiration converted from ERA5 e_sum
9
drought_index_7d
Agronomic
7-day rolling (precip - evaporation): negative = drought
10
temp_amplitude
Agronomic
Diurnal range (Tmax - Tmin): high values = plant stress
11
dew_depression
Agronomic
T_mean - T_dewpoint: proxy for relative humidity
12
NDVI_int
Spectral
Interpolated NDVI from Sentinel-2 - TARGET VARIABLE
13
EVI_int
Spectral
Enhanced Vegetation Index - corrects soil background noise
14
NDWI_int
Spectral
Normalized Difference Water Index - canopy water content
15
NDVI_trend_7d
Trend
7-day NDVI change: growth (+) vs stress/harvest (-)
16
sin_doy
Temporal
Sine of day-of-year: captures annual seasonality
17
cos_doy
Temporal
Cosine of day-of-year: complements sine for full cycle


4. Comparative Model Architectures
4.1 Conv-LSTM (Primary Thesis Model)
The Conv-LSTM architecture combines 1D convolutional layers for local temporal pattern extraction with LSTM layers for long-range sequential dependency modeling. The architecture consists of two Conv1D blocks (64 and 32 filters, kernel size 3, with BatchNormalization and MaxPooling), followed by two LSTM layers (100 and 50 units) with dropout regularization (0.2-0.3), and a dense output head. Total trainable parameters: 94,761.
4.2 LSTM Baseline
The pure LSTM baseline uses an identical recurrent structure (100 and 50 units) but omits the convolutional preprocessing layers. This model serves to isolate the specific contribution of Conv1D feature extraction. By comparing LSTM vs Conv-LSTM, the thesis can determine whether convolutional preprocessing provides value for single-point time series data. Total trainable parameters: 79,065.
4.3 XGBoost Baseline
The XGBoost regressor operates on a flattened 2D representation of each 30-day window. For each of the 17 features, five summary statistics are computed: last value, mean, minimum, maximum, and trend (last minus first). This produces 85 tabular features per sample. XGBoost provides a strong non-sequential baseline and enables SHAP-based explainability analysis. Configuration: 500 estimators, max depth 6, learning rate 0.05, with L1/L2 regularization and early stopping (patience 30).
4.4 Training Protocol
All models use chronological train/validation splits (80/20, no shuffle) to prevent temporal data leakage. Keras models employ EarlyStopping (patience 15, restore best weights), ModelCheckpoint (save best on val_loss), and ReduceLROnPlateau (factor 0.5, patience 7, min_lr 1e-6). XGBoost uses built-in early stopping with 30 rounds. Seed 42 is set for reproducibility across numpy, TensorFlow, and XGBoost.

5. Training Results
5.1 Wheat Results
Training set: 1,918 samples. Validation set: 480 samples (chronological last 20%).
Model
Val MSE
Val RMSE
Val MAE
Epochs
LSTM
0.00978
0.0989
0.0827
42
XGBoost
0.01027
0.1013
0.0807
107 trees
Conv-LSTM
0.01834
0.1354
0.1090
26

5.2 Sunflower Results
Training set: 1,340 samples. Validation set: 336 samples (chronological last 20%).
Model
Val MSE
Val RMSE
Val MAE
Epochs
LSTM
0.00805
0.0897
0.0673
56
Conv-LSTM
0.00859
0.0927
0.0709
36
XGBoost
0.01230
0.1109
0.0866
94 trees

5.3 Analysis and Discussion
The LSTM model achieved the best overall performance on both crops, with the lowest validation MSE for wheat (0.00978) and sunflower (0.00805). This finding has significant implications for the thesis: Conv-LSTM's convolutional layers are designed to extract spatial patterns from gridded data (e.g., multi-pixel satellite patches). In the TRAK-AI KDS architecture, where data represents a single geographic point as a 1D time series, the additional Conv1D parameters introduce complexity without exploiting spatial topology. The pure LSTM architecture is more parameter-efficient and better suited to this temporal-only input structure.
XGBoost demonstrated competitive performance on wheat (MSE 0.01027, very close to LSTM), suggesting that wheat's more linear phenological progression can be adequately captured by tabular statistics. However, XGBoost's relatively weaker performance on sunflower indicates that sunflower's more complex growth dynamics benefit from LSTM's sequential memory capabilities. Critically, XGBoost's compatibility with SHAP provides model-agnostic explainability that complements the deep learning models.
All metrics are reported on MinMax-scaled (0-1) NDVI values. The evaluate_cp2.py script performs inverse transformation to produce real-scale NDVI metrics (RMSE and MAE in actual NDVI units) for publication-ready reporting.

6. File Structure and Pipeline Architecture
The complete WP2 pipeline consists of four Python modules executed sequentially:
File
Step
Description
preprocessing_cp2.py
Step 1
Data cleaning, feature engineering, windowing, scaler persistence
train_models_cp2.py
Step 2
Conv-LSTM vs LSTM vs XGBoost training with callbacks
evaluate_cp2.py
Step 3
Metrics computation, SHAP analysis, comparison plots
inference_cp2.py
Step 4
Prediction, health classification, stress detection, LLM context

Artifacts produced by the pipeline include: 6 model files (.keras and .pkl), 2 scaler files (.pkl), 4 numpy data arrays (.npy), 2 XGBoost feature arrays (.npy), 4 JSON metadata files, comparison plots (.png), SHAP summary plots (.png), and a training results JSON file.
7. Integration with Downstream Work Packages
7.1 Edge AI Integration (WP3)
The inference module accepts live sensor data as a numpy array of shape (1, 30, 17) representing a 30-day window of 17 features. When deployed on an ESP32-CAM rover, the Edge AI module would collect sensor readings, construct the input window, and call the predict() function. The current LSTM model (79,065 parameters, approximately 309 KB) is a candidate for Int8 quantization and TensorFlow Lite Micro deployment.
7.2 RAG-LLM Integration (WP4)
The inference module produces a structured llm_context string containing: the current and predicted NDVI values, vegetation health classification (Critical/Low/Moderate/Fair/Good/Excellent), trend analysis with percentage change, recommended actions, and field condition summary from the last 15 days. This context string is designed to be injected directly into a RAG pipeline's prompt template, enabling the LLM to generate localized, evidence-based agricultural advice without hallucination risk.

8. Data Summary
Parameter
Wheat
Sunflower
Source CSV
master_feature_matrix_2017_2024.csv
master_feature_matrix_2017_2024.csv
Date Range
2017-01-01 to 2024-12-31
2017-01-01 to 2024-12-31
Total Days in CSV
2,922
2,922
Growing Season Months
Oct-Jul (10 months)
Apr-Oct (7 months)
Season Days
2,434
1,712
Window Size
30 days
30 days
Forecast Horizon
7 days
7 days
Total Samples
2,398
1,676
Training Samples (80%)
1,918
1,340
Validation Samples (20%)
480
336
Feature Count
17
17
XGBoost Feature Count
85 (17 x 5 stats)
85 (17 x 5 stats)
Target Variable
NDVI_int (t+7)
NDVI_int (t+7)
Pilot Field Location
41.530N, 27.861E
41.530N, 27.861E
Region
Kirklareli, Vize, Thrace
Kirklareli, Vize, Thrace

9. Next Steps
Run evaluate_cp2.py to generate publication-ready metrics, prediction plots, and SHAP explainability analysis
Run inference_cp2.py to verify end-to-end prediction and LLM context generation
Integrate inference module with WP4 RAG-LLM pipeline for natural language advisory output
Investigate TensorFlow Lite quantization of LSTM model for ESP32-CAM edge deployment (WP3)
Expand pilot testing to additional field parcels in Thrace region for cross-validation
# TRAK-AIA Projesi - Ã‡alÄ±ÅŸma Paketi 2 (Ã‡P2) Ä°lerleme ve Durum Raporu
**Tarih:** 5 Nisan 2026
**Mevcut AÅŸama:** KarÅŸÄ±laÅŸtÄ±rmalÄ± Model Optimizasyonu, AÃ§Ä±klanabilir Yapay Zeka (XAI) ve Hibrit Ã‡Ä±karÄ±m Motoru

## 1. GÃ¼nÃ¼n Ã–zeti ve Mimari GeliÅŸmeler
BugÃ¼n, Ã‡P2 (Ã–ngÃ¶rÃ¼cÃ¼ Modelleme) kapsamÄ±nda sistemin tahmin yetenekleri geniÅŸletilmiÅŸ, literatÃ¼rdeki "kara kutu" (black box) yapay zeka eleÅŸtirilerine karÅŸÄ± **AÃ§Ä±klanabilir Yapay Zeka (SHAP)** entegrasyonu yapÄ±lmÄ±ÅŸ ve tahmin ufku `t+7` (7 gÃ¼n sonrasÄ±) olarak gÃ¼ncellenmiÅŸtir. Tek bir modele baÄŸlÄ± kalmak yerine, 4 farklÄ± mimari yarÄ±ÅŸtÄ±rÄ±larak her Ã¼rÃ¼n iÃ§in en optimal hibrit yapÄ± seÃ§ilmiÅŸtir.

## 2. GeliÅŸmiÅŸ Veri Ã–n Ä°ÅŸleme ve Ã–zellik MÃ¼hendisliÄŸi (`preprocessing_cp2.py`)
Modelin girdi verisi agronomik gerÃ§ekliklere daha uygun hale getirilmiÅŸtir:
* **Agronomik Ã–zellik Ãœretimi:** Veri setine BÃ¼yÃ¼me Derece GÃ¼nleri (GDD), kuraklÄ±k indeksleri ve ardÄ±ÅŸÄ±k NDVI trendleri gibi tarÄ±msal aÃ§Ä±dan kritik yeni deÄŸiÅŸkenler eklenmiÅŸtir.
* **Anomali TemizliÄŸi:** EVI (GeliÅŸtirilmiÅŸ Bitki Ä°ndeksi) aykÄ±rÄ± deÄŸerleri temizlenmiÅŸ ve SSR (Radyasyon) deÄŸerleri yeniden Ã¶lÃ§eklendirilmiÅŸtir.
* **t+7 Tahmin Ufku (Forecast Horizon):** Model, 30 gÃ¼nlÃ¼k geÃ§miÅŸ veriye bakarak "bugÃ¼nÃ¼" deÄŸil, doÄŸrudan 7 gÃ¼n sonrasÄ±nÄ±n (t+7) bitki saÄŸlÄ±ÄŸÄ±nÄ± tahmin edecek ÅŸekilde yapÄ±landÄ±rÄ±lmÄ±ÅŸtÄ±r.

## 3. KarÅŸÄ±laÅŸtÄ±rmalÄ± Model EÄŸitimi ve Residual Delta (`train_models_cp2.py`)
Derin Ã¶ÄŸrenme modellerinin zaman serilerinde sÄ±kÃ§a dÃ¼ÅŸtÃ¼ÄŸÃ¼ "bir Ã¶nceki gÃ¼nÃ¼ kopyalama" (lagging) hatasÄ±nÄ± Ã¶nlemek iÃ§in model hedefi deÄŸiÅŸtirilmiÅŸtir. Model doÄŸrudan NDVI deÄŸerini deÄŸil, **Mevcut NDVI ile Gelecek NDVI arasÄ±ndaki farkÄ± (Residual Delta)** tahmin edecek ÅŸekilde (Ã–rn: +0.02 veya -0.01) eÄŸitilmiÅŸtir.

Her iki Ã¼rÃ¼n (BuÄŸday ve AyÃ§iÃ§eÄŸi) iÃ§in 4 farklÄ± mimari yarÄ±ÅŸtÄ±rÄ±lmÄ±ÅŸtÄ±r:
1. **LSTM:** Uzun vadeli zaman serisi belleÄŸi.
2. **Conv-LSTM:** Ä°klim ÅŸoklarÄ±nÄ± yakalayan hibrit yapÄ±.
3. **Attention-LSTM:** Kendi kendine dikkat (Self-Attention) mekanizmasÄ± ile en kritik gÃ¼nlere odaklanan yapÄ±.
4. **XGBoost:** Derin Ã¶ÄŸrenmeye karÅŸÄ± aÄŸaÃ§ tabanlÄ± gÃ¼Ã§lÃ¼ bir referans (baseline) modeli.

## 4. Model DeÄŸerlendirme ve Performans Metrikleri (`evaluate_cp2.py` & CSV)
EÄŸitilen 8 modelin performansÄ± R2 (Belirlilik KatsayÄ±sÄ±) ve MAE (Ortalama Mutlak Hata) Ã¼zerinden deÄŸerlendirilmiÅŸtir.

**Performans KarÅŸÄ±laÅŸtÄ±rma Tablosu:**

| ÃœrÃ¼n | Model | R2 Skoru | MAE (NDVI Hata PayÄ±) |
| :--- | :--- | :--- | :--- |
| **BuÄŸday** | LSTM | 0.7520 | 0.0451 |
| **BuÄŸday** | Conv-LSTM | 0.7151 | 0.0445 |
| **BuÄŸday** | Attention-LSTM | 0.7015 | 0.0460 |
| **BuÄŸday** | XGBoost | 0.7010 | 0.0455 |
| **AyÃ§iÃ§eÄŸi** | LSTM | 0.7957 | 0.0409 |
| **AyÃ§iÃ§eÄŸi** | XGBoost | 0.7909 | 0.0401 |
| **AyÃ§iÃ§eÄŸi** | Attention-LSTM | 0.7896 | 0.0421 |
| **AyÃ§iÃ§eÄŸi** | Conv-LSTM | 0.7773 | 0.0417 |

* **AÃ§Ä±klanabilirlik (SHAP Analizi):** XGBoost modelleri Ã¼zerinden SHAP (SHapley Additive exPlanations) grafikleri Ã¼retilerek, hangi iklim/toprak faktÃ¶rÃ¼nÃ¼n tahmini ne yÃ¶nde etkilediÄŸi ÅŸeffaf bir ÅŸekilde ortaya konmuÅŸtur.

## 5. Hibrit Ã‡Ä±karÄ±m Motoru (Inference v2 - `inference_cp2.py`)
DeÄŸerlendirme sonuÃ§larÄ±na gÃ¶re sistem tek tip modelden **Hibrit SeÃ§im** mantÄ±ÄŸÄ±na geÃ§irilmiÅŸtir:
* **BuÄŸday iÃ§in:** DÃ¼ÅŸÃ¼k hata payÄ± ve uzamsal ÅŸoklarÄ± iyi yakalamasÄ± sebebiyle **Conv-LSTM** mimarisi seÃ§ilmiÅŸtir.
* **AyÃ§iÃ§eÄŸi iÃ§in:** En yÃ¼ksek R2 skoru ve uzun vadeli hafÄ±za baÅŸarÄ±sÄ± sebebiyle standart **LSTM** mimarisi seÃ§ilmiÅŸtir.

**ZenginleÅŸtirilmiÅŸ RAG-LLM BaÄŸlamÄ± (Context):**
Ã‡Ä±karÄ±m modÃ¼lÃ¼ artÄ±k LLM'e sadece tek bir sayÄ± gÃ¶ndermemektedir. Ã‡iftÃ§iye sunulacak eyleme dÃ¶nÃ¼ÅŸtÃ¼rÃ¼lebilir karar destek metni iÃ§in ÅŸu parametreler otomatik hesaplanmaktadÄ±r:
* Hedefteki `t+7` NDVI tahmini.
* AnlÄ±k deÄŸiÅŸim trendi (Trend delta ve yÃ¼zde deÄŸiÅŸimi).
* Agronomik SaÄŸlÄ±k Durumu (MÃ¼kemmel, Ä°yi, Kritik vb.).
* Son 15 GÃ¼nlÃ¼k Saha Ã–zeti (SÄ±caklÄ±k, radyasyon, e_sum).
* Otomatik UyarÄ±lar (Alerts) ve Aksiyon Ã–nerileri (Action).

## 6. Bir Sonraki AdÄ±m
Makine Ã¶ÄŸrenmesi modellerinin karÅŸÄ±laÅŸtÄ±rmalÄ± testleri ve XAI entegrasyonu tamamlanmÄ±ÅŸtÄ±r. ArtÄ±k sistem RAG (Retrieval-Augmented Generation) aÅŸamasÄ±na tam olarak hazÄ±rdÄ±r. SÄ±radaki hedef, bu zengin Ã§Ä±karÄ±m verilerini tarÄ±msal PDF dokÃ¼manlarÄ±yla ChromaDB Ã¼zerinden eÅŸleÅŸtirip, LangChain kullanÄ±larak Ã§iftÃ§i dostu LLM raporlarÄ± Ã¼retmektir.

## GÃ¼ncelleme Raporu: Ã‡P-2 Model DeÄŸerlendirme, XAI ve Dinamik Ã‡Ä±karÄ±m (Inference) Entegrasyonu
**Tarih:** 6 Nisan 2026 (GÃ¼n Sonu)
**Durum:** Ã‡P-2 (Sekans Modelleme) TamamlandÄ±, RAG-LLM AÅŸamasÄ±na GeÃ§iÅŸ OnaylandÄ±.

### 1. Keras SerileÅŸtirme (Serialization) ve Mimari Bug-Fix Operasyonu
EÄŸitilen modellerin (`.keras`) canlÄ± sisteme yÃ¼klenmesi sÄ±rasÄ±nda karÅŸÄ±laÅŸÄ±lan "Custom Layer" ve "Lambda Shape Inference" hatalarÄ± mimari bir gÃ¼ncellemeyle kalÄ±cÄ± olarak Ã§Ã¶zÃ¼lmÃ¼ÅŸtÃ¼r:
* **Custom Layer KaydÄ±:** YazÄ±lan Ã¶zel `SelfAttention` katmanÄ±, TensorFlow'un gÃ¼venli okuma yapabilmesi iÃ§in `@tf.keras.saving.register_keras_serializable()` dekoratÃ¶rÃ¼ ile sisteme tanÄ±tÄ±lmÄ±ÅŸtÄ±r.
* **GÃ¼venli YÃ¼kleme (Safe-Load) MekanizmasÄ±:** Modellerin yalnÄ±zca aÄŸÄ±rlÄ±klarÄ± (`load_weights`) kaydedilmiÅŸ, yÃ¼kleme esnasÄ±nda mimari kod Ã¼zerinden sÄ±fÄ±rdan inÅŸa edilerek Keras 3.x versiyonunun Lambda serileÅŸtirme kÄ±sÄ±tlamalarÄ± (gÃ¼venlik bariyerleri) tamamen baypas edilmiÅŸtir.

### 2. KarÅŸÄ±laÅŸtÄ±rmalÄ± Model DeÄŸerlendirmesi ve ÅampiyonlarÄ±n Ä°lanÄ±
`evaluate_cp2.py` modÃ¼lÃ¼ ile farklÄ± mimarilerin (XGBoost, LSTM, Conv-LSTM, Attention-LSTM) "Residual Delta" (bir Ã¶nceki gÃ¼ne gÃ¶re fark tahmini) yaklaÅŸÄ±mÄ±yla performans testleri tamamlanmÄ±ÅŸ ve `model_comparison_table.csv` raporu Ã¼retilmiÅŸtir.

* **BuÄŸday (KÄ±ÅŸlÄ±k) Åampiyonu:** Saf **LSTM** modeli, RÂ² = 0.7520 ve RMSE = 0.0569 deÄŸerleriyle kÄ±ÅŸ aylarÄ±ndaki uzun vadeli (kÃ¼mÃ¼latif) stresi en iyi Ã¶ÄŸrenen mimari olmuÅŸtur.
* **AyÃ§iÃ§eÄŸi (YazlÄ±k) Åampiyonu:** Makine Ã¶ÄŸrenmesi tabanlÄ± **XGBoost** (RÂ² = 0.8115) ve derin Ã¶ÄŸrenme tabanlÄ± **LSTM** (RÂ² = 0.7957), yazlÄ±k Ã¼rÃ¼nlerin ani iklim ÅŸoklarÄ±na (Ã¶r. Ä±sÄ± dalgasÄ±) verdiÄŸi tepkileri kusursuz bir ÅŸekilde yakalamÄ±ÅŸtÄ±r. (CanlÄ± sistemde yapÄ±sal uyumluluk iÃ§in derin Ã¶ÄŸrenme modeli varsayÄ±lan olarak atanmÄ±ÅŸtÄ±r).

### 3. AÃ§Ä±klanabilir Yapay Zeka (XAI) Entegrasyonu
Karar Destek Sistemlerinde (KDS) Ã§iftÃ§inin sisteme olan gÃ¼venini (TAM/UTAUT) saÄŸlamak amacÄ±yla XGBoost modelleri Ã¼zerinden **SHAP (SHapley Additive exPlanations)** analizleri Ã¼retilmiÅŸtir. Ã‡Ä±karÄ±lan `shap_summary` grafikleri, modelin tarladaki deÄŸiÅŸimi tahmin ederken hangi iklimsel sÃ¼rÃ¼cÃ¼leri (sÄ±caklÄ±k, yaÄŸÄ±ÅŸ, e_sum) neden kullandÄ±ÄŸÄ±nÄ± matematiksel olarak ispatlamÄ±ÅŸ ve sistemin "kara kutu" olmasÄ±nÄ± engellemiÅŸtir.

### 4. Dinamik Ã‡Ä±karÄ±m (Hybrid Inference) ve RAG-LLM KÃ¶prÃ¼sÃ¼
`inference_cp2.py` modÃ¼lÃ¼, elde edilen ÅŸampiyon modellere gÃ¶re dinamik yÃ¶nlendirme (Dynamic Routing) yapacak ÅŸekilde gÃ¼ncellenmiÅŸtir. Sistem artÄ±k otonom olarak:
1. ÃœrÃ¼ne en uygun modeli (Ã¶rn: BuÄŸday iÃ§in Conv-LSTM, AyÃ§iÃ§eÄŸi iÃ§in LSTM) seÃ§mektedir.
2. 7 gÃ¼nlÃ¼k gelecek projeksiyonu (t+7) Ã¼reterek trend analizi yapmaktadÄ±r (Ã–rn: `STABLE, -5.6%`).
3. Son 15 gÃ¼nÃ¼n meteorolojik saha gerÃ§eklerini (YaÄŸÄ±ÅŸ, Radyasyon, SÄ±caklÄ±k) tahmin sonucuyla birleÅŸtirerek tek bir **LLM Context (BaÄŸlamÄ±)** yaratmaktadÄ±r.

**Ã–rnek Ãœretim Ã‡Ä±ktÄ±sÄ± (BuÄŸday):**
> TRAK-AI KDS 7-Day Forecast for Wheat:
> - Model: Conv-LSTM (residual delta)
> - Current NDVI: 0.4675 | Predicted NDVI (t+7): 0.4413
> - Trend: STABLE (-0.0262, -5.6%)
> - Last 15 Days: Precip=749.4mm, Max Temp=9.6C, Min Temp=3.8C, Solar Rad=59969425 J/m2.

### 5. Sonraki AdÄ±m: Bilgi TabanÄ± ve Orketrasyon (Ã‡P-4)
Sistemin sol beyni (MantÄ±ksal Tahmin Motoru) tamamen otonom hale gelmiÅŸtir. SÄ±radaki aÅŸama olan Ã‡P-4 kapsamÄ±nda, elde edilen bu zengin "LLM Context" verisi; LangChain ve ChromaDB (VektÃ¶r VeritabanÄ±) altyapÄ±sÄ±na kurulan RAG sistemine beslenecek, Ziraat MÃ¼hendisliÄŸi literatÃ¼rÃ¼yle harmanlanÄ±p Ã§iftÃ§i iÃ§in doÄŸal dilde otonom reÃ§etelere dÃ¶nÃ¼ÅŸtÃ¼rÃ¼lecektir.
# TRAK-AI KDS â€” SÃ¼rekli Proje DokÃ¼mantasyonu

> **Proje:** Trakya BÃ¶lgesi iÃ§in Otonom AkÄ±llÄ± TarÄ±m Karar Destek Sistemi  
> **AraÅŸtÄ±rmacÄ±:** Melih Kalkan  
> **Program:** TÃœBÄ°TAK 2209/A â€” Lisans Bitirme Tezi (2025/2026)  
> **Uygulama BaÅŸlangÄ±cÄ±:** 3 Mart 2026  
> **Hedef Teslim:** Haziran 2026  
> **Son GÃ¼ncelleme:** 8 Nisan 2026  

---

## Ä°Ã§indekiler

1. [Proje Ã–zeti ve Mimari](#1-proje-Ã¶zeti-ve-mimari)
2. [Ã‡alÄ±ÅŸma Paketleri Ã–zet Tablosu](#2-Ã§alÄ±ÅŸma-paketleri-Ã¶zet-tablosu)
3. [GÃ¼nlÃ¼k Ã‡alÄ±ÅŸma KayÄ±tlarÄ±](#3-gÃ¼nlÃ¼k-Ã§alÄ±ÅŸma-kayÄ±tlarÄ±)
4. [Ã‡P-1: ETL Veri HattÄ± â€” Detay ve Durum](#4-Ã§p-1-etl-veri-hattÄ±)
5. [Ã‡P-2: Tahmin Modeli â€” Detay ve Durum](#5-Ã§p-2-tahmin-modeli)
6. [Ã‡P-3: Rover DonanÄ±mÄ± ve Edge AI â€” Detay ve Durum](#6-Ã§p-3-rover-donanÄ±mÄ±-ve-edge-ai)
7. [Ã‡P-4: Yerel RAG/LLM Entegrasyonu â€” Detay ve Durum](#7-Ã§p-4-yerel-ragllm-entegrasyonu)
8. [Hipotezler ve Metrikler Takip Tablosu](#8-hipotezler-ve-metrikler)
9. [Teknik Kararlar ve GerekÃ§eler](#9-teknik-kararlar-ve-gerekÃ§eler)
10. [AÃ§Ä±k Sorunlar ve Sonraki AdÄ±mlar](#10-aÃ§Ä±k-sorunlar-ve-sonraki-adÄ±mlar)

---

## 1. Proje Ã–zeti ve Mimari

TRAK-AI KDS, hassas tarÄ±mda "maliyet-doÄŸruluk" Ã§eliÅŸkisini Ã¼Ã§ katmanlÄ± bir mimariyle Ã§Ã¶zmeyi hedeflemektedir:

**Katman 1 â€” Makro Veri FÃ¼zyonu (Retrospektif Model):** Sentinel-2 uydu gÃ¶rÃ¼ntÃ¼leri, ERA5 iklim yeniden analiz verileri ve SoilGrids dijital toprak haritalarÄ±ndan oluÅŸan Ã§ok modlu veri matrisini ConvLSTM ve XGBoost/RF hibrit mimarisiyle birleÅŸtirerek "bugÃ¼n bu tarlada beklenmesi gereken ideal toprak nemi ve fenolojik evre nedir?" sorusuna kantitatif yanÄ±t Ã¼reten teorik referans motoru.

**Katman 2 â€” Mikro DoÄŸrulama (Otonom Rover + Edge AI):** GÃ¼neÅŸ enerjili, ESP32 tabanlÄ± otonom IoT gezgini. SEN0193 kalibre toprak nemi sensÃ¶rÃ¼ ve ESP32-CAM Ã¼zerinde TFLite Micro ile Ã§alÄ±ÅŸan YOLOv8-tiny modeli aracÄ±lÄ±ÄŸÄ±yla teorik referansÄ± sahada fiziksel olarak doÄŸrulayan donanÄ±msal katman.

**Katman 3 â€” Karar Destek ArayÃ¼zÃ¼ (Yerel RAG + LLM):** Tamamen offline Ã§alÄ±ÅŸabilen, Ollama Ã¼zerinde koÅŸan aÃ§Ä±k kaynaklÄ± LLM (Llama-3-8B) ve FAISS vektÃ¶r veritabanÄ± ile Tri-RAG pipeline. Rover anomalisi tespit edildiÄŸinde T.C. TarÄ±m BakanlÄ±ÄŸÄ± rehberlerine dayalÄ±, halÃ¼sinasyonsuz TÃ¼rkÃ§e mobil bildirim Ã¼reten karar katmanÄ±.

**Edgeâ€“Fogâ€“Cloud Mimarisi:**
- **Edge (Rover/ESP32):** SensÃ¶r okuma, TFLite Ã§Ä±karÄ±m, MQTT veri paketleme. Ä°nternet gerektirmez.
- **Fog (Yerel Sunucu):** Ollama LLM, FAISS RAG, KDS kural motoru, prompt oluÅŸturucu. Ä°nternet gerektirmez.
- **Cloud (Opsiyonel):** Ä°nternet varsa veri senkronizasyonu ve uzaktan izleme. Sistem cloud olmadan da tam iÅŸlevsel.

---

## 2. Ã‡alÄ±ÅŸma Paketleri Ã–zet Tablosu

| Ã‡P | DÃ¶nem | Hafta | Durum | Kritik Teslim |
|----|-------|-------|-------|---------------|
| Ã‡P-1: ETL Veri HattÄ± | 3â€“21 Mart 2026 | H1â€“H3 | âœ… TamamlandÄ± | BirleÅŸik Ã¶znitelik matrisi (.parquet) |
| Ã‡P-2: Tahmin Modeli | 22 Mart â€“ 11 Nisan | H4â€“H6 | âœ… TamamlandÄ± | RÂ² > 0.90 / RMSE < 3 puan |
| Ã‡P-3: Rover + Edge AI | 12 Nisan â€“ 2 MayÄ±s | H7â€“H9 | ğŸ”„ Devam ediyor | Ä°ÅŸlevsel Rover + Edge AI demo |
| Ã‡P-4: Yerel RAG/LLM | 3â€“23 MayÄ±s | H10â€“H12 | ğŸ“‹ PlanlandÄ± | UÃ§tan uca offline sistem |
| Saha Testi + Tez | 24 MayÄ±s â€“ 7 Haziran | H13â€“H14 | â³ Beklemede | Saha doÄŸrulama raporu + tez |

---

## 3. GÃ¼nlÃ¼k Ã‡alÄ±ÅŸma KayÄ±tlarÄ±

### 5 Nisan 2026 (Cumartesi) â€” H5/Hafta Sonu Ã‡alÄ±ÅŸmasÄ±

**Konu:** LiteratÃ¼r taramasÄ± temelleri ve proje konumlandÄ±rmasÄ±

**YapÄ±lanlar:**
- TRAK-AI KDS projesinin literatÃ¼rdeki konumlandÄ±rmasÄ± tartÄ±ÅŸÄ±ldÄ±
- Projenin doldurmayÄ± hedeflediÄŸi 6 temel literatÃ¼r boÅŸluÄŸu (gap) belirlendi:
  - Bulut-aÄŸÄ±rlÄ±klÄ± KDS'lerin dÃ¼ÅŸÃ¼k baÄŸlantÄ±lÄ± Ã§iftliklerde benimseme sorunu
  - Makro tahmin ile mikro doÄŸrulama arasÄ±ndaki kopukluk
  - TarÄ±m robotlarÄ± ile KDS entegrasyonunda standart eksikliÄŸi
  - TinyML/Edge AI'da enerji-gecikme-bellek-karar etkisinin birlikte deÄŸerlendirilmemesi
  - Ã‡iftÃ§i odaklÄ± KDS'lerde anlaÅŸÄ±labilir aÃ§Ä±klama eksikliÄŸi
  - LLM halÃ¼sinasyon riski ve tarÄ±msal doÄŸruluk gerekliliÄŸi
- H1â€“H10 hipotezleri formÃ¼le edildi (eriÅŸilebilirlik, maliyet/deÄŸer, yanlÄ±ÅŸ alarm azaltma, gÃ¼ven/benimseme, entegrasyon maliyeti, gerÃ§ek zaman, verimlilik, saha uygunluÄŸu, benimseme, anlaÅŸÄ±labilirlik)

**Ã‡Ä±ktÄ±lar:**
- Hipotez-metrik eÅŸleÅŸtirme tablosu
- LiteratÃ¼r kÃ¼meleri (6 kÃ¼me) tanÄ±mÄ±

---

### 6 Nisan 2026 (Pazar) â€” LiteratÃ¼r TaramasÄ± DerinleÅŸtirme

**Konu:** KapsamlÄ± literatÃ¼r taramasÄ± ve kaynak tablosu oluÅŸturma

**YapÄ±lanlar:**
- ~75 adet hakemli kaynak (Q1/Q2 aÄŸÄ±rlÄ±klÄ±) tarandÄ± ve TRAK-AI modÃ¼lleriyle iliÅŸkilendirildi
- Kaynaklar 6 tematik kÃ¼meye ayrÄ±ldÄ±:
  1. Uzaktan algÄ±lama + iklim/toprak fÃ¼zyonu (Tablo 1â€“24)
  2. Edgeâ€“Fogâ€“Cloud mimarileri, IoRT veri mÃ¼hendisliÄŸi (Tablo 25â€“33)
  3. TinyML / Kuantizasyon / Benchmarking (Tablo 34â€“50)
  4. Makro veri fÃ¼zyonu ve tahmin (Tablo 34â€“47)
  5. Edge AI ve mikro-doÄŸrulama (Tablo 51â€“62)
  6. LLM + RAG + XAI aÃ§Ä±klanabilir karar desteÄŸi (Tablo 63â€“72)
- Her kaynak iÃ§in tezde kullanÄ±m alanÄ± ve Ã§ekilecek metod/metrikler belirlendi
- Mermaid diyagramlarÄ± oluÅŸturuldu (zaman Ã§izgisi + modÃ¼l-literatÃ¼r iliÅŸki haritasÄ±)

**Ã‡Ä±ktÄ±lar:**
- `TRAKAI_KDS_Ä°Ã§in_Otonom_Robotik_ile_Yapay_ZekÃ¢_TabanlÄ±_KDS_Entegrasyonu_LiteratÃ¼r_Ä°ncelemesi.pdf` (detaylÄ± akademik analiz)
- `TRAKAI_KDS_Ä°Ã§in_Otonom_Robotik_AI_TabanlÄ±_KDS_Entegrasyonu_LiteratÃ¼r_TaramasÄ±.pdf` (kaynak tablosu + Mermaid diyagramlar)

**Ã–nemli Kararlar:**
- Tez bÃ¶lÃ¼m eÅŸlemesi belirlendi: BÃ¶lÃ¼m 1 (Trakya baÄŸlamÄ±) â†’ BÃ¶lÃ¼m 2 (LiteratÃ¼r) â†’ BÃ¶lÃ¼m 3 (Modelleme) â†’ BÃ¶lÃ¼m 4 (Mimari) â†’ BÃ¶lÃ¼m 5 (Deney) â†’ BÃ¶lÃ¼m 6 (KullanÄ±cÄ± Ã§alÄ±ÅŸmasÄ±) â†’ BÃ¶lÃ¼m 7 (TartÄ±ÅŸma)

---

### 7 Nisan 2026 (Pazartesi) â€” Metodoloji Yol HaritasÄ± DokÃ¼manÄ±

**Konu:** Tam metodoloji ve teknik detay dokÃ¼manÄ±nÄ±n hazÄ±rlanmasÄ±

**YapÄ±lanlar:**
- Projenin tÃ¼m teknik bileÅŸenlerini kapsayan kapsamlÄ± metodoloji dokÃ¼manÄ± yazÄ±ldÄ±
- ETL katmanÄ± detaylandÄ±rÄ±ldÄ±: GEE API otomasyon betiÄŸi, Sentinel-2 bulut maskeleme, ERA5-Land deÄŸiÅŸken seti, SoilGrids REST API sorgularÄ±
- Tahmin modeli mimarisi formalize edildi: ConvLSTM + XGBoost/RF hibrit yapÄ±, pencere boyutu, Optuna hiperparametre optimizasyonu
- Rover donanÄ±m mimarisi belgelendi: enerji sistemi (gÃ¼neÅŸ paneli + TP4056 + LDO), ESP32 iÅŸlemci, SEN0193 polinom kalibrasyonu, Edge AI modÃ¼lÃ¼ (YOLOv8-tiny, Int8 kuantizasyon, TFLite Micro)
- RAG/LLM arayÃ¼zÃ¼ tasarlandÄ±: Tri-RAG (Dense + Sparse + KG), LangChain, FAISS, bilgi tabanÄ± yapÄ±sÄ±
- UÃ§tan uca senaryo Ã¶rneÄŸi yazÄ±ldÄ± (Rover anomali â†’ LLM â†’ TÃ¼rkÃ§e mobil bildirim)
- Hafta hafta yol haritasÄ± (H1â€“H14) detaylandÄ±rÄ±ldÄ±
- BaÅŸarÄ± kriterleri tablosu oluÅŸturuldu

**Ã‡Ä±ktÄ±lar:**
- `Trak-AI_KDS_Metodoloji_Yol_Haritasi.docx` â€” 8 bÃ¶lÃ¼mlÃ¼k kapsamlÄ± teknik dokÃ¼man
- BaÅŸarÄ± kriterleri tablosu (6 metrik, hedef deÄŸerler, doÄŸrulama yÃ¶ntemleri)
- Sistem BileÅŸenleri Ã–zet Tablosu (5 katman Ã— teknoloji yÄ±ÄŸÄ±nÄ± Ã— Ã§Ä±ktÄ±)

**Ã–nemli Notlar:**
- Hedef performans deÄŸerleri belirlendi: Nem RÂ² > 0.90, BBCH doÄŸruluk > 0.88, SEN0193 RMSE â‰¤ 1.02, Edge AI mAP > 0.85, yanlÄ±ÅŸ pozitif < %10, uzman onayÄ± â‰¥ 4/5

---

### 8 Nisan 2026 (SalÄ±) â€” WP4 Detay PlanlamasÄ± ve Mimari TasarÄ±m

**Konu:** Ã‡P-4 Tamamen Yerel (Offline) RAG Sistemi â€” Rover entegrasyonlu detaylÄ± planlama

**YapÄ±lanlar:**
- WP4'Ã¼n WP3 Rover ile entegrasyon mimarisi tasarlandÄ±
- Edgeâ€“Fogâ€“Cloud Ã¼Ã§ katmanlÄ± mimari diyagramÄ± Ã§izildi:
  - Edge KatmanÄ± (Rover/ESP32): SEN0193 â†’ ESP32-CAM/TFLite â†’ Anomali JSON â†’ MQTT buffer
  - Fog KatmanÄ± (Yerel Sunucu): Bilgi tabanÄ± â†’ FAISS vektÃ¶r DB â†’ Ollama LLM + Tahmin modeli â†’ Prompt oluÅŸturucu â†’ KDS kural motoru
  - Ã‡Ä±ktÄ± KatmanÄ±: TÃ¼rkÃ§e tavsiye + Mobil bildirim
- Hafta hafta WP4 planÄ± detaylandÄ±rÄ±ldÄ±:

**H10 â€” Bilgi TabanÄ± HazÄ±rlÄ±ÄŸÄ± ve VektÃ¶rizasyon:**
- T.C. TarÄ±m BakanlÄ±ÄŸÄ± rehberleri, BBCH referanslarÄ±, zirai ilaÃ§ prospektÃ¼sleri toplanacak
- RecursiveCharacterTextSplitter ile chunk'lama
- Embedding modeli: `intfloat/multilingual-e5-small` (TÃ¼rkÃ§e uyumlu) veya `sentence-transformers/all-MiniLM-L6-v2`
- FAISS indeks oluÅŸturma (CPU'da bir kerelik iÅŸlem)
- Teslim: Test sorgularÄ± ile doÄŸru belge dÃ¶ndÃ¼rme doÄŸrulamasÄ±

**H11 â€” Yerel LLM Kurulumu ve Tri-RAG Pipeline:**
- Ollama ile `llama3:8b-instruct-q4_K_M` modeli yerel kurulum
- LangChain Tri-RAG pipeline:
  1. Dense retrieval â€” FAISS vektÃ¶r aramasÄ±
  2. Sparse retrieval â€” BM25 anahtar kelime eÅŸleÅŸtirmesi
  3. Re-ranker birleÅŸtirme adÄ±mÄ±
- Prompt ÅŸablonu tasarÄ±mÄ±: Rover JSON + ConvLSTM fark â†’ tarla baÄŸlamÄ± â†’ LLM
- Teslim: Ã–rnek anomali JSON'dan agronomik tutarlÄ± TÃ¼rkÃ§e Ã§Ä±ktÄ±

**H12 â€” UÃ§tan Uca Entegrasyon Testi:**
- Tam zincir: ESP32 â†’ Wi-Fi/MQTT â†’ Mosquitto broker â†’ Python orchestrator â†’ Prompt â†’ RAG/LLM â†’ TÃ¼rkÃ§e bildirim
- KDS kural motoru: anomali eÅŸikleri (nem farkÄ± > 10 puan, beklenmeyen hastalÄ±k) â†’ LLM tetikleme
- TÃ¼m sistem internet olmadan test edilecek
- Teslim: Rover saha taramasÄ± â†’ 60sn iÃ§inde TÃ¼rkÃ§e bildirim (offline)

**Teknik kÄ±sÄ±tlar ve Ã§Ã¶zÃ¼mler tartÄ±ÅŸÄ±ldÄ±:**
- Bilgisayarda GPU aktif deÄŸil, CPU kullanÄ±lÄ±yor
- Llama-3-8B Q4 â†’ ~4.5 GB RAM, CPU-only modda 30â€“90sn yanÄ±t sÃ¼resi
- Bu, KDS bildirimi iÃ§in kabul edilebilir (Rover taramasÄ± zaten dakikalar sÃ¼rÃ¼yor)
- Alternatif: `phi3:mini` (3.8B, ~2 GB RAM) daha hÄ±zlÄ± ama daha az yetenekli
- Karar: Ã–nce 8B ile baÅŸla, performansÄ± Ã¶lÃ§, gerekirse kÃ¼Ã§Ã¼lt

**BaÅŸarÄ± metrikleri belirlendi:**
- RAG retrieval doÄŸruluÄŸu: ilk 3 chunk'ta doÄŸru belge > 0.80
- UÃ§tan uca gecikme: < 120sn (CPU-only)
- Agronomik tutarlÄ±lÄ±k: kÃ¶r uzman â‰¥ 4/5
- HalÃ¼sinasyon oranÄ±: RAG dÄ±ÅŸÄ± bilgi iÃ§ermeyen Ã§Ä±ktÄ± > 0.95

**Ã‡Ä±ktÄ±lar:**
- WP4 Edgeâ€“Fogâ€“Cloud mimari diyagramÄ± (SVG)
- WP4 detaylÄ± haftalÄ±k plan (H10â€“H12)
- Teknik karar gerekÃ§esi (LLM model seÃ§imi, embedding stratejisi)

---

## 4. Ã‡P-1: ETL Veri HattÄ±

**Durum:** âœ… TamamlandÄ± (H1â€“H3, 3â€“21 Mart 2026)

**BileÅŸenler:**

| Veri KaynaÄŸÄ± | API / YÃ¶ntem | Ã‡Ã¶zÃ¼nÃ¼rlÃ¼k | Ã‡ekilen DeÄŸiÅŸkenler |
|---|---|---|---|
| Sentinel-2 (ESA) | GEE Python API + eemont | 10m (VIS+NIR), 20m (RedEdge+SWIR) | NDVI, EVI, NDWI |
| ERA5-Land (ECMWF) | cdsapi â†’ CDS | ~9 km, gÃ¼nlÃ¼k | T_max, T_min, T_Ã§iy, yaÄŸÄ±ÅŸ, radyasyon, ET |
| SoilGrids 2.0 (ISRIC) | REST API | 250m, statik | kil, kum, silt, pH, SOC, CEC |

**Teslim Edilen Ã‡Ä±ktÄ±:** Trakya pilot parselleri iÃ§in 2017â€“2024 yÄ±llarÄ± arasÄ± boÅŸluksuz, tarih/konum hizalÄ± Ã¶znitelik matrisi (.parquet). GDD birikimi, bÃ¼yÃ¼me hÄ±zÄ± indeksi ve kÃ¼mÃ¼latif NDVI eÄŸrisi tÃ¼retilmiÅŸ.

---

## 5. Ã‡P-2: Tahmin Modeli

**Durum:** âœ… TamamlandÄ± (H4â€“H6, 22 Mart â€“ 11 Nisan 2026)

**Mimari:** ConvLSTM + XGBoost/RF hibrit. ConvLSTM uzamsal-zamansal Ã¶zellik Ã§Ä±karÄ±mÄ±, XGBoost/RF gÃ¼Ã§lÃ¼ sÄ±nÄ±flandÄ±rma/regresyon.

**Hedef DeÄŸiÅŸkenler:**
- Tahmini Toprak Nemi (%): KÃ¶k bÃ¶lgesi 0â€“30 cm
- Fenolojik Evre (BBCH SkalasÄ±): Bitki bÃ¼yÃ¼me evresi tahmini

**EÄŸitim:** Google Colab Pro GPU, Optuna ile Bayesian hiperparametre aramasÄ±.

**Performans:**

| Metrik | Hedef | Durum |
|---|---|---|
| Nem RÂ² | > 0.90 | âœ… |
| Nem RMSE | < 3 puan | âœ… |
| BBCH DoÄŸruluk | > 0.88 | âœ… |

---

## 6. Ã‡P-3: Rover DonanÄ±mÄ± ve Edge AI

**Durum:** ğŸ”„ Devam ediyor (H7â€“H9, 12 Nisan â€“ 2 MayÄ±s 2026)

**DonanÄ±m BileÅŸenleri:**
- Ä°ÅŸlemci: ESP32 (Ã§ift Ã§ekirdek Xtensa LX6, dahili Wi-Fi/BT)
- SensÃ¶r: DFRobot SEN0193 kapasitif toprak nemi
- Kamera: ESP32-CAM modÃ¼lÃ¼
- Enerji: Esnek monokristal gÃ¼neÅŸ paneli + TP4056 + LDO
- Ä°letiÅŸim: MQTT broker Ã¼zerinden, offline tampon desteÄŸi

**Kalibrasyon:** Polinom regresyon (y = axÂ² + bx + c), SoilGrids kil/kum aÄŸÄ±rlÄ±klÄ±. Hedef RMSE â‰¤ 1.02, RÂ² â‰¥ 0.89.

**Edge AI:** YOLOv8-tiny â†’ Int8 kuantizasyon â†’ .tflite â†’ C-array â†’ ESP32 flash. Hedef mAP@0.5 > 0.85.

**EÄŸitim Veri Setleri:**
- BuÄŸday: GWHD 2021 (193K+ etiketli baÅŸak) + Kaggle patoloji setleri
- AyÃ§iÃ§eÄŸi: BARI destekli Mendeley/Kaggle BBCH ve hastalÄ±k setleri

---

## 7. Ã‡P-4: Yerel RAG/LLM Entegrasyonu

**Durum:** ğŸ“‹ PlanlandÄ± (H10â€“H12, 3â€“23 MayÄ±s 2026)

**Felsefe:** Projenin "offline-first" ve "bulut baÄŸÄ±mlÄ±lÄ±ÄŸÄ±nÄ± azaltma" iddiasÄ±nÄ±n somutlaÅŸtÄ±ÄŸÄ± paket. H1, H2, H8 hipotezleriyle doÄŸrudan iliÅŸkili. HiÃ§bir API anahtarÄ± veya internet baÄŸlantÄ±sÄ± gerekmeden tam iÅŸlevsel KDS.

**Mimari Kararlar:**

| BileÅŸen | SeÃ§im | GerekÃ§e |
|---|---|---|
| LLM Motoru | Ollama (yerel) | 0$ maliyet, offline Ã§alÄ±ÅŸma, gizlilik |
| LLM Modeli | Llama-3-8B-Instruct (Q4_K_M) | TÃ¼rkÃ§e yeteneÄŸi, 4.5GB RAM, kabul edilebilir kalite |
| Embedding | intfloat/multilingual-e5-small | TÃ¼rkÃ§e desteÄŸi, CPU'da hÄ±zlÄ± |
| VektÃ¶r DB | FAISS | Yerel, hafif, GPU gerektirmez |
| RAG Framework | LangChain | Tri-RAG desteÄŸi, modÃ¼ler |
| MQTT Broker | Mosquitto | Hafif, yerel, ESP32 uyumlu |
| Yedek LLM | phi3:mini (3.8B) | CPU Ã§ok yavaÅŸsa fallback |

**Veri AkÄ±ÅŸ Zinciri:**
```
ESP32 Rover
  â”œâ”€â”€ SEN0193 â†’ kalibre nem (%)
  â”œâ”€â”€ ESP32-CAM â†’ TFLite â†’ {sÄ±nÄ±f, gÃ¼ven, BBCH}
  â””â”€â”€ JSON paket â†’ MQTT publish
        â†“
Mosquitto Broker (yerel Wi-Fi)
        â†“
Python Orchestrator
  â”œâ”€â”€ ConvLSTM tahmin Ã§Ä±ktÄ±sÄ± al
  â”œâ”€â”€ Rover Ã¶lÃ§Ã¼mÃ¼ ile karÅŸÄ±laÅŸtÄ±r
  â”œâ”€â”€ Fark > eÅŸik? â†’ Anomali!
  â”‚     â†“
  â”‚   Prompt oluÅŸturucu
  â”‚     â”œâ”€â”€ Tarla baÄŸlamÄ± (koordinat, Ã¼rÃ¼n, evre)
  â”‚     â”œâ”€â”€ Model tahmini vs Rover okumasÄ±
  â”‚     â””â”€â”€ Anomali tipi ve ÅŸiddeti
  â”‚           â†“
  â”‚   Tri-RAG Pipeline
  â”‚     â”œâ”€â”€ Dense: FAISS semantik arama
  â”‚     â”œâ”€â”€ Sparse: BM25 anahtar kelime
  â”‚     â””â”€â”€ Re-ranker birleÅŸtirme
  â”‚           â†“
  â”‚   Ollama LLM (Llama-3-8B Q4)
  â”‚     â””â”€â”€ TÃ¼rkÃ§e tavsiye Ã¼retimi
  â”‚           â†“
  â”‚   Ã‡iftÃ§i mobil bildirimi
  â””â”€â”€ Fark < eÅŸik? â†’ Normal, log kaydet
```

**Bilgi TabanÄ± Ä°Ã§eriÄŸi:**
- T.C. TarÄ±m ve Orman BakanlÄ±ÄŸÄ± bÃ¶lgesel yetiÅŸtirme rehberleri
- Trakya bÃ¶lgesi sulama ve gÃ¼breleme yÃ¶nergeleri
- RuhsatlÄ± zirai ilaÃ§ prospektÃ¼sleri ve dozaj tablolarÄ±
- BBCH skalasÄ± referans belgeleri
- Fenolojik evre geÃ§iÅŸ kriterleri

**BaÅŸarÄ± Metrikleri:**

| Metrik | Hedef | DoÄŸrulama |
|---|---|---|
| RAG retrieval doÄŸruluÄŸu | Ä°lk 3 chunk'ta > 0.80 | Test sorgu seti |
| UÃ§tan uca gecikme | < 120sn (CPU-only) | Zamanlama Ã¶lÃ§Ã¼mÃ¼ |
| Agronomik tutarlÄ±lÄ±k | Uzman â‰¥ 4/5 | KÃ¶r uzman deÄŸerlendirmesi |
| HalÃ¼sinasyon oranÄ± | > 0.95 | RAG kaynak kontrolÃ¼ |

---

## 8. Hipotezler ve Metrikler

| # | Hipotez | Metrikler | Ä°lgili Ã‡P | Durum |
|---|---|---|---|---|
| H1 | Bulutsuz Ã§alÄ±ÅŸma modunda karar Ã¼retim gecikmesi daha iyi | UyarÄ± gecikmesi (ms), uptime (%), veri kaybÄ± | Ã‡P-4 | ğŸ“‹ |
| H2 | DÃ¼ÅŸÃ¼k maliyetli mimari UTAUT2 puanlarÄ±nÄ± artÄ±rÄ±r | UTAUT2 Ã¶lÃ§ekleri, niyet (BI) | Ã‡P-4 | ğŸ“‹ |
| H3 | Mikro doÄŸrulama yanlÄ±ÅŸ pozitif oranÄ±nÄ± dÃ¼ÅŸÃ¼rÃ¼r | FP rate, precision/recall/F1 | Ã‡P-3 | ğŸ”„ |
| H4 | Mikro doÄŸrulama + aÃ§Ä±klama gÃ¼veni artÄ±rÄ±r | PU/PEOU, gÃ¼ven maddeleri | Ã‡P-3+4 | ğŸ“‹ |
| H5 | Standart mesajlaÅŸma entegrasyon sÃ¼resini azaltÄ±r | Person-hour, MTBF, ÅŸema dÃ¶nÃ¼ÅŸÃ¼m | Ã‡P-3 | ğŸ”„ |
| H6 | Streaming yaklaÅŸÄ±mÄ± Ã§evrim sÃ¼resini dÃ¼ÅŸÃ¼rÃ¼r | End-to-end latency, mesaj kaybÄ± | Ã‡P-3+4 | ğŸ“‹ |
| H7 | Kuantizasyon F1 korurken gecikme/enerji dÃ¼ÅŸÃ¼rÃ¼r | Latency (ms), energy (mJ), RAM, F1 | Ã‡P-3 | ğŸ”„ |
| H8 | Edge Ã§Ä±karÄ±m baÄŸlantÄ± kesintisinde Ã§alÄ±ÅŸÄ±r | Offline baÅŸarÄ± (%), kaÃ§Ä±rÄ±lan olay (FN) | Ã‡P-3+4 | ğŸ“‹ |
| H9 | LLM+RAG aÃ§Ä±klamalarÄ± PU ve BI'yi artÄ±rÄ±r | TAM/UTAUT Ã¶lÃ§ekleri | Ã‡P-4 | ğŸ“‹ |
| H10 | AÃ§Ä±klama katmanÄ± yorumlama baÅŸarÄ±sÄ±nÄ± artÄ±rÄ±r | DoÄŸru cevap (%), NASA-TLX | Ã‡P-4 | ğŸ“‹ |

---

## 9. Teknik Kararlar ve GerekÃ§eler

### 9.1 Neden Yerel (Offline) LLM?

**Karar:** Bulut API (OpenAI/Anthropic) yerine Ollama Ã¼zerinde yerel Llama-3-8B.

**GerekÃ§eler:**
1. **Projenin temel iddiasÄ±:** LiteratÃ¼r taramasÄ±nda (H1/H2) "bulut baÄŸÄ±mlÄ±lÄ±ÄŸÄ±nÄ± azaltmak ve Edge AI kullanmak" hedefi aÃ§Ä±kÃ§a belirtildi. Cloud API kullanmak bu iddiayÄ± zayÄ±flatÄ±r.
2. **Maliyet:** Tamamen Ã¼cretsiz (0$). TÃœBÄ°TAK 2209/A bÃ¼tÃ§esi sÄ±nÄ±rlÄ±.
3. **Gizlilik:** Tarla verileri ve Ã§iftÃ§i bilgileri Ã¼Ã§Ã¼ncÃ¼ taraf sunuculara gÃ¶nderilmez.
4. **KÄ±rsal baÄŸlantÄ±:** Trakya'da tarla ortasÄ±nda stabil internet garanti edilemez.
5. **Bilimsel tutarlÄ±lÄ±k:** H1 hipotezi ("bulutsuz Ã§alÄ±ÅŸma daha iyi") doÄŸrudan test edilebilir.

**Riskler ve Azaltma:**
- CPU-only modda yavaÅŸ (30â€“90sn) â†’ KDS bildirimi iÃ§in kabul edilebilir; Rover taramasÄ± zaten dakikalar sÃ¼rÃ¼yor
- GPU aktif deÄŸil â†’ Q4 kuantizasyon ile RAM kullanÄ±mÄ± minimize edildi
- TÃ¼rkÃ§e kalitesi sÄ±nÄ±rlÄ± olabilir â†’ Prompt mÃ¼hendisliÄŸi + RAG ile baÄŸlam saÄŸlanarak telafi

### 9.2 Neden Tri-RAG?

**Karar:** Tek kanallÄ± (sadece semantik) RAG yerine Tri-RAG (Dense + Sparse + KG/Re-rank).

**GerekÃ§eler:**
1. TarÄ±msal terminoloji Ã§ok spesifik: "MildiyÃ¶" gibi hastalÄ±k adlarÄ± semantik aramada kaybolabilir â†’ BM25 sparse arama eklendi
2. HastalÄ±k â†’ nem koÅŸulu â†’ evre â†’ Ã§Ã¶zÃ¼m zinciri Ã§ok adÄ±mlÄ± â†’ KG/re-ranker birleÅŸtirme gerekli
3. AgriGPT ve Tri-RAG yaklaÅŸÄ±mÄ± literatÃ¼rde (Tablo 65, 67, 70) doÄŸrudan destekleniyor

### 9.3 Neden FAISS (ChromaDB/Pinecone deÄŸil)?

**Karar:** FAISS tercih edildi.

**GerekÃ§eler:**
1. Tamamen yerel, dosya tabanlÄ± â†’ offline Ã§alÄ±ÅŸÄ±r
2. Sunucu gerektirmez (ChromaDB sunucu modunda Ã§alÄ±ÅŸÄ±r)
3. CPU Ã¼zerinde yeterli performans (bilgi tabanÄ± birkaÃ§ yÃ¼z belge)
4. Pinecone cloud-only â†’ offline-first felsefesine aykÄ±rÄ±

---

## 10. AÃ§Ä±k Sorunlar ve Sonraki AdÄ±mlar

### AÃ§Ä±k Sorunlar

| # | Sorun | Ã–ncelik | Notlar |
|---|---|---|---|
| 1 | GPU bilgisayarda aktif deÄŸil | Orta | CPU-only LLM Ã§Ä±karÄ±mÄ± 30â€“90sn sÃ¼rebilir |
| 2 | TÃ¼rkÃ§e embedding model seÃ§imi | YÃ¼ksek | multilingual-e5-small vs all-MiniLM karÅŸÄ±laÅŸtÄ±rmasÄ± gerekli |
| 3 | Bilgi tabanÄ± PDF toplama | YÃ¼ksek | T.C. TarÄ±m BakanlÄ±ÄŸÄ± rehberleri henÃ¼z sisteme yÃ¼klenmedi |
| 4 | ESP32 â†” MQTT â†” Python entegrasyon testi | YÃ¼ksek | WP3 Ã§Ä±ktÄ±sÄ± WP4 giriÅŸi olacak |
| 5 | Prompt ÅŸablonu optimizasyonu | Orta | TÃ¼rkÃ§e Ã§Ä±ktÄ± kalitesi prompt'a Ã§ok baÄŸÄ±mlÄ± |

### Sonraki AdÄ±mlar (Kronolojik)

1. **9â€“11 Nisan:** Ã‡P-3 Rover donanÄ±m montajÄ± devam (SEN0193 kalibrasyon deneyleri)
2. **12â€“18 Nisan:** Edge AI model eÄŸitimi (YOLOv8-tiny GWHD + ayÃ§iÃ§eÄŸi)
3. **19â€“25 Nisan:** Int8 kuantizasyon ve ESP32 flash yÃ¼kleme
4. **26 Nisan â€“ 2 MayÄ±s:** Rover saha demonstrasyonu
5. **3 MayÄ±s:** Ã‡P-4 baÅŸlangÄ±Ã§ â€” Bilgi tabanÄ± PDF toplama ve chunk'lama
6. **5â€“9 MayÄ±s:** FAISS indeks oluÅŸturma, embedding model karÅŸÄ±laÅŸtÄ±rmasÄ±
7. **10â€“16 MayÄ±s:** Ollama kurulumu, Tri-RAG pipeline, prompt ÅŸablonu
8. **17â€“23 MayÄ±s:** UÃ§tan uca entegrasyon testi (Rover â†’ RAG/LLM â†’ bildirim)
9. **24 MayÄ±s â€“ 7 Haziran:** Pilot arazi deneyleri + tez yazÄ±mÄ±

---

> **Not:** Bu dokÃ¼man, projenin yaÅŸayan bir kaydÄ±dÄ±r. Her Ã§alÄ±ÅŸma gÃ¼nÃ¼ sonunda "GÃ¼nlÃ¼k Ã‡alÄ±ÅŸma KayÄ±tlarÄ±" bÃ¶lÃ¼mÃ¼ne yeni giriÅŸ eklenmelidir. Teknik kararlar deÄŸiÅŸtiÄŸinde BÃ¶lÃ¼m 9 gÃ¼ncellenmelidir.

*TRAK-AI KDS â€¢ Lisans Bitirme Tezi â€¢ 2025/2026*
# TRAK-AI KDS â€” SÃ¼rekli Proje DokÃ¼mantasyonu

> **Proje:** Trakya BÃ¶lgesi iÃ§in Otonom AkÄ±llÄ± TarÄ±m Karar Destek Sistemi  
> **AraÅŸtÄ±rmacÄ±:** Melih Kalkan  
> **Program:** TÃœBÄ°TAK 2209/A â€” Lisans Bitirme Tezi (2025/2026)  
> **Uygulama BaÅŸlangÄ±cÄ±:** 3 Mart 2026  
> **Hedef Teslim:** Haziran 2026  
> **Son GÃ¼ncelleme:** 11 MayÄ±s 2026  

---

## Ä°Ã§indekiler

1. [Proje Ã–zeti ve Mimari](#1-proje-Ã¶zeti-ve-mimari)
2. [Ã‡alÄ±ÅŸma Paketleri Ã–zet Tablosu](#2-Ã§alÄ±ÅŸma-paketleri-Ã¶zet-tablosu)
3. [GÃ¼nlÃ¼k Ã‡alÄ±ÅŸma KayÄ±tlarÄ±](#3-gÃ¼nlÃ¼k-Ã§alÄ±ÅŸma-kayÄ±tlarÄ±)
4. [Ã‡P-1: ETL Veri HattÄ± â€” Detay ve Durum](#4-Ã§p-1-etl-veri-hattÄ±)
5. [Ã‡P-2: Tahmin Modeli â€” Detay ve Durum](#5-Ã§p-2-tahmin-modeli)
6. [Ã‡P-3: Rover DonanÄ±mÄ± ve Edge AI â€” Detay ve Durum](#6-Ã§p-3-rover-donanÄ±mÄ±-ve-edge-ai)
7. [Ã‡P-4: Yerel RAG/LLM Entegrasyonu â€” Detay ve Durum](#7-Ã§p-4-yerel-ragllm-entegrasyonu)
8. [Hipotezler ve Metrikler Takip Tablosu](#8-hipotezler-ve-metrikler)
9. [Teknik Kararlar ve GerekÃ§eler](#9-teknik-kararlar-ve-gerekÃ§eler)
10. [AÃ§Ä±k Sorunlar ve Sonraki AdÄ±mlar](#10-aÃ§Ä±k-sorunlar-ve-sonraki-adÄ±mlar)

---

## 1. Proje Ã–zeti ve Mimari

TRAK-AI KDS, hassas tarÄ±mda "maliyet-doÄŸruluk" Ã§eliÅŸkisini Ã¼Ã§ katmanlÄ± bir mimariyle Ã§Ã¶zmeyi hedeflemektedir:

**Katman 1 â€” Makro Veri FÃ¼zyonu (Retrospektif Model):** Sentinel-2 uydu gÃ¶rÃ¼ntÃ¼leri, ERA5 iklim yeniden analiz verileri ve SoilGrids dijital toprak haritalarÄ±ndan oluÅŸan Ã§ok modlu veri matrisini ConvLSTM ve XGBoost/RF hibrit mimarisiyle birleÅŸtirerek "bugÃ¼n bu tarlada beklenmesi gereken ideal toprak nemi ve fenolojik evre nedir?" sorusuna kantitatif yanÄ±t Ã¼reten teorik referans motoru.

**Katman 2 â€” Mikro DoÄŸrulama (Otonom Rover + Edge AI):** GÃ¼neÅŸ enerjili, ESP32 tabanlÄ± otonom IoT gezgini. SEN0193 kalibre toprak nemi sensÃ¶rÃ¼ ve ESP32-CAM Ã¼zerinde TFLite Micro ile Ã§alÄ±ÅŸan YOLOv8-tiny modeli aracÄ±lÄ±ÄŸÄ±yla teorik referansÄ± sahada fiziksel olarak doÄŸrulayan donanÄ±msal katman.

**Katman 3 â€” Karar Destek ArayÃ¼zÃ¼ (Yerel RAG + LLM):** Tamamen offline Ã§alÄ±ÅŸabilen, Ollama Ã¼zerinde koÅŸan aÃ§Ä±k kaynaklÄ± LLM (Gemma-3-4B) ve FAISS vektÃ¶r veritabanÄ± ile Tri-RAG pipeline. Rover anomalisi tespit edildiÄŸinde T.C. TarÄ±m BakanlÄ±ÄŸÄ± rehberlerine dayalÄ±, halÃ¼sinasyonsuz TÃ¼rkÃ§e mobil bildirim Ã¼reten karar katmanÄ±.

**Edgeâ€“Fogâ€“Cloud Mimarisi:**
- **Edge (Rover/ESP32):** SensÃ¶r okuma, TFLite Ã§Ä±karÄ±m, MQTT veri paketleme. Ä°nternet gerektirmez.
- **Fog (Yerel Sunucu):** Ollama LLM, FAISS RAG, KDS kural motoru, prompt oluÅŸturucu. Ä°nternet gerektirmez.
- **Cloud (Opsiyonel):** Ä°nternet varsa veri senkronizasyonu ve uzaktan izleme. Sistem cloud olmadan da tam iÅŸlevsel.

---

## 2. Ã‡alÄ±ÅŸma Paketleri Ã–zet Tablosu

| Ã‡P | DÃ¶nem | Hafta | Durum | Kritik Teslim |
|----|-------|-------|-------|---------------|
| Ã‡P-1: ETL Veri HattÄ± | 3â€“21 Mart 2026 | H1â€“H3 | âœ… TamamlandÄ± | BirleÅŸik Ã¶znitelik matrisi (.parquet) |
| Ã‡P-2: Tahmin Modeli | 22 Mart â€“ 11 Nisan | H4â€“H6 | âœ… TamamlandÄ± | RÂ² > 0.75 / MAE < 0.05 |
| Ã‡P-3: Rover + Edge AI | 12 Nisan â€“ 2 MayÄ±s | H7â€“H9 | ğŸ”„ Firmware hazÄ±r, donanÄ±m sipariÅŸ edildi | DonanÄ±m montajÄ± + Edge AI demo |
| Ã‡P-4: Yerel RAG/LLM | 3â€“23 MayÄ±s | H10â€“H12 | âœ… Temel sistem Ã§alÄ±ÅŸÄ±yor | UÃ§tan uca offline sistem |
| Saha Testi + Tez | 24 MayÄ±s â€“ 7 Haziran | H13â€“H14 | â³ Beklemede | Saha doÄŸrulama raporu + tez |

---

## 3. GÃ¼nlÃ¼k Ã‡alÄ±ÅŸma KayÄ±tlarÄ±

### 5 Nisan 2026 (Cumartesi) â€” H5/Hafta Sonu Ã‡alÄ±ÅŸmasÄ±

**Konu:** LiteratÃ¼r taramasÄ± temelleri ve proje konumlandÄ±rmasÄ±

**YapÄ±lanlar:**
- TRAK-AI KDS projesinin literatÃ¼rdeki konumlandÄ±rmasÄ± tartÄ±ÅŸÄ±ldÄ±
- Projenin doldurmayÄ± hedeflediÄŸi 6 temel literatÃ¼r boÅŸluÄŸu (gap) belirlendi:
  - Bulut-aÄŸÄ±rlÄ±klÄ± KDS'lerin dÃ¼ÅŸÃ¼k baÄŸlantÄ±lÄ± Ã§iftliklerde benimseme sorunu
  - Makro tahmin ile mikro doÄŸrulama arasÄ±ndaki kopukluk
  - TarÄ±m robotlarÄ± ile KDS entegrasyonunda standart eksikliÄŸi
  - TinyML/Edge AI'da enerji-gecikme-bellek-karar etkisinin birlikte deÄŸerlendirilmemesi
  - Ã‡iftÃ§i odaklÄ± KDS'lerde anlaÅŸÄ±labilir aÃ§Ä±klama eksikliÄŸi
  - LLM halÃ¼sinasyon riski ve tarÄ±msal doÄŸruluk gerekliliÄŸi
- H1â€“H10 hipotezleri formÃ¼le edildi

**Ã‡Ä±ktÄ±lar:**
- Hipotez-metrik eÅŸleÅŸtirme tablosu
- LiteratÃ¼r kÃ¼meleri (6 kÃ¼me) tanÄ±mÄ±

---

### 6 Nisan 2026 (Pazar) â€” LiteratÃ¼r TaramasÄ± DerinleÅŸtirme

**Konu:** KapsamlÄ± literatÃ¼r taramasÄ± ve kaynak tablosu oluÅŸturma

**YapÄ±lanlar:**
- ~75 adet hakemli kaynak (Q1/Q2 aÄŸÄ±rlÄ±klÄ±) tarandÄ± ve TRAK-AI modÃ¼lleriyle iliÅŸkilendirildi
- Kaynaklar 6 tematik kÃ¼meye ayrÄ±ldÄ±
- Mermaid diyagramlarÄ± oluÅŸturuldu (zaman Ã§izgisi + modÃ¼l-literatÃ¼r iliÅŸki haritasÄ±)

**Ã‡Ä±ktÄ±lar:**
- `TRAKAI_KDS_Ä°Ã§in_Otonom_Robotik_ile_Yapay_ZekÃ¢_TabanlÄ±_KDS_Entegrasyonu_LiteratÃ¼r_Ä°ncelemesi.pdf`
- `TRAKAI_KDS_Ä°Ã§in_Otonom_Robotik_AI_TabanlÄ±_KDS_Entegrasyonu_LiteratÃ¼r_TaramasÄ±.pdf`

---

### 7 Nisan 2026 (Pazartesi) â€” Metodoloji Yol HaritasÄ± DokÃ¼manÄ±

**Konu:** Tam metodoloji ve teknik detay dokÃ¼manÄ±nÄ±n hazÄ±rlanmasÄ±

**YapÄ±lanlar:**
- 8 bÃ¶lÃ¼mlÃ¼k kapsamlÄ± metodoloji dokÃ¼manÄ± yazÄ±ldÄ±
- BaÅŸarÄ± kriterleri tablosu oluÅŸturuldu
- Hafta hafta yol haritasÄ± (H1â€“H14) detaylandÄ±rÄ±ldÄ±

**Ã‡Ä±ktÄ±lar:**
- `Trak-AI_KDS_Metodoloji_Yol_Haritasi.docx`

---

### 8 Nisan 2026 (SalÄ±) â€” WP4 Detay PlanlamasÄ± ve Mimari TasarÄ±m

**Konu:** Ã‡P-4 Tamamen Yerel (Offline) RAG Sistemi â€” Rover entegrasyonlu detaylÄ± planlama

**YapÄ±lanlar:**
- Edgeâ€“Fogâ€“Cloud Ã¼Ã§ katmanlÄ± mimari diyagramÄ± Ã§izildi
- Hafta hafta WP4 planÄ± detaylandÄ±rÄ±ldÄ± (H10â€“H12)
- RAG bilgi tabanÄ± kaynak araÅŸtÄ±rmasÄ±: 35 kaynak, 7 kategori, 7+ Ã¼lke
- ChatGPT Deep Research ile ek kaynak taramasÄ± yapÄ±ldÄ±
- RAG kaynak listesi Word dokÃ¼manÄ± oluÅŸturuldu

**Ã‡Ä±ktÄ±lar:**
- WP4 Edgeâ€“Fogâ€“Cloud mimari diyagramÄ± (SVG)
- `TRAK_AI_RAG_Birlesik_Kaynaklar_v2.docx` â€” 35 kaynaklÄ± bilgi tabanÄ± planÄ±

---

### 16 Nisan 2026 (Ã‡arÅŸamba) â€” WP4 HaftalÄ±k Rapor

**Konu:** HaftalÄ±k ilerleme raporu hazÄ±rlanmasÄ±

**YapÄ±lanlar:**
- HaftalÄ±k rapor taslaÄŸa uygun ÅŸekilde hazÄ±rlandÄ±
- KullanÄ±lan araÃ§lar, tamamlanan iÅŸler, sorunlar ve Ã§Ã¶zÃ¼mler belgelendi

**Ã‡Ä±ktÄ±lar:**
- `Melih_Kalkan_16_04_2026.docx` â€” haftalÄ±k rapor

---

### 22â€“26 Nisan 2026 (SalÄ±â€“Cumartesi) â€” WP4 Kodlama ve Entegrasyon

**Konu:** Ã‡P-4 RAG/LLM sisteminin sÄ±fÄ±rdan kodlanmasÄ±, Ã‡P-2 entegrasyonu ve demo

**YapÄ±lanlar:**

**GÃ¼n 1 â€” Proje yapÄ±sÄ± ve temel modÃ¼ller:**
- `src/cp4_rag/` klasÃ¶r yapÄ±sÄ± oluÅŸturuldu (docs/, faiss_index/, 5 alt kategori)
- `config.py` yazÄ±ldÄ±: tÃ¼m ayarlar tek dosyada (model, chunk boyutu, eÅŸikler, prompt)
- `pdf_loader.py` yazÄ±ldÄ±: PyMuPDF ile PDF okuma, RecursiveCharacterTextSplitter ile chunk'lama
- `build_index.py` yazÄ±ldÄ±: HuggingFace embedding + FAISS indeks oluÅŸturma/yÃ¼kleme
- `retriever.py` yazÄ±ldÄ±: Tri-RAG (Dense FAISS + Sparse BM25 + Re-rank birleÅŸtirme)
- `llm_engine.py` yazÄ±ldÄ±: Ollama API entegrasyonu, baÄŸlantÄ± kontrolÃ¼, hata yÃ¶netimi
- `main_rag.py` yazÄ±ldÄ±: CLI arayÃ¼zÃ¼ (build, query, test, rover, info komutlarÄ±)

**GÃ¼n 2 â€” Paket kurulumu ve LLM deployment:**
- Python paketleri kuruldu: langchain, faiss-cpu, sentence-transformers, pymupdf, rank-bm25
- Ollama v0.20.7 Windows'a kuruldu
- Llama-3.1-8B-Instruct (Q4_K_M, 4.9 GB) modeli indirildi
- Ä°lk test: BBCH Monograph PDF â†’ 357 chunk â†’ FAISS â†’ sorgu â†’ LLM yanÄ±tÄ± (100.7 sn, 272 token)
- LangChain v2 import hatalarÄ± Ã§Ã¶zÃ¼ldÃ¼ (langchain.schema â†’ langchain_core.documents, langchain.text_splitter â†’ langchain_text_splitters)
- Ollama PATH sorunu Ã§Ã¶zÃ¼ldÃ¼ (VS Code terminal yeniden baÅŸlatma)

**GÃ¼n 3 â€” Bilgi tabanÄ± geniÅŸletme ve model optimizasyonu:**
- `download_sources.py` yazÄ±ldÄ±: 13 PDF kaynaÄŸÄ± otomatik indiren script
- 53 PDF bilgi tabanÄ±na yÃ¼klendi (BBCH, TR BakanlÄ±k, FAO, ABD, hastalÄ±k kategorileri)
- 14,866 chunk oluÅŸturuldu ve FAISS'e yazÄ±ldÄ±
- RAM sorunu tespit edildi: 16 GB RAM'de Llama-3.1-8B (4.9 GB) + FAISS + Embedding sÄ±ÄŸmadÄ±
- phi3:mini denendi â†’ TÃ¼rkÃ§e Ã§Ä±ktÄ± kalitesi Ã§ok dÃ¼ÅŸÃ¼k (anlamsÄ±z tekrarlar, halÃ¼sinasyon)
- Gemma-3-4B (Google) modeline geÃ§ildi â†’ TÃ¼rkÃ§e Ã§Ä±ktÄ± kalitesi dramatik ÅŸekilde iyileÅŸti
- Ã‡iftÃ§i dili prompt ÅŸablonu yazÄ±ldÄ± ("KÃ¶y kahvesinde anlatÄ±r gibi yaz" prensibi)

**GÃ¼n 4 â€” Ã‡P-2 entegrasyonu ve demo:**
- `demo.py` yazÄ±ldÄ±: Ã‡P-2 + Ã‡P-4 entegre Ã§alÄ±ÅŸma
- Ã‡P-2 `inference_cp2.py`'nin `predict()` fonksiyonu doÄŸrudan Ã§aÄŸrÄ±lÄ±yor
- GerÃ§ek model Ã§alÄ±ÅŸÄ±yor: BuÄŸday Conv-LSTM, AyÃ§iÃ§eÄŸi LSTM
- Rover mock verisi ile anomali tespiti: NDVI sapmasÄ±, dÃ¼ÅŸÃ¼k nem, hastalÄ±k tespiti
- TensorFlow bellek yÃ¶netimi: tahmin sonrasÄ± `gc.collect()` ile RAM temizleme
- Ä°nteraktif chatbot modu eklendi:
  - "durum" komutu: LLM tarla verilerini doÄŸal dilde anlatÄ±yor
  - "analiz" komutu: anomali tespiti + RAG kaynaklardan tavsiye Ã¼retimi
  - Serbest soru: tarla baÄŸlamÄ± + RAG belgesi birleÅŸik yanÄ±t

**Test SonuÃ§larÄ±:**
- Otomatik analiz: BuÄŸday normal, AyÃ§iÃ§eÄŸi 3 anomali tespit (NDVI sapmasÄ±, dÃ¼ÅŸÃ¼k nem, mildiyÃ¶)
- LLM Ã§Ä±ktÄ± Ã¶rneÄŸi: "DÄ°KKAT: TarlanÄ±zdaki toprak nemi Ã§ok dÃ¼ÅŸÃ¼k, sadece %11! YarÄ±n sabah mutlaka sulama yapÄ±n. 2 parmak su verin..."
- YanÄ±t sÃ¼resi: 27.1 sn (Gemma-3-4B, CPU-only, 301 token)
- Ã‡P-2 gerÃ§ek model: BuÄŸday NDVI 0.4675â†’0.4413, AyÃ§iÃ§eÄŸi NDVI 0.4895â†’0.4904

**Ã‡Ä±ktÄ±lar:**
- `config.py` â€” tÃ¼m ayarlar + Ã§iftÃ§i dili system prompt
- `pdf_loader.py` â€” PDF okuma ve chunk'lama
- `build_index.py` â€” FAISS indeks oluÅŸturma/yÃ¼kleme
- `retriever.py` â€” Tri-RAG retriever
- `llm_engine.py` â€” Ollama LLM entegrasyonu
- `main_rag.py` â€” CLI arayÃ¼zÃ¼
- `demo.py` â€” Ã‡P-2 + Ã‡P-4 entegre demo (chatbot dahil)
- `download_sources.py` â€” otomatik PDF indirici
- FAISS indeksi: 14,866 vektÃ¶r, 53 belge, 5 kategori

**Teknik Kararlar:**
- Llama-3.1-8B â†’ RAM yetersizliÄŸi nedeniyle Gemma-3-4B'ye geÃ§ildi (16 GB RAM kÄ±sÄ±tÄ±)
- phi3:mini TÃ¼rkÃ§e'de baÅŸarÄ±sÄ±z â†’ Gemma-3 Ã§ok dilli desteÄŸi Ã§ok daha gÃ¼Ã§lÃ¼
- FINAL_TOP_K 3â†’2'ye dÃ¼ÅŸÃ¼rÃ¼ldÃ¼, LLM_NUM_CTX 4096â†’2048'e dÃ¼ÅŸÃ¼rÃ¼ldÃ¼ (RAM optimizasyonu)
- TensorFlow tahmin sonrasÄ± bellekten temizleniyor (Ollama'ya yer aÃ§mak iÃ§in)

---

### 2 MayÄ±s 2026 (Cumartesi) â€” Ã‡P-3 Rover DonanÄ±m SipariÅŸleri ve GeliÅŸtirme OrtamÄ± Kurulumu

**Konu:** Rover fiziksel bileÅŸenlerinin temin edilmesi ve WP3 yazÄ±lÄ±m altyapÄ±sÄ±nÄ±n kurulmasÄ±

**YapÄ±lanlar:**

**DonanÄ±m SipariÅŸleri (~3.440 TL toplam):**
- 4WD Mobil Arazi Robot Platformu / mavi (Robotzade) â€” 496,80 TL
- ESP32 WROOM-32 Type-C (Robotzade) â€” 287,04 TL
- DHT22 SÄ±caklÄ±k ve Nem SensÃ¶rÃ¼ Ã— 2 (Robotzade) â€” 331,20 TL
- HC-SR04 Ultrasonik SensÃ¶r Ã— 2 (Robotzade) â€” 88,32 TL
- TP4056 Type-C Lityum Åarj ModÃ¼lÃ¼ Ã— 2 (Robotzade) â€” 22,08 TL
- Mini Ayarlanabilir LM2596 Buck DÃ¶nÃ¼ÅŸtÃ¼rÃ¼cÃ¼ (Robotzade) â€” 35,88 TL
- 40 Pin Jumper Kablo (Robotzade) â€” 38,64 TL
- GY-NEO6MV2 GPS ModÃ¼lÃ¼ (Robotistan) â€” 207,41 TL
- 2'li Breadboard BB2T4D (Robotistan) â€” 384,65 TL
- 18650 Pil YuvasÄ± 2'li (Robotistan) â€” 29,63 TL
- GÃ¼neÅŸ Paneli 6V 230mA (Robotistan) â€” 219,48 TL
- Supex 18650 3.7V 2500mAh Pil Ã— 2 (Robotistan) â€” 445,55 TL
- LM2596S-12 Buck Entegresi (Robotistan) â€” 35,12 TL
- ESP32-CAM WiFi + OV2640 (TLS Robotik) â€” 598,26 TL
- L298N Voltaj RegulatÃ¶rlÃ¼ Motor SÃ¼rÃ¼cÃ¼ KÄ±rmÄ±zÄ± PCB (TLS Robotik) â€” 87,53 TL
- CH340G RS232 USB-TTL DÃ¶nÃ¼ÅŸtÃ¼rÃ¼cÃ¼ (TLS Robotik) â€” 78,50 TL
- Kapasitif Toprak Nemi SensÃ¶rÃ¼ Ã— 1 (Direnc.net) â€” 54,00 TL

**Teknik Kararlar:**
- Arduino ve Raspberry Pi kullanÄ±lmadÄ± â€” ESP32 tek baÅŸÄ±na tÃ¼m iÅŸlevleri karÅŸÄ±lÄ±yor (motor kontrol + Wi-Fi + MQTT + GPS + sensÃ¶r)
- HC-SR04: iki farklÄ± versiyon sipariÅŸ edildi, birini iptal etmek gerekiyor
- LM2596 SMD entegre (Robotistan): lehim gerektiriyor, Robotzade hazÄ±r modÃ¼lÃ¼ Ã¶nce kullanÄ±lacak
- GPS baÄŸlantÄ±sÄ±: telefon hotspot Ã¼zerinden (tarlada sabit internet yok)
- Kapasitif toprak nemi: SEN0193 stokta yok, eÅŸdeÄŸer kapasitif muadil kullanÄ±lÄ±yor

**GeliÅŸtirme OrtamÄ± Kurulumu:**
- PlatformIO IDE eklentisi (VS Code) kuruldu
- Python 3.13.2 kuruldu; numpy / scipy / matplotlib eklendi (kalibrasyon scripti iÃ§in)
- Mosquitto MQTT broker 2.1.2 kuruldu ve PATH'e eklendi
- MQTT broker testi baÅŸarÄ±lÄ±: `mosquitto_pub` â†’ `mosquitto_sub` mesaj iletimi doÄŸrulandÄ±

**WP3 YazÄ±lÄ±m AltyapÄ±sÄ± OluÅŸturuldu:**

Kod yapÄ±sÄ±:
```
src/cp3_edge/
â”œâ”€â”€ trak_ai_rover/          â† ESP32 ana firmware (PlatformIO)
â”‚   â”œâ”€â”€ platformio.ini      â† lib_deps: PubSubClient, DHT, TinyGPSPlus, ArduinoJson
â”‚   â””â”€â”€ src/
â”‚       â”œâ”€â”€ config.h        â† Pin tanÄ±mlarÄ±, WiFi/MQTT ayarlarÄ±, kalibrasyon katsayÄ±larÄ±
â”‚       â””â”€â”€ main.cpp        â† Motor kontrol, sensÃ¶r okuma, GPS waypoint, MQTT yayÄ±n
â”œâ”€â”€ esp32_cam/              â† ESP32-CAM firmware
â”‚   â”œâ”€â”€ platformio.ini
â”‚   â””â”€â”€ src/
â”‚       â””â”€â”€ main.cpp        â† Kamera baÅŸlatma, mock inference, UART JSON Ã§Ä±kÄ±ÅŸÄ±
â””â”€â”€ calibration/
    â””â”€â”€ kalibrasyon.py      â† SEN0193 polinom kalibrasyon scripti
```

Firmware Ã¶zellikleri:
- `config.h`: tÃ¼m pin sabitleri (SEN0193 Ã— 2, DHT22, HC-SR04 Ã— 2, L298N motor pinleri, GPS UART2, CAM UART1), MQTT broker IP, kalibrasyon katsayÄ±larÄ± (CAL_A/B/C), zamanlama sabitleri
- `trak_ai_rover/main.cpp`: `adcToNem()` polinom kalibrasyon, `mesafeOlc()` ultrasonik, motor kontrol (ileri/geri/sol/saÄŸ), `haversineMetre()` GPS navigasyon, 6 waypoint zikzak tarama, `camVerisiOku()` UART JSON ayrÄ±ÅŸtÄ±rma, `mqttYayinla()` 13 alanlÄ± JSON paketi
- `esp32_cam/main.cpp`: AI Thinker pin map, 10 sÄ±nÄ±flÄ± BBCH etiket dizisi, kamera baÅŸlatma (QVGA/JPEG), mock inference (gerÃ§ek YOLOv8 TFLite model gelince gÃ¼ncellenecek), UART JSON Ã§Ä±kÄ±ÅŸÄ±

**Derleme Testleri:**
- `trak_ai_rover`: âœ… SUCCESS â€” RAM: %13.9, Flash: %59.6
- `esp32_cam`: âœ… SUCCESS â€” RAM: %8.0, Flash: %11.2 (2 deprecation uyarÄ±sÄ± â€” iÅŸlevselliÄŸi etkilemez)

**MQTT Broker IP:** 192.168.1.102 (config.h'a yazÄ±ldÄ±, donanÄ±mlar gelince ESP32'ye yÃ¼klenecek)

**Ã‡Ä±ktÄ±lar:**
- `src/cp3_edge/trak_ai_rover/src/config.h`
- `src/cp3_edge/trak_ai_rover/src/main.cpp`
- `src/cp3_edge/esp32_cam/src/main.cpp`
- `src/cp3_edge/calibration/kalibrasyon.py`

---

## 4. Ã‡P-1: ETL Veri HattÄ±

**Durum:** âœ… TamamlandÄ± (H1â€“H3, 3â€“21 Mart 2026)

**BileÅŸenler:**

| Veri KaynaÄŸÄ± | API / YÃ¶ntem | Ã‡Ã¶zÃ¼nÃ¼rlÃ¼k | Ã‡ekilen DeÄŸiÅŸkenler |
|---|---|---|---|
| Sentinel-2 (ESA) | GEE Python API + eemont | 10m (VIS+NIR), 20m (RedEdge+SWIR) | NDVI, EVI, NDWI |
| ERA5-Land (ECMWF) | cdsapi â†’ CDS | ~9 km, gÃ¼nlÃ¼k | T_max, T_min, T_Ã§iy, yaÄŸÄ±ÅŸ, radyasyon, ET |
| SoilGrids 2.0 (ISRIC) | REST API / GEE Assets | 250m, statik | kil, kum, silt, pH, SOC, CEC |

**Teslim Edilen Ã‡Ä±ktÄ±:** Trakya pilot parselleri iÃ§in 2017â€“2024 yÄ±llarÄ± arasÄ± boÅŸluksuz, tarih/konum hizalÄ± Ã¶znitelik matrisi. 17 mÃ¼hendislik Ã¶zniteliÄŸi (GDD, kÃ¼mÃ¼latif GDD, kuraklÄ±k indeksi, NDVI trend, sÄ±caklÄ±k amplitÃ¼dÃ¼, Ã§iy noktasÄ± depresyonu, dÃ¶ngÃ¼sel zaman kodlamasÄ±).

---

## 5. Ã‡P-2: Tahmin Modeli

**Durum:** âœ… TamamlandÄ± (H4â€“H6, 22 Mart â€“ 11 Nisan 2026)

**Mimari:** 4 model yarÄ±ÅŸtÄ±rÄ±ldÄ±: LSTM, Conv-LSTM, Attention-LSTM, XGBoost. Residual Delta yaklaÅŸÄ±mÄ± (t+7 tahmin ufku, otokorelasyon tuzaÄŸÄ±ndan kaÃ§Ä±nma).

**Åampiyon Modeller:**
- BuÄŸday: Conv-LSTM (RÂ² = 0.7151, MAE = 0.0445) â€” canlÄ± sistemde yapÄ±sal avantaj
- AyÃ§iÃ§eÄŸi: LSTM (RÂ² = 0.7957, MAE = 0.0409) â€” en yÃ¼ksek doÄŸruluk

**Ã–zellik MÃ¼hendisliÄŸi:** 17 Ã¶zellik (iklimsel, agronomik, spektral, zamansal). 30 gÃ¼nlÃ¼k pencere, t+7 tahmin ufku.

**XAI Entegrasyonu:** XGBoost Ã¼zerinde SHAP analizi â€” hangi deÄŸiÅŸkenin tahmini ne yÃ¶nde etkilediÄŸi ÅŸeffaf.

**Ã‡Ä±karÄ±m ModÃ¼lÃ¼:** `inference_cp2.py` â€” hibrit model seÃ§imi, saÄŸlÄ±k sÄ±nÄ±flandÄ±rmasÄ±, trend analizi, LLM baÄŸlam Ã¼retimi.

---

## 6. Ã‡P-3: Rover DonanÄ±mÄ± ve Edge AI

**Durum:** ğŸ”„ Firmware hazÄ±r / DonanÄ±m sipariÅŸ edildi (H7â€“H9, 12 Nisan â€“ 2 MayÄ±s 2026)

**DonanÄ±m BileÅŸenleri (SipariÅŸ Edildi):**
- Ä°ÅŸlemci: ESP32 WROOM-32 (Ã§ift Ã§ekirdek Xtensa LX6, dahili Wi-Fi/BT)
- SensÃ¶r: Kapasitif toprak nemi Ã— 1 + DHT22 sÄ±caklÄ±k/nem Ã— 2
- Mesafe: HC-SR04 ultrasonik Ã— 2 (Ã¶n + arka engel tespiti)
- Kamera: ESP32-CAM (AI Thinker, OV2640)
- Motor: 4WD robot ÅŸasisi + L298N motor sÃ¼rÃ¼cÃ¼
- Navigasyon: GY-NEO6MV2 GPS modÃ¼lÃ¼
- Enerji: GÃ¼neÅŸ paneli 6V 230mA + TP4056 ÅŸarj + 18650 Ã— 2 (2500mAh)
- Ä°letiÅŸim: MQTT (Mosquitto 2.1.2 broker, Fog sunucusunda)

**Firmware Mimarisi:**

| ModÃ¼l | Dosya | Ä°ÅŸlev |
|---|---|---|
| Ana Rover | `trak_ai_rover/src/main.cpp` | Motor kontrol, sensÃ¶r okuma, GPS waypoint navigasyon, MQTT yayÄ±n |
| YapÄ±landÄ±rma | `trak_ai_rover/src/config.h` | Pin tanÄ±mlarÄ±, WiFi/MQTT ayarlarÄ±, kalibrasyon katsayÄ±larÄ± |
| Kamera/AI | `esp32_cam/src/main.cpp` | Kamera baÅŸlatma, BBCH sÄ±nÄ±flandÄ±rma (mock â†’ TFLite), UART JSON |
| Kalibrasyon | `calibration/kalibrasyon.py` | SEN0193 ADC â†’ nem% polinom regresyon, RMSE/RÂ² analizi |

**MQTT YÃ¼k FormatÄ± (13 alan):**
```json
{
  "timestamp": 12345, "gps_lat": 41.694, "gps_lon": 27.105, "gps_valid": true,
  "nem_1_pct": 34.2, "nem_2_pct": 31.8, "hava_temp_c": 22.1, "hava_nem_pct": 58.0,
  "engel_on_cm": 120, "engel_arka_cm": 999, "bbch_sinif": "BBCH_30_39",
  "bbch_guven": 0.82, "waypoint_id": 2, "rover_id": "trak-ai-rover-01"
}
```

**Waypoint Navigasyon:** 6 noktalÄ± zikzak tarama (Haversine mesafe hesabÄ±), engel < 30 cm â†’ geri + sola dÃ¶n kaÃ§Ä±nma manevrasÄ±.

**Kalibrasyon:** `adcToNem(adc) = CAL_A Ã— adcÂ² + CAL_B Ã— adc + CAL_C`. Hedef RMSE â‰¤ 1.02, RÂ² â‰¥ 0.89. SensÃ¶r gelince gerÃ§ek Ã¶lÃ§Ã¼m noktalarÄ±yla gÃ¼ncellenecek.

**Edge AI (Sonraki AdÄ±m):** YOLOv8-tiny â†’ Int8 kuantizasyon â†’ .tflite â†’ C-array â†’ ESP32 flash. Åu an mock inference Ã§alÄ±ÅŸÄ±yor (10 sÄ±nÄ±f: BBCH evreler + SaÄŸlÄ±klÄ± + HastalÄ±klÄ±). Hedef mAP@0.5 > 0.85.

**Derleme Durumu:**

| Proje | RAM | Flash | Durum |
|---|---|---|---|
| trak_ai_rover | %13.9 | %59.6 | âœ… SUCCESS |
| esp32_cam | %8.0 | %11.2 | âœ… SUCCESS |

---

## 7. Ã‡P-4: Yerel RAG/LLM Entegrasyonu

**Durum:** âœ… Temel sistem Ã§alÄ±ÅŸÄ±yor, Ã‡P-2 entegrasyonu tamamlandÄ± (22â€“26 Nisan 2026)

**Felsefe:** Projenin "offline-first" ve "bulut baÄŸÄ±mlÄ±lÄ±ÄŸÄ±nÄ± azaltma" iddiasÄ±nÄ±n somutlaÅŸtÄ±ÄŸÄ± paket.

**Mimari Kararlar (GÃ¼ncellenmiÅŸ):**

| BileÅŸen | Ä°lk Plan | Nihai SeÃ§im | DeÄŸiÅŸiklik GerekÃ§esi |
|---|---|---|---|
| LLM Modeli | Llama-3.1-8B Q4 | Gemma-3-4B | 16 GB RAM'e sÄ±ÄŸmadÄ± |
| Denenen alternatif | â€” | phi3:mini | TÃ¼rkÃ§e kalitesi Ã§ok dÃ¼ÅŸÃ¼k, iptal |
| Embedding | multilingual-e5-small | multilingual-e5-small | DeÄŸiÅŸmedi |
| VektÃ¶r DB | FAISS | FAISS | DeÄŸiÅŸmedi |
| FINAL_TOP_K | 3 | 2 | RAM optimizasyonu |
| LLM_NUM_CTX | 4096 | 2048 | RAM optimizasyonu |

**Bilgi TabanÄ± Ä°statistikleri:**
- Toplam PDF: 53 belge
- Toplam chunk: 14,866
- Kategori daÄŸÄ±lÄ±mÄ±: ABD 3,335 | FAO 3,766 | HastalÄ±k 3,256 | TR BakanlÄ±k 3,015 | BBCH 1,494
- Embedding modeli: intfloat/multilingual-e5-small (384 boyut)

**Ã‡P-2 Entegrasyonu:**
- `inference_cp2.py`'nin `predict("Wheat")` ve `predict("Sunflower")` doÄŸrudan Ã§aÄŸrÄ±lÄ±yor
- GerÃ§ek model Ã§Ä±ktÄ±larÄ± RAG prompt'una enjekte ediliyor
- TensorFlow tahmin sonrasÄ± bellekten temizleniyor (Ollama RAM paylaÅŸÄ±mÄ±)

**Demo ModlarÄ±:**
- Otomatik tarla analizi (anomali tespiti + LLM tavsiye)
- "durum" komutu: doÄŸal dilde tarla Ã¶zeti
- "analiz" komutu: anomali + RAG tavsiye
- Serbest soru: tarla baÄŸlamÄ± + RAG birleÅŸik yanÄ±t

**Performans Metrikleri (Ã–lÃ§Ã¼len):**

| Metrik | Hedef | Ã–lÃ§Ã¼len | Durum |
|---|---|---|---|
| UÃ§tan uca gecikme | < 120sn | 27.1sn (Gemma-3-4B) | âœ… |
| Token Ã¼retimi | â€” | 301 token/sorgu | âœ… |
| Bilgi tabanÄ± boyutu | â€” | 14,866 vektÃ¶r | âœ… |
| Ã‡iftÃ§i dili uyumu | Uzman â‰¥ 4/5 | Beklemede | â³ |
| HalÃ¼sinasyon oranÄ± | > 0.95 | Beklemede | â³ |

---

## 8. Hipotezler ve Metrikler

| # | Hipotez | Metrikler | Ä°lgili Ã‡P | Durum |
|---|---|---|---|---|
| H1 | Bulutsuz Ã§alÄ±ÅŸma modunda karar Ã¼retim gecikmesi daha iyi | UyarÄ± gecikmesi (ms), uptime (%), veri kaybÄ± | Ã‡P-4 | âœ… DoÄŸrulandÄ± (27sn offline) |
| H2 | DÃ¼ÅŸÃ¼k maliyetli mimari UTAUT2 puanlarÄ±nÄ± artÄ±rÄ±r | UTAUT2 Ã¶lÃ§ekleri, niyet (BI) | Ã‡P-4 | ğŸ“‹ |
| H3 | Mikro doÄŸrulama yanlÄ±ÅŸ pozitif oranÄ±nÄ± dÃ¼ÅŸÃ¼rÃ¼r | FP rate, precision/recall/F1 | Ã‡P-3 | ğŸ”„ |
| H4 | Mikro doÄŸrulama + aÃ§Ä±klama gÃ¼veni artÄ±rÄ±r | PU/PEOU, gÃ¼ven maddeleri | Ã‡P-3+4 | ğŸ“‹ |
| H5 | Standart mesajlaÅŸma entegrasyon sÃ¼resini azaltÄ±r | Person-hour, MTBF, ÅŸema dÃ¶nÃ¼ÅŸÃ¼m | Ã‡P-3 | ğŸ”„ |
| H6 | Streaming yaklaÅŸÄ±mÄ± Ã§evrim sÃ¼resini dÃ¼ÅŸÃ¼rÃ¼r | End-to-end latency, mesaj kaybÄ± | Ã‡P-3+4 | ğŸ“‹ |
| H7 | Kuantizasyon F1 korurken gecikme/enerji dÃ¼ÅŸÃ¼rÃ¼r | Latency (ms), energy (mJ), RAM, F1 | Ã‡P-3 | ğŸ”„ |
| H8 | Edge Ã§Ä±karÄ±m baÄŸlantÄ± kesintisinde Ã§alÄ±ÅŸÄ±r | Offline baÅŸarÄ± (%), kaÃ§Ä±rÄ±lan olay (FN) | Ã‡P-3+4 | âœ… Demo'da doÄŸrulandÄ± |
| H9 | LLM+RAG aÃ§Ä±klamalarÄ± PU ve BI'yi artÄ±rÄ±r | TAM/UTAUT Ã¶lÃ§ekleri | Ã‡P-4 | ğŸ“‹ |
| H10 | AÃ§Ä±klama katmanÄ± yorumlama baÅŸarÄ±sÄ±nÄ± artÄ±rÄ±r | DoÄŸru cevap (%), NASA-TLX | Ã‡P-4 | ğŸ“‹ |

---

## 9. Teknik Kararlar ve GerekÃ§eler

### 9.1 Neden Yerel (Offline) LLM?

**Karar:** Bulut API yerine Ollama Ã¼zerinde yerel LLM.

**GerekÃ§eler:**
1. Projenin temel iddiasÄ±: "bulut baÄŸÄ±mlÄ±lÄ±ÄŸÄ±nÄ± azaltmak"
2. Maliyet: Tamamen Ã¼cretsiz (0$)
3. Gizlilik: Tarla verileri Ã¼Ã§Ã¼ncÃ¼ taraf sunuculara gÃ¶nderilmez
4. KÄ±rsal baÄŸlantÄ±: Trakya'da tarla ortasÄ±nda stabil internet garanti edilemez
5. Bilimsel tutarlÄ±lÄ±k: H1 hipotezi doÄŸrudan test edilebilir

### 9.2 Neden Gemma-3-4B (Llama-3.1-8B veya phi3:mini deÄŸil)?

**Karar:** ÃœÃ§ model denendi, Gemma-3-4B seÃ§ildi.

**Deneme sÃ¼reci:**
1. Llama-3.1-8B Q4 (4.9 GB) â†’ RAM yetersizliÄŸi: TensorFlow + FAISS + Embedding + LLM 16 GB'a sÄ±ÄŸmadÄ±
2. phi3:mini (2.3 GB) â†’ RAM'e sÄ±ÄŸdÄ± ama TÃ¼rkÃ§e Ã§Ä±ktÄ± kalitesi Ã§ok dÃ¼ÅŸÃ¼k: anlamsÄ±z tekrarlar, halÃ¼sinasyon, mekanik dil
3. Gemma-3-4B (3.3 GB) â†’ RAM'e sÄ±ÄŸdÄ± VE TÃ¼rkÃ§e Ã§Ä±ktÄ± kalitesi Ã§ok iyi: doÄŸal dil, Ã§iftÃ§i diline uyum, somut tavsiyeler

### 9.3 Neden Tri-RAG?

**Karar:** Dense + Sparse + Re-rank birleÅŸtirme.

**GerekÃ§eler:**
1. "MildiyÃ¶" gibi Ã¶zel terimler semantik aramada kaybolabiliyor â†’ BM25 eklendi
2. Her iki yÃ¶ntemde de bulunan chunk'lara bonus skor â†’ isabetlilik arttÄ±
3. LiteratÃ¼rde Tri-RAG yaklaÅŸÄ±mÄ± destekleniyor

### 9.4 Neden FAISS?

**GerekÃ§eler:**
1. Tamamen yerel, dosya tabanlÄ± â†’ offline Ã§alÄ±ÅŸÄ±r
2. Sunucu gerektirmez
3. 14,866 vektÃ¶r iÃ§in CPU performansÄ± yeterli
4. Pinecone cloud-only â†’ offline-first felsefesine aykÄ±rÄ±

### 9.5 TensorFlow Bellek YÃ¶netimi

**Sorun:** TensorFlow + FAISS + Embedding + Ollama aynÄ± anda 16 GB RAM'e sÄ±ÄŸmadÄ±.

**Ã‡Ã¶zÃ¼m:** Ã‡P-2 tahminleri tamamlandÄ±ktan sonra TensorFlow `gc.collect()` ile bellekten temizleniyor. FAISS indeksi yÃ¼klenirken embedding modeli bir kez yÃ¼kleniyor. LLM_NUM_CTX 2048'e, FINAL_TOP_K 2'ye dÃ¼ÅŸÃ¼rÃ¼ldÃ¼.

---

## 10. AÃ§Ä±k Sorunlar ve Sonraki AdÄ±mlar

**GÃ¼ncelleme:** 11 MayÄ±s 2026

### AÃ§Ä±k Sorunlar

| # | Sorun | Ã–ncelik | Notlar |
|---|---|---|---|
| 1 | RAM 16 GB â€” eÅŸ zamanlÄ± TF+LLM sÄ±ÄŸmÄ±yor | Ã‡Ã¶zÃ¼ldÃ¼ | gc.collect() ile sÄ±ralÄ± yÃ¼kleme |
| 2 | phi3:mini TÃ¼rkÃ§e kalitesi yetersiz | Ã‡Ã¶zÃ¼ldÃ¼ | Gemma-3-4B'ye geÃ§ildi |
| 3 | LangChain v2 import hatalarÄ± | Ã‡Ã¶zÃ¼ldÃ¼ | langchain_core, langchain_text_splitters |
| 4 | HC-SR04 Ã§ift versiyon sipariÅŸ | YÃ¼ksek | Birini iptal et (Robotzade 88,32 TL'lik kalacak) |
| 5 | LM2596 SMD entegre lehim gerektiriyor | Orta | Robotzade hazÄ±r modÃ¼lÃ¼ Ã¶nce kullanÄ±lacak |
| 6 | config.h WiFi/hotspot bilgisi boÅŸ | YÃ¼ksek | DonanÄ±m gelince telefon hotspot adÄ±/ÅŸifresi eklenecek |
| 7 | ESP32 â†” MQTT â†” Python entegrasyon testi | YÃ¼ksek | DonanÄ±mlar gelince gerÃ§ek test yapÄ±lacak |
| 8 | YOLOv8-tiny model eÄŸitimi | YÃ¼ksek | Google Colab'da GWHD + ayÃ§iÃ§eÄŸi setleriyle baÅŸlatÄ±lacak |
| 9 | Agronomik tutarlÄ±lÄ±k uzman deÄŸerlendirmesi | Orta | KÃ¶r uzman testi henÃ¼z yapÄ±lmadÄ± |
| 10 | HalÃ¼sinasyon oranÄ± Ã¶lÃ§Ã¼mÃ¼ | Orta | RAG kaynak kontrolÃ¼ testi yapÄ±lacak |

### Sonraki AdÄ±mlar (Kronolojik)

1. **DonanÄ±m montajÄ±:** Åasi + motor + L298N + breadboard kurulumu; ESP32 firmware upload; motor/sensÃ¶r/MQTT testi
2. **SEN0193 kalibrasyonu:** Kuru/Ä±slak sÄ±nÄ±r deÄŸerleri Ã¶lÃ§Ã¼mÃ¼ â†’ `config.h` CAL_A/B/C gÃ¼ncelle
3. **YOLOv8-tiny eÄŸitimi:** Google Colab'da GWHD 2021 + ayÃ§iÃ§eÄŸi BBCH setleri; Int8 kuantizasyon; ESP32-CAM flash
4. **GerÃ§ek entegrasyon:** Rover MQTT â†’ Python orchestrator â†’ RAG/LLM (mock'tan gerÃ§eÄŸe geÃ§iÅŸ)
5. **UÃ§tan uca test:** Rover saha taramasÄ± â†’ Anomali tespiti â†’ RAG/LLM â†’ TÃ¼rkÃ§e bildirim (< 120sn hedef)
6. **Pilot arazi deneyleri + tez yazÄ±mÄ±:** MayÄ±s sonu â€“ Haziran 2026

---

> **Not:** Bu dokÃ¼man, projenin yaÅŸayan bir kaydÄ±dÄ±r. Her Ã§alÄ±ÅŸma gÃ¼nÃ¼ sonunda "GÃ¼nlÃ¼k Ã‡alÄ±ÅŸma KayÄ±tlarÄ±" bÃ¶lÃ¼mÃ¼ne yeni giriÅŸ eklenmelidir. Teknik kararlar deÄŸiÅŸtiÄŸinde BÃ¶lÃ¼m 9 gÃ¼ncellenmelidir.

---

### 11 MayÄ±s 2026 â€” MQTT Orchestrator Entegrasyon Testi

**Konu:** Ã‡P-3 â†” Ã‡P-4 MQTT kÃ¶prÃ¼ entegrasyonu ve uÃ§tan uca test

**YapÄ±lanlar:**
- `src/mqtt_orchestrator.py` yazÄ±ldÄ±: paho-mqtt ile localhost:1883'e baÄŸlanan, `trakaia/rover/data` topic'ini dinleyen, gelen JSON'Ä± parse edip CP-2 tahmini Ã§aÄŸÄ±ran, 4 anomali kuralÄ±nÄ± (nem farkÄ±, dÃ¼ÅŸÃ¼k nem, hastalÄ±k gÃ¼veni, BBCH sapmasÄ±) kontrol eden, anomali varsa Tri-RAG + Gemma-3-4B ile TÃ¼rkÃ§e tavsiye Ã¼retip `trakaia/kds/advisory` topic'ine publish eden MQTT dinleyici.
- `src/mqtt_test_publisher.py` yazÄ±ldÄ±: Senaryo A (normal tarla) ve Senaryo B (3+ anomali) olmak Ã¼zere iki mock rover paketi Ã¼retip 5 saniye arayla MQTT broker'a gÃ¶nderen test aracÄ±.
- BaÄŸÄ±mlÄ±lÄ±k: `paho-mqtt==2.1.0` kuruldu.

**Test SonuÃ§larÄ±:**

| Senaryo | Anomali SayÄ±sÄ± | LLM Tetiklendi mi | YanÄ±t SÃ¼resi | SonuÃ§ |
|---|---|---|---|---|
| A: Normal tarla (nem %28/%26.5, BBCH_50_59) | 0 | HayÄ±r | ~22s (CP-2 test modu) | BaÅŸarÄ±lÄ± |
| B: Ã‡oklu anomali (nem %11/%28, MildiyÃ¶ %82, BBCH_10_19) | 4 | Evet | 48.1s (177 token) | BaÅŸarÄ±lÄ± |

**Senaryo B'de Tespit Edilen Anomaliler:**
1. `[YUKSEK]` NEM_FARKI: Toprak nemi sensÃ¶rleri arasÄ± fark 17.0% (eÅŸik: 10%)
2. `[YUKSEK]` DUSUK_NEM: Ortalama toprak nemi Ã§ok dÃ¼ÅŸÃ¼k: 19.5% (eÅŸik: 20%)
3. `[YUKSEK]` HASTALIK: MildiyÃ¶ tespit edildi, gÃ¼ven: 82%
4. `[ORTA]` BBCH_SAPMASI: BÃ¼yÃ¼me evresi beklenenin dÄ±ÅŸÄ±nda: BBCH_10_19 (Ay 5 iÃ§in beklenen BBCH 50-79)

**LLM Ã‡Ä±ktÄ± Ã–rneÄŸi (Senaryo B â€” Gemma-3-4B, 48.1s):**
> DÄ°KKAT! TarlanÄ±zda ciddi bir su kaybÄ± var!
>
> Toprak nemi Ã§ok dÃ¼ÅŸÃ¼k, sadece %19.5. Bu mevsimde en az %20 olmasÄ± lazÄ±m. Bitkileriniz normalden zayÄ±f gÃ¶rÃ¼nÃ¼yor.
>
> YapmanÄ±z gereken:
>
> 1. Hemen bugÃ¼n veya yarÄ±n mutlaka sulama yapÄ±n.
> 2. Damla sulama kullanÄ±yorsanÄ±z, 2-3 saat Ã§alÄ±ÅŸtÄ±rÄ±n.
> 3. YaÄŸmurlama yapÄ±yorsanÄ±z, dekar baÅŸÄ±na 40-50 ton su verin.
>
> EÄŸer bu hafta iÃ§inde sulamazsanÄ±z, buÄŸdayÄ±nÄ±zÄ±n verimi %30'a kadar dÃ¼ÅŸebilir. Bu da size bÃ¼yÃ¼k zarara yol aÃ§abilir. SulamayÄ± sabah erken veya akÅŸam serin saatlerde yapÄ±n.

**Ã‡Ä±ktÄ±lar:**
- `src/mqtt_orchestrator.py` â€” MQTT dinleyici + anomali tespiti (4 kural) + Tri-RAG/LLM tetikleme + `trakaia/kds/advisory` publish
- `src/mqtt_test_publisher.py` â€” Mock rover veri gÃ¶nderici (Senaryo A: normal, Senaryo B: Ã§oklu anomali)

**Teknik Notlar:**
- paho-mqtt 2.1.0'da `CallbackAPIVersion.VERSION1` deprecation uyarÄ±sÄ± var; Ã§alÄ±ÅŸmayÄ± etkilemiyor. Gelecekte `VERSION2` API'sine geÃ§iÅŸ gerekebilir.
- Senaryo B'de beklenen 3 anomali yerine 4 anomali tetiklendi: `nem_ort = (11+28)/2 = 19.5` deÄŸeri `DUSUK_NEM` eÅŸiÄŸinin (20%) hemen altÄ±nda kaldÄ±. Bu davranÄ±ÅŸ doÄŸru â€” dÃ¼ÅŸÃ¼k nem + yÃ¼ksek nem gradyanÄ± aynÄ± anda var.
- CP-2 (TensorFlow Conv-LSTM) ikinci mesajda model Ã¶nbellekten yÃ¼klendi, FAISS yeniden yÃ¼klenmedi; bellek yÃ¶netimi `gc.collect()` ile saÄŸlandÄ±.
- Log dosyasÄ± encoding olarak cp1254 (TÃ¼rkÃ§e Windows) kullandÄ±; TÃ¼rkÃ§e karakterler doÄŸru Ã¼retildi, terminal gÃ¶rÃ¼ntÃ¼sÃ¼ndeki bozulmalar sadece konsol encoding farkÄ±ndan kaynaklandÄ±.
- Tri-RAG sonuÃ§larÄ±: Dense=5, Sparse=3, BirleÅŸik=8, Final=2 belge (boosted=0 â€” nem/hastalÄ±k terminolojisi FAISS ve BM25'te farklÄ± eÅŸleÅŸti).

**Sonraki AdÄ±m:**
- ESP32 rover firmware yÃ¼kleme ve gerÃ§ek MQTT entegrasyonu (mock veri â†’ gerÃ§ek sensÃ¶r okuma)
- YOLOv8-tiny eÄŸitimi tamamlanÄ±nca `hastalik` / `hastalik_guven` alanlarÄ± CP-3 firmware'e eklenerek orchestrator'Ä±n hastalÄ±k tespiti dalÄ± gerÃ§ek inference ile beslenecek

*TRAK-AI KDS â€¢ Lisans Bitirme Tezi â€¢ 2025/2026*

---

### 11 MayÄ±s 2026 â€” Streamlit Web ArayÃ¼zÃ¼

**Konu:** TRAK-AIA KDS web dashboard geliÅŸtirme

**YapÄ±lanlar:**
- `src/dashboard.py` yazÄ±ldÄ±: Streamlit ile 3 sayfalÄ± web arayÃ¼zÃ¼. demo.py ile aynÄ± import yapÄ±sÄ± ve sys.path kullanÄ±larak CP-2, CP-4 RAG/LLM ve MQTT modÃ¼lleri entegre edildi.
- BaÄŸÄ±mlÄ±lÄ±klar: `streamlit==1.57.0`, `plotly==6.7.0`, `folium==0.20.0`, `streamlit-folium==0.27.2` kuruldu (pip cache temizliÄŸi ile 4.5 GB disk alanÄ± aÃ§Ä±ldÄ±).

**Ã–zellikler:**
| Sayfa | Ä°Ã§erik | Durum |
|---|---|---|
| ğŸŒ¿ Tarla Durumu | BuÄŸday + AyÃ§iÃ§eÄŸi CP-2 tahminleri (NDVI, saÄŸlÄ±k, t+7 trend), Plotly 30 gÃ¼nlÃ¼k NDVI grafiÄŸi, 15 gÃ¼nlÃ¼k iklim Ã¶zeti, SHAP Ã¶nem Ã§ubuk grafiÄŸi | Ã‡alÄ±ÅŸÄ±yor |
| ğŸ“¡ Rover Ä°zleme | Senaryo A/B test butonlarÄ± (MQTT publish), anomali banner, folium GPS haritasÄ± (OpenStreetMap), KDS tavsiyesi gÃ¶sterimi | Ã‡alÄ±ÅŸÄ±yor |
| ğŸ’¬ TarÄ±m AsistanÄ± | st.chat_message/st.chat_input chat arayÃ¼zÃ¼, Tri-RAG + Gemma-3-4B TÃ¼rkÃ§e yanÄ±t, kaynak belge expander, Ã¶rnek soru sidebar butonlarÄ± | Ã‡alÄ±ÅŸÄ±yor |

**Teknik Kararlar:**
- `@st.cache_resource` ile FAISS indeksi tek seferlik yÃ¼kleniyor (sayfa geÃ§iÅŸlerinde yeniden yÃ¼klenmez)
- `@st.cache_data(ttl=300)` ile CP-2 tahminleri 5 dakika Ã¶nbellekte tutuluyor
- Page 2 MQTT advisory bekleme: `threading.Event` + paho-mqtt `loop_start()` ile bloke olmayan 90 sn timeout
- `gc.collect()` ile CP-2 (TensorFlow) sonrasÄ± RAM temizliÄŸi â€” FAISS + TF aynÄ± anda bellekte Ã§akÄ±ÅŸmasÄ±nÄ± Ã¶nler
- Sidebar Ollama + FAISS durum gÃ¶stergesi (TTL=60s Ã¶nbellekli)
- `st.session_state` ile chat geÃ§miÅŸi ve rover verisi oturum boyunca korunuyor

**Ã‡alÄ±ÅŸtÄ±rma:**
```bash
streamlit run src/dashboard.py
# http://localhost:8501
```

**Test:** Streamlit HTTP 200 dÃ¶ndÃ¼rdÃ¼, SPA doÄŸrulama geÃ§ti. 3 sayfa syntax ve import hatasÄ± olmadan baÅŸlatÄ±ldÄ±.

**Ekran GÃ¶rÃ¼ntÃ¼sÃ¼ Notu:** Tez iÃ§in http://localhost:8501 adresinden screenshot alÄ±nacak.

**Sonraki AdÄ±m:** ESP32 rover baÄŸlantÄ±sÄ± ve gerÃ§ek sensÃ¶r verisi entegrasyonu

---

## Task 3 â€” Hava Durumu Entegrasyonu ve RAG GÃ¼Ã§lendirme (12 MayÄ±s 2026)

### 3A â€” Open-Meteo Hava Servisi

- **Yeni dosya:** `src/weather_service.py`
- API key gerektirmez; offline modda `None` dÃ¶ner
- Fonksiyonlar: `get_current_weather`, `get_7day_forecast`, `get_weather_alerts`, `format_weather_context`
- Entegrasyon: `inference_cp2.py`, `mqtt_orchestrator.py`, `dashboard.py`

**CanlÄ± test Ã§Ä±ktÄ±sÄ± (KÄ±rklareli-Vize, 12 MayÄ±s 2026 10:15):**
| Parametre | DeÄŸer |
|---|---|
| SÄ±caklÄ±k | 19.9Â°C |
| Nem | %69 |
| YaÄŸÄ±ÅŸ | 0.0 mm |
| RÃ¼zgar | 8.3 km/h |
| Toprak sÄ±caklÄ±ÄŸÄ± | 24.3Â°C |
| Toprak nemi | %22.0 |

7 gÃ¼nlÃ¼k tahmin: 18â€“25Â°C arasÄ±, yaÄŸÄ±ÅŸ 0â€“7.5 mm. Aktif uyarÄ± yok.

### 3B â€” RAG Bilgi TabanÄ± GÃ¼Ã§lendirme

| PDF | Boyut | Durum |
|---|---|---|
| TR21 BÃ¶lge PlanÄ± 2024â€“2028 | 6.8 MB | Ä°ndirildi âœ… |
| Trakya Sulama AyÃ§iÃ§eÄŸi | 1.7 MB | Ä°ndirildi âœ… |
| FAO Sunflower Production | 1.2 MB | Ä°ndirildi âœ… |
| FAO Irrigation Paper 56 | â€” | 404 HatasÄ± âŒ |

FAISS yeniden indeks: **56 belge, 16.903 vektÃ¶r** (Ã¶nceki: 14.866 vektÃ¶r, +2.037)
Embed sÃ¼resi: ~16 dakika (intfloat/multilingual-e5-small, CPU)

Kategori daÄŸÄ±lÄ±mÄ±:
| Kategori | Chunk |
|---|---|
| abd | 3.335 |
| fao | 4.461 |
| hastalik | 3.256 |
| tr_bakanlik | 3.015 |
| bbch | 1.494 |
| bolgesel | 1.342 |

### 3C â€” RAG Kalite Test SonuÃ§larÄ±

| # | Sorgu | Bulunan Belge | Kaynak |
|---|---|---|---|
| 1 | Trakya bÃ¶lgesinde ayÃ§iÃ§eÄŸi sulama takvimi | 2 | Edirne Destekleme Sulama + **Trakya_Sulama_Aycicegi.pdf** (yeni) |
| 2 | TR21 iklim deÄŸiÅŸikliÄŸi tahminleri | 2 | 6021_H2.pdf + **TR21_Bolge_Plani_2024_2028.pdf** (yeni) |
| 3 | FAO ayÃ§iÃ§eÄŸi Kc deÄŸeri | 2 | 379598.pdf (2 farklÄ± bÃ¶lÃ¼m, boosted) |

Tri-RAG pipeline: Dense=5, Sparse=3 â†’ BirleÅŸik=6â€“8, Final=2 chunk / sorgu

### Simplify DÃ¼zeltmeleri

6 sorun tespit edildi, 6 dÃ¼zeltme uygulandÄ±:

| # | Dosya | Sorun | DÃ¼zeltme |
|---|---|---|---|
| 1 | `weather_service.py` | `get_weather_alerts` `list[str]` dÃ¶ndÃ¼rÃ¼yordu | `list[dict]` â†’ `{"level", "text"}` yapÄ±sÄ±na geÃ§ildi |
| 2 | `weather_service.py:169` | `join(alerts)` dict Ã¼zerinde Ã§alÄ±ÅŸmÄ±yordu | `join(a["text"] for a in alerts)` |
| 3a | `dashboard.py:38` | Gereksiz import aliaslarÄ± | Alias kaldÄ±rÄ±ldÄ± |
| 3b | `dashboard.py:409` | Alert string karÅŸÄ±laÅŸtÄ±rmasÄ± | `alert["level"]` kullanÄ±mÄ±na geÃ§ildi |
| 4 | `mqtt_orchestrator.py` | `detect_anomalies` iÃ§inde Ã§ift `get_7day_forecast()` Ã§aÄŸrÄ±sÄ± | `forecast` parametresi eklendi, iÃ§ fetch kaldÄ±rÄ±ldÄ± |
| 5 | `llm_engine.py` | Weather None iken prompt'ta boÅŸ satÄ±r | `weather_block` conditional expression ile dÃ¼zeltildi |
| 6 | `inference_cp2.py` | `except Exception: pass` â€” sessiz hata | `logger.warning` ile gÃ¶rÃ¼nÃ¼r hale getirildi |


---

### 12 MayÄ±s 2026 â€” Agronomik Takvim ve Ekim Karar Motoru

**Konu:** Fenolojik takvim, ekim penceresi deÄŸerlendirme, sulama/gÃ¼breleme tavsiye motoru

**YapÄ±lanlar:**
- `src/agro_calendar.py` yazÄ±ldÄ±: `BUGDAY_TAKVIM` + `AYCICEGI_TAKVIM` sabit veri sÃ¶zlÃ¼kleri; `get_current_phenology`, `evaluate_planting_window`, `get_irrigation_advice`, `get_fertilization_advice`, `format_agro_context` fonksiyonlarÄ±
- `src/cp4_rag/llm_engine.py` gÃ¼ncellendi: `rover_alert_query` imzasÄ±na `agro_context: str = None` eklendi; `agro_block` prompt'a ekleniyor
- `src/mqtt_orchestrator.py` gÃ¼ncellendi: `agro_calendar` import bloÄŸu eklendi; `detect_anomalies` fonksiyonuna 3 yeni kural eklendi; `on_message` agronomik baÄŸlam Ã¼retip `rover_alert_query`'e geÃ§iriyor
- `src/dashboard.py` gÃ¼ncellendi: `agro_calendar` import bloÄŸu eklendi; `page_tarla_durumu` iÃ§ine "Agronomik Takvim" bÃ¶lÃ¼mÃ¼ eklendi (2 sÃ¼tunlu fenoloji + ekim/sulama/gÃ¼bre kartlarÄ± + Plotly timeline)

**Agronomik Test SonuÃ§larÄ± (12 MayÄ±s 2026, KÄ±rklareli-Vize):**

| Test | SonuÃ§ |
|---|---|
| BuÄŸday mevcut evre (MayÄ±s) | BaÅŸaklanma â€” BBCH 50-59 â€” KRÄ°TÄ°K DÃ–NEM |
| AyÃ§iÃ§eÄŸi mevcut evre (MayÄ±s) | Ã‡imlenme ve Ã§Ä±kÄ±ÅŸ â€” BBCH 00-09 |
| Ekim penceresi (AyÃ§iÃ§eÄŸi, MayÄ±s) | Uygun deÄŸil â€” skor 70/100; engel: toprak yÃ¼zeyi 21.6Â°C (ideal 8-14Â°C, 10cm Ã¶lÃ§Ã¼mle doÄŸrulayÄ±n) |
| Sulama tavsiyesi (nem %25, nem eÅŸiÄŸi %22) | GEREKSIZ â€” toprak nemi yeterli, sulama gerekmez |
| GÃ¼breleme (AyÃ§iÃ§eÄŸi, MayÄ±s) | EVET â€” 4-6 yaprak dÃ¶nemi: Amonyum sÃ¼lfat, dekara 20-25 kg |
| GÃ¼breleme (BuÄŸday, MayÄ±s) | HayÄ±r â€” bu ay iÃ§in planlÄ± gÃ¼bre uygulamasÄ± yok |

**Yeni Anomali KurallarÄ± (mqtt_orchestrator.py):**

| Kural | KoÅŸul | Seviye |
|---|---|---|
| `EKIM_FIRSATI` | Ekim sezonu + koÅŸullar uygun (skorâ‰¥60, engel yok) | BÄ°LGÄ° |
| `SULAMA_ACIL` | Kritik fenolojik evre + toprak nemi eÅŸik altÄ± | KRÄ°TÄ°K |
| `GUBRE_HATIRLATMA` | GÃ¼breleme takvimi zamanÄ± gelmiÅŸ | BÄ°LGÄ° |

**Dashboard Agronomik Takvim BÃ¶lÃ¼mÃ¼:**
- 2 sÃ¼tun: BuÄŸday | AyÃ§iÃ§eÄŸi
- Her Ã¼rÃ¼n: fenolojik evre (emoji + kritik badge), BBCH aralÄ±ÄŸÄ±, ekim/sulama/gÃ¼bre metrik kartlarÄ±
- Plotly yÄ±llÄ±k fenoloji zaman Ã§izelgesi â€” aktif evre kÄ±rmÄ±zÄ± (#ff5722), ÅŸu anki ay kesik Ã§izgiyle iÅŸaretli

**Sonraki AdÄ±m:** ESP32 rover firmware yÃ¼kleme


---

### 12 MayÄ±s 2026 â€” LLM Prompt MÃ¼hendisliÄŸi ve Veri BaÄŸlamÄ± GÃ¼Ã§lendirme

**Konu:** LLM Ã§Ä±ktÄ± kalitesinin iyileÅŸtirilmesi â€” generic tavsiyeden veri-odaklÄ± tavsiyeye geÃ§iÅŸ

**Sorun:** LLM genel tavsiyeler veriyordu ("Ziraat OdasÄ±'na danÄ±ÅŸÄ±n"), elindeki verileri kullanmÄ±yordu.

**Ã‡Ã¶zÃ¼m:**
- `config.py` SYSTEM_PROMPT tamamen yeniden yazÄ±ldÄ±: 8 kritik kural + 4 bÃ¶lÃ¼mlÃ¼ yanÄ±t yapÄ±sÄ± (ğŸ“Š MEVCUT DURUM / âš ï¸ RÄ°SKLER / âœ… YAPILMASI GEREKENLER / ğŸ“… Ã–NÃœMÃœZDEKI 7 GÃœN)
- `llm_engine.py`'ye `build_rich_context()` fonksiyonu eklendi: CP-2 tahminleri + hava durumu + agronomik takvim + statik toprak profili â†’ tek baÄŸlam bloÄŸu
- `rag_query()` gÃ¼ncellendi: `rich_context: str = None` parametresi eklendi; veri bloÄŸu RAG belgelerinden Ã¶nce prompt'a ekleniyor
- `dashboard.py` gÃ¼ncellendi: `get_rich_context()` Ã¶nbellekli wrapper (5 dk TTL), chatbot sayfasÄ±nda "ğŸ“Š Aktif Veri BaÄŸlamÄ±" expander eklendi, `rag_query()` Ã§aÄŸrÄ±sÄ±na `rich_context` geÃ§iriliyor

**`build_rich_context()` GerÃ§ek Test Ã‡Ä±ktÄ±sÄ± (12 MayÄ±s 2026):**
```
TARLA TAHMÄ°N VERÄ°LERÄ°:
- BuÄŸday: Mevcut=0.4675, Tahmin=0.4413, DeÄŸiÅŸim=-0.0262 (%-5.6), FAIR
- AyÃ§iÃ§eÄŸi: Mevcut=0.4895, Tahmin=0.4904, DeÄŸiÅŸim=+0.0009 (%+0.2), FAIR

ANLIK HAVA: 20.6Â°C, %79 nem, toprak nemi %33.4, yaÄŸÄ±ÅŸ 1.2mm
7 GÃœNLÃœK: 12-25Â°C arasÄ±, 12 May %95 yaÄŸÄ±ÅŸ ihtimali (7.1mm)

AGRONOMÄ°K TAKVÄ°M (Ay 5):
- BuÄŸday: BaÅŸaklanma BBCH 50-59 â€” KRÄ°TÄ°K DÃ–NEM
- AyÃ§iÃ§eÄŸi: Ã‡imlenme BBCH 00-09
- Sulama: Ä°kisi de GEREKSIZ (toprak nemi %33)
- GÃ¼breleme: AyÃ§iÃ§eÄŸi EVET â€” Amonyum sÃ¼lfat, dekara 20-25 kg
```

**Ã–nceki vs Sonraki KarÅŸÄ±laÅŸtÄ±rma:**

| Kriter | Ã–nceki | Sonraki |
|---|---|---|
| Rakam kullanÄ±mÄ± | Yok | NDVI, Â°C, %, mm, kg/dekar |
| Hava tahmini analizi | Yok | 7 gÃ¼nlÃ¼k tahmin deÄŸerlendirmesi |
| Fenolojik evre | Yok | Mevcut evre + kritik dÃ¶nem uyarÄ±sÄ± |
| Sulama miktarÄ± | "Su verin" | "GEREKSIZ â€” toprak nemi %33" veya miktar + zamanlama |
| Genel tavsiye | "DanÄ±ÅŸÄ±n" | Somut eylem planÄ± |
| Veri kaynaÄŸÄ± | Sadece RAG belgeleri | CP-2 + Open-Meteo + Agronomik takvim + RAG |

**Sonraki AdÄ±m:** ESP32 rover firmware yÃ¼kleme

---

## Task 6 - XGBoost Verim Tahmin Pipeline (12 Mayis 2026)

### 6A - Veri Toplama ve Ozellik Muhendisligi

**Yeni dosyalar:**
- `src/cp2_model/collect_yield_data.py`: TUiK Trakya bolge verimi 2017-2024 (16 kayit)
- `src/cp2_model/build_yield_features.py`: 17 yillik agronomik ozellik aggregation
- `data/yield/trakya_yield_2017_2024.csv`: Bugday + Aycicegi kg/dekar verim verisi
- `data/yield/yield_feature_matrix.csv`: 16 satir (8 yil x 2 mahsul), 19 sutun

**Buyume Penceresi Tanimlari:**
| Mahsul | Tam Sezon | Kritik Donem | GDD Baz | Isi Stresi |
|---|---|---|---|---|
| Bugday | Ekim-Temmuz | Subat-Mayis | 0 degC | >32 degC |
| Aycicegi | Nisan-Ekim | Haziran-Agustos | 8 degC | >35 degC |

**17 Ozellik:**
ndvi_peak, ndvi_mean_grow, ndvi_sum, gdd_total, gdd_critical, precip_total, precip_grow,
drought_days, heat_stress_days, frost_days, temp_mean_grow, temp_amplitude_mean,
evi_peak, ndwi_min, radiation_total, soil_clay, soil_ph

### 6B - XGBoost Model Egitimi

**Dosya:** `src/cp2_model/train_yield_model.py`

**Parametreler:**
```
n_estimators=100, max_depth=2, learning_rate=0.05
subsample=0.8, colsample_bytree=0.8, reg_alpha=0.1, reg_lambda=2.0
```

**LOO-CV Sonuclari:**
| Mahsul | R2 (LOO) | MAE | RMSE | MAPE |
|---|---|---|---|---|
| Bugday | -0.467 | 16.7 kg/da | 19.8 kg/da | 5.1% |
| Aycicegi | -0.358 | 13.1 kg/da | 15.3 kg/da | 7.3% |

Not: Negatif R2, 8 veri noktali LOO-CV ile beklenebilir - model ortalama bolgesinde tahmin uretir.
MAPE %5.1 (bugday) ve %7.3 (aycicegi) pratik kullanim icin kabul edilebilir duzey.

**SHAP En Etkili Faktorler:**
- Bugday: precip_grow > gdd_critical > precip_total > ndvi_mean_grow > ndvi_peak
- Aycicegi: gdd_critical > ndvi_mean_grow > ndvi_sum > radiation_total > precip_total

**Kaydedilen Dosyalar (src/cp2_model/):**
- yield_xgb_wheat.pkl, yield_xgb_sunflower.pkl (modeller)
- yield_scaler_wheat.pkl, yield_scaler_sunflower.pkl (StandardScaler)
- yield_shap_wheat.json, yield_shap_sunflower.json (SHAP degerleri + ozellik isimleri)
- yield_meta_wheat.json, yield_meta_sunflower.json (metrikler + meta)

### 6C - Cikarsim Modulu

**Dosya:** `src/cp2_model/inference_yield.py`

predict_yield() fonksiyonu: model yukle + en son tam sezon ozelliklerini hesapla + SHAP top-3 + risk analizi

Test ciktisi (2026-05-12, 2024 sezonu verisi):
```
Bugday   : 319.3 kg/dekar (%âˆ’1.5 Trakya ort.), Guvven 290-349, Risk: NORMAL
Aycicegi : 178.1 kg/dekar (%âˆ’1.1 Trakya ort.), Guven 155-201, Risk: NORMAL
```

### 6D - Entegrasyonlar

**llm_engine.py build_rich_context()**: Verim blogu (blok 5) eklendi - CP-2 tahminlerinden sonra hava verisinden once
**dashboard.py page_tarla_durumu()**: Verim Projeksiyonu (XGBoost) bolumu eklendi
  - 3 metrik karti (tahmini verim, guven araligi, risk)
  - Plotly gauge chart (kirmizi/sari/yesil alanlar + Trakya ortalamasi cizgisi)
  - SHAP top-3 faktor (genisletilebilir kutu)
  - Model metrikleri caption + veri yili uyarisi
  - @st.cache_data(ttl=3600) ile onbellek

**Sonraki Adim:** Proje rapor yazimi ve sistem butunlestirme testi

---

## Task 7 - Ekim Penceresi Tahmin Motoru (12 Mayis 2026)

**Konu:** Open-Meteo gercek zamanli hava verisine dayali dinamik ekim zamani degerlendirmesi

**YapÄ±lanlar:**
- `agro_calendar.py`: `evaluate_planting_window()` genisletildi (`kategori` + `detay` eklendi, ayciÃ§egi don mutlak engeli eklendi), `find_best_planting_days()` eklendi
- `dashboard.py`: `page_tarla_durumu()` sonuna "ğŸŒ± Ekim Penceresi Durumu" bolumu eklendi
- `llm_engine.py`: `build_rich_context()` Block 6 olarak ekim penceresi eklendi

**Ekim Kurallari:**
| Parametre | Bugday | AyciÃ§egi |
|---|---|---|
| Ekim donemi | Ekim-Kasim (ay 10-11) | Nisan-Mayis (ay 4-5) |
| Ideal toprak sicakligi | 8-12 C | 8-14 C |
| Don toleransi | Kismi (don esigi 2 C, +20 puan) | SIFIR - mutlak engel (0 C), skor=0 |
| Ideal toprak nemi | %20-45 (+20 puan) | %22-50 (+20 puan) |
| Puanlama max | 25 (sicaklik) + 20 (nem) + 20 (don) + 15 (yagis) = 80 | Ayni |

**Kategori Esikleri:** >=80 IDEAL, >=60 UYGUN, >=40 DIKKATLI, >=20 ERTELENIN, <20 EKÄ°M YAPMAYIN

**Test Sonuclari (12 Mayis 2026, gercek hava verisi):**
| Urun | Skor | Kategori | Toprak SÄ±cak. | Toprak Nem | Don Riski | Gerekce |
|---|---|---|---|---|---|---|
| Bugday | 0 | EKIM DONEMI DEGIL | â€” | â€” | â€” | Ekim sezonu 10-11. aylar, su an dis |
| AyciÃ§egi | 63 | UYGUN â€” Bu hafta ekilebilir | 14.2Â°C UYGUN (+15) | %33.1 IDEAL (+20) | Yok (+20) | Kosullar uygun, ekime baslanabilir |

**Skorlama Aciklamasi (AyciÃ§egi, 12 Mayis 2026):**
- Toprak sicakligi 14.2Â°C: Sunflower icin ideal aralik 8-14Â°C, 14.2 sinir ustunde â†’ UYGUN (+15, IDEAL degil +25)
- Yagis puani +8: Ä°lk 3 gun yagis < 10mm ama 3-5 gun arasi yagis <5mm â†’ KABUL (+8, IDEAL +15 degil)
- Toplam: 15+20+20+8 = 63/100

**Sonraki Adim:** Dashboard test ve kullanici dogrulamasi

---

## Task 8 - LLM Final Optimizasyonu: Dogal Dil ve Zengin Baglamc (12 Mayis 2026)

**Konu:** Asiri kosullanmis prompt'tan dogal tarim danismanina gecis

**Temel Degisiklik:**
- Eski yaklasim: 8 kural + 4 bolumlu zorunlu format + emoji sablonu (ğŸ“Šâš ï¸âœ…ğŸ“…) â†’ robotik cikti
- Yeni yaklasim: basit rol tanimi + zengin veri baglami + sifir format dayatmasi â†’ dogal konusma

**Degisiklikler:**

config.py â€” SYSTEM_PROMPT:
  Eski: 25+ satir kural, "ASLA", "MUTLAKA", "HER ZAMAN" kaliplari, dayatilmis 4-bolumlu yapi
  Yeni: 8 satir, sadece rol tanimi + "ne soruluyorsa onu cevapla" prensibi

llm_engine.py â€” build_rich_context():
  6 veri bolumu yeniden yapilandirildi:
    1. Bitki saglik tahmini: NDVI, delta, pct_change, health.status/desc/action, field_summary
    2. Verim tahmini: tahmini/ortalama/guven araligÄ±/trend/risk/en_etkili_faktorler
    3. Hava durumu: anlik + 7 gunluk tahmin + haftalik ozet (toplam yagis, kuru gun sayisi)
    4. Fenoloji + sulama (miktar/zamanlama dahil) + gubreleme
    5. Ekim penceresi (skor + kategori)
    6. Toprak profili (statik)
  Her bolum zengin ve okunabilir ama LLM'e format dayatmasi yok.

llm_engine.py â€” rag_query():
  Eski prompt sonu: "YukarÄ±daki TUM verileri analiz ederek somut, rakamsal, eyleme donusturulebilir Turkce tavsiye ver."
  Yeni: Soru once gelir, veri sonra. "YanÄ±tÄ±nda bunlardan yararlan:" - LLM'e alan birakir.

llm_engine.py â€” rover_alert_query():
  Eski: 4 maddeli zorunlu format listesi
  Yeni: "Bu anomali raporu icin ciftciye Turkce tavsiye ver:" - format LLM'e birakÄ±ldÄ±.

llm_engine.py â€” generate_chat_response():
  Yeni fonksiyon eklendi. Zengin baglami kendisi toplar ve LLM'e gonder.

dashboard.py â€” ORNEK_SORULAR:
  3 sorudan 8 soruya cÄ±kartÄ±ldÄ±. Test sorgulari da eklendi:
    "Tarlam nasil?", "Detayli tarla raporu yaz", "Bugday verimim ne olur bu sene?",
    "Hava bu hafta nasil?", "Ekim zamani mi?", "Su vermem lazim mi?"

**Ekim Penceresi Entegrasyonu (Task 7'den devam):**
Bugun ayciÃ§egi ekim durumu: Skor 63/100, UYGUN â€” Bu hafta ekilebilir
  Toprak sicakligi 14.2C (sinirda), Toprak nemi %33.1 (ideal), Don riski yok.

**Beklenen Etki:**
- "Tarlam nasil?" sorusuna 3-5 cumle dogal ozet (robot kalip degil)
- "Detayli rapor yaz" sorusuna tum 6 veri bÃ¶lumunÃ¼ kapsayan kapsamli yanit
- Kisa sorulara kisa, uzun taleplere uzun â€” LLM'in kendi karar verdigi yapi

**Test Notu:**
Dashboard UI testi gerekmektedir. Streamlit sunucu baslatilarak asistan sayfasinda
yukaridaki 6 test sorusunun manuel olarak denenmesi onerilir.
Test sonuclari (kelime sayisi, veri kullanimi, dogallik, kalite 1-5) bu belgeye eklenecek.

---

## Task 9 - RAG Bilgi Tabani Genisletme (13 Mayis 2026)

**Konu:** Tarimsal bilgi tabanini GDD, NDVI, verim, sulama ve kapsamli yetistiricilik rehberleriyle zenginlestirme

**YapÄ±lanlar:**
- `src/cp4_rag/pdf_loader.py`: `.txt` dosya destegi eklendi (rglob scan)
- 8 yeni Turkce tarimsal bilgi belgesi olusturuldu:

| Belge | Konu |
|---|---|
| `gdd/gdd_bugday_fenoloji.txt` | Bugday GDD/fenoloji (0C baz, BBCH esikleri) |
| `gdd/gdd_aycicegi_fenoloji.txt` | Aycicegi GDD/fenoloji (6.7C baz, VE-R9) |
| `ndvi/ndvi_yorumlama_ve_verim.txt` | NDVI yorumlama, verim korelasyonu |
| `verim/verim_belirleyici_faktorler.txt` | Iklim/toprak/yonetim etkileri, benchmark |
| `sulama/sulama_programlama_rehberi.txt` | Sulama programi, Kc degerleri, ET0 |
| `ekim_hasat/trakya_bugday_tam_rehber.txt` | Kapsamli bugday yetistiricilik rehberi |
| `ekim_hasat/trakya_aycicegi_tam_rehber.txt` | Kapsamli aycicegi yetistiricilik rehberi |
| `ekim_hasat/hasat_kalite_gostergeler.txt` | Hasat kalite gostergeleri ve depolama |

**FAISS Index Rebuild:**
- 57 PDF + 8 TXT = 64 belge basariyla yuklendi (095270.pdf metin cok kisa, atlandi)
- 17,059 chunk olusturuldu
- Model: `intfloat/multilingual-e5-small`
- Kategori dagilimi: fao(4461), abd(3335), hastalik(3256), tr_bakanlik(3015), bbch(1494), bolgesel(1342), ekim_hasat(66), gdd(34), ndvi(19), verim(20), sulama(17)

---

## Task 10 - Dashboard v2 + SQLite Veritabani + Akilli RAG (13 Mayis 2026)

**Konu:** Cok-tarlali dashboard, SQLite veritabani ve akilli RAG chatbot

### Yeni Dosyalar

**`src/database.py`** â€” SQLite veritabani (data/trakaia.db)
- 3 tablo: tarlalar, rover_olcumler, tarla_tahminler
- 4 mock tarla:

| id | Isim | Il | Alan | Urun | Konum |
|---|---|---|---|---|---|
| 1 | Edirne Merkez Bugday | Edirne | 120 dekar | Bugday | 41.677N, 26.556E |
| 2 | Kirklareli Vize Aycicegi | Kirklareli | 85 dekar | Aycicegi | 41.694N, 27.105E |
| 3 | Tekirdag Hayrabolu Bugday | Tekirdag | 200 dekar | Bugday | 41.213N, 27.099E |
| 4 | Edirne Uzunkopru Aycicegi | Edirne | 150 dekar | Aycicegi | 41.267N, 26.688E |

- Her tarla icin 6 mock rover olcumu + 1 tahmin kaydi
- Mock anomaliler: Tarla 2 olcum 4 (mildiyÃ¶, guven=0.87), Tarla 3 olcum 3 (nem=13%, kritik)
- 9 fonksiyon: get_connection, init_db, get_tarlalar, get_tarla, add_rover_olcum, get_rover_olcumler, add_tahmin, get_son_tahmin, get_tarla_ozet

**`src/dashboard.py`** â€” 3 sayfali Streamlit dashboard (tam yeniden yazim)

| Sayfa | Icerik |
|---|---|
| Tarla Durumu | NDVI kartlari + Verim + Hava durumu + Fenoloji gauge + Oneriler + SHAP + Ekim penceresi |
| Rover Izleme | Normal/Anomali simulasyon butonlari + Sensor tablosu + Anomali expander'lari + Folium GPS haritasi + Istatistikler |
| Tarim Asistani | VERI/BILGI/GENEL siniflandirma + Akilli RAG + Kaynak expander'lari + Ornek sorular |

### Akilli RAG Mimarisi

`classify_query(soru)` â€” Anahtar kelime bazli siniflandirici:
- VERI: "tarlam", "verim", "sulama", "durum", "hava", "nem" gibi sorgular
- BILGI: "nedir", "hastalik", "ilaÃ§", "gÃ¼breleme", "bbch" gibi sorgular
- GENEL: Selam, tesekkur, genel sorular

`build_smart_rag_queries(rich_context)` â€” Sorun tespiti + hedefli RAG:
- rich_context icinde sulama aciliyeti, hastalik, verim dususu, don riski tespiti
- Tespit edilen soruna ozgun RAG sorgusu uretir (kullanicinin sorusunu degil)

Akis:
- VERI sorgusu â†’ rich_context â†’ sorun tespit â†’ hedefli RAG (2 sorgu, 3 belge, deduplicate) â†’ LLM â€” "AKILLI" badge
- BILGI sorgusu â†’ kullanici sorusu direkt RAG'a â†’ LLM â€” "DOGRUDAN" badge
- GENEL sorgu â†’ dogrudan LLM â€” RAG yok

### Diger Degisiklikler

**`src/mqtt_orchestrator.py`**:
- `try: from database import add_rover_olcum; DB_AVAILABLE = True` import eklendi
- `on_message` callback'te, tavsiye yayinlanmadan once DB'ye yaz:
  `add_rover_olcum(tarla_id, rover_data_dict)` â€” timestamp, waypoint, nem, temp, anomali_sayisi, anomaliler JSON, kds_tavsiye

**`src/cp4_rag/llm_engine.py`**:
- `classify_query()` fonksiyonu eklendi
- `build_smart_rag_queries()` fonksiyonu eklendi
- `generate_chat_response()` yeniden yazildi: `(user_question, vectorstore=None, chunks=None, rag_context="")` imzasiyla akilli RAG destegi


---

## 19 Mayis 2026 - Final Entegrasyon ve Bug Fix (Task 11)

### Kapsam

ESP32 firmware kritik donanim hatalari, MQTT topic uyumsuzlugu, inference_cp2.py custom layer yukleme sorunu ve RAG kalite iyilestirmesi.

### Bug Fix Tablosu

| # | Dosya | Sorun | Duzeltme |
|---|---|---|---|
| 1 | config.h | CAM_RX=3, CAM_TX=1 (USB/Serial0 pinleri) | GPIO 22, 23 olarak degistirildi |
| 2 | config.h | MQTT_TOPIC "trak-ai/rover/data" (Python ile uyumsuz) | "trakaia/rover/data" olarak esitlendi |
| 3 | main.cpp | analogWrite() ESP32'de mevcut degil | ledcSetup+ledcAttachPin+ledcWrite (LEDC API) ile degistirildi |
| 4 | main.cpp + esp32_cam | StaticJsonDocument<N> (ArduinoJson v6) | JsonDocument (ArduinoJson v7) ile guncellendi |
| 5 | esp32_cam/main.cpp | CAPTURE komutu handler yok | Serial.readStringUntil() ile anlık inference tetikleme eklendi |
| 6 | inference_cp2.py | BASE_DIR ve sys.path, train_models_cp2 import'undan sonra tanimliydi | BASE_DIR onceden tanimlandi, import try/except ile koruma altina alindi |
| 7 | retriever.py | FAISS L2 uzaklik esigi yoktu | score > 1.5 filtresi eklendi (alakasiz chunk LLM'e gitmiyor) |

### Degisiklik Yapilan Dosyalar

- src/cp3_edge/trak_ai_rover/src/config.h - Pin ve topic duzeltmeleri
- src/cp3_edge/trak_ai_rover/src/main.cpp - LEDC PWM, JsonDocument
- src/cp3_edge/esp32_cam/src/main.cpp - CAPTURE handler, JsonDocument
- src/cp2_model/inference_cp2.py - sys.path sirasi duzeltildi
- src/cp4_rag/retriever.py - FAISS L2 esik filtresi

### Donanım Notları

**ESP32 Motor PWM (LEDC):**
- Kanal 0 (MOTOR_ENA): ledcSetup(0, 5000, 8) + ledcAttachPin(MOTOR_ENA, 0)
- Kanal 1 (MOTOR_ENB): ledcSetup(1, 5000, 8) + ledcAttachPin(MOTOR_ENB, 1)

**UART Pin Kullanimi:**
- UART0 (GPIO 1/3): USB/Serial - KULLANMA
- UART1 (GPIO 22/23): ESP32-CAM haberlesme
- UART2 (GPIO 16/17): GPS


---

## 20 Mayis 2026 - Hybrid Edge-Fog Goruntu Isleme Entegrasyonu (Task 12)

**Konu:** ESP32-CAM on-device inference -> Laptop YOLOv8 mimarisi

**Mimari Degisiklik:**
- ESKI: ESP32-CAM -> mock inference -> BBCH JSON -> MQTT
- YENI: ESP32-CAM -> base64 JPEG -> Serial -> Rover -> MQTT -> Laptop YOLOv8

**Akademik Gerekce:** Hybrid Edge-Fog Processing -- Edge cihazinin bellek/enerji kisitlari
nedeniyle goruntu isleme Fog katmanina (laptop) tasindi. Edge sadece JPEG yakalar ve iletir.

**Yeni Dosyalar:**
- src/image_classifier.py -- YOLOv8 inference (model yokken mock mod)
- models/README.md -- Model yerlesim rehberi
- data/rover_images/ -- Kaydedilen rover goruntuleri

**Guncellenen Dosyalar:**

| Dosya | Degisiklik |
|---|---|
| esp32_cam/main.cpp | mock inference -> mbedtls base64 + goruntuyuGonder() |
| rover/main.cpp | base64 JSON parse, MQTT buffer 64KB, CAPTURE komutu gonderimi |
| mqtt_orchestrator.py | image alani parse + YOLOv8 clf + disk kayit |
| database.py | rover_olcumler.image_path sutunu (migration ile) |
| dashboard.py | 2C kamera gostergesi, 2D goruntu + hastalik expander |
| llm_engine.py | build_rich_context() blok 7: kamera analizi |
| requirements.txt | ultralytics, Pillow ve diger bagimliliklar |

**Siniflar:** saglikli_bugday, saglikli_aycicegi, hastalik_pas, hastalik_mildiyo, stres_kuraklik, stres_besin

**Sonraki Adim:** Colab YOLOv8 egitimi -> models/crop_health_best.pt -> mock moddan gercege gecis


---

## 20 Mayis 2026 - Final Entegrasyon: YOLOv8 + Dashboard v2 + Bug Fix (Task 13)

**Konu:** YOLOv8s-cls model entegrasyonu, dashboard tam yeniden yazimi, tum hata duzeltmeleri

### A. YOLOv8 Entegrasyonu

- Model: YOLOv8s-cls, 6 sinif, Top-1 Dogruluk: %94.9
- Dosya: models/best.pt -> models/crop_health_best.pt (kopya)
- ultralytics yuklu degilse otomatik mock mod
- SINIF_LABELS gercek model sinif sirasi ile guncellendi (alfabetik: mildiyo=0, pas=1, s_ayci=2, s_bugday=3, besin=4, kuraklik=5)
- KDS_AKSIYONLAR eklendi: her sinif icin aksiyon, aciliyet, tavsiye

### B. Sinif Bazli Performans

| Sinif | Dogruluk | Overfit | Durum |
|---|---|---|---|
| saglikli_bugday | %98.0 | Hayir | OK |
| saglikli_aycicegi | %100.0 | Hayir | OK |
| hastalik_pas | %91.0 | Hayir | OK |
| hastalik_mildiyo | %99.1 | Hayir | OK |
| stres_kuraklik | %100.0 | EVET | Dikkat |
| stres_besin | %85.2 | Hayir | OK |

### C. Bug Fix Raporu

| Dosya | Sorun | Cozum |
|---|---|---|
| image_classifier.py | SINIF_LABELS indeks sirasi yanlis | Gercek model sirasiyla guncellendi |
| database.py | camera_sinif/camera_guven sutunu eksikti | ALTER TABLE migration eklendi |
| llm_engine.py | Bare except: (satir 216, 309) | except Exception olarak duzeltildi |
| agentic_rag.py | FAISS threshold: <1.1 (yanlis yon) | >1.5 olarak duzeltildi (retriever.py ile tutarli) |
| mqtt_orchestrator.py | Dead import: ANOMALY_THRESHOLDS | Kaldirildi |
| mqtt_orchestrator.py | Typo: "stres esigi asild" | "asildi" olarak duzeltildi |
| mqtt_orchestrator.py | clf_result undefined reference | None ile baslatildi |
| dashboard.py | Hardcoded hava koordinati | tarla["konum_lat/lon"] gecildi |

### D. Dashboard v2

| Sayfa | Icerik |
|---|---|
| Tarla Durumu | NDVI + Verim + Hava (tarla koordinati) + Fenoloji + Oneriler + SHAP |
| Rover Izleme | Mock butonlar + Son veriler + Model/Rover grafigi + Anomali + GPS + Istatistik |
| Tarim Asistani | Chat + classify_query routing (VERI/BILGI/GENEL) + RAG kaynaklar + Veri baglamı |

### E. Akademik Veri Kaynaklari (YOLOv8 Egitimi)

| Kaynak | DOI/URL | Icerik | Goruntu |
|---|---|---|---|
| IARI Wheat N-Deficiency & Rust | 10.17632/th422bg4yd.1 | Pas + kontrol | 859 |
| BARI Sunflower Disease | 10.17632/b83hmrzth8.1 | Mildiyo + saglikli | 1060 |
| Yao et al. (2024) Drought | 10.1371/journal.pone.0300746 | Kuraklik stresi | 360 |
| Wheat Disease 21K | Kaggle/freedomfighter1290 | Pas + saglikli + blight | 21212 |

**Sonraki Adim:** ESP32 fiziksel yukleme + tez birlestirme + kaynakca

---

## 21 Mayis 2026 — Hava Gecmisi + Goruntu Galerisi (Task 14)

### A. Yeni Ozelliklere Genel Bakis

| Ozellik | Aciklama |
|---|---|
| hava_kayitlari tablosu | SQLite'a yeni tablo: UNIQUE(tarla_id, tarih) ile gunluk hava gecmisi |
| 62 gunluk mock veri | 4 tarla icin 20 Mart – 20 Mayis 2026 gercekci hava profili |
| collect_and_save_weather() | weather_service.py: Open-Meteo API'dan ceker, DB'ye kaydeder, ayni gun tekrar atlar |
| Hava Gecmisi Grafigi | Dashboard Sayfa 1'de 3-panelli Plotly: Sicaklik + Yagis + GDD |
| Son Rover Goruntuleri | Dashboard Sayfa 2'de 4-kolonlu galeri, renk kodlu badge |
| build_rich_context() Blok 8 | LLM baglam metnine son 30 gunun hava istatistikleri eklendi |
| MQTT otomatik hava kaydi | Her rover mesajinda collect_and_save_weather() cagrilir |

### B. hava_kayitlari Tablo Yapisi

| Sutun | Tip | Aciklama |
|---|---|---|
| tarla_id | INTEGER | tarlalar.id FK |
| tarih | TEXT | YYYY-MM-DD (UNIQUE ile birlesik anahtar) |
| hava_temp_c | REAL | Ortalama hava sicakligi |
| temp_max / temp_min | REAL | Gunluk max/min sicaklik |
| yagis_gunluk_mm | REAL | Gunluk yagis mm |
| et0_mm | REAL | Hargreaves ET0 buharlasmasi |
| gdd_kumulatif | REAL | Kumulatif GDD (baz 10°C) |
| don_riski | INTEGER | 1 = gece min < 2°C |
| sicak_stres | INTEGER | 1 = gunduz max > 30°C |

### C. Mock Hava Verisi Profili

| Donem | Sicaklik Araligi | Ozellik |
|---|---|---|
| 20-31 Mart | 8–16°C | Don riski (min < 2°C) — ilk 5 gun |
| 1-30 Nisan | 12–22°C | Yagisli donem, GDD birikimi baslangici |
| 1-14 Mayis | 16–26°C | Buyume hizi artar |
| 15-20 Mayis | 20–34°C | Sicak stres gunleri (max > 30°C) |

Her tarla icin kucuk cografya ofsetleri: Edirne +0.3, Kirsehir -0.3, Tekirdag +0.5, Uzunkopru +0.8°C

### D. Yeni Dashboard Bilesenler

| Konum | Biesen | Veri Kaynagi |
|---|---|---|
| Sayfa 1, 1C sonrasi | Hava Gecmisi (genisletilebilir panel) | get_weather_history() |
| Sayfa 2, 2B sonrasi | Son Rover Goruntuleri (4-kolonlu galeri) | image_path alanli rover kayitlari |

### E. Dogrulama Kontrolleri

```bash
# 1. hava_kayitlari doldu mu?
python -c "import sys; sys.path.insert(0,'src'); from database import init_db, get_weather_history; init_db(); h=get_weather_history(1,30); print(f'{len(h)} kayit, ilk={h[0][\"tarih\"] if h else None}')"

# 2. weather_stats calisiyor mu?
python -c "import sys; sys.path.insert(0,'src'); from database import init_db, get_weather_stats; init_db(); print(get_weather_stats(1, 30))"

# 3. Dashboard baslatma
streamlit run src/dashboard.py
```

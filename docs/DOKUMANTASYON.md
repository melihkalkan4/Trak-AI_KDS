📝 ÇP-1: ETL Veri Hattı - 1. Hafta (H1) Geliştirme Raporu
Proje: Trak-AI KDS (Karar Destek Sistemi)
Modül: Çalışma Paketi 1 (Veri Füzyonu ve Altyapı)
Tarih: 14 Mart 2026

📌 Genel Bakış
Projenin birinci hafta hedefleri doğrultusunda, Trakya bölgesi pilot parsellerine ait retrospektif verileri (2017-2024) çekecek olan çok kaynaklı veri altyapısı sıfırdan kurulmuştur. Sistem mimarisi için gerekli olan Python sanal ortamı yapılandırılmış, ana veri sağlayıcıların (Google Earth Engine, Copernicus CDS, ISRIC SoilGrids) kimlik doğrulama süreçleri ve ilk veri çekim testleri başarıyla tamamlanmıştır.

🛠️ 1. Geliştirme Ortamı ve Mimari Kurulumu
VS Code üzerinde projenin modüler klasör yapısı (data/raw, src/cp1_etl, keys vb.) oluşturuldu.

Kütüphane çakışmalarını önlemek amacıyla izole bir Python sanal ortamı (venv) kuruldu.

Güvenlik protokolleri gereği API anahtarlarının sızmasını engellemek için .gitignore dosyası yapılandırıldı.

🛰️ 2. Google Earth Engine (GEE) ve Sentinel-2 Entegrasyonu
Bağlantı ve Yetkilendirme: Google Cloud üzerinden akademik/ticari olmayan (Noncommercial) kullanım onaylı bir proje (trak-ai-kds) oluşturuldu. Sisteme otonom erişim için Servis Hesabı (Service Account) açılarak JSON kimlik dosyası entegre edildi.

Veri Çekimi ve İşleme: Pilot bölge (Enlem: 41.40, Boylam: 27.35) için 2023 yılına ait Sentinel-2 uydu görüntüleri sorgulandı.

Bulut Maskeleme: eemont kütüphanesi kullanılarak s2_cloud_masker algoritması koda entegre edildi. Bulutlu görüntüler filtrelenerek 46 adet temiz NDVI (Normalize Edilmiş Fark Bitki İndeksi) verisi elde edildi ve s2_ndvi_2023.csv olarak yerel diske kaydedildi.

🌦️ 3. Copernicus CDS (ERA5-Land) Yapılandırması
Bağlantı ve Yetkilendirme: Büyüme Derece Günleri (GDD) ve iklimsel anomali tespiti için gerekli olan ERA5-Land veritabanına erişim sağlandı.

Yapılandırma: Copernicus portalından alınan UID ve API anahtarı, Python betiği yardımıyla Windows kök dizininde .cdsapirc yapılandırma dosyasına (YAML formatında) dönüştürülerek kaydedildi.

Doğrulama: cdsapi kütüphanesi üzerinden sunucu bağlantı testleri başarıyla gerçekleştirildi.

🌱 4. ISRIC SoilGrids Toprak Verisi Entegrasyonu (Sistem Revizyonu)
Problem Tespiti: ISRIC REST API sunucularında yaşanan kararsızlık (HTTP 503 - Service Unavailable) veri çekimini engelledi.

Mühendislik Çözümü: Veri hattının tıkanmasını önlemek amacıyla REST API yerine, verilerin doğrudan GEE Assets (projects/soilgrids-isric/) üzerinden çekilmesine karar verildi.

İşlem ve Çıktı: Sentinel-2 ile aynı koordinat sistemi dinamikleri kurularak reduceRegion metoduyla nokta bazlı örnekleme yapıldı. Pilot bölge için fiziksel ve kimyasal toprak özellikleri başarıyla çekilerek soilgrids_2023.csv dosyasına yazdırıldı:

Kil (0-5cm): %30.97

Kum (0-5cm): %34.99

pH (0-5cm): 7.11

🚀 Sonuç ve Sonraki Adımlar
Haftanın tüm hedefleri (%100) tamamlanmıştır. Sistem, Trakya bölgesindeki herhangi bir koordinat için uydu ve toprak verilerini otonom olarak çekebilir durumdadır.
2. Hafta Hedefi: ERA5-Land günlük iklim verilerinin (Sıcaklık, Yağış, Radyasyon) NetCDF formatında indirilmesi ve elde edilen bu üç farklı veri setinin (Uydu, İklim, Toprak) Pandas ile birleştirilerek nihai "Öznitelik Matrisi"nin (Feature Matrix) oluşturulmasıdır.
📝 ÇP-1: ETL Veri Hattı - 2. Gün Geliştirme Raporu ve Veri Sözlüğü
Proje: Trak-AI KDS (Karar Destek Sistemi)
Modül: Çalışma Paketi 1 (Veri Füzyonu ve Altyapı)
Tarih: 15 Mart 2026

📌 1. Genel Bakış
Projenin 2. gün hedefleri doğrultusunda, bitkilerin fenolojik evre geçişlerini (BBCH) tetikleyen Büyüme Derece Günleri (GDD) ve su dengesi analizleri için zorunlu olan atmosferik verilerin çekim işlemi tamamlanmıştır. Copernicus Climate Data Store (CDS) yeni API altyapısının getirdiği kısıtlamalar proaktif bir mühendislik yaklaşımıyla aşılarak otonom bir veri hattı inşa edilmiştir. Devamında, elde edilen çok kaynaklı veri setlerinin yapısal analizleri gerçekleştirilerek veri sözlüğü (Data Dictionary) oluşturulmuştur.

🌦️ 2. ERA5-Land İklim Verisi Entegrasyonu ve İşleme
Veri Kaynağı: Copernicus CDS (reanalysis-era5-land)

Pilot Bölge: Trakya (Lat: 41.40, Lon: 27.35)

Zaman Aralığı: 2023 Tam Yıl (Ocak - Aralık)

Otomasyon ve Hata Yönetimi:

Kota sınırlarına (Cost Limits) takılmamak için veriler 12 aylık döngüler halinde (Chunking) talep edilmiştir.

CDS API v2'nin büyük verileri gizlice .zip arşivi olarak gönderme problemine karşı, sisteme otomatik ZIP çözücü (zipfile) ve .nc (NetCDF) ayıklayıcı entegre edilmiştir.

Dosya okuma hatalarına karşı çoklu motor (netcdf4, h5netcdf, scipy) yedeği (fallback) kurularak sistemin kararlılığı maksimuma çıkarılmıştır.

Agronomik Dönüşümler: Ham xarray veri setleri işlenerek günlük ortalamalara (resample('1D').mean()) dönüştürülmüş ve SI birimlerinden agronomik analiz birimlerine geçilmiştir:

Hava Sıcaklığı (t2m): Kelvin'den Santigrat'a (°C)

Toplam Yağış (tp): Metreden Milimetreye (mm)

Sonuç: Geçici dosyaların otomatik temizliği sonrası 365 günlük kesintisiz iklim matrisi yerel diske kaydedilmiştir.

📊 3. Kullanılan Ham Veri Setlerinin Yapısal Analizi (Veri Sözlüğü)
Veri toplama (ETL) sürecinin tamamlanmasıyla birlikte, Trak-AI KDS projesinin temelini oluşturacak üç farklı kaynaktan elde edilen veri setleri yerel diske (data/raw/) alınmıştır. Makine öğrenmesi modeli için bu verilerin yapısal boyutları ve veri tipleri (Dtypes) ileriki veri birleştirme (Data Fusion) işlemleri için referans kabul edilmiştir.

3.1. Atmosferik ve İklimsel Veri Seti (era5_2023.csv)
Veri Kaynağı: Copernicus CDS

Veri Boyutu (Shape): (365, 5) — 2023 yılının her günü için 1 satır olmak üzere kesintisiz zaman serisi.
Öznitelik Adı,Veri Tipi (Dtype),Açıklama,Birim
date,object,Gözlem tarihi (YYYY-MM-DD formatında),-
t2m_celsius,float64,2m yükseklikteki ortalama hava sıcaklığı,°C
tp_mm,float64,Günlük toplam yağış miktarı,mm
radiation,float64,Yüzey net kısa dalga güneş radyasyonu,J/m²
evaporation,float64,Toplam buharlaşma,m

3.2. Spektral Uydu ve Fenoloji Veri Seti (s2_ndvi_2023.csv)
Veri Kaynağı: Google Earth Engine (Sentinel-2)

Veri Boyutu (Shape): (46, 2) — Bulutlu günlerin filtrelenmesi nedeniyle 365 günlük yıl içerisinde 46 adet net uydu geçiş gözlemi kalmıştır.

Öznitelik Adı,Veri Tipi (Dtype),Açıklama,Birim
date,object,Görüntünün çekildiği tarih,-
NDVI,float64,Normalize Edilmiş Fark Bitki İndeksi,Boyutsuz

3.3. Statik Pedolojik (Toprak) Veri Seti (soilgrids_2023.csv)
Veri Kaynağı: ISRIC SoilGrids

Veri Boyutu (Shape): (1, 5) — Tek bir pilot lokasyon (nokta) için zamandan bağımsız tek satırlık veri matrisi.

Öznitelik Adı,Veri Tipi (Dtype),Açıklama,Birim
lat,float64,Hedef tarlanın enlem koordinatı,DD
lon,float64,Hedef tarlanın boylam koordinatı,DD
clay,float64,0-5 cm derinlikteki ortalama kil oranı,%
sand,float64,0-5 cm derinlikteki ortalama kum oranı,%
phh2o,float64,0-5 cm derinlikteki su bazlı toprak pH değeri,pH

🔄 4. Veri Füzyonu (Data Fusion) Stratejisi
Yapısal analiz sonucunda veri boyutlarındaki asimetri (365 satır vs 46 satır vs 1 satır) tespit edilmiştir. Bu bağlamda:

365 günlük ERA5 iklim verisi ana iskelet (base dataframe) olarak kabul edilecektir.

Statik toprak verisi (1 satır), bu ana iskelete kolon bazında çoğaltılarak (broadcasting) eklenecektir.

46 satırlık NDVI verisi, date anahtarı üzerinden (Left Join) eşleştirilecek ve uydu geçişi olmayan günlerdeki boşluklar (NaN), zaman serisi algoritmaları (Linear Interpolation / İleriye Dönük Doldurma) ile optimize edilerek nihai Öznitelik Matrisi (Feature Matrix) oluşturulacaktır.
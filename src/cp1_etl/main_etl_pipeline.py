"""
=====================================================================================
TRAK-AIA KDS: OTONOM ETL VE VERİ FÜZYONU BORU HATTI (ORCHESTRATOR)
=====================================================================================
Bu dosya sistemin kalbidir. Tarih ve koordinat bilgilerini alır, 
tüm alt modülleri sırasıyla çalıştırır ve nihai 'Öznitelik Matrisi'ni oluşturur.
=====================================================================================
"""

import pandas as pd
import os
import time
import sys
import os

# Kodun çalıştığı klasörü değil, dosyanın olduğu klasörü referans almasını sağlar
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# keys klasörüne ana dizinden (root) ulaşmak için yolu düzeltiyoruz
# Eğer kodun içinde 'keys/trak-ai...' yazıyorsa onu şu değişkenle yönetebiliriz:
KEY_PATH = os.path.join(current_dir, "../../keys/trak-ai-kds-d3e5e5b6e168.json")

# Kendi yazdığımız modülleri içe aktarıyoruz
from mod_soil_isric import fetch_soil_data
from mod_s2_gee import fetch_s2_data
from mod_era5_cds import fetch_era5_data

print("="*60)
print("🚀 TRAK-AIA KDS: Otonom ETL Boru Hattı Başlatıldı")
print("="*60)

# =====================================================================================
# 1. AYARLAR VE PARAMETRELER 
# =====================================================================================
# Tez için modelin farklı iklim rejimlerini görmesi adına 2017-2024 arası tam periyot:
START_YEAR = 2017 
END_YEAR = 2024

# Kırklareli, Vize - Evrenli Köyü Pilot Tarla Koordinatları (Decimal Degrees)
LAT, LON = 41.530333, 27.861194

# Uydu verisi için ilgi alanı poligonu (Merkez koordinat etrafında ~1-2 km'lik Bounding Box)
ROI_COORDS = [
    [27.851194, 41.520333], # Sol Alt
    [27.871194, 41.520333], # Sağ Alt
    [27.871194, 41.540333], # Sağ Üst
    [27.851194, 41.540333]  # Sol Üst
]

start_time = time.time()

# =====================================================================================
# 2. VERİ ÇEKME SÜREÇLERİ (EKSTRAKSİYON)
# =====================================================================================
print("\n[ADIM 1/4] Toprak Profili Çekiliyor (Statik)...")
soil_dict = fetch_soil_data(LAT, LON)

print("\n[ADIM 2/4] Uydu İndeksleri Çekiliyor (Dinamik/Boşluklu)...")
df_s2 = fetch_s2_data(START_YEAR, END_YEAR, ROI_COORDS)

print("\n[ADIM 3/4] İklim Verisi Çekiliyor (Dinamik/Sürekli)...")
# Tam veri setini çektiğimiz için test_mode=False olarak ayarlandı
df_era5 = fetch_era5_data(START_YEAR, END_YEAR, LAT, LON, test_mode=False)

# Güvenlik kontrolü
if df_era5.empty or df_s2.empty or not soil_dict:
    print("\n❌ KRİTİK HATA: Veri akışlarından biri veya birkaçı boş döndü. Füzyon iptal edildi.")
    exit()

# =====================================================================================
# 3. VERİ FÜZYONU VE İNTERPOLASYON (BİRLEŞTİRME)
# =====================================================================================
print("\n[ADIM 4/4] Çok-Modallı Veri Füzyonu Başlıyor...")

# A) Ana iskeletimiz İklim (ERA5) tablosu
df_master = df_era5.copy()

# B) Statik Toprak Verisini Ana İskelete Yayınla (Broadcasting)
for col_name, value in soil_dict.items():
    df_master[col_name] = value

print(f"   ✅ Toprak profili (3 katman) iklim iskeletine entegre edildi.")

# C) Uydu Verisini Tarih Üzerinden Birleştir (Left Join)
df_master = pd.merge(df_master, df_s2, on='date', how='left')
valid_days = df_master['NDVI'].notna().sum()
print(f"   ✅ Uydu verisi eklendi. ({len(df_master)} günün {valid_days} gününde net ölçüm var)")

# D) Eksik Uydu Günlerini Doğrusal İnterpolasyon ile Doldur
# Sentinel-2 verilerindeki (bulut kaynaklı) boşlukları bitki büyüme doğasına uygun dolduruyoruz
index_cols = ['NDVI', 'EVI', 'NDWI']
for col in index_cols:
    df_master[f'{col}_int'] = df_master[col].interpolate(method='linear')
    # Yıl başı ve sonundaki dışta kalan boşlukları doldur
    df_master[f'{col}_int'] = df_master[f'{col}_int'].bfill().ffill()

print(f"   ✅ Spektral indeksler (NDVI, EVI, NDWI) için zaman serisi interpolasyonu tamamlandı.")

# =====================================================================================
# 4. KAYDETME VE ÖZET
# =====================================================================================
output_dir = 'data/processed'
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, f'master_feature_matrix_{START_YEAR}_{END_YEAR}.csv')

df_master.to_csv(output_path, index=False)
elapsed_time = (time.time() - start_time) / 60

print("\n" + "="*60)
print(f"🎉 İŞLEM BAŞARILI: YENİ NESİL ÖZNİTELİK MATRİSİ HAZIR!")
print("="*60)
print(f" Boyut: {df_master.shape[0]} satır (Gün), {df_master.shape[1]} sütun (Öznitelik)")
print(f" Çıktı: {output_path}")
print(f" Süre:  {elapsed_time:.2f} dakika")
print("="*60)
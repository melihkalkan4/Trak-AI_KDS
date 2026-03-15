import pandas as pd
import numpy as np
import os

print("="*50)
print("Trak-AI KDS: Veri Füzyonu (Data Fusion) Başlıyor...")
print("="*50)

# 1. Ham Verileri Yükleme
try:
    df_climate = pd.read_csv('data/raw/era5_2023.csv')
    df_soil = pd.read_csv('data/raw/soilgrids_2023.csv')
    df_ndvi = pd.read_csv('data/raw/s2_ndvi_2023.csv')
    print("✅ Bütün ham veri setleri başarıyla yüklendi.")
except Exception as e:
    print(f"❌ Dosya okuma hatası: {e}")
    exit()

# Tarih formatlarını datetime objesine çeviriyoruz (Güvenli eşleştirme için)
df_climate['date'] = pd.to_datetime(df_climate['date'])
df_ndvi['date'] = pd.to_datetime(df_ndvi['date'])

# 2. İklim ve Toprak Verisini Birleştirme (Broadcasting)
# Toprak verisi statik (tek satır) olduğu için, 365 günün yanına sabit değer olarak kopyalıyoruz
for col in df_soil.columns:
    df_climate[col] = df_soil[col].iloc[0]

print("✅ İklim (365 satır) ve Toprak (1 satır) verileri başarıyla birleştirildi.")

# 3. NDVI Verisini Ana Tabloya Ekleme (Left Join)
# Sadece uydunun geçtiği 46 günde NDVI değeri olacak, diğer 319 gün NaN (Boş) kalacak
df_master = pd.merge(df_climate, df_ndvi, on='date', how='left')
valid_ndvi_count = df_master['NDVI'].notna().sum()
print(f"✅ Uydu verisi eklendi. (Toplam {valid_ndvi_count} günde gerçek NDVI ölçümü var)")

# 4. Eksik NDVI Verilerini Doldurma (Linear Interpolation)
# Bitki büyümesi doğrusal ve sürekli bir süreç olduğu için, uydunun geçmediği günleri (bulutlu günler vb.)
# iki gerçek ölçüm arasındaki eğilimi hesaplayarak (matematiksel tahminle) dolduruyoruz.
df_master['NDVI_interpolated'] = df_master['NDVI'].interpolate(method='linear')

# Yılın en başındaki (ilk uydu geçişinden önceki) ve sonundaki olası boşlukları ileri/geri doldurma ile kapatıyoruz
df_master['NDVI_interpolated'] = df_master['NDVI_interpolated'].bfill().ffill()

print("✅ Uydu geçmeyen günler için NDVI interpolasyonu (boşluk doldurma) tamamlandı.")

# 5. Çıktıyı İşlenmiş (Processed) Klasörüne Kaydetme
output_dir = 'data/processed'
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

output_path = os.path.join(output_dir, 'master_feature_matrix_2023.csv')
df_master.to_csv(output_path, index=False)

print("\n" + "="*50)
print(f"🎉 İŞLEM BAŞARILI: Nihai Öznitelik Matrisi (Feature Matrix) oluşturuldu!")
print(f"Boyut: {df_master.shape[0]} satır (Gün), {df_master.shape[1]} sütun (Öznitelik)")
print(f"Dosya Yolu: {output_path}")
print("="*50)
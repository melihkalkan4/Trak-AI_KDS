import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import os

# Dosyanın kendi bulunduğu klasör: src/cp2_model
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Proje ana dizini (BASE_DIR'den 2 üst klasöre çıkıyoruz): Trak-AI_KDS
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))

# 1. Veriyi Yükleme ve Tarih Formatına Çevirme
# CSV'nin bulunduğu yol: Trak-AI_KDS/data/processed/master_feature_matrix_2017_2024.csv
csv_path = os.path.join(PROJECT_ROOT, 'data', 'processed', 'master_feature_matrix_2017_2024.csv')

print(f"Veri şu yoldan okunuyor: {csv_path}\n")
df = pd.read_csv(csv_path)
df['date'] = pd.to_datetime(df['date'])
df = df.sort_values('date')

# Modelde kullanılacak dinamik özellikler
features = ['t2m_mean', 't2m_max', 't2m_min', 'tp_sum', 'ssr_sum', 'e_sum', 'NDVI_int']

# 2. Ürüne Göre Sezon Ayrıştırıcı Fonksiyon (Kritik Adım)
def urune_gore_ayristir(data, urun_tipi):
    data = data.copy()
    data['month'] = data['date'].dt.month
    
    if urun_tipi == 'Bugday':
        mask = data['month'].isin([11, 12, 1, 2, 3, 4, 5, 6])
    elif urun_tipi == 'Aycicegi':
        mask = data['month'].isin([4, 5, 6, 7, 8, 9])
    else:
        mask = data['month'].isin(range(1, 13))
        
    filtered = data[mask].copy()
    filtered.drop('month', axis=1, inplace=True)
    return filtered

# 3. Zaman Serisi Pencereleme (Sliding Window) Fonksiyonu
def zaman_penceresi_olustur(data_array, pencere_boyutu, hedef_sutun_indeksi):
    X, y = [], []
    for i in range(len(data_array) - pencere_boyutu):
        X.append(data_array[i:(i + pencere_boyutu), :])
        y.append(data_array[i + pencere_boyutu, hedef_sutun_indeksi])
    return np.array(X), np.array(y)

# ==========================================
# ÇP2 ANA VERİ HAZIRLAMA AKIŞI
# ==========================================
if __name__ == "__main__":
    pencere_boyutu = 30
    hedef_indeks = features.index('NDVI_int') 

    print("Veri hazırlığı başlıyor...\n")

    # --- A. BUĞDAY İÇİN HAZIRLIK ---
    print("--- Buğday Verisi Hazırlanıyor ---")
    df_wheat = urune_gore_ayristir(df, 'Bugday')
    scaler_wheat = MinMaxScaler(feature_range=(0, 1))
    scaled_wheat = scaler_wheat.fit_transform(df_wheat[features])
    X_wheat, y_wheat = zaman_penceresi_olustur(scaled_wheat, pencere_boyutu, hedef_indeks)
    
    print(f"Buğday Girdi (X) Boyutu: {X_wheat.shape}")
    print(f"Buğday Çıktı (y) Boyutu: {y_wheat.shape}")
    
    np.save(os.path.join(BASE_DIR, 'X_wheat.npy'), X_wheat)
    np.save(os.path.join(BASE_DIR, 'y_wheat.npy'), y_wheat)
    print("Buğday verileri (npy) kaydedildi.\n")

    # --- B. AYÇİÇEĞİ İÇİN HAZIRLIK ---
    print("--- Ayçiçeği Verisi Hazırlanıyor ---")
    df_sun = urune_gore_ayristir(df, 'Aycicegi')
    scaler_sun = MinMaxScaler(feature_range=(0, 1))
    scaled_sun = scaler_sun.fit_transform(df_sun[features])
    X_sun, y_sun = zaman_penceresi_olustur(scaled_sun, pencere_boyutu, hedef_indeks)
    
    print(f"Ayçiçeği Girdi (X) Boyutu: {X_sun.shape}")
    print(f"Ayçiçeği Çıktı (y) Boyutu: {y_sun.shape}")

    np.save(os.path.join(BASE_DIR, 'X_sunflower.npy'), X_sun)
    np.save(os.path.join(BASE_DIR, 'y_sunflower.npy'), y_sun)
    print("Ayçiçeği verileri (npy) kaydedildi.\n")

    print("İşlem başarıyla tamamlandı!")
import cdsapi
import pandas as pd
import xarray as xr
import os
import calendar

# 1. CDS Client Başlatma
c = cdsapi.Client()

# 2. Pilot Bölge Koordinatları
lat, lon = 41.40, 27.35
area = [lat + 0.1, lon - 0.1, lat - 0.1, lon + 0.1]

print("Copernicus CDS üzerinden 2023 ERA5-Land verileri talep ediliyor...")
all_monthly_data = []

# Yılın 12 ayı için döngü
for month in range(1, 13):
    month_str = f"{month:02d}"
    _, num_days = calendar.monthrange(2023, month)
    days = [f"{d:02d}" for d in range(1, num_days + 1)]
    nc_filename = f'data/raw/era5_2023_{month_str}.nc'
    
    print(f"-> {month_str}. Ay verisi indiriliyor...")
    
    try:
        # Veriyi İndirme
        c.retrieve(
            'reanalysis-era5-land',
            {
                'variable': [
                    '2m_temperature',
                    'total_precipitation',
                    'surface_net_solar_radiation',
                    'total_evaporation'
                ],
                'year': '2023',
                'month': month_str,
                'day': days,
                'time': [f'{i:02d}:00' for i in range(24)],
                'area': area,
                'format': 'netcdf',
            },
            nc_filename
        )
        
        # 3. İnen Veriyi Anında İşleme (Motor Koruması Eklendi)
        ds = xr.open_dataset(nc_filename, engine='netcdf4')
        ds_point = ds.sel(latitude=lat, longitude=lon, method='nearest')
        
        # Saatlik veriyi GÜNLÜK ortalamaya çevir
        df_daily = ds_point.resample(time='1D').mean().to_dataframe().reset_index()
        all_monthly_data.append(df_daily)
        
        # Temizlik: Dosyayı kapat ve sil
        ds.close()
        os.remove(nc_filename)
        print(f"   {month_str}. Ay başarıyla işlendi ve .nc dosyası silindi.")
        
    except Exception as e:
        print(f"HATA ({month_str}. Ay): {e}")

# 4. Tüm Ayları Birleştirme
if all_monthly_data:
    print("\nTüm aylar başarıyla çekildi. Nihai CSV oluşturuluyor...")
    final_df = pd.concat(all_monthly_data, ignore_index=True)
    
    # Agronomik Birim Dönüşümleri
    final_df['t2m_celsius'] = final_df['t2m'] - 273.15 # Kelvin -> Santigrat
    final_df['tp_mm'] = final_df['tp'] * 1000          # Metre -> Milimetre
    
    # Gerekli sütunları seçme ve isimlendirme
    final_df = final_df[['time', 't2m_celsius', 'tp_mm', 'ssr', 'e']]
    final_df.rename(columns={'time': 'date', 'ssr': 'radiation', 'e': 'evaporation'}, inplace=True)
    final_df['date'] = final_df['date'].dt.strftime('%Y-%m-%d')
    
    # Kayıt
    csv_file_path = 'data/raw/era5_2023.csv'
    final_df.to_csv(csv_file_path, index=False)
    
    print(f"BAŞARILI: {len(final_df)} günlük (1 tam yıl) iklim verisi kaydedildi.")
    print(f"Dosya Yolu: {csv_file_path}")
else:
    print("Veri çekilemediği için birleştirme işlemi yapılamadı.")
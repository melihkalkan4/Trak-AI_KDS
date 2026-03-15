"""
=====================================================================================
ERA5-LAND İKLİM VERİSİ MODÜLÜ - TAM ÇALIŞAN VERSİYON
=====================================================================================
Bu dosyayı kullanın: python era5_module_WORKING.py
=====================================================================================
"""

import cdsapi
import pandas as pd
import xarray as xr
import os
import calendar
import zipfile
import traceback
from pathlib import Path
import warnings

warnings.filterwarnings("ignore")

# =====================================================================================
# YARDIMCI FONKSİYONLAR
# =====================================================================================

def download_monthly_data(client, year, month, area, variables, output_file):
    """Belirtilen ay için ERA5-Land verilerini indir"""
    month_str = f"{month:02d}"
    _, num_days = calendar.monthrange(year, month)
    days = [f"{d:02d}" for d in range(1, num_days + 1)]
    hours = [f'{h:02d}:00' for h in range(24)]
    
    print(f"   📥 İndiriliyor: {year}-{month_str} ({num_days} gün)")
    
    try:
        client.retrieve(
            'reanalysis-era5-land',
            {
                'variable': variables,
                'year': str(year),
                'month': month_str,
                'day': days,
                'time': hours,
                'area': area,
                'format': 'netcdf',
            },
            output_file
        )
        
        if os.path.exists(output_file):
            size_mb = os.path.getsize(output_file) / (1024 * 1024)
            print(f"   ✅ İndirildi: {size_mb:.2f} MB")
            
            if size_mb < 0.05:
                print(f"   ⚠️  UYARI: Dosya boyutu çok küçük!")
                return False
            
            return True
        else:
            print(f"   ❌ Dosya oluşmadı")
            return False
            
    except Exception as e:
        print(f"   ❌ İndirme hatası: {str(e)[:100]}")
        return False


def extract_netcdf_from_zip(zip_file, extract_dir):
    """ZIP dosyasından NetCDF'i çıkar - KRİTİK FONKSİYON"""
    print(f"   📂 ZIP dosyası işleniyor...")
    
    try:
        # Önce ZIP mi kontrol et
        is_zip = zipfile.is_zipfile(zip_file)
        print(f"      Dosya tipi: {'ZIP arşivi' if is_zip else 'Direkt dosya'}")
        
        if not is_zip:
            # ZIP değilse direkt .nc olarak yeniden adlandır
            nc_file = str(zip_file).replace('.zip', '.nc')
            print(f"      ZIP değil, yeniden adlandırılıyor: {os.path.basename(nc_file)}")
            os.rename(zip_file, nc_file)
            return nc_file
        
        # ZIP ise aç ve çıkar
        print(f"      ZIP açılıyor...")
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            print(f"      ZIP içeriği: {file_list}")
            
            nc_files = [f for f in file_list if f.endswith('.nc')]
            
            if not nc_files:
                print(f"   ❌ ZIP içinde .nc dosyası yok!")
                return None
            
            nc_filename = nc_files[0]
            print(f"      NetCDF bulundu: {nc_filename}")
            
            # Çıkar
            zip_ref.extract(nc_filename, extract_dir)
            nc_filepath = os.path.join(extract_dir, nc_filename)
            
            print(f"   ✅ Çıkarıldı: {nc_filepath}")
            return nc_filepath
            
    except Exception as e:
        print(f"   ❌ ZIP hatası: {str(e)[:100]}")
        import traceback
        traceback.print_exc()
        return None


def open_netcdf_with_fallback(nc_file):
    """NetCDF'i farklı engine'lerle açmayı dene"""
    print(f"   ⚙️  NetCDF açılıyor: {os.path.basename(nc_file)}")
    
    # Dosya var mı kontrol et
    if not os.path.exists(nc_file):
        print(f"   ❌ Dosya bulunamadı: {nc_file}")
        return None
    
    file_size = os.path.getsize(nc_file)
    print(f"      Dosya boyutu: {file_size / (1024*1024):.2f} MB")
    
    engines = ['netcdf4', 'h5netcdf', 'scipy', None]
    
    for engine in engines:
        try:
            engine_name = engine if engine else 'otomatik'
            print(f"      {engine_name} engine deneniyor...")
            ds = xr.open_dataset(nc_file, engine=engine)
            print(f"   ✅ Açıldı: {engine_name} engine")
            print(f"      Boyutlar: {list(ds.dims)}")
            print(f"      Değişkenler: {list(ds.data_vars)}")
            return ds
        except Exception as e:
            print(f"      ❌ {engine_name} başarısız: {str(e)[:80]}")
            if engine is None:
                print(f"   ❌ Hiçbir engine çalışmadı!")
            continue
    
    return None


def process_netcdf_to_daily(ds, lat, lon):
    """NetCDF verisini işleyip günlük agronomik özet çıkar"""
    print(f"   🔄 Veri işleniyor (saatlik → günlük)...")
    
    try:
        # Boyut isimlerini otomatik bul
        time_dims = [dim for dim in ds.dims if 'time' in dim.lower()]
        if not time_dims:
            print(f"   ❌ Zaman boyutu bulunamadı! Boyutlar: {list(ds.dims)}")
            return None
        
        time_dim = time_dims[0]
        print(f"      Zaman boyutu: {time_dim}")
        
        lat_dims = [dim for dim in ds.dims if 'lat' in dim.lower()]
        lon_dims = [dim for dim in ds.dims if 'lon' in dim.lower()]
        
        if not lat_dims or not lon_dims:
            print(f"   ❌ Konum boyutları bulunamadı!")
            return None
        
        lat_dim = lat_dims[0]
        lon_dim = lon_dims[0]
        print(f"      Konum boyutları: {lat_dim}, {lon_dim}")
        
        # En yakın nokta seç
        sel_dict = {lat_dim: lat, lon_dim: lon}
        ds_point = ds.sel(sel_dict, method='nearest')
        
        # Saatlik veriyi DataFrame'e çevir
        df_hourly = ds_point.to_dataframe().reset_index()
        print(f"      Saatlik kayıt sayısı: {len(df_hourly)}")
        
        # Tarih sütunu ekle
        df_hourly['date'] = pd.to_datetime(df_hourly[time_dim]).dt.date
        
        # Günlük agregasyon kuralları
        agg_dict = {}
        
        if 't2m' in df_hourly.columns:
            agg_dict['t2m'] = ['mean', 'min', 'max']
        
        if 'd2m' in df_hourly.columns:
            agg_dict['d2m'] = ['mean']
        
        if 'tp' in df_hourly.columns:
            agg_dict['tp'] = ['sum']
        
        if 'ssr' in df_hourly.columns:
            agg_dict['ssr'] = ['sum']
        
        if 'e' in df_hourly.columns:
            agg_dict['e'] = ['sum']
        
        print(f"      Agregasyon kuralları: {list(agg_dict.keys())}")
        
        # Günlük agregasyon yap
        df_daily = df_hourly.groupby('date').agg(agg_dict).reset_index()
        
        # Multi-index sütun isimlerini düzleştir
        new_cols = ['date']
        for col in df_daily.columns[1:]:
            if isinstance(col, tuple):
                new_cols.append(f"{col[0]}_{col[1]}")
            else:
                new_cols.append(col)
        
        df_daily.columns = new_cols
        
        print(f"   ✅ İşlendi: {len(df_daily)} gün")
        print(f"      Sütunlar: {list(df_daily.columns)}")
        
        return df_daily
        
    except Exception as e:
        print(f"   ❌ İşleme hatası: {str(e)[:150]}")
        import traceback
        traceback.print_exc()
        return None


def convert_to_agronomic_units(df):
    """SI birimlerini agronomik birimlere çevir"""
    df_conv = df.copy()
    
    # Sıcaklık: Kelvin → Celsius
    temp_cols = ['t2m_mean', 't2m_min', 't2m_max', 'd2m_mean']
    for col in temp_cols:
        if col in df_conv.columns:
            df_conv[col] = df_conv[col] - 273.15
    
    # Yağış: Metre → Milimetre
    if 'tp_sum' in df_conv.columns:
        df_conv['tp_sum'] = df_conv['tp_sum'] * 1000
    
    # Yuvarlama (4 ondalık)
    for col in df_conv.select_dtypes(include=['float64', 'float32']).columns:
        df_conv[col] = df_conv[col].round(4)
    
    return df_conv


def cleanup_files(*files):
    """Belirtilen dosyaları sil"""
    for file in files:
        if file and os.path.exists(file):
            try:
                os.remove(file)
                print(f"      🗑️  Silindi: {os.path.basename(file)}")
            except Exception as e:
                print(f"      ⚠️  Silinemedi: {os.path.basename(file)}")


# =====================================================================================
# ANA MODÜL FONKSİYONU
# =====================================================================================

def fetch_era5_data(start_year, end_year, lat, lon, test_mode=False):
    """
    ERA5-Land iklim verilerini indir ve işle
    
    Returns:
        pd.DataFrame: Günlük iklim verileri
            - date: Tarih
            - t2m_mean: Ortalama sıcaklık (°C)
            - t2m_min: Minimum sıcaklık (°C)
            - t2m_max: Maksimum sıcaklık (°C)
            - d2m_mean: Ortalama çiy noktası (°C)
            - tp_sum: Toplam yağış (mm)
            - ssr_sum: Toplam radyasyon (J/m²)
            - e_sum: Toplam buharlaşma (m)
    """
    
    print("\n" + "="*80)
    print(f"🌦️  ERA5-LAND İKLİM VERİSİ İNDİRME MODÜLÜ")
    print("="*80)
    print(f"Dönem: {start_year}-{end_year}")
    print(f"Konum: Lat={lat}, Lon={lon}")
    print(f"Mod: {'TEST (sadece 1 ay)' if test_mode else 'TAM (tüm aylar)'}")
    print("="*80)
    
    # CDS Client başlat
    try:
        client = cdsapi.Client()
        print("✅ CDS API bağlantısı başarılı")
    except Exception as e:
        print(f"❌ CDS API bağlantı hatası: {e}")
        return pd.DataFrame()
    
    # Alan tanımla
    area = [lat + 0.1, lon - 0.1, lat - 0.1, lon + 0.1]
    
    # Klasörler
    DATA_DIR = Path('data/raw')
    TEMP_DIR = DATA_DIR / 'temp_extract'
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    
    # İndirilecek değişkenler
    variables = [
        '2m_temperature',
        '2m_dewpoint_temperature',
        'total_precipitation',
        'surface_net_solar_radiation',
        'total_evaporation'
    ]
    
    all_daily_data = []
    failed_months = []
    
    # Ana döngü
    for year in range(start_year, end_year + 1):
        end_month = 1 if test_mode else 12
        
        for month in range(1, end_month + 1):
            month_str = f"{month:02d}"
            
            print(f"\n{'─'*80}")
            print(f"📅 İŞLENİYOR: {year}-{month_str}")
            print(f"{'─'*80}")
            
            zip_file = str(DATA_DIR / f'era5_{year}_{month_str}.zip')
            nc_file = None
            
            try:
                # ADIM 1: İNDİR
                success = download_monthly_data(client, year, month, area, variables, zip_file)
                if not success:
                    print(f"   ❌ İndirme başarısız")
                    failed_months.append(f"{year}-{month_str}")
                    continue
                
                # ADIM 2: ZIP'TEN ÇIKAR
                nc_file = extract_netcdf_from_zip(zip_file, str(TEMP_DIR))
                if not nc_file:
                    print(f"   ❌ ZIP çıkarma başarısız")
                    failed_months.append(f"{year}-{month_str}")
                    cleanup_files(zip_file)
                    continue
                
                # ADIM 3: NETCDF AÇ
                ds = open_netcdf_with_fallback(nc_file)
                if ds is None:
                    print(f"   ❌ NetCDF açma başarısız")
                    failed_months.append(f"{year}-{month_str}")
                    cleanup_files(zip_file, nc_file)
                    continue
                
                # ADIM 4: VERİYİ İŞLE
                df_daily = process_netcdf_to_daily(ds, lat, lon)
                ds.close()
                
                if df_daily is None:
                    print(f"   ❌ Veri işleme başarısız")
                    failed_months.append(f"{year}-{month_str}")
                    cleanup_files(zip_file, nc_file)
                    continue
                
                # Başarılı!
                all_daily_data.append(df_daily)
                print(f"   ✅ {year}-{month_str} BAŞARILI!")
                
                # ADIM 5: TEMİZLE
                cleanup_files(zip_file, nc_file)
                
            except Exception as e:
                print(f"\n   ❌ Beklenmeyen hata: {str(e)[:100]}")
                traceback.print_exc()
                failed_months.append(f"{year}-{month_str}")
                cleanup_files(zip_file, nc_file)
    
    # Geçici klasörü temizle
    try:
        if TEMP_DIR.exists():
            for file in TEMP_DIR.iterdir():
                file.unlink()
            TEMP_DIR.rmdir()
            print(f"\n🗑️  Geçici klasör temizlendi")
    except:
        pass
    
    # Sonuçları birleştir
    if not all_daily_data:
        print("\n" + "="*80)
        print("❌ HİÇBİR VERİ İŞLENEMEDİ")
        print("="*80)
        if failed_months:
            print(f"Başarısız aylar: {failed_months}")
        return pd.DataFrame()
    
    print("\n" + "="*80)
    print("🔄 VERİLER BİRLEŞTİRİLİYOR")
    print("="*80)
    
    combined_df = pd.concat(all_daily_data, ignore_index=True)
    print(f"Toplam kayıt (birleştirme öncesi): {len(combined_df)}")
    
    # Agronomik birimlere çevir
    print("🔄 Birim dönüşümleri yapılıyor...")
    final_df = convert_to_agronomic_units(combined_df)
    
    # Tarihi datetime'a çevir ve sırala
    final_df['date'] = pd.to_datetime(final_df['date'])
    final_df = final_df.sort_values('date').reset_index(drop=True)
    
    # Özet
    print("\n" + "="*80)
    print("✅ ERA5 MODÜLÜ TAMAMLANDI")
    print("="*80)
    print(f"Toplam kayıt: {len(final_df)} gün")
    print(f"Tarih aralığı: {final_df['date'].min().date()} → {final_df['date'].max().date()}")
    print(f"Başarılı aylar: {len(all_daily_data)}")
    
    if failed_months:
        print(f"⚠️  Başarısız aylar ({len(failed_months)}): {failed_months}")
    
    print(f"\nSütunlar: {list(final_df.columns)}")
    
    if len(final_df) > 0:
        print("\n📊 İLK 3 SATIR:")
        print(final_df.head(3).to_string(index=False))
    
    print("="*80)
    
    return final_df


# =====================================================================================
# TEST BÖLÜMÜ
# =====================================================================================

if __name__ == "__main__":
    print("\n" + "="*80)
    print("ERA5 MODÜL TESTİ BAŞLIYOR")
    print("="*80)
    
    # Test parametreleri
    TEST_LAT = 41.40
    TEST_LON = 27.35
    TEST_YEAR = 2023
    
    print(f"\nTest Parametreleri:")
    print(f"  Konum: {TEST_LAT}N, {TEST_LON}E")
    print(f"  Yıl: {TEST_YEAR}")
    print(f"  Mod: TEST (sadece Ocak ayı)")
    
    # Test et
    df_test = fetch_era5_data(
        start_year=TEST_YEAR,
        end_year=TEST_YEAR,
        lat=TEST_LAT,
        lon=TEST_LON,
        test_mode=True
    )
    
    print("\n" + "="*80)
    print("TEST SONUÇLARI")
    print("="*80)
    
    if not df_test.empty:
        print("✅ TEST BAŞARILI!")
        print(f"\nVeri boyutu: {df_test.shape}")
        print(f"Sütunlar: {list(df_test.columns)}")
        
        print(f"\nİlk 5 satır:")
        print(df_test.head())
        
        # İstatistikler
        if 't2m_mean' in df_test.columns:
            print(f"\n📊 SICAKLIK İSTATİSTİKLERİ:")
            print(f"  Ortalama: {df_test['t2m_mean'].mean():.1f}°C")
            print(f"  Minimum: {df_test['t2m_min'].min():.1f}°C")
            print(f"  Maksimum: {df_test['t2m_max'].max():.1f}°C")
        
        if 'tp_sum' in df_test.columns:
            print(f"\n🌧️  YAĞIŞ İSTATİSTİKLERİ:")
            print(f"  Toplam: {df_test['tp_sum'].sum():.1f} mm")
            print(f"  Günlük ortalama: {df_test['tp_sum'].mean():.2f} mm")
        
        print("\n✅ Modül tam çalışır durumda!")
        
    else:
        print("❌ TEST BAŞARISIZ - Veri boş!")
        print("\nLütfen şunları kontrol edin:")
        print("  1. netCDF4 yüklü mü: pip install netCDF4")
        print("  2. CDS hesabı aktif mi")
        print("  3. Lisanslar kabul edildi mi")
    
    print("="*80)
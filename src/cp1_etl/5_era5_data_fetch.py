"""
=====================================================================================
ERA5-LAND İKLİM VERİSİ İNDİRME SİSTEMİ
=====================================================================================
Amaç: Copernicus CDS'den 2023 yılı ERA5-Land verilerini indirip işlemek
Bölge: Trakya (Lat: 41.40, Lon: 27.35)
Değişkenler: Sıcaklık, Yağış, Güneş Radyasyonu, Buharlaşma
Çıktı: data/raw/era5_2023.csv (365 günlük veri)
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

# =====================================================================================
# BÖLÜM 1: YAPILANDIRMA VE BAŞLATMA
# =====================================================================================

print("="*90)
print(" "*30 + "ERA5-LAND VERİ İNDİRME")
print("="*90)

# Bölge koordinatları (Trakya pilot bölgesi)
LAT, LON = 41.40, 27.35
AREA = [LAT + 0.1, LON - 0.1, LAT - 0.1, LON + 0.1]  # [Kuzey, Batı, Güney, Doğu]

# Yıl
YEAR = 2023

# Klasör yapısı
DATA_DIR = Path('data/raw')
TEMP_DIR = DATA_DIR / 'temp_extract'
DATA_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# İndirilecek değişkenler
VARIABLES = [
    '2m_temperature',              # 2 metre yükseklikteki hava sıcaklığı
    'total_precipitation',         # Toplam yağış
    'surface_net_solar_radiation', # Yüzey net güneş radyasyonu
    'total_evaporation'            # Toplam buharlaşma
]

print(f"\nYapılandırma:")
print(f"  Bölge Merkezi: Lat={LAT}°, Lon={LON}°")
print(f"  Alan: {AREA}")
print(f"  Yıl: {YEAR}")
print(f"  Değişkenler: {len(VARIABLES)} adet")
print(f"  Veri klasörü: {DATA_DIR}")
print("="*90)

# CDS Client başlat
try:
    client = cdsapi.Client()
    print("\n✅ Copernicus CDS bağlantısı başarılı")
except Exception as e:
    print(f"\n❌ CDS Client başlatılamadı: {e}")
    print("\nLütfen ~/.cdsapirc dosyanızı kontrol edin:")
    print("  url: https://cds.climate.copernicus.eu/api")
    print("  key: {UID}:{API-KEY}")
    exit(1)

# =====================================================================================
# BÖLÜM 2: YARDIMCI FONKSİYONLAR
# =====================================================================================

def download_monthly_data(client, year, month, area, variables, output_file):
    """
    Belirtilen ay için ERA5-Land verilerini indir
    
    Args:
        client: CDS API client
        year: Yıl (int)
        month: Ay (int, 1-12)
        area: Bölge koordinatları [N, W, S, E]
        variables: İndirilecek değişkenler listesi
        output_file: Çıktı dosyası yolu (ZIP olarak kaydedilir)
    
    Returns:
        bool: İndirme başarılı ise True
    """
    month_str = f"{month:02d}"
    _, num_days = calendar.monthrange(year, month)
    days = [f"{d:02d}" for d in range(1, num_days + 1)]
    hours = [f'{h:02d}:00' for h in range(24)]
    
    print(f"\n  📥 İndiriliyor: {year}-{month_str} ({num_days} gün)")
    
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
        
        # Dosya boyutu kontrolü
        if os.path.exists(output_file):
            size_mb = os.path.getsize(output_file) / (1024 * 1024)
            print(f"  ✅ İndirildi: {size_mb:.2f} MB")
            return True
        else:
            print(f"  ❌ Dosya oluşmadı: {output_file}")
            return False
            
    except Exception as e:
        print(f"  ❌ İndirme hatası: {str(e)[:80]}")
        return False


def extract_netcdf_from_zip(zip_file, extract_dir):
    """
    ZIP dosyasından NetCDF dosyasını çıkar
    
    Args:
        zip_file: ZIP dosya yolu
        extract_dir: Çıkarılacak klasör
    
    Returns:
        str: NetCDF dosya yolu veya None
    """
    print(f"  📂 ZIP açılıyor...")
    
    try:
        # ZIP mi kontrol et
        if not zipfile.is_zipfile(zip_file):
            print(f"  ⚠️  ZIP değil, muhtemelen direkt NetCDF dosyası")
            # Dosyayı .nc olarak yeniden adlandır
            nc_file = str(zip_file).replace('.zip', '.nc')
            os.rename(zip_file, nc_file)
            return nc_file
        
        # ZIP'i aç
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            
            # NetCDF dosyalarını bul
            nc_files = [f for f in file_list if f.endswith('.nc')]
            
            if not nc_files:
                print(f"  ❌ ZIP içinde .nc dosyası yok! İçerik: {file_list}")
                return None
            
            # İlk NetCDF'i çıkar
            nc_filename = nc_files[0]
            zip_ref.extract(nc_filename, extract_dir)
            nc_filepath = os.path.join(extract_dir, nc_filename)
            
            print(f"  ✅ Çıkarıldı: {nc_filename}")
            return nc_filepath
            
    except Exception as e:
        print(f"  ❌ ZIP hatası: {str(e)[:80]}")
        return None


def open_netcdf_with_fallback(nc_file):
    """
    NetCDF dosyasını farklı engine'lerle açmaya çalış
    
    Args:
        nc_file: NetCDF dosya yolu
    
    Returns:
        xarray.Dataset veya None
    """
    print(f"  ⚙️  NetCDF açılıyor...")
    
    # Denenecek engine'ler (öncelik sırasına göre)
    engines = ['netcdf4', 'h5netcdf', 'scipy', None]
    
    for engine in engines:
        try:
            engine_name = engine if engine else 'otomatik'
            ds = xr.open_dataset(nc_file, engine=engine)
            print(f"  ✅ Açıldı: {engine_name} engine")
            return ds
        except Exception as e:
            if engine is None:  # Son deneme de başarısız
                print(f"  ❌ Hiçbir engine çalışmadı!")
                print(f"     Son hata: {str(e)[:80]}")
            continue
    
    return None


def process_netcdf_to_daily(ds, lat, lon):
    """
    NetCDF verisini işleyip günlük DataFrame'e çevir
    
    Args:
        ds: xarray.Dataset
        lat: Enlem
        lon: Boylam
    
    Returns:
        pd.DataFrame: Günlük iklim verileri
    """
    print(f"  🔄 Veri işleniyor...")
    
    try:
        # Zaman boyutunun adını bul (genellikle 'time' veya 'valid_time')
        time_dims = [dim for dim in ds.dims if 'time' in dim.lower()]
        if not time_dims:
            print(f"  ❌ Zaman boyutu bulunamadı! Mevcut boyutlar: {list(ds.dims)}")
            return None
        
        time_dim = time_dims[0]
        print(f"     Zaman boyutu: {time_dim}")
        
        # Konum boyutlarının adını bul
        lat_dims = [dim for dim in ds.dims if 'lat' in dim.lower()]
        lon_dims = [dim for dim in ds.dims if 'lon' in dim.lower()]
        
        if not lat_dims or not lon_dims:
            print(f"  ❌ Konum boyutları bulunamadı! Boyutlar: {list(ds.dims)}")
            return None
        
        lat_dim = lat_dims[0]
        lon_dim = lon_dims[0]
        print(f"     Konum boyutları: {lat_dim}, {lon_dim}")
        
        # En yakın nokta seç (dinamik boyut adlarıyla)
        sel_dict = {lat_dim: lat, lon_dim: lon}
        ds_point = ds.sel(sel_dict, method='nearest')
        
        # Saatlik veriyi günlük ortalamaya çevir (dinamik zaman boyutuyla)
        df_daily = ds_point.resample({time_dim: '1D'}).mean().to_dataframe().reset_index()
        
        # Zaman sütununu 'time' olarak yeniden adlandır
        if time_dim != 'time':
            df_daily.rename(columns={time_dim: 'time'}, inplace=True)
        
        print(f"  ✅ İşlendi: {len(df_daily)} gün")
        return df_daily
        
    except Exception as e:
        print(f"  ❌ İşleme hatası: {str(e)[:120]}")
        print(f"     Dataset boyutları: {list(ds.dims)}")
        print(f"     Dataset değişkenleri: {list(ds.data_vars)}")
        return None


def cleanup_files(*files):
    """Belirtilen dosyaları sil"""
    for file in files:
        if file and os.path.exists(file):
            try:
                os.remove(file)
            except:
                pass


def convert_to_agronomic_units(df):
    """
    SI birimlerini agronomik birimlere çevir
    
    Args:
        df: Ham veri DataFrame
    
    Returns:
        pd.DataFrame: Dönüştürülmüş veri
    """
    df_converted = df.copy()
    
    # Sıcaklık: Kelvin → Santigrat
    df_converted['t2m_celsius'] = df_converted['t2m'] - 273.15
    
    # Yağış: Metre → Milimetre
    df_converted['tp_mm'] = df_converted['tp'] * 1000
    
    # Gerekli sütunları seç ve yeniden adlandır
    final_df = df_converted[['time', 't2m_celsius', 'tp_mm', 'ssr', 'e']].copy()
    final_df.rename(columns={
        'time': 'date',
        'ssr': 'radiation',
        'e': 'evaporation'
    }, inplace=True)
    
    # Tarihi string formatına çevir
    final_df['date'] = pd.to_datetime(final_df['date']).dt.strftime('%Y-%m-%d')
    
    return final_df


# =====================================================================================
# BÖLÜM 3: ANA İŞLEM DÖNGÜSÜ (12 AY)
# =====================================================================================

print("\n" + "="*90)
print(" "*35 + "AYLARA GÖRE İNDİRME")
print("="*90)

all_monthly_data = []
failed_months = []

for month in range(1, 13):
    month_str = f"{month:02d}"
    
    print(f"\n{'─'*90}")
    print(f"  AY {month:02d}/12 - {calendar.month_name[month]} {YEAR}")
    print(f"{'─'*90}")
    
    # Dosya adları
    zip_file = DATA_DIR / f'era5_{YEAR}_{month_str}.zip'
    nc_file = None
    
    try:
        # ADIM 1: Veriyi İndir
        success = download_monthly_data(
            client=client,
            year=YEAR,
            month=month,
            area=AREA,
            variables=VARIABLES,
            output_file=str(zip_file)
        )
        
        if not success:
            failed_months.append(month)
            continue
        
        # ADIM 2: ZIP'ten NetCDF Çıkar
        nc_file = extract_netcdf_from_zip(str(zip_file), str(TEMP_DIR))
        
        if not nc_file:
            failed_months.append(month)
            cleanup_files(zip_file)
            continue
        
        # ADIM 3: NetCDF'i Aç
        ds = open_netcdf_with_fallback(nc_file)
        
        if ds is None:
            failed_months.append(month)
            cleanup_files(zip_file, nc_file)
            continue
        
        # ADIM 4: Veriyi İşle
        df_daily = process_netcdf_to_daily(ds, LAT, LON)
        ds.close()
        
        if df_daily is None:
            failed_months.append(month)
            cleanup_files(zip_file, nc_file)
            continue
        
        # Başarılı - veriyi sakla
        all_monthly_data.append(df_daily)
        
        # ADIM 5: Temizlik
        cleanup_files(zip_file, nc_file)
        print(f"  🗑️  Geçici dosyalar temizlendi")
        print(f"  ✅ {month_str}. ay başarıyla tamamlandı!")
        
    except Exception as e:
        print(f"\n  ❌ Beklenmeyen hata ({month_str}. ay):")
        print(f"     {str(e)}")
        print("\n  Detaylı hata:")
        traceback.print_exc()
        
        failed_months.append(month)
        cleanup_files(zip_file, nc_file)


# Geçici klasörü temizle
try:
    if TEMP_DIR.exists():
        for file in TEMP_DIR.iterdir():
            file.unlink()
        TEMP_DIR.rmdir()
        print(f"\n🗑️  Geçici klasör temizlendi: {TEMP_DIR}")
except:
    pass


# =====================================================================================
# BÖLÜM 4: VERİLERİ BİRLEŞTİR VE KAYDET
# =====================================================================================

print("\n" + "="*90)
print(" "*35 + "VERİ BİRLEŞTİRME")
print("="*90)

if not all_monthly_data:
    print("\n❌ HİÇBİR AY VERİSİ İNDİRİLEMEDİ!")
    print(f"\nBaşarısız aylar: {failed_months}")
    print("\nLütfen şunları kontrol edin:")
    print("  1. İnternet bağlantınız")
    print("  2. CDS hesap bilgileriniz")
    print("  3. Lisansların kabul edilmiş olması")
    print("  4. netCDF4 kütüphanesinin yüklü olması: pip install netCDF4")
    exit(1)

if failed_months:
    print(f"\n⚠️  UYARI: {len(failed_months)} ay indirilemedi: {failed_months}")
    print(f"✅ {len(all_monthly_data)} ay başarılı")

# Tüm ayları birleştir
print(f"\n🔄 {len(all_monthly_data)} aylık veri birleştiriliyor...")
combined_df = pd.concat(all_monthly_data, ignore_index=True)

# Agronomik birimlere çevir
print("🔄 Birim dönüşümleri yapılıyor...")
final_df = convert_to_agronomic_units(combined_df)

# Sıralama ve kontrol
final_df = final_df.sort_values('date').reset_index(drop=True)

# CSV olarak kaydet
output_csv = DATA_DIR / f'era5_{YEAR}.csv'
final_df.to_csv(output_csv, index=False)

print(f"💾 CSV dosyası kaydedildi: {output_csv}")


# =====================================================================================
# BÖLÜM 5: ÖZET VE İSTATİSTİKLER
# =====================================================================================

print("\n" + "="*90)
print(" "*35 + "İŞLEM TAMAMLANDI")
print("="*90)

print(f"\n📊 VERİ ÖZETİ:")
print(f"  {'─'*86}")
print(f"  Toplam kayıt sayısı    : {len(final_df)} gün")
print(f"  Tarih aralığı          : {final_df['date'].min()} → {final_df['date'].max()}")
print(f"  Başarılı aylar         : {len(all_monthly_data)}/12")
print(f"  Başarısız aylar        : {len(failed_months)}/12 {failed_months if failed_months else ''}")
print(f"  {'─'*86}")

print(f"\n📁 ÇIKTI DOSYASI:")
print(f"  {'─'*86}")
print(f"  Dosya yolu             : {output_csv}")
print(f"  Dosya boyutu           : {os.path.getsize(output_csv)/1024:.2f} KB")
print(f"  Sütunlar               : {list(final_df.columns)}")
print(f"  {'─'*86}")

print(f"\n🌡️  İKLİM İSTATİSTİKLERİ ({YEAR}):")
print(f"  {'─'*86}")
print(f"  Ortalama sıcaklık      : {final_df['t2m_celsius'].mean():.1f}°C")
print(f"  Minimum sıcaklık       : {final_df['t2m_celsius'].min():.1f}°C")
print(f"  Maksimum sıcaklık      : {final_df['t2m_celsius'].max():.1f}°C")
print(f"  Toplam yağış           : {final_df['tp_mm'].sum():.1f} mm")
print(f"  Ortalama günlük yağış  : {final_df['tp_mm'].mean():.2f} mm")
print(f"  Ortalama radyasyon     : {final_df['radiation'].mean():.0f} J/m²")
print(f"  Ortalama buharlaşma    : {final_df['evaporation'].mean():.6f} m")
print(f"  {'─'*86}")

print("\n" + "="*90)
print(" "*30 + "✅ TÜM İŞLEMLER TAMAMLANDI")
print("="*90)

print(f"\n💡 SONRAKİ ADIMLAR:")
print(f"  1. Veriyi kontrol edin: {output_csv}")
print(f"  2. Pandas ile analiz yapabilirsiniz:")
print(f"     df = pd.read_csv('{output_csv}')")
print(f"     df.head()")
print(f"  3. Eksik aylar varsa tekrar indirin (aylar: {failed_months})")

print("\n" + "="*90)
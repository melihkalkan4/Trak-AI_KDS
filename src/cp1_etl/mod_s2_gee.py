import ee
import json
import pandas as pd
import eemont

def fetch_s2_data(start_year, end_year, roi_coords, key_path='keys/trak-ai-kds-d3e5e5b6e168.json'):
    print(f"🛰️ Sentinel-2: {start_year}-{end_year} arası uydu indeksleri (NDVI, EVI, NDWI) çekiliyor...")
    
    # GEE Yetkilendirme
    try:
        with open(key_path, 'r') as f:
            credentials = ee.ServiceAccountCredentials(json.load(f)['client_email'], key_path)
        ee.Initialize(credentials)
    except Exception as e:
        print(f"❌ GEE Kimlik Doğrulama Hatası: {e}")
        return pd.DataFrame()

    roi = ee.Geometry.Polygon([roi_coords])
    
    # Eemont ile otomatik maskeleme ve 3 farklı indeks hesaplama
    try:
        dataset = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
            .filterBounds(roi)
            .filterDate(f'{start_year}-01-01', f'{end_year}-12-31')
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 70))
            .maskClouds()
            .scaleAndOffset()
            .spectralIndices(['NDVI', 'EVI', 'NDWI'])) # Teze uygun 3 indeks

        def get_stats(image):
            stats = image.reduceRegion(reducer=ee.Reducer.mean(), geometry=roi, scale=10, maxPixels=1e9)
            # DÜZELTME BURADA: 'YYYY-MM-DD' yerine 'YYYY-MM-dd' kullanıyoruz
            return ee.Feature(None, stats).set('date', image.date().format('YYYY-MM-dd'))

        # Veriyi çekme süreci
        print("   Veriler GEE sunucularında işleniyor, lütfen bekleyin...")
        features = dataset.map(get_stats).getInfo()['features']
        
        data = []
        for f in features:
            props = f['properties']
            # Eğer o gün bulutlardan dolayı NDVI hesaplanamadıysa atla
            if props.get('NDVI') is not None:
                data.append({
                    'date': props['date'],
                    'NDVI': round(props['NDVI'], 4),
                    'EVI': round(props['EVI'], 4),
                    'NDWI': round(props['NDWI'], 4)
                })
                
        df = pd.DataFrame(data)
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            # Aynı güne denk gelen geçişlerin (farklı uydu kiremitleri) ortalamasını al
            df = df.groupby('date').mean().reset_index() 
            df = df.sort_values('date').reset_index(drop=True)
            
        print(f"✅ Sentinel-2 verisi başarıyla çekildi ({len(df)} net uydu geçişi).")
        return df

    except Exception as e:
        print(f"❌ Sentinel-2 Veri Çekme Hatası: {e}")
        return pd.DataFrame()

# Eğer bu dosya tek başına çalıştırılırsa test et:
if __name__ == "__main__":
    test_coords = [[27.30, 41.35], [27.32, 41.35], [27.32, 41.37], [27.30, 41.37]]
    # Sadece küçük bir testi hızlıca yapmak için 1 aylık süre veriyoruz
    df_test = fetch_s2_data(2023, 2023, test_coords)
    print("\nTest Çıktısı (İlk 5 Satır):")
    print(df_test.head())
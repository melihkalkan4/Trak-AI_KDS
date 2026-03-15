import ee
import json

def fetch_soil_data(lat, lon, key_path='keys/trak-ai-kds-d3e5e5b6e168.json'):
    print(f"🌍 SoilGrids: Kök derinliği toprak profili çekiliyor (Lat: {lat}, Lon: {lon})...")
    
    # GEE Yetkilendirme
    try:
        with open(key_path, 'r') as f:
            credentials = ee.ServiceAccountCredentials(json.load(f)['client_email'], key_path)
        ee.Initialize(credentials)
    except Exception as e:
        print(f"❌ GEE Kimlik Doğrulama Hatası: {e}")
        return {}

    # Teze uygun derinlikler ve özellikler
    depths = ['0-5cm', '5-15cm', '15-30cm']
    properties = ['clay', 'sand', 'phh2o']
    results = {}

    for prop in properties:
        for depth in depths:
            asset_id = f'projects/soilgrids-isric/{prop}_mean'
            band_name = f'{prop}_{depth}_mean'
            
            try:
                img = ee.Image(asset_id).select(band_name)
                
                # Projeksiyon ve ölçek düzeltmeleri (Önceki testte çözdüğümüz bug)
                proj = img.projection()
                native_scale = proj.nominalScale()
                region = ee.Geometry.Point([lon, lat]).buffer(2000) # 2km buffer
                
                value = img.reduceRegion(
                    reducer=ee.Reducer.mean(), 
                    geometry=region, 
                    crs=proj, 
                    scale=native_scale, 
                    maxPixels=1e9, 
                    bestEffort=True
                ).getInfo()
                
                raw = value.get(band_name)
                if raw is not None:
                    # ISRIC 0.1 ölçekleme faktörü
                    results[f'{prop}_{depth}'] = round(raw * 0.1, 2) 
                else:
                    print(f"⚠️ {prop}_{depth} için değer okunamadı (None).")
                    results[f'{prop}_{depth}'] = None
                    
            except Exception as e:
                print(f"⚠️ Hata ({prop}-{depth}): {e}")
                results[f'{prop}_{depth}'] = None

    print(f"✅ Toprak profili başarıyla çıkarıldı ({len(results)} parametre).")
    return results

# Eğer bu dosya tek başına çalıştırılırsa test et:
if __name__ == "__main__":
    test_lat, test_lon = 41.40, 27.35
    data = fetch_soil_data(test_lat, test_lon)
    print("\nTest Çıktısı:")
    for k, v in data.items():
        print(f" - {k}: {v}")
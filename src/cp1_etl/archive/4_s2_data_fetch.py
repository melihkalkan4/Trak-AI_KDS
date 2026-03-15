import ee
import pandas as pd
import json
import eemont

# 1. GEE Başlatma
json_key_path = 'keys/trak-ai-kds-d3e5e5b6e168.json'
with open(json_key_path, 'r') as f:
    service_account = json.load(f)['client_email']
credentials = ee.ServiceAccountCredentials(service_account, json_key_path)
ee.Initialize(credentials)

# 2. Pilot Arazi
roi = ee.Geometry.Polygon([[
    [27.30, 41.35], [27.32, 41.35], [27.32, 41.37], [27.30, 41.37]
]])

# 3. Koleksiyon — FIX: bulut yüzdesi filtresi eklendi
dataset = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
    .filterBounds(roi)
    .filterDate('2023-01-01', '2023-12-31')
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 80))  # FIX: tamamen bulutlu görüntüleri at
    .maskClouds()
    .scaleAndOffset())

# 4. NDVI
ndvi_dataset = dataset.spectralIndices('NDVI')

# 5. Zaman Serisi
def get_stats(image):
    stats = image.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=roi,
        scale=10,
        maxPixels=1e9,
        bestEffort=True
    )
    # FIX: .get() ile None default — boş dict'te KeyError olmaz
    return ee.Feature(None, {
        'date': image.date().format('YYYY-MM-dd'),
        'NDVI': stats.get('NDVI', None)
    })

data_list = ndvi_dataset.map(get_stats).getInfo()

# 6. Kayıt — dropna() zaten None satırları temizler
features = [f['properties'] for f in data_list['features']]
df = pd.DataFrame(features).dropna()

df.to_csv('data/raw/s2_ndvi_2023.csv', index=False)
print(f"BAŞARILI: {len(df)} adet temiz uydu verisi kaydedildi.")
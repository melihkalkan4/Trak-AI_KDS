import ee, json, pandas as pd

json_key_path = 'keys/trak-ai-kds-d3e5e5b6e168.json'
with open(json_key_path, 'r') as f:
    service_account = json.load(f)['client_email']
credentials = ee.ServiceAccountCredentials(service_account, json_key_path)
ee.Initialize(credentials)

lat, lon = 41.40, 27.35

ASSETS = {
    'clay':  ('projects/soilgrids-isric/clay_mean',  'clay_0-5cm_mean',  0.1),
    'sand':  ('projects/soilgrids-isric/sand_mean',  'sand_0-5cm_mean',  0.1),
    'phh2o': ('projects/soilgrids-isric/phh2o_mean', 'phh2o_0-5cm_mean', 0.1),
}

print(f"SoilGrids (GEE) sorgulanıyor — Lat: {lat}, Lon: {lon}\n")
results = {}

for prop, (asset_id, band_name, scale_factor) in ASSETS.items():
    try:
        img = ee.Image(asset_id).select(band_name)

        # FIX 1: Görüntünün kendi native projeksiyonunu al
        proj = img.projection()
        native_scale = proj.nominalScale()  # ~250m ama Homolosine cinsinden

        # FIX 2: Büyük buffer — projeksiyon dönüşümü sonrası nokta kayabilir
        point = ee.Geometry.Point([lon, lat])
        region = point.buffer(2000)  # 2km buffer, 250m yerine

        value = img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=region,
            crs=proj,           # FIX 3: native CRS kullan
            scale=native_scale, # FIX 4: native scale kullan
            maxPixels=1e9,
            bestEffort=True
        ).getInfo()

        print(f"  [{prop}] raw result: {value}")  # debug — ne döndüğünü gör

        raw = value.get(band_name)
        if raw is not None:
            results[prop] = round(raw * scale_factor, 2)
            print(f"- {prop.capitalize()} (0-5cm): {results[prop]}")
        else:
            print(f"- {prop}: hâlâ None — asset erişim sorunu olabilir")

    except Exception as e:
        print(f"- {prop} HATA: {e}")

print(f"\nBAŞARILI: {len(results)} toprak özelliği çekildi.")

if results:
    df = pd.DataFrame([{'lat': lat, 'lon': lon, **results}])
    df.to_csv('data/raw/soilgrids_2023.csv', index=False)
    print("CSV kaydedildi: data/raw/soilgrids_2023.csv")
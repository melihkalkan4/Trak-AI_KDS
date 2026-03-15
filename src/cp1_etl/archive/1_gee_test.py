import ee
import json

# Ekran görüntüsündeki JSON dosyanın tam yolu
json_key_path = 'keys/trak-ai-kds-d3e5e5b6e168.json'

try:
    # JSON içindeki mail adresini (client_email) otomatik okuyoruz
    with open(json_key_path, 'r') as f:
        key_data = json.load(f)
        service_account = key_data['client_email']

    # GEE sistemine yetkilendirme isteği gönderiyoruz
    credentials = ee.ServiceAccountCredentials(service_account, json_key_path)
    ee.Initialize(credentials)
    
    print("BAŞARILI: Google Earth Engine API bağlantısı kusursuz çalışıyor!")
    print("Sentinel-2 verilerini çekmeye hazırız.")
    
except Exception as e:
    print(f"HATA: Bağlantı kurulamadı. Detay: {e}")
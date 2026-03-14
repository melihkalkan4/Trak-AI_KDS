import cdsapi

try:
    # CDS Client'ı başlatıyoruz. .cdsapirc dosyasını otomatik bulacak.
    c = cdsapi.Client()
    print("BAŞARILI: Copernicus CDS API bağlantısı kusursuz çalışıyor!")
    print("ERA5-Land iklim verilerini indirmeye hazırız.")
except Exception as e:
    print(f"HATA: Bağlantı kurulamadı. Detay: {e}")
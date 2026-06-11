# TRAK-AI Rover — Saha Donanım Alışveriş Listesi

**Hazırlanma tarihi:** 2026-05-27
**Hedef:** ÇP-3 rover'ı sahaya çıkarmak (tarla ortamında otonom çalışma)
**Şu anki blocker:** ESP32 + ESP32-CAM PC USB'den besleniyor → yetersiz akım, brownout

---

## 🎯 Mevcut Sistem Durumu

| Bileşen | Durum | Eksiklik |
|---|---|---|
| Ana ESP32 + sensörler | Çalışıyor, USB'den besleniyor | Bağımsız güç gerek |
| ESP32-CAM | Brownout, hiç boot etmiyor | Ayrı 5V gerek |
| Motorlar (L298N) | Test edilmedi | Yüksek akım gerekli → ayrı motor pili |
| WiFi/MQTT/Telnet | Tamam | — |
| Saha düzeni | — | Su geçirmez kutu, kablo organizasyonu |

---

## 🔋 KATEGORİ 1: Güç Sistemi (Öncelik: YÜKSEK)

### 1.1 Ana batarya — Rover Gövdesi İçin

**Önerilen: 2S LiPo 7.4V 5200-10000 mAh**

| Ürün tipi | Avantaj | Dezavantaj | Ortalama fiyat |
|---|---|---|---|
| **2S LiPo 7.4V 5200mAh** ⭐ önerilir | Hafif, yüksek akım çıkışı, uzun ömür | LiPo charger gerekir, dikkatli kullanım | ~250-400 TL |
| 3S LiPo 11.1V 5200mAh | Daha geniş voltaj marjı | Buck converter zorlanır | ~350-500 TL |
| 6×AA Eneloop NiMH 7.2V | Güvenli, kolay şarj | Kapasite düşük (~2000mAh), ağır | ~150-200 TL |
| 18650 4S 2-pack (kendin yap) | Modüler, değiştirilebilir | Holder + BMS lazım | ~200-300 TL |

**Tavsiye:** 2S LiPo 7.4V **5200mAh, 25C+ deşarj oranı**. Marka: GensAce, Tattu, Turnigy.

⚠️ **LiPo charger ayrı satın alınır:** ~200-400 TL (IMAX B6 veya muadili)

### 1.2 Buck Converter (Voltaj Düşürücü)

7.4V LiPo → 5V'a düşürmek için. ESP32 + sensörler için **5V/3A** yeterli.

| Ürün | Spec | Fiyat |
|---|---|---|
| **XL4015** ⭐ önerilir | 5A çıkış, 5-32V→1.25-32V ayarlanabilir | ~50-80 TL |
| LM2596 | 2A, 4-40V→1.5-37V | ~25-40 TL (CAM için yetebilir, motor değil) |
| MP1584EN | 3A mini | ~40-60 TL |

**Tavsiye:** XL4015 (5A) — ESP32 + tüm sensörler + CAM hep birlikte besler.

### 1.3 Powerbank (kısa vadeli ESP32-CAM için)

Saha öncesi development için yeterli, ucuz çözüm:

| Ürün | Spec | Fiyat |
|---|---|---|
| **USB powerbank 10000mAh 2A** ⭐ | 5V çıkış, taşınabilir | ~150-300 TL |
| Pocket powerbank 5000mAh | Sadece CAM için yeter | ~100-150 TL |

**Tavsiye:** Anker / Xiaomi 10000mAh powerbank — ana ESP32'yi de besleyebilir (saha dışı test için).

### 1.4 Motor Bataryası (ayrı sistem)

L298N motor pini 6-12V kaldırır, **ESP32'den AYRI** beslenmeli:

| Ürün | Spec | Fiyat |
|---|---|---|
| **2S LiPo 7.4V 2000mAh (sadece motor)** | Hafif | ~150-250 TL |
| 6×AA AccuPower 1.2V | Daha güvenli | ~80-120 TL |

⚠️ Motor pili **ana ESP32 pilinden bağımsız** olmalı — motor stall akım çekerken ESP32 brownout etmesin.

---

## 🔌 KATEGORİ 2: Kablo + Konnektör (Öncelik: ORTA)

### 2.1 Jumper Kablo Seti

| Ürün | Adet | Fiyat |
|---|---|---|
| Erkek-Dişi 40'lı set (10cm) | 1 paket | ~30-50 TL |
| Erkek-Erkek 40'lı set (20cm) | 1 paket | ~30-50 TL |
| Dupont konnektör krimper | 1 adet | ~150-250 TL (opsiyonel) |
| **Silicon kaplı sağlam kablo** ⭐ | 22AWG, 5m | ~80-120 TL |

### 2.2 USB Bağlantı Aksesuarları

| Ürün | Kullanım | Fiyat |
|---|---|---|
| Powered USB Hub 4-port | PC'den birden fazla cihaz | ~80-150 TL |
| USB-A → micro USB kablo | ESP32 + CAM için | ~20-40 TL |
| USB-A → USB-C kablo | Modern adaptörler | ~25-50 TL |
| **Sağlam kalın USB kablo (data destekli)** | Brownout riskini azaltır | ~40-80 TL |

### 2.3 Klemensli/Lehimli Bağlantı

Sahada gevşek kabloyu önlemek için:

| Ürün | Fiyat |
|---|---|
| **JST-XH konnektör seti (2-6 pin)** | ~40-80 TL |
| Krimper aletiyle (JST için) | ~200-350 TL |
| Lehim teli + havya (varsa) | ~100-300 TL |
| Isı büzüşen makaron (5 boy) | ~30-60 TL |

---

## 📡 KATEGORİ 3: GPS Eki (Öncelik: ORTA)

GPS Chars:1 sorunu — anten ve kablo problemi olabilir.

| Ürün | Spec | Fiyat |
|---|---|---|
| **NEO-6M aktif anten (uPL konnektörlü)** | 25dB kazanç | ~80-150 TL |
| NEO-8M tam paket (anten dahil) | Daha yeni, daha hızlı fix | ~200-350 TL |
| Mini SMA-uPL adaptör | Anten genişletme | ~30-60 TL |

⚠️ Mevcut NEO-6M kullanılabilir → önce **kabloyu kontrol et** (TX kopuk olabilir).

---

## 🛡 KATEGORİ 4: Saha Koruma (Öncelik: ORTA-DÜŞÜK)

### 4.1 Su Geçirmez Kutu (IP65+)

Tarla ortamı için elektronik kutu:

| Ürün | Boyut | Fiyat |
|---|---|---|
| **Plastik IP65 kutu 200×150×100mm** ⭐ | ESP32 + sensörler + pil | ~80-150 TL |
| Junction box 150×110×70mm | Daha küçük | ~50-100 TL |
| Kablo rakoru (PG7-PG11) | Su geçirmez kablo çıkış | ~10-20 TL/adet |

### 4.2 Sensör Probu Koruma

| Ürün | Kullanım | Fiyat |
|---|---|---|
| Toprak nemi sensörü için sızdırmaz silikon | SEN0193 koruması | ~50-80 TL |
| HC-SR04 koruma kapı (3D print) | Yağmurdan korur | DIY |

---

## 🛠 KATEGORİ 5: Multimetre + Test (Öncelik: YÜKSEK önce)

GPS / sensör tanısı için **multimetre ŞART**:

| Ürün | Spec | Fiyat |
|---|---|---|
| **UNI-T UT33B Multimetre** ⭐ | DC voltaj ±0.5%, direnç, süreklilik | ~250-350 TL |
| Cheap multimetre | Temel ölçümler | ~80-150 TL |

Kullanım alanları:
- Sensör VCC voltajı kontrolü (3.3V veya 5V geliyor mu)
- Pil voltaj takibi
- Kablo süreklilik testi
- GND ortak doğrulama

---

## 💡 KATEGORİ 6: Opsiyonel İyileştirmeler

### 6.1 OLED Ekran (Status göstergesi)

Rover'a doğrudan baktığında durum bilgisi:

| Ürün | Spec | Fiyat |
|---|---|---|
| SSD1306 OLED I2C 128×64 | 0.96 inç, ucuz | ~60-100 TL |
| SH1106 OLED 1.3 inç | Daha büyük | ~90-130 TL |

### 6.2 RTC Modülü (zaman sürekliliği)

GPS olmadan da zaman bilgisi:

| Ürün | Spec | Fiyat |
|---|---|---|
| DS3231 RTC + pil | ±2ppm hassas | ~50-80 TL |
| DS1307 RTC | Daha ucuz, daha az hassas | ~30-50 TL |

### 6.3 SD Kart Modülü (büyük log)

SPIFFS 1.5MB sınırı yerine GB seviyesi:

| Ürün | Spec | Fiyat |
|---|---|---|
| Mini SD card module + 16GB SD | SPI interface | ~80-150 TL |

---

## 💰 ÖNERİLEN MİNİMUM PAKET (~1100-1500 TL)

Sahaya çıkmak için **mutlaka gerekli**:

| Ürün | Adet | Fiyat |
|---|---|---|
| 2S LiPo 7.4V 5200mAh | 1 | 300 TL |
| LiPo charger (IMAX B6) | 1 | 250 TL |
| XL4015 buck converter | 2 | 100 TL (ESP32 ve CAM için ayrı) |
| Powerbank 10000mAh | 1 | 200 TL |
| Multimetre (temel) | 1 | 150 TL |
| Jumper kablo seti | 2 paket | 80 TL |
| IP65 kutu 200×150×100 | 1 | 120 TL |
| Kablo rakoru × 4 | 4 | 40 TL |
| **TOPLAM** | | **~1240 TL** |

## 💰 ÖNERİLEN GELİŞMİŞ PAKET (~2500-3500 TL)

Üstüne aşağıdakileri ekle:

| Ürün | Fiyat |
|---|---|
| Yedek 2S LiPo (motor için ayrı) | 250 TL |
| NEO-8M GPS (NEO-6M yedek olarak) | 250 TL |
| OLED status ekranı | 80 TL |
| DS3231 RTC | 60 TL |
| SD kart modülü + 32GB | 120 TL |
| JST konnektör seti + krimper | 350 TL |
| Powered USB hub | 100 TL |
| Silikon kaplı kablo 22AWG | 100 TL |
| **EK TOPLAM** | **~1310 TL** |

---

## 🛒 Türkiye'de Bulunabilecek Mağazalar

### Online (hızlı + güvenilir)
- **Robotistan.com** — geniş yelpaze, ESP32/Arduino özelinde
- **Direnc.net** — ana toptan elektronik parça
- **Robolink** — robotik özelinde, kit'ler
- **Trendyol / Hepsiburada** — fiyat karşılaştırma
- **AliExpress** — daha ucuz ama 2-4 hafta bekleme

### Fiziksel (İstanbul/Ankara)
- Karaköy/Galata (elektronik sokağı) — fiyat pazarlığı yapılabilir
- Mecidiyeköy — bazı toptan mağazalar
- Ankara Ulus — TerraDot, Apex Electronics

---

## ⚠️ Saha Çıkışı Öncesi Yapılacak Hazırlıklar

### Test edilmesi gereken
1. ✅ **WiFi sinyali tarla noktasında ölçüm** — telefon WiFi sinyal uygulaması
2. ✅ **Mobil hotspot yedek** — tarladaki WiFi kapsama dışındaysa
3. ⏳ **Pil dayanma süresi** — full charge ile kaç saat (test)
4. ⏳ **GPS açık alan fix süresi** — cold start ortalama 30-90 saniye
5. ⏳ **Motor stall akımı** — boş hız vs yüklü hız ölçüm

### Bilinen riskler
- 🔴 **Yağmur** → kutu IP65+ olmalı
- 🔴 **Aşırı sıcak** → ESP32 80°C üstünde reset olur, gölgeli yer
- 🟡 **WiFi koparsa** → SPIFFS kuyruğa yazma var ama 1MB limit
- 🟡 **Pil bitmesi** → IDLE moda otomatik geçiş yok (yarın eklenebilir)
- 🟡 **Motor çarpması** → HC-SR04 25cm öncesinde dur, ama yan engelleri görmez

---

## 📦 Saha Çıkış Hazırlık Checklist

Donanım hazırladıktan sonra:

- [ ] Pil tam şarjlı
- [ ] LiPo charger yedek olarak çantada
- [ ] Multimetre + yedek pil
- [ ] Jumper kablo yedekleri
- [ ] WiFi mobil hotspot hazır (telefondan)
- [ ] Laptop tam şarjlı (OTA upload için gerekirse)
- [ ] Yedek SD kart (log için)
- [ ] Anahtarlar/tornavida temel set
- [ ] Sigorta (motor kısa devre için inline fuse)
- [ ] First-aid: kablo bandı, sıcak tutkal, yedek breadboard

---

*Bu liste yarın yapılacak ilk alışveriş için hazırlandı. Önce KATEGORİ 1
(Güç) + KATEGORİ 5 (Multimetre) önceliklidir. Diğerleri proje ilerledikçe
eklenir.*

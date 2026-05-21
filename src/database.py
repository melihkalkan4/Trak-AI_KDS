"""
TRAK-AI KDS — SQLite Veritabanı Katmanı
=========================================
Tarlalar, rover ölçümleri ve model tahminlerini yerel SQLite'da saklar.
DB dosyası: data/trakaia.db
"""
import sqlite3
import json
import math
import os
import random
from datetime import datetime, timedelta, date

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(PROJECT_ROOT, "data", "trakaia.db")

TODAY = date(2026, 5, 13)
MOCK_VERSION = "2"  # Artırmak eski mock veriyi siler ve yeniden üretir

# ─────────────────────────────────────────────────────────────────────────────
# Şema
# ─────────────────────────────────────────────────────────────────────────────

_CREATE_TARLALAR = """
CREATE TABLE IF NOT EXISTS tarlalar (
    id          INTEGER PRIMARY KEY,
    isim        TEXT NOT NULL,
    il          TEXT NOT NULL,
    ilce        TEXT NOT NULL,
    konum_lat   REAL NOT NULL,
    konum_lon   REAL NOT NULL,
    alan_dekar  REAL,
    toprak_tipi TEXT,
    toprak_kil  REAL,
    toprak_kum  REAL,
    toprak_ph   REAL,
    aktif_urun  TEXT,
    ekim_tarihi TEXT,
    notlar      TEXT
)
"""

_CREATE_ROVER = """
CREATE TABLE IF NOT EXISTS rover_olcumler (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    tarla_id         INTEGER REFERENCES tarlalar(id),
    timestamp        TEXT NOT NULL,
    waypoint_id      INTEGER,
    waypoint_label   TEXT,
    gps_lat          REAL,
    gps_lon          REAL,
    nem_1_pct        REAL,
    nem_2_pct        REAL,
    hava_temp_c      REAL,
    hava_nem_pct     REAL,
    bbch_sinif       TEXT,
    bbch_guven       REAL,
    hastalik         TEXT,
    hastalik_guven   REAL,
    engel_on_cm      INTEGER,
    ndvi_tahmini     REAL,
    verim_tahmini    REAL,
    anomali_sayisi   INTEGER DEFAULT 0,
    anomaliler       TEXT,
    kds_tavsiye      TEXT,
    image_path       TEXT,
    camera_sinif     TEXT,
    camera_guven     REAL
)
"""

_CREATE_TAHMINLER = """
CREATE TABLE IF NOT EXISTS tarla_tahminler (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    tarla_id                INTEGER REFERENCES tarlalar(id),
    timestamp               TEXT NOT NULL,
    urun                    TEXT,
    ndvi_mevcut             REAL,
    ndvi_tahmin_7gun        REAL,
    ndvi_delta              REAL,
    saglik_durumu           TEXT,
    verim_tahmini_kg_dekar  REAL,
    verim_guven_alt         REAL,
    verim_guven_ust         REAL,
    verim_risk              TEXT,
    fenolojik_evre          TEXT,
    bbch_aralik             TEXT,
    kritik_donem            INTEGER DEFAULT 0,
    sulama_aciliyet         TEXT,
    sulama_miktar           REAL,
    gubre_zamani            INTEGER DEFAULT 0,
    gubre_tip               TEXT,
    ekim_skoru              INTEGER,
    ekim_kategori           TEXT,
    hava_sicaklik           REAL,
    hava_nem                REAL,
    hava_yagis_7gun         REAL,
    hava_uyarilar           TEXT
)
"""

_CREATE_META = """
CREATE TABLE IF NOT EXISTS db_meta (
    key   TEXT PRIMARY KEY,
    value TEXT
)
"""

_CREATE_HAVA = """
CREATE TABLE IF NOT EXISTS hava_kayitlari (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    tarla_id            INTEGER REFERENCES tarlalar(id),
    timestamp           TEXT NOT NULL,
    tarih               TEXT NOT NULL,
    konum_lat           REAL,
    konum_lon           REAL,
    hava_temp_c         REAL,
    hava_nem_pct        REAL,
    toprak_temp_c       REAL,
    toprak_nem_pct      REAL,
    yagis_mm            REAL,
    ruzgar_kmh          REAL,
    temp_max            REAL,
    temp_min            REAL,
    yagis_gunluk_mm     REAL,
    et0_mm              REAL,
    yagis_olasilik      INTEGER,
    gdd_kumulatif       REAL,
    don_riski           INTEGER DEFAULT 0,
    sicak_stres         INTEGER DEFAULT 0,
    UNIQUE(tarla_id, tarih)
)
"""

_CREATE_HAVA_INDEX = (
    "CREATE INDEX IF NOT EXISTS idx_hava_tarla_tarih "
    "ON hava_kayitlari(tarla_id, tarih)"
)

# ─────────────────────────────────────────────────────────────────────────────
# Mock tarla tanımları
# ─────────────────────────────────────────────────────────────────────────────

_MOCK_TARLALAR = [
    {
        "id": 1, "isim": "Edirne Merkez Buğday Tarlası",
        "il": "Edirne", "ilce": "Merkez",
        "konum_lat": 41.677, "konum_lon": 26.556,
        "alan_dekar": 120.0, "toprak_tipi": "killi-tınlı",
        "toprak_kil": 31.0, "toprak_kum": 35.0, "toprak_ph": 7.1,
        "aktif_urun": "Buğday", "ekim_tarihi": "2025-10-15",
        "notlar": "Ergene havzası, sulama kanalına yakın",
    },
    {
        "id": 2, "isim": "Kırklareli Vize Ayçiçeği Tarlası",
        "il": "Kırklareli", "ilce": "Vize",
        "konum_lat": 41.694, "konum_lon": 27.105,
        "alan_dekar": 85.0, "toprak_tipi": "tınlı",
        "toprak_kil": 25.0, "toprak_kum": 40.0, "toprak_ph": 6.8,
        "aktif_urun": "Ayçiçeği", "ekim_tarihi": "2026-04-20",
        "notlar": "Pilot tarla, CP-2 model eğitim verisi",
    },
    {
        "id": 3, "isim": "Tekirdağ Hayrabolu Buğday Tarlası",
        "il": "Tekirdağ", "ilce": "Hayrabolu",
        "konum_lat": 41.213, "konum_lon": 27.099,
        "alan_dekar": 200.0, "toprak_tipi": "killi",
        "toprak_kil": 38.0, "toprak_kum": 28.0, "toprak_ph": 7.3,
        "aktif_urun": "Buğday", "ekim_tarihi": "2025-10-20",
        "notlar": "Ağır killi toprak, drenaj sorunu takip edilmeli",
    },
    {
        "id": 4, "isim": "Edirne Uzunköprü Ayçiçeği Tarlası",
        "il": "Edirne", "ilce": "Uzunköprü",
        "konum_lat": 41.267, "konum_lon": 26.688,
        "alan_dekar": 150.0, "toprak_tipi": "kumlu-tınlı",
        "toprak_kil": 20.0, "toprak_kum": 45.0, "toprak_ph": 6.5,
        "aktif_urun": "Ayçiçeği", "ekim_tarihi": "2026-04-25",
        "notlar": "Hafif toprak, su tutma kapasitesi düşük",
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# Mevsimsel profil fonksiyonları
# ─────────────────────────────────────────────────────────────────────────────

def _wheat_season(scan_date: date, clay_pct: float = 31.0) -> dict:
    """Buğday için mevsimsel ölçüm aralıkları.
    clay_bonus: yüksek kil → daha fazla nem tutulur."""
    clay_bonus = (clay_pct - 31.0) * 0.18
    m, y = scan_date.month, scan_date.year

    if y == 2025:
        if m == 10:
            return dict(nem_c=34+clay_bonus, nem_s=5, temp_c=12, temp_s=3,
                        bb=(0, 9), ndvi=0.20)
        else:  # Kasım
            return dict(nem_c=37+clay_bonus, nem_s=5, temp_c=8, temp_s=4,
                        bb=(5, 19), ndvi=0.27)
    # 2026
    if m == 1:
        return dict(nem_c=41+clay_bonus, nem_s=5, temp_c=2, temp_s=4,
                    bb=(15, 25), ndvi=0.35)
    elif m == 2:
        return dict(nem_c=39+clay_bonus, nem_s=5, temp_c=4, temp_s=4,
                    bb=(20, 29), ndvi=0.43)
    elif m == 3:
        return dict(nem_c=31+clay_bonus, nem_s=5, temp_c=11, temp_s=4,
                    bb=(25, 35), ndvi=0.51)
    elif m == 4:
        return dict(nem_c=26+clay_bonus, nem_s=4, temp_c=17, temp_s=5,
                    bb=(35, 55), ndvi=0.63)
    elif m == 5:
        return dict(nem_c=22+clay_bonus, nem_s=4, temp_c=22, temp_s=5,
                    bb=(50, 69), ndvi=0.69)
    # fallback
    return dict(nem_c=30+clay_bonus, nem_s=5, temp_c=15, temp_s=4,
                bb=(0, 9), ndvi=0.30)


def _sunflower_season(days_since_planting: int, scan_date: date) -> dict:
    """Ayçiçeği için büyüme-bazlı profil."""
    # Mayıs ilerledikçe sıcaklık artar
    temp_c = 17.0 + (scan_date.day / 31.0) * 5.0 + (scan_date.month - 4) * 4.0
    if days_since_planting < 7:
        return dict(nem_c=33, nem_s=5, temp_c=temp_c, temp_s=3,
                    bb=(0, 5), ndvi=0.12)
    elif days_since_planting < 14:
        return dict(nem_c=29, nem_s=4, temp_c=temp_c, temp_s=3,
                    bb=(5, 10), ndvi=0.19)
    elif days_since_planting < 21:
        return dict(nem_c=26, nem_s=4, temp_c=temp_c, temp_s=3,
                    bb=(10, 14), ndvi=0.27)
    else:
        return dict(nem_c=24, nem_s=4, temp_c=temp_c + 1, temp_s=3,
                    bb=(14, 19), ndvi=0.34)


# ─────────────────────────────────────────────────────────────────────────────
# Anomali olayları — tarla bazında, belirli haftalarda
# ─────────────────────────────────────────────────────────────────────────────

_ANOMALY_EVENTS = {
    1: [  # Edirne Merkez Buğday
        {
            "date_start": date(2026, 1, 14), "date_end": date(2026, 1, 22),
            "apply_wp": 3,
            "overrides": {"hava_temp_c": -4.0, "anomali_sayisi": 1},
            "anomaliler": ["Don tespiti: -4°C hava sıcaklığı (eşik: 2°C)"],
            "kds_tavsiye": (
                "DİKKAT: Don riski — BBCH 15-25 döneminde genç sürgünler zarar görebilir. "
                "Sabah saatlerinde tarlayı kontrol edin. Kar örtüsü yoksa stres izleniyor."
            ),
        },
        {
            "date_start": date(2026, 3, 7), "date_end": date(2026, 3, 15),
            "apply_wp": None,
            "overrides": {"nem_1_pct": 19.0, "nem_2_pct": 17.5, "anomali_sayisi": 1},
            "anomaliler": ["Düşük toprak nemi: %19 (eşik: %20)"],
            "kds_tavsiye": (
                "Toprak nemi %19'a düştü. Kardeşlenme-sapa kalkma geçiş döneminde nem kritik. "
                "20-25 ton/dekar sulama önerilir. Bir hafta içinde yağış beklenmiyorsa hemen sulayın."
            ),
        },
        {
            "date_start": date(2026, 4, 22), "date_end": date(2026, 4, 29),
            "apply_wp": 2,
            "overrides": {"hastalik": "sarı_pas", "hastalik_guven": 0.65, "anomali_sayisi": 1},
            "anomaliler": ["Hastalık şüphesi: sarı_pas (güven: %65)"],
            "kds_tavsiye": (
                "Sarı pas şüphesi (%65 güven). Bayrak yaprak döneminde kritik — "
                "triazol fungisit (tebukonazol veya propikonazol) uygulamasını değerlendirin."
            ),
        },
        {
            "date_start": date(2026, 5, 6), "date_end": date(2026, 5, 13),
            "apply_wp": None,
            "overrides": {"nem_1_pct": 17.0, "nem_2_pct": 10.5, "anomali_sayisi": 2},
            "anomaliler": [
                "Kritik dönem düşük nem: %17 (başaklanma evresinde)",
                "Nem sensör farkı yüksek: %6.5 (eşik: %10)",
            ],
            "kds_tavsiye": (
                "KRİTİK: Başaklanma-çiçeklenme evresinde toprak nemi %17, sensör farkı yüksek. "
                "Bu evredeki su stresi dane sayısını %20-30 düşürür. "
                "ACIL: 40-50 ton/dekar sulama, sabah 05:00-09:00 arası."
            ),
        },
    ],
    2: [  # Kırklareli Vize Ayçiçeği
        {
            "date_start": date(2026, 4, 27), "date_end": date(2026, 5, 7),
            "apply_wp": None,
            "overrides": {"nem_1_pct": 21.0, "nem_2_pct": 19.5, "anomali_sayisi": 1},
            "anomaliler": ["Düşük toprak nemi: %21 (ayçiçeği çimlenme döneminde, eşik: %25)"],
            "kds_tavsiye": (
                "Çimlenme aşamasında toprak nemi %21'e geriledi. İdeal aralık %25-35. "
                "15-20 ton/dekar hafif sulama — aşırı su kök çürüklüğüne yol açabilir."
            ),
        },
    ],
    3: [  # Tekirdağ Hayrabolu Buğday
        {
            "date_start": date(2026, 1, 31), "date_end": date(2026, 2, 8),
            "apply_wp": 4,
            "overrides": {"hava_temp_c": -6.0, "anomali_sayisi": 1},
            "anomaliler": ["Şiddetli don: -6°C (kritik eşik: -5°C)"],
            "kds_tavsiye": (
                "ŞİDDETLİ DON UYARISI: -6°C ölçüldü. BBCH 20-25 döneminde "
                "yaprak ve sürgün hasarı riski yüksek. Sabah tarlayı kontrol edin. "
                "Don zararı varsa fosfat gübrelemesini erteleyin."
            ),
        },
        {
            "date_start": date(2026, 4, 1), "date_end": date(2026, 4, 8),
            "apply_wp": 1,
            "overrides": {"hastalik": "kök_çürüklüğü", "hastalik_guven": 0.72, "anomali_sayisi": 1},
            "anomaliler": ["Hastalık şüphesi: kök_çürüklüğü (güven: %72)"],
            "kds_tavsiye": (
                "Kök çürüklüğü belirtileri tespit edildi (%72 güven). "
                "Ağır killi toprakta drenaj sorunu bu hastalığı tetikler. "
                "Etkilenen bitkileri kaldırın. Gelecek sezonda karbendazim tohumla ilaçlama yapın."
            ),
        },
        {
            "date_start": date(2026, 5, 1), "date_end": date(2026, 5, 8),
            "apply_wp": None,
            "overrides": {
                "hava_temp_c": 32.0, "nem_1_pct": 16.5,
                "nem_2_pct": 15.0, "anomali_sayisi": 2,
            },
            "anomaliler": [
                "Sıcak stres: 32°C (eşik: 30°C, dane dolumu dönemi)",
                "Düşük nem + yüksek sıcaklık kombinasyonu: %16.5 nem",
            ],
            "kds_tavsiye": (
                "ÇİFT STRES: 32°C + düşük nem (%16.5) — dane dolumunda bu kombinasyon "
                "dane ağırlığını %15-25 düşürür. "
                "ACIL sulama: 40-50 ton/dekar. 11:00-16:00 arası sulama yapmayın."
            ),
        },
    ],
    4: [  # Edirne Uzunköprü Ayçiçeği
        {
            "date_start": date(2026, 4, 30), "date_end": date(2026, 5, 8),
            "apply_wp": 3,
            "overrides": {"hastalik": "mildiyö", "hastalik_guven": 0.78, "anomali_sayisi": 1},
            "anomaliler": ["Hastalık tespiti: mildiyö (güven: %78)"],
            "kds_tavsiye": (
                "Mildiyö şüphesi (%78 güven). Çimlenme döneminde tohum kaynaklı olabilir. "
                "Metalaksil+mancozeb veya fosetil-Al uygulaması yapın. "
                "Hastalıklı fidecikleri kaldırın. Sıcaklık 20-25°C ve nem yüksekse hızla yayılır."
            ),
        },
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
# GDD yardımcısı
# ─────────────────────────────────────────────────────────────────────────────

def calculate_gdd(temp_max: float, temp_min: float, base: float = 10.0) -> float:
    """Growing Degree Days: max(0, (T_max + T_min)/2 - base)."""
    return max(0.0, (temp_max + temp_min) / 2.0 - base)


# ─────────────────────────────────────────────────────────────────────────────
# Mock hava verisi üretici (20 Mart – 20 Mayıs 2026)
# ─────────────────────────────────────────────────────────────────────────────

def _generate_mock_weather() -> list:
    """4 tarla için 62 günlük gerçekçi hava geçmişi üret."""
    rows = []
    start = date(2026, 3, 20)
    end   = date(2026, 5, 20)

    # Küçük il bazlı sıcaklık farkları (coğrafi konum)
    _offset  = {1: 0.3, 2: -0.3, 3: 0.5, 4: 0.8}
    # Toprak nemi başlangıç (killi toprak daha fazla tutar)
    _soil_b  = {1: 28.0, 2: 25.0, 3: 26.0, 4: 22.0}

    for tarla in _MOCK_TARLALAR:
        tid      = tarla["id"]
        lat, lon = tarla["konum_lat"], tarla["konum_lon"]
        offset   = _offset.get(tid, 0.0)
        soil_b   = _soil_b.get(tid, 25.0)
        rng      = random.Random(tid * 97 + 53)

        gdd_cum  = 0.0
        cur_date = start

        while cur_date <= end:
            # Trakya ilkbahar ısınma eğrisi: Mart ~10°C → Mayıs ~23°C
            progress = (cur_date - start).days / 61.0
            avg_ref  = 10.0 + progress * 13.0 + offset

            diurnal  = 10.0 + rng.gauss(0, 1.5)
            t_max    = avg_ref + diurnal / 2.0 + rng.gauss(0, 1.5)
            t_min    = avg_ref - diurnal / 2.0 + rng.gauss(0, 1.5)
            t_avg    = (t_max + t_min) / 2.0

            # Don günleri: Mart başı-ortası, Nisan ilk hafta nadiren
            if cur_date.month == 3 and cur_date.day <= 25:
                t_min = min(t_min, rng.uniform(0.5, 3.5))
                t_max = min(t_max, t_min + rng.uniform(7, 10))
                t_avg = (t_max + t_min) / 2.0

            # Sıcak stres: Mayıs son haftası
            if cur_date.month == 5 and cur_date.day >= 14:
                t_max = max(t_max, rng.uniform(29.0, 34.0))
                t_avg = (t_max + t_min) / 2.0

            # Yağış: Trakya'da bahar ~%30 günlük olasılık
            if rng.random() < 0.30:
                yagis = round(rng.uniform(3.0, 22.0), 1)
                yagis_olas = 85
            else:
                yagis = 0.0
                yagis_olas = 15

            # ET0 (Hargreaves basit)
            et0 = max(0.0, 0.0023 * (t_avg + 17.8) * abs(t_max - t_min) ** 0.5 * 22.0 * 0.408)

            # Toprak nemi
            soil_nem = soil_b + yagis * 0.3 - et0 * 0.8 + rng.gauss(0, 1.5)
            soil_nem = max(10.0, min(45.0, soil_nem))
            soil_tmp = t_avg - 2.0 + rng.gauss(0, 0.5)

            ruzgar    = max(0.0, rng.gauss(18.0, 8.0))
            hava_nem  = min(95.0, max(30.0, 65.0 - progress * 15 + rng.gauss(0, 8.0)))

            gdd_daily = calculate_gdd(t_max, t_min)
            gdd_cum  += gdd_daily

            ts = datetime(cur_date.year, cur_date.month, cur_date.day, 12, 0, 0
                          ).strftime("%Y-%m-%d %H:%M:%S")

            rows.append({
                "tarla_id":         tid,
                "timestamp":        ts,
                "tarih":            cur_date.isoformat(),
                "konum_lat":        lat,
                "konum_lon":        lon,
                "hava_temp_c":      round(t_avg,  1),
                "hava_nem_pct":     round(hava_nem, 1),
                "toprak_temp_c":    round(soil_tmp, 1),
                "toprak_nem_pct":   round(soil_nem, 1),
                "yagis_mm":         yagis,
                "ruzgar_kmh":       round(ruzgar, 1),
                "temp_max":         round(t_max, 1),
                "temp_min":         round(t_min, 1),
                "yagis_gunluk_mm":  yagis,
                "et0_mm":           round(et0, 2),
                "yagis_olasilik":   yagis_olas,
                "gdd_kumulatif":    round(gdd_cum, 1),
                "don_riski":        1 if t_min < 2.0 else 0,
                "sicak_stres":      1 if t_max > 30.0 else 0,
            })

            cur_date += timedelta(days=1)

    return rows


# ─────────────────────────────────────────────────────────────────────────────
# Mock rover veri üretici
# ─────────────────────────────────────────────────────────────────────────────

def _generate_mock_scans(tarla: dict) -> list:
    """Ekim tarihinden TODAY'e kadar haftalık (×5 WP) rover ölçümleri üret."""
    tarla_id   = tarla["id"]
    lat        = tarla["konum_lat"]
    lon        = tarla["konum_lon"]
    urun       = tarla["aktif_urun"]
    ekim_date  = date.fromisoformat(tarla["ekim_tarihi"])
    clay_pct   = tarla.get("toprak_kil") or 31.0

    rng = random.Random(tarla_id * 31 + 17)  # tekrarlanabilir
    rows = []

    scan_date = ekim_date
    while scan_date <= TODAY:
        # Mevsimsel profil
        if urun == "Buğday":
            prof = _wheat_season(scan_date, clay_pct)
        else:
            days_since = (scan_date - ekim_date).days
            prof = _sunflower_season(days_since, scan_date)

        nem_c  = prof["nem_c"]
        nem_s  = prof["nem_s"]
        temp_c = prof["temp_c"]
        temp_s = prof["temp_s"]
        bb_low, bb_high = prof["bb"]
        ndvi_base = prof["ndvi"]

        # Gün düzeyinde rastgele temel değer
        nem_day  = rng.gauss(nem_c, nem_s / 2.0)
        temp_day = rng.gauss(temp_c, temp_s / 2.0)
        bbch_label = f"BBCH_{bb_low:02d}_{bb_high:02d}"

        # Bu tarama tarihinde aktif anomali olayları
        active_events = [
            evt for evt in _ANOMALY_EVENTS.get(tarla_id, [])
            if evt["date_start"] <= scan_date <= evt["date_end"]
        ]

        for wp in range(1, 6):
            # Waypoint düzeyinde ±varyasyon
            nem1   = round(nem_day + rng.uniform(-2.5, 2.5), 1)
            nem2   = round(nem1   + rng.uniform(-3.5, -0.5), 1)
            temp   = round(temp_day + rng.uniform(-1.2, 1.2), 1)
            h_nem  = round(rng.uniform(40.0, 78.0), 1)
            b_guv  = round(rng.uniform(0.74, 0.93), 2)
            ndvi_e = round(ndvi_base + rng.uniform(-0.04, 0.04), 3)

            # GPS saçılımı
            angle  = rng.uniform(0, 2 * math.pi)
            radius = rng.uniform(0.0001, 0.0007)
            gps_lat = round(lat + radius * math.sin(angle), 6)
            gps_lon = round(lon + radius * math.cos(angle), 6)

            # Zaman damgası
            hour   = rng.randint(7, 16)
            minute = rng.randint(0, 59)
            ts = datetime(
                scan_date.year, scan_date.month, scan_date.day, hour, minute
            ).strftime("%Y-%m-%d %H:%M:%S")

            anomali     = 0
            anomaliler  = None
            hastalik    = None
            has_guven   = None
            kds_tavsiye = None

            # Anomali uygula (bu WP için geçerliyse)
            for evt in active_events:
                hedef_wp = evt.get("apply_wp")
                if hedef_wp is None or hedef_wp == wp:
                    for key, val in evt.get("overrides", {}).items():
                        if key == "nem_1_pct":       nem1    = val
                        elif key == "nem_2_pct":     nem2    = val
                        elif key == "hava_temp_c":   temp    = val
                        elif key == "hastalik":      hastalik= val
                        elif key == "hastalik_guven": has_guven = val
                        elif key == "anomali_sayisi": anomali = val
                    anomaliler  = json.dumps(evt["anomaliler"], ensure_ascii=False)
                    kds_tavsiye = evt.get("kds_tavsiye")
                    break  # tek olay uygula

            rows.append({
                "tarla_id":        tarla_id,
                "timestamp":       ts,
                "waypoint_id":     wp,
                "waypoint_label":  f"WP{wp}",
                "gps_lat":         gps_lat,
                "gps_lon":         gps_lon,
                "nem_1_pct":       max(4.0, min(70.0, nem1)),
                "nem_2_pct":       max(3.0, min(68.0, nem2)),
                "hava_temp_c":     temp,
                "hava_nem_pct":    h_nem,
                "bbch_sinif":      bbch_label,
                "bbch_guven":      b_guv,
                "hastalik":        hastalik,
                "hastalik_guven":  has_guven,
                "engel_on_cm":     None,
                "ndvi_tahmini":    max(0.05, min(0.95, ndvi_e)),
                "verim_tahmini":   None,
                "anomali_sayisi":  anomali,
                "anomaliler":      anomaliler,
                "kds_tavsiye":     kds_tavsiye,
            })

        scan_date += timedelta(weeks=1)

    return rows


# ─────────────────────────────────────────────────────────────────────────────
# Mock tahmin kayıtları (son durum, statik)
# ─────────────────────────────────────────────────────────────────────────────

_MOCK_TAHMINLER = [
    {
        "tarla_id": 1, "urun": "Buğday",
        "ndvi_mevcut": 0.680, "ndvi_tahmin_7gun": 0.655, "ndvi_delta": -0.025,
        "saglik_durumu": "İyi", "verim_tahmini_kg_dekar": 415.0,
        "verim_guven_alt": 365.0, "verim_guven_ust": 465.0, "verim_risk": "NORMAL",
        "fenolojik_evre": "Başaklanma / Çiçeklenme", "bbch_aralik": "55-65",
        "kritik_donem": 1,
        "sulama_aciliyet": "ACİL", "sulama_miktar": 45.0,
        "gubre_zamani": 0, "gubre_tip": None,
        "ekim_skoru": 0, "ekim_kategori": "EKİM DÖNEMİ DEĞİL",
        "hava_sicaklik": 22.8, "hava_nem": 55.0, "hava_yagis_7gun": 8.2,
        "hava_uyarilar": "Kuraklık riski: 5 günlük yağışsız + sıcak tahmin",
    },
    {
        "tarla_id": 2, "urun": "Ayçiçeği",
        "ndvi_mevcut": 0.290, "ndvi_tahmin_7gun": 0.340, "ndvi_delta": 0.050,
        "saglik_durumu": "Gelişiyor", "verim_tahmini_kg_dekar": 172.0,
        "verim_guven_alt": 140.0, "verim_guven_ust": 205.0, "verim_risk": "NORMAL",
        "fenolojik_evre": "Yaprak Gelişimi", "bbch_aralik": "14-19",
        "kritik_donem": 0,
        "sulama_aciliyet": "YAKINDA", "sulama_miktar": 20.0,
        "gubre_zamani": 1, "gubre_tip": "Amonyum nitrat (dekara 15 kg, V4 döneminde)",
        "ekim_skoru": 65, "ekim_kategori": "UYGUN — Bu hafta ekilebilir",
        "hava_sicaklik": 24.3, "hava_nem": 48.0, "hava_yagis_7gun": 5.8,
        "hava_uyarilar": None,
    },
    {
        "tarla_id": 3, "urun": "Buğday",
        "ndvi_mevcut": 0.610, "ndvi_tahmin_7gun": 0.572, "ndvi_delta": -0.038,
        "saglik_durumu": "Orta", "verim_tahmini_kg_dekar": 298.0,
        "verim_guven_alt": 248.0, "verim_guven_ust": 348.0, "verim_risk": "YÜKSEK",
        "fenolojik_evre": "Başaklanma / Çiçeklenme", "bbch_aralik": "55-65",
        "kritik_donem": 1,
        "sulama_aciliyet": "ACİL", "sulama_miktar": 50.0,
        "gubre_zamani": 0, "gubre_tip": None,
        "ekim_skoru": 0, "ekim_kategori": "EKİM DÖNEMİ DEĞİL",
        "hava_sicaklik": 24.1, "hava_nem": 52.0, "hava_yagis_7gun": 6.5,
        "hava_uyarilar": "Sıcak stres geçmişi: Mayıs başında 32°C ölçüldü",
    },
    {
        "tarla_id": 4, "urun": "Ayçiçeği",
        "ndvi_mevcut": 0.235, "ndvi_tahmin_7gun": 0.290, "ndvi_delta": 0.055,
        "saglik_durumu": "Gelişiyor", "verim_tahmini_kg_dekar": 158.0,
        "verim_guven_alt": 128.0, "verim_guven_ust": 188.0, "verim_risk": "NORMAL",
        "fenolojik_evre": "Çimlenme / Fide", "bbch_aralik": "05-10",
        "kritik_donem": 0,
        "sulama_aciliyet": "NORMAL", "sulama_miktar": 18.0,
        "gubre_zamani": 0, "gubre_tip": None,
        "ekim_skoru": 65, "ekim_kategori": "UYGUN — Bu hafta ekilebilir",
        "hava_sicaklik": 25.6, "hava_nem": 46.0, "hava_yagis_7gun": 7.2,
        "hava_uyarilar": None,
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# Bağlantı
# ─────────────────────────────────────────────────────────────────────────────

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ─────────────────────────────────────────────────────────────────────────────
# init_db
# ─────────────────────────────────────────────────────────────────────────────

def init_db():
    """Tabloları oluştur; mock versiyon uyuşmuyorsa sıfırla ve yeniden üret."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_connection() as conn:
        conn.execute(_CREATE_TARLALAR)
        conn.execute(_CREATE_ROVER)
        conn.execute(_CREATE_TAHMINLER)
        conn.execute(_CREATE_META)
        conn.execute(_CREATE_HAVA)
        conn.execute(_CREATE_HAVA_INDEX)
        conn.commit()

        # Migration: image_path sütunu yoksa ekle (mevcut DB'leri bozmadan)
        mevcut_kolonlar = [
            r[1] for r in conn.execute("PRAGMA table_info(rover_olcumler)").fetchall()
        ]
        if "image_path" not in mevcut_kolonlar:
            conn.execute("ALTER TABLE rover_olcumler ADD COLUMN image_path TEXT")
            conn.commit()
        if "camera_sinif" not in mevcut_kolonlar:
            conn.execute("ALTER TABLE rover_olcumler ADD COLUMN camera_sinif TEXT")
            conn.commit()
        if "camera_guven" not in mevcut_kolonlar:
            conn.execute("ALTER TABLE rover_olcumler ADD COLUMN camera_guven REAL")
            conn.commit()

        # Versiyon kontrolü
        row = conn.execute(
            "SELECT value FROM db_meta WHERE key='mock_version'"
        ).fetchone()
        current_ver = row[0] if row else None

        if current_ver != MOCK_VERSION:
            conn.execute("DELETE FROM rover_olcumler")
            conn.execute("DELETE FROM tarla_tahminler")
            conn.execute("DELETE FROM tarlalar")
            conn.commit()
            print(f"[DB] Mock v{current_ver} -> v{MOCK_VERSION}: eski veri silindi.")

        # Tarlalar
        if conn.execute("SELECT COUNT(*) FROM tarlalar").fetchone()[0] == 0:
            for t in _MOCK_TARLALAR:
                conn.execute(
                    """INSERT INTO tarlalar
                       (id,isim,il,ilce,konum_lat,konum_lon,alan_dekar,
                        toprak_tipi,toprak_kil,toprak_kum,toprak_ph,
                        aktif_urun,ekim_tarihi,notlar)
                       VALUES (:id,:isim,:il,:ilce,:konum_lat,:konum_lon,:alan_dekar,
                               :toprak_tipi,:toprak_kil,:toprak_kum,:toprak_ph,
                               :aktif_urun,:ekim_tarihi,:notlar)""",
                    t,
                )
            conn.commit()
            print("[DB] 4 mock tarla eklendi.")

        # Rover ölçümleri
        if conn.execute("SELECT COUNT(*) FROM rover_olcumler").fetchone()[0] == 0:
            total = 0
            for t in _MOCK_TARLALAR:
                rows = _generate_mock_scans(t)
                for r in rows:
                    cols = ", ".join(r.keys())
                    phs  = ", ".join(f":{k}" for k in r)
                    conn.execute(
                        f"INSERT INTO rover_olcumler ({cols}) VALUES ({phs})", r
                    )
                total += len(rows)
            conn.commit()
            print(f"[DB] {total} mock rover ölçümü eklendi.")

        # Tahminler
        if conn.execute("SELECT COUNT(*) FROM tarla_tahminler").fetchone()[0] == 0:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for tahmin in _MOCK_TAHMINLER:
                row = {"timestamp": ts, **tahmin}
                cols = ", ".join(row.keys())
                phs  = ", ".join(f":{k}" for k in row)
                conn.execute(
                    f"INSERT INTO tarla_tahminler ({cols}) VALUES ({phs})", row
                )
            conn.commit()
            print("[DB] 4 mock tahmin kaydı eklendi.")

        # Hava geçmişi
        if conn.execute("SELECT COUNT(*) FROM hava_kayitlari").fetchone()[0] == 0:
            hava_rows = _generate_mock_weather()
            for r in hava_rows:
                cols = ", ".join(r.keys())
                phs  = ", ".join(f":{k}" for k in r)
                conn.execute(
                    f"INSERT OR IGNORE INTO hava_kayitlari ({cols}) VALUES ({phs})", r
                )
            conn.commit()
            print(f"[DB] {len(hava_rows)} mock hava kaydı eklendi.")

        # Versiyonu kaydet
        if current_ver != MOCK_VERSION:
            conn.execute(
                "INSERT OR REPLACE INTO db_meta VALUES ('mock_version', ?)",
                (MOCK_VERSION,),
            )
            conn.commit()

    print(f"[DB] Hazir: {DB_PATH}")


# ─────────────────────────────────────────────────────────────────────────────
# Sorgular
# ─────────────────────────────────────────────────────────────────────────────

def get_tarlalar() -> list:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM tarlalar ORDER BY id").fetchall()
        return [dict(r) for r in rows]


def get_tarla(tarla_id: int):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM tarlalar WHERE id=?", (tarla_id,)
        ).fetchone()
        return dict(row) if row else None


def add_rover_olcum(tarla_id: int, data: dict) -> int:
    """Rover ölçümü kaydet, yeni kaydın id'sini döndür."""
    data = {"tarla_id": tarla_id, **data}
    valid_cols = {
        "tarla_id", "timestamp", "waypoint_id", "waypoint_label",
        "gps_lat", "gps_lon", "nem_1_pct", "nem_2_pct", "hava_temp_c",
        "hava_nem_pct", "bbch_sinif", "bbch_guven", "hastalik", "hastalik_guven",
        "engel_on_cm", "ndvi_tahmini", "verim_tahmini", "anomali_sayisi",
        "anomaliler", "kds_tavsiye", "image_path", "camera_sinif", "camera_guven",
    }
    if "timestamp" not in data:
        data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    filtered = {k: v for k, v in data.items() if k in valid_cols}
    cols = ", ".join(filtered.keys())
    phs  = ", ".join(f":{k}" for k in filtered)
    with get_connection() as conn:
        cur = conn.execute(
            f"INSERT INTO rover_olcumler ({cols}) VALUES ({phs})", filtered
        )
        conn.commit()
        return cur.lastrowid


def get_rover_olcumler(tarla_id: int, limit: int = 50) -> list:
    """Son rover ölçümleri (en yeni önce)."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM rover_olcumler WHERE tarla_id=? "
            "ORDER BY timestamp DESC LIMIT ?",
            (tarla_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def get_rover_olcumler_asc(tarla_id: int, limit: int = 5000) -> list:
    """Rover ölçümleri kronolojik sırayla (timeline için)."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM rover_olcumler WHERE tarla_id=? "
            "ORDER BY timestamp ASC LIMIT ?",
            (tarla_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def add_tahmin(tarla_id: int, data: dict) -> int:
    """Model tahmini kaydet."""
    data = {"tarla_id": tarla_id, **data}
    if "timestamp" not in data:
        data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    valid_cols = {
        "tarla_id", "timestamp", "urun", "ndvi_mevcut", "ndvi_tahmin_7gun",
        "ndvi_delta", "saglik_durumu", "verim_tahmini_kg_dekar", "verim_guven_alt",
        "verim_guven_ust", "verim_risk", "fenolojik_evre", "bbch_aralik",
        "kritik_donem", "sulama_aciliyet", "sulama_miktar", "gubre_zamani",
        "gubre_tip", "ekim_skoru", "ekim_kategori", "hava_sicaklik", "hava_nem",
        "hava_yagis_7gun", "hava_uyarilar",
    }
    filtered = {k: v for k, v in data.items() if k in valid_cols}
    cols = ", ".join(filtered.keys())
    phs  = ", ".join(f":{k}" for k in filtered)
    with get_connection() as conn:
        cur = conn.execute(
            f"INSERT INTO tarla_tahminler ({cols}) VALUES ({phs})", filtered
        )
        conn.commit()
        return cur.lastrowid


def get_son_tahmin(tarla_id: int):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM tarla_tahminler WHERE tarla_id=? "
            "ORDER BY timestamp DESC LIMIT 1",
            (tarla_id,),
        ).fetchone()
        return dict(row) if row else None


def get_tarla_ozet(tarla_id: int) -> dict:
    tarla    = get_tarla(tarla_id) or {}
    tahmin   = get_son_tahmin(tarla_id) or {}
    olcumler = get_rover_olcumler(tarla_id, limit=1)
    son_rover = olcumler[0] if olcumler else {}
    return {"tarla": tarla, "tahmin": tahmin, "son_rover": son_rover}


def save_weather_snapshot(tarla_id: int, data: dict) -> bool:
    """Hava durumu anlık görüntüsü kaydet. Aynı gün varsa atla (IGNORE)."""
    data = {"tarla_id": tarla_id, **data}
    if "tarih" not in data:
        data["tarih"] = date.today().isoformat()
    if "timestamp" not in data:
        data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    valid_cols = {
        "tarla_id", "timestamp", "tarih", "konum_lat", "konum_lon",
        "hava_temp_c", "hava_nem_pct", "toprak_temp_c", "toprak_nem_pct",
        "yagis_mm", "ruzgar_kmh", "temp_max", "temp_min", "yagis_gunluk_mm",
        "et0_mm", "yagis_olasilik", "gdd_kumulatif", "don_riski", "sicak_stres",
    }
    filtered = {k: v for k, v in data.items() if k in valid_cols}
    cols = ", ".join(filtered.keys())
    phs  = ", ".join(f":{k}" for k in filtered)
    with get_connection() as conn:
        conn.execute(
            f"INSERT OR IGNORE INTO hava_kayitlari ({cols}) VALUES ({phs})", filtered
        )
        conn.commit()
    return True


def get_weather_history(tarla_id: int, days: int = 30) -> list:
    """Son N günün hava kayıtlarını kronolojik sırayla döndür."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM hava_kayitlari WHERE tarla_id=? "
            "ORDER BY tarih DESC LIMIT ?",
            (tarla_id, days),
        ).fetchall()
        return [dict(r) for r in reversed(rows)]


def get_weather_by_date_range(tarla_id: int, start_date: str, end_date: str) -> list:
    """Belirli tarih aralığındaki hava kayıtları (ASC)."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM hava_kayitlari "
            "WHERE tarla_id=? AND tarih BETWEEN ? AND ? "
            "ORDER BY tarih ASC",
            (tarla_id, start_date, end_date),
        ).fetchall()
        return [dict(r) for r in rows]


def get_weather_stats(tarla_id: int, days: int = 30) -> dict:
    """Son N günün özet istatistikleri."""
    history = get_weather_history(tarla_id, days)
    if not history:
        return {}
    temps     = [r["hava_temp_c"]      for r in history if r.get("hava_temp_c")      is not None]
    t_maxs    = [r["temp_max"]          for r in history if r.get("temp_max")          is not None]
    t_mins    = [r["temp_min"]          for r in history if r.get("temp_min")          is not None]
    yagislar  = [r["yagis_gunluk_mm"]   for r in history if r.get("yagis_gunluk_mm")  is not None]
    return {
        "gun_sayisi":    len(history),
        "avg_temp":      round(sum(temps) / len(temps), 1) if temps else None,
        "max_temp":      round(max(t_maxs), 1) if t_maxs else None,
        "min_temp":      round(min(t_mins), 1) if t_mins else None,
        "toplam_yagis":  round(sum(yagislar), 1) if yagislar else None,
        "yagisli_gun":   sum(1 for y in yagislar if y > 0.5),
        "don_gun":       sum(1 for r in history if r.get("don_riski", 0)),
        "sicak_gun":     sum(1 for r in history if r.get("sicak_stres", 0)),
        "son_gdd_kum":   history[-1].get("gdd_kumulatif") if history else None,
    }


def generate_model_predictions_for_tarla(tarla_id):
    """
    Seçili tarla için model tahminleri üretir.
    ConvLSTM/LSTM → bu tarla bu tarihte nasıl olmalıydı?
    XGBoost → sezon sonu tahmini verim?
    Sonuçları tarla_tahminler tablosuna yazar.
    """
    tarla = get_tarla(tarla_id)
    if not tarla:
        return
    
    # 1. predict() çağır — modelin "olması gerekeni" üretir
    try:
        from inference_cp2 import predict
        crop = "Wheat" if "Buğday" in tarla["aktif_urun"] else "Sunflower"
        model_tahmin = predict(crop)
    except Exception as e:
        print(f"[Tahmin Hata] predict(): {e}")
        model_tahmin = {}
        crop = "Wheat" if "Buğday" in tarla["aktif_urun"] else "Sunflower"
    
    # 2. predict_yield() çağır — sezon sonu verim projeksiyonu
    try:
        from inference_yield import predict_yield
        verim_tahmin = predict_yield(crop)
    except Exception as e:
        print(f"[Tahmin Hata] predict_yield(): {e}")
        verim_tahmin = None
    
    # 3. Hava ve fenoloji
    try:
        from weather_service import get_current_weather, get_7day_forecast
        from agro_calendar import get_current_phenology, get_irrigation_advice
        
        weather = get_current_weather(tarla["konum_lat"], tarla["konum_lon"])
        forecast = get_7day_forecast(tarla["konum_lat"], tarla["konum_lon"])
        fenoloji = get_current_phenology(crop)
        sulama = get_irrigation_advice(crop, datetime.now().month, 
                                        weather.get("soil_moisture", 0.25)*100 if weather else 25,
                                        forecast)
    except Exception as e:
        print(f"[Tahmin Hata] Hava/Fenoloji: {e}")
        weather = {}
        forecast = []
        fenoloji = {}
        sulama = {}
    
    # 4. DB'ye kaydet
    
    # inference_cp2 structure compatibility
    delta = model_tahmin.get("trend", {}).get("delta") if isinstance(model_tahmin.get("trend"), dict) else model_tahmin.get("delta")
    status = model_tahmin.get("health", {}).get("status") if isinstance(model_tahmin.get("health"), dict) else model_tahmin.get("health_status")
    
    add_tahmin(tarla_id, {
        "urun": crop,
        "ndvi_mevcut": model_tahmin.get("current_ndvi"),
        "ndvi_tahmin_7gun": model_tahmin.get("predicted_ndvi"),
        "ndvi_delta": delta,
        "saglik_durumu": status,
        "verim_tahmini_kg_dekar": verim_tahmin.get("tahmini_verim_kg_dekar") if verim_tahmin else None,
        "verim_risk": verim_tahmin.get("risk_analizi", {}).get("risk_seviyesi") if isinstance(verim_tahmin, dict) and isinstance(verim_tahmin.get("risk_analizi"), dict) else (verim_tahmin.get("risk_analizi") if verim_tahmin else None),
        "fenolojik_evre": fenoloji.get("evre"),
        "sulama_aciliyet": sulama.get("aciliyet"),
    })


# ─────────────────────────────────────────────────────────────────────────────
# CLI test
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    if "--reset" in sys.argv:
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
            print("[DB] Eski veritabanı silindi.")
    init_db()
    tarlalar = get_tarlalar()
    print(f"\n{len(tarlalar)} tarla:")
    for t in tarlalar:
        cnt = len(get_rover_olcumler(t["id"], limit=9999))
        print(f"  [{t['id']}] {t['isim']} — {cnt} rover ölçümü")
    print()
    for tid in range(1, 5):
        olc = get_rover_olcumler(tid, limit=9999)
        anomalili = [r for r in olc if r.get("anomali_sayisi", 0) > 0]
        print(f"  Tarla {tid}: {len(olc)} ölçüm, {len(anomalili)} anomalili")

"""
TRAK-AI KDS — Open-Meteo Hava Servisi
=======================================
API key gerektirmez, tamamen ücretsiz.
Offline modda None döner, sistem çalışmaya devam eder.

Kullanım:
    from weather_service import get_current_weather, get_7day_forecast
    w = get_current_weather()
"""
import requests
from datetime import datetime

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
DEFAULT_LAT = 41.694
DEFAULT_LON = 27.105
TIMEOUT = 8  # saniye


def get_current_weather(lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON) -> dict | None:
    """Anlık hava ve toprak durumu.

    Döndürür:
        {"temp_c", "humidity", "precipitation_mm", "wind_kmh",
         "soil_temp_c", "soil_moisture", "timestamp"}
        Hata durumunda None.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": (
            "temperature_2m,relative_humidity_2m,precipitation,"
            "wind_speed_10m,soil_temperature_0cm,soil_moisture_0_to_1cm"
        ),
        "timezone": "Europe/Istanbul",
    }
    try:
        resp = requests.get(OPEN_METEO_URL, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        cur = resp.json().get("current", {})
        return {
            "temp_c":          float(cur.get("temperature_2m", 0)),
            "humidity":        float(cur.get("relative_humidity_2m", 0)),
            "precipitation_mm": float(cur.get("precipitation", 0)),
            "wind_kmh":        float(cur.get("wind_speed_10m", 0)),
            "soil_temp_c":     float(cur.get("soil_temperature_0cm", 0)),
            "soil_moisture":   round(float(cur.get("soil_moisture_0_to_1cm", 0)) * 100, 1),
            "timestamp":       cur.get("time", datetime.now().isoformat()),
        }
    except Exception:
        return None


def get_7day_forecast(lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON) -> list[dict] | None:
    """7 günlük günlük tahmin.

    Döndürür:
        list[{"date", "temp_max", "temp_min", "precip_mm", "et0_mm", "precip_prob"}]
        Hata durumunda None.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": (
            "temperature_2m_max,temperature_2m_min,precipitation_sum,"
            "et0_fao_evapotranspiration,precipitation_probability_max"
        ),
        "timezone": "Europe/Istanbul",
        "forecast_days": 7,
    }
    try:
        resp = requests.get(OPEN_METEO_URL, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        daily = resp.json().get("daily", {})
        dates      = daily.get("time", [])
        t_max      = daily.get("temperature_2m_max", [])
        t_min      = daily.get("temperature_2m_min", [])
        precip     = daily.get("precipitation_sum", [])
        et0        = daily.get("et0_fao_evapotranspiration", [])
        precip_prob = daily.get("precipitation_probability_max", [])
        return [
            {
                "date":       dates[i],
                "temp_max":   float(t_max[i]) if i < len(t_max) else 0,
                "temp_min":   float(t_min[i]) if i < len(t_min) else 0,
                "precip_mm":  float(precip[i]) if i < len(precip) else 0,
                "et0_mm":     float(et0[i]) if i < len(et0) else 0,
                "precip_prob": int(precip_prob[i]) if i < len(precip_prob) else 0,
            }
            for i in range(len(dates))
        ]
    except Exception:
        return None


def get_weather_alerts(forecast: list[dict] | None) -> list[dict]:
    """Tahmin listesinden otomatik uyarılar üret.

    Her eleman: {"level": "error" | "warning", "text": str}
    """
    if not forecast:
        return []
    alerts = []
    hot_dry_streak = 0

    for day in forecast:
        date   = day["date"]
        t_max  = day["temp_max"]
        t_min  = day["temp_min"]
        precip = day["precip_mm"]

        if t_max > 35:
            alerts.append({
                "level": "error",
                "text": f"SICAK DALGASI: {date} günü {t_max:.0f}°C bekleniyor",
            })
        if t_min < 2:
            alerts.append({
                "level": "error",
                "text": f"DON RİSKİ: {date} günü gece {t_min:.0f}°C'ye düşebilir",
            })
        if precip > 30:
            alerts.append({
                "level": "warning",
                "text": f"YOĞUN YAĞIŞ: {date} günü {precip:.0f}mm yağış bekleniyor",
            })

        hot_dry_streak = hot_dry_streak + 1 if (precip == 0 and t_max > 30) else 0

    if hot_dry_streak >= 3:
        alerts.append({
            "level": "warning",
            "text": f"KURAKLIK RİSKİ: {hot_dry_streak} gündür yağışsız ve sıcak",
        })
    return alerts


def format_weather_context(
    current: dict | None = None,
    forecast: list[dict] | None = None,
) -> str | None:
    """Hava verisini LLM bağlamı için Türkçe metne dönüştür."""
    if current is None and forecast is None:
        return None

    parts = []

    if current:
        parts.append(
            f"Anlık Hava (Kırklareli-Vize): "
            f"Sıcaklık {current['temp_c']:.0f}°C, "
            f"Nem %{current['humidity']:.0f}, "
            f"Yağış {current['precipitation_mm']:.1f}mm, "
            f"Rüzgar {current['wind_kmh']:.0f}km/h, "
            f"Toprak sıcaklığı {current['soil_temp_c']:.0f}°C."
        )

    if forecast:
        fc_parts = []
        for d in forecast[:3]:
            fc_parts.append(
                f"{d['date']}: max {d['temp_max']:.0f}°C / min {d['temp_min']:.0f}°C, "
                f"yağış {d['precip_mm']:.0f}mm"
            )
        parts.append("3 Günlük Tahmin: " + "; ".join(fc_parts) + ".")

        alerts = get_weather_alerts(forecast)
        if alerts:
            parts.append("HAVA UYARILARI: " + " | ".join(a["text"] for a in alerts))

    return " ".join(parts) if parts else None


def collect_and_save_weather(tarla_id: int, force: bool = False) -> bool:
    """Tarla için anlık hava verisini çekip DB'ye kaydet.

    force=False → bugün zaten kayıt varsa atla (UNIQUE kısıtı zaten korur,
    ama önce kontrol ederek gereksiz API çağrısını önleriz).
    """
    try:
        from database import get_tarla, save_weather_snapshot, get_weather_by_date_range
    except ImportError:
        return False

    tarla = get_tarla(tarla_id)
    if not tarla:
        return False

    today = datetime.now().strftime("%Y-%m-%d")

    if not force:
        existing = get_weather_by_date_range(tarla_id, today, today)
        if existing:
            return True  # zaten var, tekrar çekmeye gerek yok

    lat = tarla.get("konum_lat", DEFAULT_LAT)
    lon = tarla.get("konum_lon", DEFAULT_LON)

    current  = get_current_weather(lat, lon)
    forecast = get_7day_forecast(lat, lon)

    if not current and not forecast:
        return False

    # Bugünün tahmin satırını bul (veya current'ı kullan)
    today_fc = {}
    if forecast:
        for d in forecast:
            if d.get("date", "").startswith(today):
                today_fc = d
                break

    temp_c   = current.get("temp_c")   if current else None
    hava_nem = current.get("humidity") if current else None
    precip   = today_fc.get("precip_mm", current.get("precipitation_mm", 0) if current else 0)
    wind     = current.get("wind_kmh") if current else None
    soil_tmp = current.get("soil_temp_c") if current else None
    soil_nem = current.get("soil_moisture") if current else None
    t_max    = today_fc.get("temp_max")
    t_min    = today_fc.get("temp_min")
    et0      = today_fc.get("et0_mm")
    precip_p = today_fc.get("precip_prob")

    save_weather_snapshot(tarla_id, {
        "tarih":           today,
        "konum_lat":       lat,
        "konum_lon":       lon,
        "hava_temp_c":     temp_c,
        "hava_nem_pct":    hava_nem,
        "toprak_temp_c":   soil_tmp,
        "toprak_nem_pct":  soil_nem,
        "yagis_mm":        precip,
        "ruzgar_kmh":      wind,
        "temp_max":        t_max,
        "temp_min":        t_min,
        "yagis_gunluk_mm": precip,
        "et0_mm":          et0,
        "yagis_olasilik":  precip_p,
    })
    return True


def collect_weather_for_all_tarlalar() -> dict:
    """Tüm tarlalar için hava verisini topla. {tarla_id: True/False} döndür."""
    try:
        from database import get_tarlalar
        tarlalar = get_tarlalar()
    except ImportError:
        return {}
    return {t["id"]: collect_and_save_weather(t["id"]) for t in tarlalar}


if __name__ == "__main__":
    print("=== Open-Meteo Hava Servisi Testi ===")
    cur = get_current_weather()
    if cur:
        print(f"Anlık: {cur}")
    else:
        print("Anlık hava alınamadı (offline?)")

    fc = get_7day_forecast()
    if fc:
        print(f"7 Günlük ({len(fc)} gün):")
        for d in fc:
            print(f"  {d['date']}: max {d['temp_max']}°C, yağış {d['precip_mm']}mm")
        alerts = get_weather_alerts(fc)
        print(f"Uyarılar: {alerts or 'yok'}")
    else:
        print("Tahmin alınamadı")

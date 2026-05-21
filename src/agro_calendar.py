"""
TRAK-AI KDS — Agronomik Takvim ve Ekim Karar Motoru
=====================================================
Trakya bölgesi buğday ve ayçiçeği için fenoloji,
ekim penceresi, sulama ve gübreleme tavsiyeleri.

Kullanım:
    from agro_calendar import get_current_phenology, format_agro_context
"""
from datetime import datetime

BUGDAY_TAKVIM = {
    "urun": "Kışlık Buğday",
    "ekim_ay_baslangic": 10,
    "ekim_ay_bitis": 11,
    "ideal_toprak_sicaklik_min": 8,
    "ideal_toprak_sicaklik_max": 12,
    "don_riski_esik": 2,
    "min_toprak_nem": 20,
    "max_toprak_nem": 45,
    "hasat_ay": [6, 7],
    "fenoloji": {
        "ekim_cimlenme": {"ay": [10, 11], "bbch": "00-09", "aciklama": "Tohum ekimi ve çimlenme"},
        "kardeslenme": {"ay": [11, 12, 1, 2], "bbch": "20-29", "aciklama": "Kardeşlenme, kök gelişimi"},
        "sapa_kalkma": {"ay": [3, 4], "bbch": "30-39", "aciklama": "Sapa kalkma, boğum oluşumu"},
        "basaklanma": {"ay": [4, 5], "bbch": "50-59", "aciklama": "Başaklanma"},
        "ciceklenme": {"ay": [5], "bbch": "60-69", "aciklama": "Çiçeklenme, tozlanma"},
        "dane_dolumu": {"ay": [5, 6], "bbch": "70-79", "aciklama": "Dane dolum, süt-hamur olumu"},
        "olgunlasma": {"ay": [6, 7], "bbch": "80-89", "aciklama": "Olgunlaşma ve hasat"},
    },
    "sulama_kritik_donemler": [
        {"evre": "Kardeşlenme", "ay": [11, 12], "aciklama": "Kök gelişimi için yeterli nem şart"},
        {"evre": "Sapa kalkma", "ay": [3, 4], "aciklama": "Hızlı büyüme, su ihtiyacı artar"},
        {"evre": "Çiçeklenme", "ay": [5], "aciklama": "EN KRİTİK — su stresi verimi %30-50 düşürür"},
        {"evre": "Dane dolumu", "ay": [5, 6], "aciklama": "Dane ağırlığı için nem gerekli"},
    ],
    "gubre_takvimi": [
        {"donem": "Ekim", "ay": [10], "tip": "Taban gübresi", "aciklama": "DAP 20-20-0, dekara 20-25 kg"},
        {"donem": "Kardeşlenme sonu", "ay": [2, 3], "tip": "Üst gübresi", "aciklama": "Amonyum nitrat %33, dekara 15-20 kg"},
        {"donem": "Sapa kalkma", "ay": [3, 4], "tip": "2. üst gübresi", "aciklama": "Üre %46, dekara 10-15 kg (isteğe bağlı)"},
    ],
}

AYCICEGI_TAKVIM = {
    "urun": "Yazlık Ayçiçeği",
    "ekim_ay_baslangic": 4,
    "ekim_ay_bitis": 5,
    "ideal_toprak_sicaklik_min": 8,
    "ideal_toprak_sicaklik_max": 14,
    "don_riski_esik": 0,
    "min_toprak_nem": 22,
    "max_toprak_nem": 50,
    "hasat_ay": [8, 9],
    "fenoloji": {
        "cimlenme": {"ay": [4, 5], "bbch": "00-09", "aciklama": "Çimlenme ve çıkış"},
        "yaprak": {"ay": [5, 6], "bbch": "10-19", "aciklama": "Yaprak gelişimi"},
        "sap_uzamasi": {"ay": [6], "bbch": "30-39", "aciklama": "Sap uzaması"},
        "tabla_olusumu": {"ay": [6, 7], "bbch": "50-59", "aciklama": "Tabla (çiçek yatağı) oluşumu"},
        "ciceklenme": {"ay": [7], "bbch": "60-69", "aciklama": "Çiçeklenme — EN KRİTİK dönem"},
        "dane_dolumu": {"ay": [7, 8], "bbch": "70-79", "aciklama": "Dane dolumu, yağ birikimi"},
        "olgunlasma": {"ay": [8, 9], "bbch": "80-89", "aciklama": "Olgunlaşma ve hasat"},
    },
    "sulama_kritik_donemler": [
        {"evre": "Tabla oluşumu", "ay": [6, 7], "aciklama": "Tabla büyüklüğü sulama ile doğru orantılı"},
        {"evre": "Çiçeklenme", "ay": [7], "aciklama": "EN KRİTİK — su stresi verimi %40-60 düşürür"},
        {"evre": "Dane dolumu", "ay": [7, 8], "aciklama": "Yağ oranı ve dane ağırlığı için kritik"},
    ],
    "gubre_takvimi": [
        {"donem": "Ekim", "ay": [4], "tip": "Taban gübresi", "aciklama": "DAP 20-20-0, dekara 25-30 kg"},
        {"donem": "4-6 yaprak", "ay": [5], "tip": "Üst gübresi", "aciklama": "Amonyum sülfat, dekara 20-25 kg"},
    ],
}

_CROP_MAP = {"Wheat": BUGDAY_TAKVIM, "Sunflower": AYCICEGI_TAKVIM}


def _get_takvim(crop_type: str) -> dict:
    t = _CROP_MAP.get(crop_type)
    if t is None:
        raise ValueError(f"Bilinmeyen ürün: '{crop_type}'. Geçerli: {list(_CROP_MAP)}")
    return t


def _in_ekim_sezonu(takvim: dict, month: int) -> bool:
    bas = takvim["ekim_ay_baslangic"]
    bit = takvim["ekim_ay_bitis"]
    return month >= bas or month <= bit if bas > bit else bas <= month <= bit


def get_current_phenology(crop_type: str, month: int = None) -> dict:
    """Verilen ay için hangi fenolojik evrede olunması gerektiğini döndürür."""
    if month is None:
        month = datetime.now().month

    takvim = _get_takvim(crop_type)
    kritik_aylar = {ay for k in takvim["sulama_kritik_donemler"] for ay in k["ay"]}

    for evre_adi, evre in takvim["fenoloji"].items():
        if month in evre["ay"]:
            return {
                "evre": evre_adi,
                "bbch_aralik": evre["bbch"],
                "aciklama": evre["aciklama"],
                "kritik_mi": month in kritik_aylar,
            }

    return {
        "evre": "ara_donem",
        "bbch_aralik": "—",
        "aciklama": "Bu ay aktif üretim dönemi dışında (dinlenme/toprak hazırlığı).",
        "kritik_mi": False,
    }


def _skor_kategori(skor: int) -> str:
    if skor >= 80:
        return "EKİM İÇİN İDEAL — Hemen ekin!"
    if skor >= 60:
        return "UYGUN — Bu hafta ekilebilir"
    if skor >= 40:
        return "DİKKATLİ — Koşullar tam ideal değil"
    if skor >= 20:
        return "ERTELEYİN — Bekleyin"
    return "EKİM YAPMAYIN"


def evaluate_planting_window(
    crop_type: str,
    weather_current: dict = None,
    weather_forecast: list = None,
) -> dict:
    """Gerçek zamanlı hava verisine dayalı dinamik ekim kararı (0-100 skor).

    Bileşenler: toprak sıcaklığı (+25), toprak nemi (+20), don riski (+20), yağış (+15) = max 80.
    Skor ≥ 60 ve engel yok → ekim_uygun=True.
    """
    takvim = _get_takvim(crop_type)
    month = datetime.now().month

    _detay_bos = {
        "toprak_sicaklik": {"deger": None, "durum": "VERİ YOK", "puan": 0},
        "toprak_nem":      {"deger": None, "durum": "VERİ YOK", "puan": 0},
        "don_riski":       {"var_mi": False, "gunler": [], "puan": 0},
        "yagis":           {"uygun_mu": False, "aciklama": "Veri yok", "puan": 0},
    }

    if not _in_ekim_sezonu(takvim, month):
        bas = takvim["ekim_ay_baslangic"]
        bit = takvim["ekim_ay_bitis"]
        return {
            "ekim_uygun": False,
            "skor": 0,
            "kategori": "EKİM DÖNEMİ DEĞİL",
            "gerekce": (
                f"{takvim['urun']} için ekim sezonu {bas}–{bit}. aylar arasındadır. "
                "Şu an ekim dönemi değil."
            ),
            "engeller": ["Ekim sezonu dışında"],
            "oneriler": [f"Ekim için {bas}. ayı bekleyin"],
            "detay": _detay_bos,
        }

    if weather_current is None:
        return {
            "ekim_uygun": False,
            "skor": 25,
            "kategori": _skor_kategori(25),
            "gerekce": (
                f"{takvim['urun']} için ekim sezonu uygun ancak hava verisi alınamadı. "
                "Sadece takvim bazlı değerlendirme."
            ),
            "engeller": [],
            "oneriler": ["Hava verisi mevcut olduğunda daha detaylı değerlendirme yapılabilir"],
            "detay": _detay_bos,
        }

    engeller = []
    oneriler = []
    skor = 0
    detay = {}

    # 1. Toprak sıcaklığı (+25 ideal, +15 uygun, +0 kötü)
    soil_temp = weather_current.get("soil_temp_c")
    t_min = takvim["ideal_toprak_sicaklik_min"]
    t_max = takvim["ideal_toprak_sicaklik_max"]
    t_uygun_ust = 18 if crop_type == "Sunflower" else 15
    if soil_temp is not None:
        if t_min <= soil_temp <= t_max:
            puan_st, durum_st = 25, "İDEAL"
        elif (t_min - 2) <= soil_temp < t_min or t_max < soil_temp <= t_uygun_ust:
            puan_st, durum_st = 15, "UYGUN"
            if soil_temp > t_max:
                oneriler.append("Sabah erken saatlerde veya birkaç gün sonra ölçüm alın")
        else:
            puan_st, durum_st = 0, "KÖTÜ"
            if soil_temp < (t_min - 2):
                engeller.append(f"Toprak çok soğuk: {soil_temp:.1f}°C (ideal: {t_min}–{t_max}°C)")
            else:
                engeller.append(f"Toprak çok sıcak: {soil_temp:.1f}°C (ideal: {t_min}–{t_max}°C)")
    else:
        puan_st, durum_st = 0, "VERİ YOK"
    skor += puan_st
    detay["toprak_sicaklik"] = {"deger": soil_temp, "durum": durum_st, "puan": puan_st}

    # 2. Toprak nemi (+20 ideal, +10 sınırda, +0 kötü)
    soil_nem = weather_current.get("soil_moisture")
    n_min = takvim["min_toprak_nem"]
    n_max = takvim["max_toprak_nem"]
    n_sinir_ust = 55 if crop_type == "Sunflower" else 50
    if soil_nem is not None:
        if n_min <= soil_nem <= n_max:
            puan_sn, durum_sn = 20, "İDEAL"
        elif 15 <= soil_nem < n_min or n_max < soil_nem <= n_sinir_ust:
            puan_sn, durum_sn = 10, "SINIRDA"
            if soil_nem < n_min:
                oneriler.append("Ekim öncesi can suyu verin (15-20 mm)")
            else:
                oneriler.append("Toprak kuruyunca ekin, çamurda ekimde tohum çürür")
        else:
            puan_sn, durum_sn = 0, "KÖTÜ"
            if soil_nem < 15:
                engeller.append(f"Toprak çok kuru: %{soil_nem:.0f} (ideal: %{n_min}–{n_max})")
                oneriler.append("Ekim öncesi can suyu verin (15-20 mm)")
            else:
                engeller.append(f"Toprak çok nemli/çamurlu: %{soil_nem:.0f} (ideal: %{n_min}–{n_max})")
                oneriler.append("Toprak kuruyunca ekin, çamurda ekimde tohum çürür")
    else:
        puan_sn, durum_sn = 0, "VERİ YOK"
    skor += puan_sn
    detay["toprak_nem"] = {"deger": soil_nem, "durum": durum_sn, "puan": puan_sn}

    # 3. Don riski (+20 don yok, +0 don var; ayçiçeği için mutlak engel)
    if weather_forecast:
        don_esik = takvim["don_riski_esik"]
        don_gunleri = [d["date"] for d in weather_forecast if d.get("temp_min", 99) < don_esik]
        var_mi = len(don_gunleri) > 0
        if var_mi:
            puan_don = 0
            engeller.append(
                f"Don riski: {', '.join(don_gunleri)} günlerinde {don_esik}°C altı bekleniyor"
            )
            oneriler.append("Don geçene kadar ekim yapmayın")
        else:
            puan_don = 20
        detay["don_riski"] = {"var_mi": var_mi, "gunler": don_gunleri, "puan": puan_don}
        skor += puan_don

        if crop_type == "Sunflower" and var_mi:
            detay["yagis"] = {
                "uygun_mu": False,
                "aciklama": "Don riski nedeniyle değerlendirilmedi",
                "puan": 0,
            }
            return {
                "ekim_uygun": False,
                "skor": 0,
                "kategori": "EKİM YAPMAYIN",
                "gerekce": (
                    f"Ayçiçeği dona dayanmaz. Önümüzdeki günlerde don riski var: "
                    f"{', '.join(don_gunleri)}. Kesinlikle ekim yapmayın."
                ),
                "engeller": engeller,
                "oneriler": oneriler,
                "detay": detay,
            }
    else:
        detay["don_riski"] = {"var_mi": False, "gunler": [], "puan": 20}
        skor += 20

    # 4. Yağış (+15 ideal, +8 kabul edilebilir, +0 kötü)
    if weather_forecast:
        ilk_3_max = max((d.get("precip_mm", 0) for d in weather_forecast[:3]), default=0)
        ilk_3_toplam = sum(d.get("precip_mm", 0) for d in weather_forecast[:3])
        gun_3_5_toplam = sum(d.get("precip_mm", 0) for d in weather_forecast[2:5])

        if ilk_3_max > 30:
            puan_yag, uygun_mu = 0, False
            aciklama = f"Ekim sonrası aşırı yağış riski ({ilk_3_max:.0f} mm)"
            engeller.append("Yoğun yağış riski — ekim sonrası tohum çürüme tehlikesi")
            oneriler.append("Yağış geçtikten 2-3 gün sonra ekin")
        elif ilk_3_toplam < 10 and 5 <= gun_3_5_toplam <= 25:
            puan_yag, uygun_mu = 15, True
            aciklama = "Ekim sonrası hafif yağış bekleniyor — ideal koşul"
        else:
            puan_yag, uygun_mu = 8, True
            aciklama = "Yağış koşulları kabul edilebilir"
    else:
        puan_yag, uygun_mu = 8, True
        aciklama = "Tahmin verisi yok"
    skor += puan_yag
    detay["yagis"] = {"uygun_mu": uygun_mu, "aciklama": aciklama, "puan": puan_yag}

    ekim_uygun = skor >= 60 and len(engeller) == 0
    kategori = _skor_kategori(skor)

    if ekim_uygun:
        gerekce = (
            f"{takvim['urun']} için koşullar uygun (skor: {skor}/100). "
            "Ekime başlayabilirsiniz."
        )
    elif engeller:
        gerekce = (
            f"{takvim['urun']} ekiminde {len(engeller)} engel var (skor: {skor}/100): "
            + "; ".join(engeller[:2])
        )
    else:
        gerekce = f"{takvim['urun']} için koşullar kısmen uygun (skor: {skor}/100)."

    return {
        "ekim_uygun": ekim_uygun,
        "skor": skor,
        "kategori": kategori,
        "gerekce": gerekce,
        "engeller": engeller,
        "oneriler": oneriler,
        "detay": detay,
    }


def find_best_planting_days(crop_type: str, forecast: list) -> list:
    """7 günlük forecast'ten her gün için ekim skoru hesaplar, en iyiden kötüye sıralar.

    Toprak verisi bilinmediğinden yalnızca hava bileşenleri değerlendirilir (max ~80).
    """
    takvim = _get_takvim(crop_type)
    don_esik = takvim["don_riski_esik"]
    results = []

    for i, day in enumerate(forecast):
        skor = 50  # Toprak verisi bilinmiyor — nötr başlangıç
        gerekce_parts = []

        temp_min = day.get("temp_min", 99)
        precip = day.get("precip_mm", 0)

        # Don riski
        if temp_min < don_esik:
            if crop_type == "Sunflower":
                results.append({
                    "tarih": day.get("date", f"Gün {i + 1}"),
                    "skor": 0,
                    "gerekce": f"Don riski ({temp_min:.1f}°C) — ayçiçeği dona dayanmaz",
                })
                continue
            else:
                skor -= 30
                gerekce_parts.append(f"Don riski ({temp_min:.1f}°C)")
        else:
            skor += 15
            gerekce_parts.append("Don riski yok")

        # Yağış
        if precip > 30:
            skor -= 25
            gerekce_parts.append(f"Aşırı yağış ({precip:.0f} mm)")
        elif precip > 10:
            skor -= 10
            gerekce_parts.append(f"Orta yağış ({precip:.0f} mm)")
        else:
            future_rain = sum(d.get("precip_mm", 0) for d in forecast[i + 1: i + 4])
            if 5 <= future_rain <= 20:
                skor += 15
                gerekce_parts.append("Sonraki günlerde hafif yağış bekleniyor")
            else:
                skor += 5
                gerekce_parts.append("Yağış yok/az")

        skor = max(0, min(100, skor))
        results.append({
            "tarih": day.get("date", f"Gün {i + 1}"),
            "skor": skor,
            "gerekce": ", ".join(gerekce_parts),
        })

    results.sort(key=lambda x: x["skor"], reverse=True)
    return results


def get_irrigation_advice(
    crop_type: str,
    month: int,
    soil_moisture: float,
    weather_forecast: list = None,
) -> dict:
    """Mevcut evre, toprak nemi ve hava tahminine göre sulama tavsiyesi."""
    takvim = _get_takvim(crop_type)
    fenoloji = get_current_phenology(crop_type, month)
    min_nem = takvim["min_toprak_nem"]
    kritik_mi = fenoloji["kritik_mi"]

    yagis_3gun = 0.0
    if weather_forecast:
        yagis_3gun = sum(d.get("precip_mm", 0) for d in weather_forecast[:3])

    if soil_moisture < min_nem and kritik_mi:
        return {
            "sulama_gerekli": True,
            "aciliyet": "ACIL",
            "miktar_ton_dekar": 5.5 if crop_type == "Sunflower" else 4.5,
            "zamanlama": "Hemen (en geç bugün akşam)",
            "gerekce": (
                f"Toprak nemi %{soil_moisture:.0f} — kritik eşiğin (%{min_nem}) altında. "
                f"{fenoloji['aciklama']} evresinde su stresi verimi ciddi düşürür."
            ),
        }

    if soil_moisture < min_nem:
        return {
            "sulama_gerekli": True,
            "aciliyet": "PLANLI",
            "miktar_ton_dekar": 3.5 if crop_type == "Sunflower" else 3.0,
            "zamanlama": "Sabah erken (2-3 gün içinde)",
            "gerekce": (
                f"Toprak nemi %{soil_moisture:.0f} — minimum eşiğin (%{min_nem}) altında. "
                "Nem takviyesi gerekli."
            ),
        }

    if kritik_mi and soil_moisture < (min_nem + 10) and yagis_3gun < 10:
        return {
            "sulama_gerekli": True,
            "aciliyet": "PLANLI",
            "miktar_ton_dekar": 4.0 if crop_type == "Sunflower" else 3.5,
            "zamanlama": "Sabah erken (bu hafta içinde)",
            "gerekce": (
                f"Kritik dönem ({fenoloji['aciklama']}) — toprak nemi %{soil_moisture:.0f}, "
                f"3 günlük yağış {yagis_3gun:.0f}mm. Takviye sulama önerilir."
            ),
        }

    if yagis_3gun > 20:
        return {
            "sulama_gerekli": False,
            "aciliyet": "GEREKSIZ",
            "miktar_ton_dekar": 0.0,
            "zamanlama": "—",
            "gerekce": f"Önümüzdeki 3 günde {yagis_3gun:.0f}mm yağış bekleniyor. Sulama gereksiz.",
        }

    return {
        "sulama_gerekli": False,
        "aciliyet": "GEREKSIZ",
        "miktar_ton_dekar": 0.0,
        "zamanlama": "—",
        "gerekce": f"Toprak nemi %{soil_moisture:.0f} yeterli. Sulama şimdilik gerekmez.",
    }


def get_fertilization_advice(crop_type: str, month: int) -> dict:
    """Bu ay gübreleme yapılmalı mı?"""
    takvim = _get_takvim(crop_type)

    for g in takvim["gubre_takvimi"]:
        if month in g["ay"]:
            return {
                "gubre_zamani": True,
                "tip": g["tip"],
                "doz": g["aciklama"],
                "aciklama": f"{g['donem']} dönemi: {g['aciklama']}",
            }

    return {
        "gubre_zamani": False,
        "tip": "—",
        "doz": "—",
        "aciklama": "Bu ay için planlı gübre uygulaması yok.",
    }


def format_agro_context(
    crop_type: str,
    weather_data: dict = None,
    forecast: list = None,
) -> str:
    """Tüm agronomik bilgiyi LLM bağlamı için Türkçe metne dönüştür."""
    month = datetime.now().month
    takvim = _get_takvim(crop_type)

    fenoloji = get_current_phenology(crop_type, month)
    kritik_label = " — KRİTİK DÖNEM" if fenoloji["kritik_mi"] else ""

    parts = [
        f"AGRONOMİK DURUM ({takvim['urun']}):",
        f"Mevcut evre: {fenoloji['aciklama']} (BBCH {fenoloji['bbch_aralik']}){kritik_label}.",
    ]

    if weather_data:
        soil_temp = weather_data.get("soil_temp_c")
        soil_nem = weather_data.get("soil_moisture")
        if soil_temp is not None:
            parts.append(f"Toprak sıcaklığı: {soil_temp:.0f}°C.")
        if soil_nem is not None:
            esik = takvim["min_toprak_nem"]
            nem_durum = "kritik eşiğe yakın" if soil_nem < (esik + 5) else "yeterli"
            parts.append(f"Toprak nemi: %{soil_nem:.0f} ({nem_durum}).")

    soil_moisture_val = (weather_data.get("soil_moisture", 30) if weather_data else 30)
    sulama = get_irrigation_advice(crop_type, month, soil_moisture_val, forecast)
    if sulama["sulama_gerekli"]:
        parts.append(
            f"SULAMA TAVSİYESİ [{sulama['aciliyet']}]: {sulama['gerekce']} "
            f"Tavsiye: {sulama['miktar_ton_dekar']} ton/dekar. "
            f"Zamanlama: {sulama['zamanlama']}."
        )
    else:
        parts.append(f"Sulama: {sulama['gerekce']}")

    if _in_ekim_sezonu(takvim, month):
        ekim = evaluate_planting_window(crop_type, weather_data, forecast)
        durum = "UYGUN" if ekim["ekim_uygun"] else "UYGUN DEĞİL"
        parts.append(f"Ekim penceresi [{durum}]: {ekim['gerekce']}")
    else:
        bas = takvim["ekim_ay_baslangic"]
        bit = takvim["ekim_ay_bitis"]
        parts.append(
            f"Ekim penceresi: {takvim['urun']} için ekim dönemi değil ({bas}-{bit}. aylar)."
        )

    gubre = get_fertilization_advice(crop_type, month)
    if gubre["gubre_zamani"]:
        parts.append(f"Gübreleme: {gubre['aciklama']}")
    else:
        parts.append("Gübreleme: Bu dönemde ek gübreleme önerilmez.")

    return " ".join(parts)


if __name__ == "__main__":
    print("=== Agronomik Takvim Testi ===")
    month = datetime.now().month
    print(f"Test ayı: {month}\n")

    weather_test = {
        "soil_temp_c": 18.5,
        "soil_moisture": 22.0,
        "temp_c": 20.0,
    }
    forecast_test = None
    try:
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from weather_service import get_current_weather, get_7day_forecast
        weather_test = get_current_weather() or weather_test
        forecast_test = get_7day_forecast()
    except Exception:
        pass

    for crop in ["Wheat", "Sunflower"]:
        print(f"--- {crop} ---")
        fen = get_current_phenology(crop)
        print(f"  Fenoloji: evre={fen['evre']}, bbch={fen['bbch_aralik']}, kritik={fen['kritik_mi']}")
        print(f"  Açıklama: {fen['aciklama']}")

        sulama = get_irrigation_advice(crop, month, weather_test.get("soil_moisture", 22.0), forecast_test)
        print(f"  Sulama: [{sulama['aciliyet']}] {sulama['gerekce']}")

        gubre = get_fertilization_advice(crop, month)
        print(f"  Gübreleme: {gubre['gubre_zamani']} — {gubre['aciklama']}")

        ctx = format_agro_context(crop, weather_test, forecast_test)
        print(f"  Bağlam:\n    {ctx}\n")

    print("--- Ekim Penceresi (Ayçiçeği, canlı hava) ---")
    ekim = evaluate_planting_window("Sunflower", weather_test, forecast_test)
    print(f"  Skor: {ekim['skor']}, Uygun: {ekim['ekim_uygun']}")
    print(f"  Gerekçe: {ekim['gerekce']}")
    if ekim["engeller"]:
        print(f"  Engeller: {ekim['engeller']}")
    if ekim["oneriler"]:
        print(f"  Öneriler: {ekim['oneriler']}")
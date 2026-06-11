"""
TRAK-AI Hibrit BBCH Motoru
============================

3 katmanlı BBCH (Biologische Bundesanstalt, Bundessortenamt and CHemical
industry) fenolojik evre hesaplama:

  KATMAN A — GDD (Growing Degree Days) — BİRİNCİL kaynak
              Buğday/ayçiçeği için base_temp ile günlük sıcaklık birikmesi

  KATMAN B — NDVI (Sentinel-2) — KONTROL/onaylayıcı
              Son 30 günün NDVI eğimi + değeri evre tahmin eder

  KATMAN C — Tarih (Sabit takvim) — YEDEK
              Hava + NDVI yoksa ekim tarihine göre sezonluk takvim

Ana fonksiyon: hesapla_bbch(tarla_id) -> dict
  {bbch, kaynak, guven, uyari}

Tablo bağımlılıkları:
  - tarla (lat, lon, crop_type, season_start_month, ekim_tarihi opsiyonel)
  - hava_kayitlari (temperature, sicaklik_c — günlük ortalama sıcaklık)
  - ndvi_kayitlari (tarih, ndvi) — fetch_sentinel2_ndvi.py üretir
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

# Database import
THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from database import get_connection  # noqa: E402

logger = logging.getLogger("trakai.bbch")


# ════════════════════════════════════════════════════════════════════
# GDD EŞIK TABLOLARI
# ════════════════════════════════════════════════════════════════════
WHEAT_GDD_THRESHOLDS = [
    (0, 150, "00-09", "cimlenme"),
    (151, 500, "10-19", "yaprak_gelisimi"),
    (501, 1000, "20-29", "kardeslenme"),
    (1001, 1500, "30-39", "sap_uzamasi"),
    (1501, 1800, "40-49", "basaklanma"),
    (1801, 2100, "60-69", "ciceklenme"),
    (2101, 2400, "70-79", "tane_gelisimi"),
    (2400, 99999, "80-89", "olgunlasma"),
]

SUNFLOWER_GDD_THRESHOLDS = [
    (0, 100, "00-09", "cimlenme"),
    (101, 400, "10-19", "yaprak"),
    (401, 800, "30-39", "sap"),
    (801, 1100, "50-59", "tomurcuk"),
    (1101, 1400, "60-69", "ciceklenme"),
    (1401, 1700, "70-79", "tane_dolumu"),
    (1700, 99999, "80-89", "olgunlasma"),
]

GDD_THRESHOLDS = {
    "wheat":     {"base_temp": 0,  "table": WHEAT_GDD_THRESHOLDS},
    "bugday":    {"base_temp": 0,  "table": WHEAT_GDD_THRESHOLDS},  # alias
    "sunflower": {"base_temp": 6,  "table": SUNFLOWER_GDD_THRESHOLDS},
    "aycicegi":  {"base_temp": 6,  "table": SUNFLOWER_GDD_THRESHOLDS},  # alias
}


def _bbch_to_stage_index(bbch_str: str) -> int:
    """BBCH string ("70-79") -> sıralama indeksi (örn 70)."""
    if not bbch_str or "-" not in bbch_str:
        return -1
    try:
        return int(bbch_str.split("-")[0])
    except ValueError:
        return -1


# ════════════════════════════════════════════════════════════════════
# Tarla ve veri yardımcıları
# ════════════════════════════════════════════════════════════════════
def _get_tarla(tarla_id: int) -> Optional[dict]:
    with get_connection() as c:
        row = c.execute(
            "SELECT id, name, evrenli_id, lat, lon, crop_type, "
            "       season_start_month, season_end_month, active_season_year "
            "FROM tarla WHERE id = ?",
            (tarla_id,)
        ).fetchone()
    return dict(row) if row else None


def _get_ekim_tarihi(tarla: dict) -> Optional[date]:
    """Ekim tarihini tahmin et: season_start_month + 15 = ortalama gün.
    crop_type'a göre default başlangıç ayı:
      wheat: 10 (Ekim)
      sunflower: 4 (Nisan)
    """
    smonth = tarla.get("season_start_month")
    year = tarla.get("active_season_year") or datetime.now().year
    if smonth is None:
        crop = (tarla.get("crop_type") or "").lower()
        smonth = 10 if "wheat" in crop or "bugday" in crop else 4

    # Buğday önceki yıl ekildiği için
    crop = (tarla.get("crop_type") or "").lower()
    if ("wheat" in crop or "bugday" in crop) and smonth >= 9:
        year -= 1

    try:
        return date(year, smonth, 15)
    except ValueError:
        return None


# ════════════════════════════════════════════════════════════════════
# KATMAN A — GDD
# ════════════════════════════════════════════════════════════════════
def _gdd_total(tarla_id: int, ekim: date, today: date,
               base_temp: float) -> tuple[float, int]:
    """hava_kayitlari'ndan ekim ile today arası toplam GDD.
    Döndürür: (total_gdd, gun_sayisi_with_data)
    """
    with get_connection() as c:
        rows = c.execute(
            "SELECT DATE(timestamp) AS gun, "
            "       AVG(COALESCE(temperature, sicaklik_c)) AS t_mean "
            "FROM hava_kayitlari "
            "WHERE tarla_id = ? "
            "  AND DATE(timestamp) BETWEEN ? AND ? "
            "GROUP BY DATE(timestamp) "
            "ORDER BY gun ASC",
            (tarla_id, ekim.isoformat(), today.isoformat())
        ).fetchall()

    total = 0.0
    days_counted = 0
    for r in rows:
        t = r["t_mean"]
        if t is None:
            continue
        gdd = max(0.0, float(t) - base_temp)
        total += gdd
        days_counted += 1
    return total, days_counted


def gdd_to_bbch(crop: str, ekim_tarihi: date, today: date,
                tarla_id: int) -> Optional[dict]:
    """GDD bazlı BBCH tahmin. None döner: yetersiz veri."""
    crop_key = (crop or "").lower()
    cfg = GDD_THRESHOLDS.get(crop_key)
    if cfg is None:
        return None

    base_temp = cfg["base_temp"]
    table = cfg["table"]
    total_gdd, days = _gdd_total(tarla_id, ekim_tarihi, today, base_temp)

    if days < 7:  # en az 1 hafta veri olmalı
        return None

    for low, high, bbch, ad in table:
        if low <= total_gdd <= high:
            return {
                "bbch": bbch,
                "kaynak": "GDD",
                "guven": 0.85,
                "detay": {
                    "total_gdd": round(total_gdd, 1),
                    "base_temp": base_temp,
                    "gun_sayisi": days,
                    "evre_adi": ad,
                    "ekim_tarihi": ekim_tarihi.isoformat(),
                }
            }

    # En üst eşiğin de üstünde
    last = table[-1]
    return {
        "bbch": last[2],
        "kaynak": "GDD",
        "guven": 0.75,
        "detay": {"total_gdd": round(total_gdd, 1), "evre_adi": last[3]}
    }


# ════════════════════════════════════════════════════════════════════
# KATMAN B — NDVI
# ════════════════════════════════════════════════════════════════════
def _get_ndvi_series(tarla_id: int, days: int = 30) -> list[dict]:
    """ndvi_kayitlari'ndan son N günlük seri al."""
    with get_connection() as c:
        # Önce tablo var mı kontrol
        exists = c.execute(
            "SELECT name FROM sqlite_master WHERE name='ndvi_kayitlari'"
        ).fetchone()
        if not exists:
            return []

        cutoff = (datetime.now() - timedelta(days=days)).date()
        rows = c.execute(
            "SELECT tarih, ndvi FROM ndvi_kayitlari "
            "WHERE tarla_id = ? AND tarih >= ? "
            "ORDER BY tarih ASC",
            (tarla_id, cutoff.isoformat())
        ).fetchall()
    return [dict(r) for r in rows]


def ndvi_to_bbch(crop: str, ndvi_series: list[dict]) -> Optional[dict]:
    """NDVI seri (son 30 gün) bazlı BBCH tahmin. None döner: yetersiz veri."""
    if len(ndvi_series) < 3:
        return None

    values = [float(r["ndvi"]) for r in ndvi_series if r.get("ndvi") is not None]
    if len(values) < 3:
        return None

    avg = sum(values) / len(values)
    last = values[-1]
    first = values[0]
    slope = (last - first) / max(1, len(values) - 1)

    # Eğim negatif + değer düşüyorsa olgunlasma
    if slope < -0.005 and last < 0.55:
        return {"bbch": "80-89", "kaynak": "NDVI", "guven": 0.78,
                "detay": {"avg": round(avg, 3), "last": round(last, 3),
                          "slope": round(slope, 4), "evre_adi": "olgunlasma"}}

    # Değer bazlı tablo
    if last < 0.20:
        bbch, ad = "00-09", "toprak_cimlenme"
    elif last < 0.35:
        bbch, ad = "10-19", "yaprak_gelisimi"
    elif last < 0.55:
        bbch, ad = "20-39", "kardeslenme_sap"
    elif last < 0.75:
        bbch, ad = "40-69", "basaklanma_ciceklenme"
    elif last < 0.85:
        bbch, ad = "70-79", "tane_peak"
    else:
        bbch, ad = "70-79", "peak"

    return {"bbch": bbch, "kaynak": "NDVI", "guven": 0.72,
            "detay": {"avg": round(avg, 3), "last": round(last, 3),
                      "slope": round(slope, 4), "n_gozlem": len(values),
                      "evre_adi": ad}}


# ════════════════════════════════════════════════════════════════════
# KATMAN C — TARİH BAZLI YEDEK
# ════════════════════════════════════════════════════════════════════
WHEAT_DATE_TABLE = [
    (0, 14, "00-09"),     # ekimden 0-14 gün → çimlenme
    (15, 60, "10-19"),    # 15-60 gün → yaprak
    (61, 150, "20-29"),   # 2-5 ay → kardeşlenme (kış)
    (151, 195, "30-39"),  # 5-6.5 ay → sap (Mart-Nisan)
    (196, 225, "40-49"),  # 6.5-7.5 ay → başaklanma (Mayıs)
    (226, 245, "60-69"),  # 7.5-8 ay → çiçeklenme
    (246, 270, "70-79"),  # 8-9 ay → tane gelişimi
    (271, 365, "80-89"),  # 9+ ay → olgunlaşma
]

SUNFLOWER_DATE_TABLE = [
    (0, 10, "00-09"),
    (11, 30, "10-19"),
    (31, 60, "30-39"),
    (61, 80, "50-59"),
    (81, 100, "60-69"),
    (101, 130, "70-79"),
    (131, 365, "80-89"),
]


def date_to_bbch(crop: str, ekim_tarihi: date, today: date) -> dict:
    """Tarih bazlı yedek BBCH tahmin."""
    days_since = (today - ekim_tarihi).days
    crop_key = (crop or "").lower()
    table = (WHEAT_DATE_TABLE if ("wheat" in crop_key or "bugday" in crop_key)
             else SUNFLOWER_DATE_TABLE)
    for low, high, bbch in table:
        if low <= days_since <= high:
            return {"bbch": bbch, "kaynak": "DATE", "guven": 0.50,
                    "detay": {"days_since_planting": days_since}}
    return {"bbch": table[-1][2], "kaynak": "DATE", "guven": 0.40,
            "detay": {"days_since_planting": days_since}}


# ════════════════════════════════════════════════════════════════════
# ANA FONKSİYON
# ════════════════════════════════════════════════════════════════════
def hesapla_bbch(tarla_id: int, target_date: Optional[date] = None) -> dict:
    """Tarla için hibrit BBCH hesaplama.

    Returns:
      {
        "bbch":   "70-79",
        "kaynak": "GDD" | "NDVI" | "DATE" | "GDD+NDVI",
        "guven":  0.0-1.0,
        "uyari":  "..."  veya boş,
        "detay":  {...}
      }
    """
    today = target_date or date.today()
    tarla = _get_tarla(tarla_id)
    if tarla is None:
        return {"bbch": None, "kaynak": "NONE", "guven": 0.0,
                "uyari": f"Tarla bulunamadı: id={tarla_id}", "detay": {}}

    crop = (tarla.get("crop_type") or "").lower()
    if not crop:
        return {"bbch": None, "kaynak": "NONE", "guven": 0.0,
                "uyari": "Tarla'da crop_type yok", "detay": {}}

    ekim = _get_ekim_tarihi(tarla)
    if ekim is None or ekim > today:
        return {"bbch": "00-09", "kaynak": "DATE", "guven": 0.30,
                "uyari": "Ekim tarihi hesaplanamadı veya gelecekte",
                "detay": {"ekim_estimate": ekim.isoformat() if ekim else None}}

    # Katman A — GDD
    a = gdd_to_bbch(crop, ekim, today, tarla_id)
    # Katman B — NDVI
    series = _get_ndvi_series(tarla_id)
    b = ndvi_to_bbch(crop, series) if series else None

    # Karşılaştırma + karar
    if a and b:
        # İki kaynaktan da var
        gap = abs(_bbch_to_stage_index(a["bbch"]) - _bbch_to_stage_index(b["bbch"]))
        if a["bbch"] == b["bbch"]:
            return {**a, "kaynak": "GDD+NDVI", "guven": 0.95, "uyari": ""}
        elif gap <= 10:
            # 1 evre fark (10-19 vs 20-29 gibi) — birbirine yakın, GDD birincil
            return {**a, "kaynak": "GDD", "guven": 0.80,
                    "uyari": f"NDVI farklı evre öneriyor: {b['bbch']}"}
        else:
            # 2+ evre fark — uyarı kritik
            return {**a, "kaynak": "GDD", "guven": 0.60,
                    "uyari": (f"GDD ve NDVI çelişiyor: "
                              f"GDD={a['bbch']}, NDVI={b['bbch']}")}

    if a:
        return {**a, "kaynak": "GDD", "guven": 0.80, "uyari": ""}
    if b:
        return {**b, "kaynak": "NDVI", "guven": 0.70, "uyari": ""}

    # Hiçbiri yoksa tarih
    c = date_to_bbch(crop, ekim, today)
    return {**c, "uyari": "Hava ve NDVI verisi yok, tarih bazlı yedek"}


# ════════════════════════════════════════════════════════════════════
# CLI
# ════════════════════════════════════════════════════════════════════
def _cli() -> None:
    import argparse
    ap = argparse.ArgumentParser(description="Hibrit BBCH hesaplama")
    ap.add_argument("--tarla-id", type=int, default=1)
    ap.add_argument("--date", default=None, help="YYYY-MM-DD, default bugün")
    args = ap.parse_args()

    target = (date.fromisoformat(args.date) if args.date else None)
    result = hesapla_bbch(args.tarla_id, target)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    _cli()

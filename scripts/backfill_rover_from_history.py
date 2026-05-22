"""
backfill_rover_from_history.py
================================
Geçmişte çekilmiş (S2 + ERA5 + Soil) unified-features parquet'ini gerçek bir
rover taraması gibi DB'ye yazar.

Akış (her hafta, default cadence=7 gün):
  1. data/prospective/<year>/<site>_unified_features.parquet okunur.
  2. Her satır rover_olcumler şeması için bir kayda dönüştürülür:
       - timestamp     = parquet date + 10:30
       - gps_lat/lon   = tarla centroid + küçük jitter
       - nem_1_pct     = NDWI tabanlı toprak nemi proxy'si
       - hava_temp_c   = ERA5 t2m_mean
       - hava_nem_pct  = ERA5 dew_depression'tan türetilmiş RH proxy
       - bbch_sinif    = sezona göre fenoloji bandı
       - ndvi_tahmini  = S2 NDVI_int
       - kds_tavsiye   = NDVI + drought_index_7d kurallarından
  3. YOLOv8 sınıflandırması:
       a) Eğer `models/crop_health_best.pt` yüklenebiliyor + tarihe ait
          gerçek field-photo var → gerçek inferans.
       b) Aksi halde özellik tabanlı türetim (NDVI + drought + sezon → sınıf).
  4. hava_kayitlari tablosu aynı parquet'ten upsert edilir (offline cache).

Kullanım:
    python scripts/backfill_rover_from_history.py
    python scripts/backfill_rover_from_history.py --site EVR_01 --year 2025
    python scripts/backfill_rover_from_history.py --cadence 1   # günlük
    python scripts/backfill_rover_from_history.py --year 2025 --year 2026

Çıkış:
    logs/backfill_history.jsonl  — her kayıt için audit satırı
    stdout  — özet KPI'lar
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd

# ── path setup ───────────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent
PROJECT_ROOT = _HERE.parent
SRC = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC))

from database import (                                                # noqa: E402
    add_rover_olcum, get_tarla_by_research_code,
    init_db, upsert_weather_snapshot,
)

# Optional: real YOLOv8 if available
try:
    from image_classifier import classifier as _yolo_classifier        # noqa: E402
    _YOLO_AVAILABLE = _yolo_classifier.model is not None
except Exception:                                                      # noqa: BLE001
    _yolo_classifier = None
    _YOLO_AVAILABLE = False


LOG_PATH = PROJECT_ROOT / "logs" / "backfill_history.jsonl"
PROSPECTIVE_DIR = PROJECT_ROOT / "data" / "prospective"
FIELD_PHOTOS_DIR = PROJECT_ROOT / "data" / "visual" / "field_photos"

logger = logging.getLogger("trakai.backfill")


# ─────────────────────────────────────────────────────────────────────────────
# Derivations: parquet row → rover scan dict
# ─────────────────────────────────────────────────────────────────────────────

def _safe(v, default=None):
    if v is None:
        return default
    try:
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return default
    except Exception:                                                  # noqa: BLE001
        pass
    return v


def _is_sunflower(crop: str) -> bool:
    c = (crop or "").lower()
    return ("ayci" in c) or ("ayçi" in c) or ("sunflower" in c)


def _bbch_from_doy(date: datetime, crop: str) -> str:
    """Sezon içi DOY'a göre kabaca BBCH bandı."""
    doy = date.timetuple().tm_yday
    if _is_sunflower(crop):
        # ayçiçeği: ekim Apr 20, hasat Sep 10
        if doy < 110 or doy > 260:
            return "00-09"
        if doy < 130:  return "10-19"
        if doy < 155:  return "20-39"
        if doy < 180:  return "50-59"
        if doy < 210:  return "60-69"
        if doy < 240:  return "70-79"
        return "80-89"
    # bugday: ekim Oct, hasat Jul
    if 274 <= doy or doy < 60:
        return "10-29"
    if doy < 110:  return "30-39"
    if doy < 140:  return "40-59"
    if doy < 170:  return "60-79"
    if doy < 200:  return "80-89"
    return "00-09"


def _rh_from_dew_depression(t2m: float, dew_depr: float) -> float:
    """ERA5 dew-point depression'dan kaba bağıl nem (%) tahmini."""
    if t2m is None or dew_depr is None or math.isnan(t2m) or math.isnan(dew_depr):
        return 60.0
    td = t2m - dew_depr
    # Magnus
    def es(T): return 6.112 * math.exp(17.62 * T / (243.12 + T))
    try:
        return round(100.0 * es(td) / es(t2m), 1)
    except Exception:                                                  # noqa: BLE001
        return 60.0


def _soil_moisture_from_ndwi(ndwi: float) -> float:
    """NDWI -> kaba toprak nemi yüzdesi (mock-friendly proxy).
    NDWI typically in [-0.5, 0.5]; map to [10, 45]%.
    """
    if ndwi is None or math.isnan(ndwi):
        return 20.0
    n = max(min(ndwi, 0.5), -0.5)
    return round(10.0 + (n + 0.5) * 35.0, 1)


def _kds_tavsiye(ndvi: float, drought: float, crop: str) -> tuple[str, list[str]]:
    """Basit NDVI + drought_index kuralları → öneri + anomali listesi."""
    anomaliler: list[str] = []
    tavsiye = ""
    if ndvi is not None and not math.isnan(ndvi) and ndvi < 0.30:
        anomaliler.append(f"Düşük NDVI: {ndvi:.2f}")
    if drought is not None and not math.isnan(drought) and drought < -10.0:
        anomaliler.append(f"Yüksek kuraklık baskısı (DI={drought:.1f})")
        tavsiye = "Sulama önerilir (30-40 mm)."
    if ndvi is not None and ndvi > 0.55 and not anomaliler:
        tavsiye = "Bitki sağlıklı, rutin izleme yeterli."
    return tavsiye, anomaliler


# ─────────────────────────────────────────────────────────────────────────────
# Image classification: real YOLO if photo exists, otherwise feature-derived
# ─────────────────────────────────────────────────────────────────────────────

def _find_field_photo(site_code: str, date: datetime) -> Optional[Path]:
    """`data/visual/field_photos/EVR_01_20250715*.jpg` gibi bir dosya ara."""
    if not FIELD_PHOTOS_DIR.exists():
        return None
    pattern = f"{site_code}_{date.strftime('%Y%m%d')}*"
    for ext in (".jpg", ".jpeg", ".png"):
        for p in FIELD_PHOTOS_DIR.glob(pattern + ext):
            return p
    return None


def _derived_class(ndvi: float, drought: float, crop: str,
                   rng: random.Random) -> tuple[str, float]:
    """Özellik tabanlı sınıf türetimi (YOLO yokken / fotoğraf yokken).

    Stres / hastalık olasılığını NDVI ve drought baskısından çıkarır.
    """
    sunflower = _is_sunflower(crop)
    healthy_label = "saglikli_aycicegi" if sunflower else "saglikli_bugday"
    n = ndvi if (ndvi is not None and not math.isnan(ndvi)) else 0.5
    d = drought if (drought is not None and not math.isnan(drought)) else 0.0

    if n < 0.25 and d < -15:
        return "stres_kuraklik", round(rng.uniform(0.75, 0.92), 3)
    if n < 0.35:
        return "stres_besin", round(rng.uniform(0.65, 0.85), 3)
    if n > 0.55 and rng.random() < 0.08:
        # rare disease pop on dense canopy (proxy)
        return ("hastalik_mildiyo" if sunflower
                else "hastalik_pas"), round(rng.uniform(0.70, 0.86), 3)
    return healthy_label, round(rng.uniform(0.85, 0.97), 3)


def _classify(site_code: str, date: datetime, ndvi: float,
              drought: float, crop: str,
              rng: random.Random) -> tuple[str, float, str, Optional[str]]:
    """Returns (sinif, guven, kaynak, image_path)."""
    photo = _find_field_photo(site_code, date)
    if photo and _YOLO_AVAILABLE and _yolo_classifier is not None:
        try:
            res = _yolo_classifier.classify_file(str(photo))
            if res.get("sinif") and res["sinif"] != "hata":
                return (res["sinif"], float(res.get("guven", 0.0)),
                        "yolo_real", str(photo))
        except Exception as exc:                                       # noqa: BLE001
            logger.debug("YOLO failed on %s: %s", photo, exc)
    sinif, guven = _derived_class(ndvi, drought, crop, rng)
    return sinif, guven, "feature_derived", (str(photo) if photo else None)


# ─────────────────────────────────────────────────────────────────────────────
# Main backfill
# ─────────────────────────────────────────────────────────────────────────────

def _audit(rec: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")


def backfill_one(site_code: str, year: int, cadence_days: int = 7) -> dict:
    parquet = PROSPECTIVE_DIR / str(year) / f"{site_code}_unified_features.parquet"
    if not parquet.exists():
        return {"site": site_code, "year": year, "status": "no_parquet",
                "path": str(parquet)}

    tarla = get_tarla_by_research_code(site_code)
    if tarla is None:
        return {"site": site_code, "year": year, "status": "no_tarla_in_db"}
    tarla_id = int(tarla["id"])
    crop = tarla.get("aktif_urun") or "Bugday"
    lat0 = float(tarla.get("konum_lat") or 41.045)
    lon0 = float(tarla.get("konum_lon") or 27.205)

    df = pd.read_parquet(parquet).copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    df = df[df["date"].dt.year == year]
    if df.empty:
        return {"site": site_code, "year": year, "status": "empty_after_year_filter"}

    rng = random.Random(hash((site_code, year)) & 0xFFFFFFFF)
    rover_inserted = 0
    weather_upserted = 0
    n_yolo = 0
    n_derived = 0

    last_emit: Optional[datetime] = None
    for _, row in df.iterrows():
        d: datetime = row["date"].to_pydatetime()

        # ── 1) weather backfill (her gün) ────────────────────────────────
        try:
            upsert_weather_snapshot(tarla_id, {
                "tarih":           d.strftime("%Y-%m-%d"),
                "konum_lat":       lat0,
                "konum_lon":       lon0,
                "hava_temp_c":     _safe(row.get("t2m_mean")),
                "hava_nem_pct":    _rh_from_dew_depression(
                    row.get("t2m_mean"), row.get("dew_depression")),
                "toprak_temp_c":   _safe(row.get("t2m_mean")),
                "toprak_nem_pct":  _soil_moisture_from_ndwi(row.get("NDWI_int")),
                "yagis_mm":        _safe(row.get("tp_sum"), 0.0),
                "ruzgar_kmh":      None,
                "temp_max":        _safe(row.get("t2m_max")),
                "temp_min":        _safe(row.get("t2m_min")),
                "yagis_gunluk_mm": _safe(row.get("tp_sum"), 0.0),
                "et0_mm":          _safe(row.get("evaporation_mm")),
                "yagis_olasilik":  None,
                "gdd_kumulatif":   _safe(row.get("GDD_cum")),
                "kaynak":          "backfill_era5_s2",
            })
            weather_upserted += 1
        except Exception as exc:                                       # noqa: BLE001
            logger.debug("weather upsert failed for %s: %s", d, exc)

        # ── 2) rover scan emit on cadence ────────────────────────────────
        if last_emit is not None and (d - last_emit).days < cadence_days:
            continue
        last_emit = d

        ndvi = _safe(row.get("NDVI_int"))
        evi  = _safe(row.get("EVI_int"))
        ndwi = _safe(row.get("NDWI_int"))
        drought = _safe(row.get("drought_index_7d"))

        bbch = _bbch_from_doy(d, crop)
        sinif, guven, kaynak_cls, photo = _classify(
            site_code, d, ndvi, drought, crop, rng)
        n_yolo += int(kaynak_cls == "yolo_real")
        n_derived += int(kaynak_cls == "feature_derived")

        tavsiye, anomaliler = _kds_tavsiye(ndvi, drought, crop)
        # ek anomali: stres/hastalık sınıfı tespit edildiyse
        if not sinif.startswith("saglikli"):
            anomaliler.append(f"Kamera: {sinif} (guven %{guven*100:.0f})")

        scan_ts = d.replace(hour=10, minute=30, second=0)
        jitter_lat = rng.uniform(-0.0003, 0.0003)
        jitter_lon = rng.uniform(-0.0003, 0.0003)

        rec = {
            "timestamp":       scan_ts.strftime("%Y-%m-%d %H:%M:%S"),
            "waypoint_id":     int((d - datetime(year, 1, 1)).days),
            "waypoint_label":  f"WP-HIST-{d.strftime('%j')}",
            "gps_lat":         round(lat0 + jitter_lat, 6),
            "gps_lon":         round(lon0 + jitter_lon, 6),
            "nem_1_pct":       _soil_moisture_from_ndwi(ndwi),
            "nem_2_pct":       _soil_moisture_from_ndwi(ndwi) + rng.uniform(-2, 2),
            "hava_temp_c":     _safe(row.get("t2m_mean")),
            "hava_nem_pct":    _rh_from_dew_depression(
                row.get("t2m_mean"), row.get("dew_depression")),
            "bbch_sinif":      bbch,
            "bbch_guven":      0.80,
            "hastalik":        sinif if sinif.startswith("hastalik") else None,
            "hastalik_guven":  guven if sinif.startswith("hastalik") else None,
            "ndvi_tahmini":    ndvi,
            "anomali_sayisi":  len(anomaliler),
            "anomaliler":      json.dumps(anomaliler, ensure_ascii=False)
                                if anomaliler else None,
            "kds_tavsiye":     tavsiye or None,
            "image_path":      photo,
            "camera_sinif":    sinif,
            "camera_guven":    guven,
        }
        try:
            add_rover_olcum(tarla_id, rec)
            rover_inserted += 1
            _audit({
                "site": site_code, "tarla_id": tarla_id, "date": d.date(),
                "sinif": sinif, "guven": guven, "kaynak": kaynak_cls,
                "ndvi": ndvi, "drought": drought, "bbch": bbch,
            })
        except Exception as exc:                                       # noqa: BLE001
            logger.warning("insert failed for %s/%s: %s", site_code, d, exc)

    return {
        "site": site_code, "year": year, "status": "ok",
        "rows_in_parquet": len(df),
        "weather_upserted": weather_upserted,
        "rover_inserted": rover_inserted,
        "yolo_real":   n_yolo,
        "feature_derived": n_derived,
        "yolo_available": _YOLO_AVAILABLE,
    }


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def _discover(sites: Iterable[str], years: Iterable[int]) -> list[tuple[str, int]]:
    pairs: list[tuple[str, int]] = []
    for s in sites:
        for y in years:
            if (PROSPECTIVE_DIR / str(y) / f"{s}_unified_features.parquet").exists():
                pairs.append((s, y))
    return pairs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--site",  action="append",
                    help="Saha kodu (ör. EVR_01). Birden fazla verilebilir.")
    ap.add_argument("--year",  action="append", type=int,
                    help="Yıl (ör. 2025). Birden fazla verilebilir.")
    ap.add_argument("--cadence", type=int, default=7,
                    help="Rover tarama sıklığı (gün). Default: 7 (haftalık).")
    ap.add_argument("--all", action="store_true",
                    help="Tüm EVRENLI sahalar × mevcut yıllar.")
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:                                                  # noqa: BLE001
        pass

    init_db()

    if args.all:
        try:
            from prospective_validation import config as _flov
            sites = [s.id for s in _flov.EVRENLI_SITES]
        except Exception:                                              # noqa: BLE001
            sites = ["EVR_01"]
        years = sorted({int(p.name) for p in PROSPECTIVE_DIR.iterdir()
                        if p.is_dir() and p.name.isdigit()})
    else:
        sites = args.site or ["EVR_01"]
        years = args.year or [2025]

    pairs = _discover(sites, years)
    if not pairs:
        print(f"[BACKFILL] No parquet found for sites={sites} years={years}.")
        return 1

    print(f"[BACKFILL] YOLO model available: {_YOLO_AVAILABLE}")
    print(f"[BACKFILL] Targets: {pairs}")
    print(f"[BACKFILL] Cadence: 1 rover scan / {args.cadence} day(s)")
    print()

    summaries = []
    for site, year in pairs:
        s = backfill_one(site, year, cadence_days=args.cadence)
        summaries.append(s)
        print(f"  {site} {year}: {s}")

    print()
    total_rover = sum(s.get("rover_inserted", 0) for s in summaries)
    total_weather = sum(s.get("weather_upserted", 0) for s in summaries)
    total_real = sum(s.get("yolo_real", 0) for s in summaries)
    total_derived = sum(s.get("feature_derived", 0) for s in summaries)
    print(f"[BACKFILL] Toplam rover satır:    {total_rover}")
    print(f"[BACKFILL] Toplam hava upsert:    {total_weather}")
    print(f"[BACKFILL]   - YOLO inferans:     {total_real}")
    print(f"[BACKFILL]   - Feature-derived:   {total_derived}")
    print(f"[BACKFILL] Audit log:             {LOG_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

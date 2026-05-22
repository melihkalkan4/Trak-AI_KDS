"""
TRAK-AI KDS — Per-Site Yield JSON Producer (FLOV panel)
========================================================
Reads ``data/prospective/<year>/<site>_unified_features.parquet`` and runs
the crop-aware XGBoost yield model
(``cp2_model/yield_xgb_{sunflower,wheat}.pkl``), then writes
``reports/prospective/<site>_<year>_yield.json`` in the shape the FLOV
"Yield Forecast" dashboard panel expects:

    {
      "predicted_yield_t_ha": ...,
      "predicted_yield_kg_da": ...,
      "model_sha256_short": "...",
      "model_path": "...",
      "site_id": "EVR_01",
      "season_year": 2025,
      "crop": "sunflower",
      "confidence_interval_kg_da": {"low": ..., "high": ...},
      "yuzde_karsilastirma": ...,
      "risk": "...",
      "top_factors": [...],
      "features": {...}
    }

Usage:
    python scripts/predict_yield.py --site EVR_01 --year 2025
    python scripts/predict_yield.py --site EVR_02 --year 2025
    python scripts/predict_yield.py --all    # all 5 sites x configured years

The script looks up the tarla's ``crop_type`` from ``data/trakai.db`` so a
site flagged as wheat uses the wheat XGBoost model.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = REPO_ROOT / "data" / "trakai.db"
PROSPECTIVE_DIR = REPO_ROOT / "data" / "prospective"
REPORTS_DIR = REPO_ROOT / "reports" / "prospective"
CP2_DIR = REPO_ROOT / "src" / "cp2_model"

sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(CP2_DIR))


def _crop_for_site(site_id: str) -> str:
    """Look up crop_type in the tarla table. Defaults to sunflower."""
    if not DB_PATH.exists():
        return "sunflower"
    con = sqlite3.connect(DB_PATH)
    try:
        row = con.execute(
            "SELECT crop_type FROM tarla WHERE evrenli_id = ?", (site_id,)
        ).fetchone()
    finally:
        con.close()
    if not row or not row[0]:
        return "sunflower"
    return str(row[0]).lower()


def _model_sha256(crop_key: str) -> tuple[str, Path]:
    model_path = CP2_DIR / f"yield_xgb_{crop_key}.pkl"
    if not model_path.exists():
        return "", model_path
    h = hashlib.sha256(model_path.read_bytes()).hexdigest()
    return h, model_path


def _build_features(df: pd.DataFrame, crop_model: str, season_year: int) -> dict:
    """17 features from a unified parquet (mirrors predict_all_tarlalar)."""
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])

    if crop_model == "Wheat":
        start = pd.Timestamp(season_year - 1, 10, 1)
        end = pd.Timestamp(season_year, 7, 31, 23, 59, 59)
        cs = pd.Timestamp(season_year, 2, 1)
        ce = pd.Timestamp(season_year, 5, 30, 23, 59, 59)
        base_gdd, heat_thr = 0.0, 32.0
    else:
        start = pd.Timestamp(season_year, 4, 1)
        end = pd.Timestamp(season_year, 10, 31, 23, 59, 59)
        cs = pd.Timestamp(season_year, 6, 1)
        ce = pd.Timestamp(season_year, 8, 30, 23, 59, 59)
        base_gdd, heat_thr = 8.0, 35.0

    df_full = df[(df["date"] >= start) & (df["date"] <= end)]
    df_crit = df[(df["date"] >= cs) & (df["date"] <= ce)]
    if df_full.empty:
        df_full = df
    if df_crit.empty:
        df_crit = df_full

    rolling7 = df_full["tp_sum"].rolling(7, min_periods=1).sum()

    def gdd(series):
        return float(series.apply(lambda t: max(0, t - base_gdd)).sum())

    soil_clay = 31.0
    soil_ph = 6.8
    clay_cols = [c for c in df_full.columns if c.startswith("clay_")]
    ph_cols = [c for c in df_full.columns if c.startswith("phh2o_")]
    if clay_cols:
        soil_clay = float(df_full[clay_cols].iloc[0].mean())
    if ph_cols:
        soil_ph = float(df_full[ph_cols].iloc[0].mean())

    radiation = 0.0
    if "ssr_sum" in df_full.columns:
        radiation = float(df_full["ssr_sum"].sum() / 1_000_000.0)

    return {
        "ndvi_peak":           float(df_full["NDVI_int"].max()),
        "ndvi_mean_grow":      float(df_full["NDVI_int"].mean()),
        "ndvi_sum":            float(df_full["NDVI_int"].sum()),
        "gdd_total":           gdd(df_full["t2m_mean"]),
        "gdd_critical":        gdd(df_crit["t2m_mean"]),
        "precip_total":        float(df_full["tp_sum"].sum()),
        "precip_grow":         float(df_crit["tp_sum"].sum()),
        "drought_days":        int((rolling7 < 1.0).sum()),
        "heat_stress_days":    int((df_full["t2m_max"] > heat_thr).sum()),
        "frost_days":          int((df_full["t2m_min"] < 0.0).sum()),
        "temp_mean_grow":      float(df_full["t2m_mean"].mean()),
        "temp_amplitude_mean": float((df_full["t2m_max"] - df_full["t2m_min"]).mean()),
        "evi_peak":            float(df_full["EVI_int"].max()),
        "ndwi_min":            float(df_full["NDWI_int"].min()),
        "radiation_total":     radiation,
        "soil_clay":           soil_clay,
        "soil_ph":             soil_ph,
    }


def predict_one(site_id: str, year: int) -> int:
    crop_key = _crop_for_site(site_id)              # "sunflower" / "wheat"
    crop_model = "Wheat" if crop_key == "wheat" else "Sunflower"

    parquet = PROSPECTIVE_DIR / str(year) / f"{site_id}_unified_features.parquet"
    if not parquet.exists():
        print(f"ERROR: parquet missing: {parquet}")
        return 2

    df = pd.read_parquet(parquet)
    feats = _build_features(df, crop_model, year)

    from inference_yield import predict_yield                # type: ignore
    result = predict_yield(crop_model, current_year_features=feats)

    pred_kg_da = result.get("tahmini_verim_kg_dekar")
    if pred_kg_da is None:
        print(f"ERROR: yield predictor returned no value. err={result.get('hata')}")
        return 3

    model_sha, model_path = _model_sha256(crop_key)
    ci = result.get("guven_araligi", {}) or {}
    top_factors = result.get("en_etkili_faktorler", []) or []

    # ── ERA5 precipitation scale correction (display only) ────────────────
    # The trained yield model was fit on data where `tp_sum` was the SUM of
    # 24 accumulated-since-midnight hourly values — this over-counts the true
    # daily total by a factor of ~12.5 (triangular sum). The fix has been
    # applied at the ETL source (cp1_etl/mod_era5_cds.py, sum → max), but
    # existing parquets and the trained XGB model both use the inflated
    # scale, so we MUST feed the model the raw `feats` to keep its accuracy.
    # We expose a parallel realistic-scale view (`features_realistic`) for
    # the dashboard / JSON expander so users see physically plausible mm.
    ERA5_TP_TRIANGULAR_FACTOR = 12.5
    feats_realistic = dict(feats)
    feats_realistic["precip_total"] = round(
        feats["precip_total"] / ERA5_TP_TRIANGULAR_FACTOR, 1)
    feats_realistic["precip_grow"] = round(
        feats["precip_grow"] / ERA5_TP_TRIANGULAR_FACTOR, 1)
    # radiation_total uses the same accumulated-hourly bug -> also overshoot.
    feats_realistic["radiation_total"] = round(
        feats["radiation_total"] / ERA5_TP_TRIANGULAR_FACTOR, 4)

    out = {
        "site_id":              site_id,
        "season_year":          year,
        "crop":                 crop_key,
        "model_crop_label":     crop_model,
        "model_path":           str(model_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "model_sha256":         model_sha,
        "model_sha256_short":   model_sha[:16] if model_sha else "",
        "predicted_yield_kg_da": round(float(pred_kg_da), 2),
        "predicted_yield_t_ha":  round(float(pred_kg_da) * 0.01, 3),
        "confidence_interval_kg_da": {
            "low":  float(ci.get("alt",  pred_kg_da * 0.85)),
            "high": float(ci.get("ust", pred_kg_da * 1.15)),
        },
        "yuzde_karsilastirma":  result.get("yuzde_karsilastirma"),
        "risk":                 result.get("risk_analizi"),
        "top_factors":          top_factors,
        "veri_yili":            result.get("veri_yili"),
        "features":             feats_realistic,         # display (realistic mm)
        "features_model_input": feats,                   # exact bytes fed to XGB
        "era5_tp_scale_note":   ("ERA5-Land hourly tp accumulated-since-midnight "
                                  "summed in legacy ETL -> ~12.5x over-count. "
                                  "Fixed at source in cp1_etl/mod_era5_cds.py "
                                  "(sum -> max). Model still consumes raw scale "
                                  "for training-time contract; `features` here "
                                  "shows realistic mm."),
        "parquet":              str(parquet.relative_to(REPO_ROOT)).replace("\\", "/"),
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORTS_DIR / f"{site_id}_{year}_yield.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False),
                        encoding="utf-8")

    print(f"\n=== Yield JSON written ===")
    print(f"site            : {site_id}  ({crop_model})")
    print(f"season_year     : {year}")
    print(f"predicted_yield : {pred_kg_da:.2f} kg/da   ({pred_kg_da * 0.01:.3f} t/ha)")
    print(f"CI              : [{out['confidence_interval_kg_da']['low']:.1f}, "
          f"{out['confidence_interval_kg_da']['high']:.1f}] kg/da")
    print(f"risk            : {out['risk']}")
    print(f"model sha (16)  : {out['model_sha256_short']}")
    print(f"output          : {out_path}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--site", default="EVR_01",
                   help="EVRENLI site id (EVR_01..EVR_05).")
    p.add_argument("--year", type=int, default=2025,
                   help="Season harvest year.")
    p.add_argument("--all", action="store_true",
                   help="Run for all 5 sites x [2025, 2026].")
    args = p.parse_args()

    if args.all:
        rc = 0
        for s in ("EVR_01", "EVR_02", "EVR_03", "EVR_04", "EVR_05"):
            for y in (2025, 2026):
                try:
                    if predict_one(s, y) != 0:
                        rc = 1
                except Exception as exc:                                 # noqa: BLE001
                    print(f"  !! {s} {y} failed: {exc}")
                    rc = 1
        return rc
    return predict_one(args.site, args.year)


if __name__ == "__main__":
    raise SystemExit(main())

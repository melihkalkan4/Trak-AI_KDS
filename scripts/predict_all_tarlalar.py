"""
TRAK-AI KDS — Crop-Aware Multi-Tarla Prediction Pipeline
=========================================================
For every tarla, this script:

    1. Runs the frozen LSTM walk-forward NDVI predictor on the site's
       unified-features parquet (crop-agnostic — same NDVI engine).
    2. Computes yield with cp2_model.inference_yield.predict_yield, which
       loads either model_xgb_sunflower.pkl or model_xgb_wheat.pkl based
       on the tarla's crop_type.
    3. Writes results to THREE tables:
           ndvi_prediction       — canonical history (audit trail)
           yield_prediction      — schema-modelled end-of-season verim
           tarla_tahminler       — legacy table the live dashboard reads
                                   (this is why dashboard previously showed "—")

Idempotent: INSERT OR REPLACE on natural keys; tarla_tahminler gets a
fresh row per run (timestamp-keyed).
"""
from __future__ import annotations

import json
import sqlite3
import sys
import traceback
from datetime import datetime
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = REPO_ROOT / "data" / "trakai.db"

sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "src" / "cp2_model"))

try:
    from loguru import logger
except ImportError:                                                  # pragma: no cover
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("predict_all_tarlalar")


# ----------------------- helpers -----------------------

def _crop_meta(crop_type: str) -> dict:
    """Crop-specific defaults for inference_yield + dashboard UI."""
    if crop_type == "wheat":
        return {
            "model_crop": "Wheat",
            "phenology_table": {
                (270, 305): ("emergence",     "BBCH 09-13"),
                (306, 365): ("germination",   "BBCH 14-19"),
                (1,   60):  ("tillering",     "BBCH 20-29"),
                (61,  120): ("stem_extension","BBCH 30-39"),
                (121, 150): ("heading",       "BBCH 50-59"),
                (151, 175): ("flowering",     "BBCH 60-69"),
                (176, 200): ("grain_fill",    "BBCH 70-89"),
                (201, 220): ("maturity",      "BBCH 90-99"),
                (221, 269): ("post_harvest",  "—"),
            },
            "trakya_avg_yield": 400.0,
            "model_hash": "wheat_xgb_v1",
        }
    return {
        "model_crop": "Sunflower",
        "phenology_table": {
            (1,   104): ("pre_season",   "BBCH 00-09"),
            (105, 130): ("emergence",    "BBCH 10-19"),
            (131, 170): ("vegetative",   "BBCH 20-39"),
            (171, 200): ("flowering",    "BBCH 60-69"),
            (201, 240): ("grain_fill",   "BBCH 70-89"),
            (241, 280): ("maturity",     "BBCH 90-99"),
            (281, 366): ("post_harvest", "—"),
        },
        "trakya_avg_yield": 180.0,
        "model_hash": "43ef61b5a70f16cd",
    }


def _stage_for_doy(doy: int, table: dict) -> tuple[str, str]:
    for (a, b), val in table.items():
        if a <= doy <= b:
            return val
    return ("unknown", "—")


def _saglik_from_ndvi(ndvi: float | None) -> str:
    if ndvi is None:
        return "Bilinmiyor"
    if ndvi >= 0.75:
        return "Mukemmel"
    if ndvi >= 0.55:
        return "Iyi"
    if ndvi >= 0.35:
        return "Orta"
    return "Stres"


def _risk_from_pct(pct: float) -> str:
    if pct < -10:
        return "YUKSEK RISK"
    if pct < 5:
        return "NORMAL"
    return "OLUMLU"


# ----------------------- predictor (singleton) -----------------------

_PREDICTOR = None


def _get_predictor():
    global _PREDICTOR
    if _PREDICTOR is not None:
        return _PREDICTOR
    from prospective_validation.model_loader import load_frozen_champion
    from prospective_validation.frozen_model_predictor import FrozenPredictor
    from prospective_validation import climatology as clim_mod

    champion = load_frozen_champion()
    try:
        clim = clim_mod.load_default_climatology()
    except Exception:                                                # noqa: BLE001
        try:
            clim = clim_mod.load_climatology()
        except Exception:                                            # noqa: BLE001
            clim = None
    _PREDICTOR = FrozenPredictor(champion=champion, climatology=clim)
    return _PREDICTOR


# ----------------------- DB ops -----------------------

def _load_tarla_rows(con) -> list[dict]:
    cur = con.cursor()
    cur.execute(
        "SELECT id, name, evrenli_id, crop_type, active_season_year, "
        "       lat, lon, area_da "
        "FROM tarla ORDER BY id"
    )
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def _store_ndvi_predictions(con, tarla_id: int, df_preds: pd.DataFrame,
                            model_hash: str) -> int:
    cur = con.cursor()
    n = 0
    for _, r in df_preds.iterrows():
        try:
            cur.execute(
                """
                INSERT OR REPLACE INTO ndvi_prediction
                    (tarla_id, prediction_date, target_date,
                     predicted_ndvi, last_observed_ndvi, residual_delta,
                     climatology_ndvi, anomaly_vs_climatology, model_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tarla_id,
                    pd.Timestamp(r["prediction_date"]).strftime("%Y-%m-%d"),
                    pd.Timestamp(r["target_date"]).strftime("%Y-%m-%d"),
                    float(r["predicted_ndvi"]),
                    float(r["last_observed_ndvi"]),
                    float(r["residual_delta"]),
                    float(r.get("climatology_ndvi", 0) or 0),
                    float(r.get("anomaly_vs_climatology", 0) or 0),
                    model_hash,
                ),
            )
            n += 1
        except Exception as exc:                                     # noqa: BLE001
            logger.debug("ndvi_prediction insert fail: {}", exc)
    con.commit()
    return n


def _store_yield_prediction(con, tarla_id: int, season_year: int,
                             yield_result: dict, crop_type: str,
                             model_hash: str) -> None:
    pred = yield_result.get("tahmini_verim_kg_dekar")
    if pred is None:
        return
    ci = yield_result.get("guven_araligi", {}) or {}
    shap = yield_result.get("en_etkili_faktorler", []) or []
    cur = con.cursor()
    cur.execute(
        """
        INSERT OR REPLACE INTO yield_prediction
            (tarla_id, season_year, predicted_yield_kg_da,
             confidence_low, confidence_high, shap_top_features,
             veri_yili, model_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            tarla_id, season_year, float(pred),
            float(ci.get("alt", pred * 0.85)),
            float(ci.get("ust", pred * 1.15)),
            json.dumps(shap, ensure_ascii=False),
            int(yield_result.get("veri_yili") or season_year),
            f"{model_hash}_{crop_type}",
        ),
    )
    con.commit()


def _store_tarla_tahminler(
    con, tarla_id: int, *, crop_type: str,
    ndvi_mevcut: float | None, ndvi_tahmin: float | None,
    ndvi_delta: float | None,
    yield_result: dict, doy: int, meta: dict,
    sensor_row: dict,
) -> None:
    """Populate the legacy table the live dashboard reads."""
    saglik = _saglik_from_ndvi(ndvi_mevcut)
    stage, bbch = _stage_for_doy(doy, meta["phenology_table"])

    pred = yield_result.get("tahmini_verim_kg_dekar") or 0.0
    ci = yield_result.get("guven_araligi", {}) or {}
    pct_comp = yield_result.get("yuzde_karsilastirma", 0.0) or 0.0
    risk = yield_result.get("risk_analizi") or _risk_from_pct(pct_comp)
    shap_list = yield_result.get("en_etkili_faktorler", []) or []
    top_factor = shap_list[0]["ozellik"] if shap_list else None

    cur = con.cursor()
    cur.execute(
        """
        INSERT INTO tarla_tahminler
            (tarla_id, timestamp, urun,
             ndvi_mevcut, ndvi_tahmin_7gun, ndvi_delta, saglik_durumu,
             verim_tahmini_kg_dekar, verim_guven_alt, verim_guven_ust,
             verim_risk, fenolojik_evre, bbch_aralik, kritik_donem,
             hava_sicaklik, hava_nem, hava_yagis_7gun, hava_uyarilar,
             kaynak)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            tarla_id,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            crop_type,
            ndvi_mevcut, ndvi_tahmin, ndvi_delta, saglik,
            float(pred),
            float(ci.get("alt", pred * 0.85)),
            float(ci.get("ust", pred * 1.15)),
            risk, stage, bbch,
            1 if stage in {"flowering", "heading", "grain_fill"} else 0,
            sensor_row.get("temperature"),
            sensor_row.get("humidity"),
            sensor_row.get("yagis_7gun"),
            top_factor,
            "predict_all_tarlalar",
        ),
    )
    con.commit()


def _last_sensor_row(con, tarla_id: int) -> dict:
    cur = con.cursor()
    cur.execute(
        "SELECT timestamp, ndvi, temperature, humidity, precipitation "
        "FROM sensor_reading WHERE tarla_id = ? "
        "ORDER BY timestamp DESC LIMIT 1",
        (tarla_id,),
    )
    row = cur.fetchone()
    if not row:
        return {}
    # 7-day rain sum
    cur.execute(
        "SELECT COALESCE(SUM(precipitation), 0) FROM sensor_reading "
        "WHERE tarla_id = ? AND timestamp >= date(?, '-7 days')",
        (tarla_id, row[0]),
    )
    yagis7 = float(cur.fetchone()[0] or 0)
    return {
        "timestamp": row[0],
        "ndvi": row[1],
        "temperature": row[2],
        "humidity": row[3],
        "precipitation": row[4],
        "yagis_7gun": yagis7,
    }


# ----------------------- main per-tarla -----------------------

def predict_for_tarla(con, tarla: dict) -> dict:
    crop = (tarla.get("crop_type") or "sunflower").lower()
    meta = _crop_meta(crop)
    season_year = int(tarla.get("active_season_year") or datetime.now().year)
    evr = tarla["evrenli_id"]

    # find parquet
    parquet = None
    for year_dir in sorted((REPO_ROOT / "data" / "prospective").glob("*"),
                           reverse=True):
        cand = year_dir / f"{evr}_unified_features.parquet"
        if cand.exists():
            parquet = cand
            break
    if parquet is None:
        return {"status": "no_parquet", "tarla_id": tarla["id"]}

    df_feat = pd.read_parquet(parquet)

    # ---- NDVI walk-forward predictions ----
    try:
        predictor = _get_predictor()
        preds = predictor.predict_ndvi_series(df_feat, verify_integrity=False)
    except Exception as exc:                                         # noqa: BLE001
        logger.exception("[{}] NDVI predictor failed: {}", evr, exc)
        return {"status": "ndvi_fail", "tarla_id": tarla["id"], "error": str(exc)}

    n_ndvi = _store_ndvi_predictions(con, tarla["id"], preds, meta["model_hash"])

    # latest prediction summary
    if not preds.empty:
        last = preds.iloc[-1]
        ndvi_mevcut = float(last["last_observed_ndvi"])
        ndvi_tahmin = float(last["predicted_ndvi"])
        ndvi_delta = float(last["residual_delta"])
        target_doy = pd.Timestamp(last["target_date"]).dayofyear
    else:
        ndvi_mevcut = ndvi_tahmin = ndvi_delta = None
        target_doy = datetime.now().timetuple().tm_yday

    # ---- Yield prediction (crop-aware) ----
    yield_result = {}
    try:
        from inference_yield import predict_yield                    # type: ignore
        # Build current-year feature dict from the per-site parquet itself,
        # so each tarla gets a yield that reflects its own NDVI trajectory.
        feats_for_yield = _build_yield_features(df_feat, meta["model_crop"],
                                                season_year)
        yield_result = predict_yield(meta["model_crop"],
                                     current_year_features=feats_for_yield)
        if yield_result.get("hata"):
            logger.warning("[{}] yield error: {}", evr, yield_result["hata"])
            yield_result = {}
    except Exception as exc:                                         # noqa: BLE001
        logger.exception("[{}] yield predictor failed: {}", evr, exc)
        yield_result = {}

    if yield_result:
        _store_yield_prediction(con, tarla["id"], season_year,
                                yield_result, crop, meta["model_hash"])

    # ---- dashboard-compat row in tarla_tahminler ----
    sensor_row = _last_sensor_row(con, tarla["id"])
    _store_tarla_tahminler(
        con, tarla["id"], crop_type=crop,
        ndvi_mevcut=ndvi_mevcut, ndvi_tahmin=ndvi_tahmin,
        ndvi_delta=ndvi_delta,
        yield_result=yield_result, doy=target_doy, meta=meta,
        sensor_row=sensor_row,
    )

    return {
        "status": "ok", "tarla_id": tarla["id"],
        "evrenli_id": evr, "crop": crop,
        "n_ndvi_preds": n_ndvi,
        "ndvi_mevcut": ndvi_mevcut, "ndvi_tahmin": ndvi_tahmin,
        "yield_kg_da": yield_result.get("tahmini_verim_kg_dekar"),
    }


def _build_yield_features(df: pd.DataFrame, crop_model: str,
                          season_year: int) -> dict:
    """Compute the 17 features inference_yield expects from a unified parquet.

    Mirrors the logic of inference_yield._compute_season_features but
    over per-site Sentinel-2-derived NDVI/EVI/NDWI (i.e. site-distinct).
    """
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

    # If the per-year window is empty (early in season), fall back to whole df
    if df_full.empty:
        df_full = df
    if df_crit.empty:
        df_crit = df_full

    rolling7 = df_full["tp_sum"].rolling(7, min_periods=1).sum()

    def gdd(series):
        return float(series.apply(lambda t: max(0, t - base_gdd)).sum())

    feats = {
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
        "radiation_total":     float(df_full["ssr_sum"].sum() / 1_000_000.0)
                               if "ssr_sum" in df_full.columns else 0.0,
        # No SoilGrids columns in synthetic parquet — use Trakya typical defaults.
        "soil_clay":           31.0,
        "soil_ph":             6.8,
    }
    return feats


def main() -> int:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"DB missing: {DB_PATH}")
    con = sqlite3.connect(DB_PATH)
    try:
        tarlalar = _load_tarla_rows(con)
        print(f"\n{'='*60}")
        print(f"  PREDICTING FOR {len(tarlalar)} TARLALAR")
        print(f"{'='*60}")
        results = []
        for t in tarlalar:
            print(f"\n-> Tarla {t['id']} ({t['evrenli_id']}, "
                  f"{t.get('crop_type')}): {t['name']}")
            try:
                r = predict_for_tarla(con, t)
                results.append(r)
                if r["status"] == "ok":
                    print(f"   OK NDVI preds={r['n_ndvi_preds']} "
                          f"mevcut={r['ndvi_mevcut']:.3f} "
                          f"tahmin={r['ndvi_tahmin']:.3f} "
                          f"verim={(r.get('yield_kg_da') or 0):.1f} kg/da")
                else:
                    print(f"   ⚠ {r['status']}")
            except Exception as exc:                                 # noqa: BLE001
                print(f"   FAIL: {exc}")
                traceback.print_exc()
                results.append({"status": "exception",
                                "tarla_id": t["id"], "error": str(exc)})
        print(f"\n{'='*60}")
        ok = sum(1 for r in results if r["status"] == "ok")
        print(f"  PREDICTIONS DONE: {ok}/{len(results)} tarlalar")
        print(f"{'='*60}")
        return 0 if ok == len(results) else 1
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())

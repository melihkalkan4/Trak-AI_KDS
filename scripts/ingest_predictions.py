"""
TRAK-AI KDS — NDVI Prediction Ingestion
========================================
Loads `reports/prospective/<EVR_xx>_<year>_predictions.parquet` into the
`ndvi_prediction` table of `data/trakai.db`.

If a site's prediction parquet is missing, the script generates one
on-the-fly by running the frozen LSTM via
``data_integration.live_predictor.predict_for_tarla``-style logic.

Idempotent via INSERT OR REPLACE on (tarla_id, prediction_date, target_date).
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

try:
    from loguru import logger
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("ingest_predictions")


DB_PATH = REPO_ROOT / "data" / "trakai.db"
PRED_DIR = REPO_ROOT / "reports" / "prospective"

EVR_IDS = ("EVR_01", "EVR_02", "EVR_03", "EVR_04", "EVR_05")
YEARS = (2025, 2026)
DEFAULT_MODEL_HASH = "43ef61b5a70f16cd"     # frozen LSTM sunflower champion


def _to_iso(d) -> str:
    if isinstance(d, str):
        return d.split(" ")[0]
    if isinstance(d, (pd.Timestamp,)):
        return d.strftime("%Y-%m-%d")
    return str(d).split(" ")[0]


def _maybe_float(v) -> float | None:
    try:
        if v is None or pd.isna(v):
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _tarla_id_for(cur, evrenli_id: str) -> int | None:
    cur.execute("SELECT id FROM tarla WHERE evrenli_id = ?", (evrenli_id,))
    row = cur.fetchone()
    return int(row[0]) if row else None


def _ensure_predictions_parquet(evrenli_id: str, year: int) -> Path | None:
    """If `<EVR>_<year>_predictions.parquet` is missing, try to generate it
    by running the frozen predictor against the unified-features parquet."""
    path = PRED_DIR / f"{evrenli_id}_{year}_predictions.parquet"
    if path.exists():
        return path

    feats = REPO_ROOT / "data" / "prospective" / str(year) / \
            f"{evrenli_id}_unified_features.parquet"
    if not feats.exists():
        logger.info("[{}] no features parquet for {}, skipping",
                    evrenli_id, year)
        return None

    try:
        from prospective_validation.model_loader import load_frozen_champion
        from prospective_validation.frozen_model_predictor import FrozenPredictor
        from prospective_validation import climatology as clim_mod

        champion = load_frozen_champion()
        try:
            clim = clim_mod.load_default_climatology()
        except Exception:                                              # noqa: BLE001
            clim = None
        predictor = FrozenPredictor(champion=champion, climatology=clim)

        df_feat = pd.read_parquet(feats)
        preds = predictor.predict_ndvi_series(df_feat, verify_integrity=True)
        if preds is None or preds.empty:
            logger.warning("[{}] predictor returned empty", evrenli_id)
            return None

        path.parent.mkdir(parents=True, exist_ok=True)
        preds.to_parquet(path)
        logger.info("[{}] generated {} predictions -> {}",
                    evrenli_id, len(preds), path.name)
        return path
    except Exception as exc:                                           # noqa: BLE001
        logger.exception("[{}] live prediction generation failed: {}",
                         evrenli_id, exc)
        return None


def ingest_one(con: sqlite3.Connection, evrenli_id: str, year: int) -> dict:
    cur = con.cursor()
    tarla_id = _tarla_id_for(cur, evrenli_id)
    if tarla_id is None:
        return {"site": evrenli_id, "year": year,
                "status": "no_mapping", "inserted": 0}

    path = _ensure_predictions_parquet(evrenli_id, year)
    if path is None:
        return {"site": evrenli_id, "year": year,
                "status": "no_predictions", "inserted": 0}

    df = pd.read_parquet(path)
    inserted = 0
    failed = 0
    for _, r in df.iterrows():
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
                    _to_iso(r.get("prediction_date")),
                    _to_iso(r.get("target_date")),
                    _maybe_float(r.get("predicted_ndvi")),
                    _maybe_float(r.get("last_observed_ndvi")),
                    _maybe_float(r.get("residual_delta")),
                    _maybe_float(r.get("climatology_ndvi")),
                    _maybe_float(r.get("anomaly_vs_climatology")),
                    DEFAULT_MODEL_HASH,
                ),
            )
            inserted += 1
        except Exception as exc:                                       # noqa: BLE001
            failed += 1
            logger.debug("[{}] pred row failed: {}", evrenli_id, exc)
    con.commit()
    return {"site": evrenli_id, "year": year, "status": "ok",
            "inserted": inserted, "failed": failed,
            "rows_in_parquet": int(len(df))}


def ingest_all(sites=EVR_IDS, years=YEARS) -> list[dict]:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"DB missing at {DB_PATH}. Run scripts/init_database.py first."
        )
    con = sqlite3.connect(DB_PATH)
    try:
        results = []
        for s in sites:
            for y in years:
                results.append(ingest_one(con, s, y))
        return results
    finally:
        con.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sites", nargs="+", default=list(EVR_IDS))
    parser.add_argument("--years", nargs="+", type=int, default=list(YEARS))
    args = parser.parse_args()

    results = ingest_all(args.sites, args.years)

    print("\n=== PREDICTION INGESTION ===")
    total = 0
    n_ok = n_skip = n_fail = 0
    for r in results:
        st = r["status"]
        if st == "ok":
            print(f"  OK    {r['site']:<7} {r['year']}: "
                  f"{r['inserted']} stored "
                  f"({r.get('failed', 0)} failed, "
                  f"{r.get('rows_in_parquet', 0)} in parquet)")
            total += r["inserted"]
            n_ok += 1
        elif st in ("no_predictions", "no_mapping"):
            print(f"  SKIP  {r['site']:<7} {r['year']}: {st}")
            n_skip += 1
        else:
            print(f"  FAIL  {r['site']:<7} {r['year']}: {st}")
            n_fail += 1
    print(f"\nTotal: {n_ok} ok, {n_skip} skipped, {n_fail} failed")
    print(f"Total ndvi_prediction rows: {total}")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

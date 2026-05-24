"""ÇP-2.5 — Anomali yıl validasyonu.

``data/external/tuik/anomaly_years.csv`` içindeki |z|>1.5 yıllarda model
ne kadar başarılı?  Kritik düşük yıllar (z<-1.5) için H3 hipotezi (yanlış
pozitif düşürme) doğrultusunda kanıt verisi üretir.

Yöntem
------
1. Calibration train set'i yükle (2017-2024 × 3 il).
2. Anomali yıllarını train'den ÇIKAR, kalanı eğit.
3. Anomali yıllarını test et — gerçek vs tahmin karşılaştır.
4. 2025 hold-out (kritik kuraklık yılı) için ekstra ayrımı raporla.

Çıktılar
--------
* ``reports/cp25_anomaly_validation.md``
* ``reports/cp25_anomaly_predictions.csv``
"""

from __future__ import annotations

import json
import logging
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger("trakai.cp25.anom")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR     = PROJECT_ROOT / "data" / "processed"
EXT_DIR      = PROJECT_ROOT / "data" / "external" / "tuik"
MODELS_DIR   = PROJECT_ROOT / "models"
REPORTS_DIR  = PROJECT_ROOT / "reports"

CROPS = (("bugday", "bugday"), ("aycicegi", "aycicegi_yaglik"))
FEATURE_COLS_BASE = [
    "ndvi_max", "ndvi_mean", "ndvi_integral",
    "ndvi_flowering", "ndvi_grain_fill", "greenness_days",
    "gdd_cum_season", "tp_season_sum",
    "ndwi_min_flowering", "t2m_max_flowering_mean",
]
IL_DUMMY_COLS = ["il_Edirne", "il_Kirklareli", "il_Tekirdag"]


def _onehot_il(df: pd.DataFrame) -> pd.DataFrame:
    mapping = {"Edirne": "il_Edirne",
               "Kırklareli": "il_Kirklareli",
               "Tekirdağ": "il_Tekirdag"}
    out = df.copy()
    for col in IL_DUMMY_COLS:
        out[col] = 0
    for src_il, dst_col in mapping.items():
        out.loc[out["il"] == src_il, dst_col] = 1
    return out


def _prepare_xy(df: pd.DataFrame):
    df = _onehot_il(df)
    cols = FEATURE_COLS_BASE + IL_DUMMY_COLS
    X = df[cols].astype(float).fillna(df[cols].median(numeric_only=True))
    y = df["yield_kg_da"].astype(float).values
    return X, y, cols


def _rebuild_champion(bundle):
    """Re-instantiate the champion model class (untrained)."""
    name = bundle["champion_name"]
    if name.startswith("Ridge"):
        alpha = float(name.split("alpha=")[1].rstrip(")"))
        return Ridge(alpha=alpha), True
    if name == "GradientBoostingRegressor":
        from sklearn.ensemble import GradientBoostingRegressor
        return GradientBoostingRegressor(n_estimators=200, max_depth=3,
                                          learning_rate=0.05, random_state=42), False
    if name == "RandomForestRegressor":
        from sklearn.ensemble import RandomForestRegressor
        return RandomForestRegressor(n_estimators=300, max_depth=5,
                                      random_state=42, n_jobs=-1), False
    raise ValueError(f"Unknown champion: {name}")


def validate_crop(crop_short: str, crop_full: str,
                  anom_df: pd.DataFrame) -> dict:
    df = pd.read_csv(DATA_DIR / f"calibration_train_set_{crop_short}.csv")
    bundle_path = MODELS_DIR / f"cp25_calibration_{crop_short}.pkl"
    with bundle_path.open("rb") as fh:
        bundle = pickle.load(fh)

    # Anomaly rows present in our train set
    anom_sub = anom_df[anom_df["urun_tr"].isin(
        ["Buğday" if crop_full == "bugday" else "Ayçiçeği (Yağlık)"]
    )].copy()
    anom_keys = set(zip(anom_sub["il"], anom_sub["year"].astype(int)))
    df["_is_anom"] = list(zip(df["il"], df["year"].astype(int)))
    df["_is_anom"] = df["_is_anom"].isin(anom_keys)

    test_df  = df[df["_is_anom"]].copy()
    train_df = df[~df["_is_anom"]].copy()
    logger.info("[%s] anomaly rows in train set: %d / %d",
                crop_short, len(test_df), len(df))

    if test_df.empty:
        return {"crop": crop_short, "n_anom_in_train": 0,
                "note": "No anomaly rows fall inside MFM coverage 2017-2024."}

    # Refit champion on train\anomaly and predict on anomaly rows
    X_tr, y_tr, cols = _prepare_xy(train_df)
    X_te, y_te, _    = _prepare_xy(test_df)
    model, needs_scaler = _rebuild_champion(bundle)
    if needs_scaler:
        scaler = StandardScaler().fit(X_tr)
        model.fit(scaler.transform(X_tr), y_tr)
        preds = model.predict(scaler.transform(X_te))
    else:
        model.fit(X_tr.values, y_tr)
        preds = model.predict(X_te.values)

    out = test_df[["il", "year", "yield_kg_da"]].copy()
    out["yield_pred"] = preds
    out["abs_error"] = (out["yield_kg_da"] - out["yield_pred"]).abs()
    out["pct_error"] = out["abs_error"] / out["yield_kg_da"] * 100
    # Attach z_score from anomaly_years.csv
    z_map = dict(zip(zip(anom_sub["il"], anom_sub["year"].astype(int)),
                     anom_sub["z_score"].astype(float)))
    out["z_score_tuik"] = [z_map.get((il, int(y))) for il, y in
                           zip(out["il"], out["year"])]
    out["anomaly_yon"] = ["DÜŞÜK" if (z is not None and z < 0) else "YÜKSEK"
                          for z in out["z_score_tuik"]]
    out["crop"] = crop_short

    return {
        "crop":             crop_short,
        "champion":         bundle["champion_name"],
        "n_anom_in_train":  int(len(test_df)),
        "mae_anom_kg_da":   float(out["abs_error"].mean()),
        "mape_anom_pct":    float(out["pct_error"].mean()),
        "predictions":      out.to_dict(orient="records"),
    }


def main() -> None:
    anom = pd.read_csv(EXT_DIR / "anomaly_years.csv")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    all_preds: list[pd.DataFrame] = []
    summary = {}
    for short, full in CROPS:
        r = validate_crop(short, full, anom)
        summary[short] = r
        if "predictions" in r:
            all_preds.append(pd.DataFrame(r["predictions"]))

    if all_preds:
        merged = pd.concat(all_preds, ignore_index=True)
        merged.to_csv(REPORTS_DIR / "cp25_anomaly_predictions.csv", index=False)

    # ---- Markdown report ----
    md = ["# ÇP-2.5 — Anomali Yıl Validasyonu", ""]
    md.append("**Yöntem:** Anomali yılı (|z|>1.5) train set'ten çıkarıldı, "
              "şampiyon model kalanla eğitildi, anomali yıllarında tahmin yapıldı.")
    md.append("")
    for short, r in summary.items():
        md.append(f"## {short.upper()}")
        if r.get("n_anom_in_train", 0) == 0:
            md.append(f"_Train set'te (2017-2024) anomali satırı yok._")
            md.append("")
            continue
        md.append(f"- Şampiyon model: `{r['champion']}`")
        md.append(f"- Test edilen anomali satırı: **{r['n_anom_in_train']}**")
        md.append(f"- Anomali yıllarında MAE: **{r['mae_anom_kg_da']:.1f} kg/da**")
        md.append(f"- Anomali yıllarında MAPE: **{r['mape_anom_pct']:.1f}%**")
        md.append("")
        md.append("| İl | Yıl | Yön | z | Gerçek (kg/da) | Tahmin (kg/da) | Mutlak Hata |")
        md.append("|---|---|---|---|---|---|---|")
        for rec in r["predictions"]:
            z = rec["z_score_tuik"]
            md.append(f"| {rec['il']} | {rec['year']} | {rec['anomaly_yon']} | "
                      f"{z:+.2f} | {rec['yield_kg_da']:.0f} | "
                      f"{rec['yield_pred']:.0f} | {rec['abs_error']:.1f} |")
        md.append("")

    md.append("## Yorum")
    md.append("")
    md.append("- **H3 (yanlış pozitif düşürme) için kanıt:** Anomali MAE'si "
              "calibration LOOCV MAE'sine yakın ise, model kuraklık/uç "
              "yıllarda da bozulmuyor — alert sisteminin yanlış pozitif "
              "oranını düşürmek için kullanılabilir.")
    md.append("- **Sınırlama:** Anomali test seti üç il × birkaç yıl ile "
              "küçüktür; tek bir uç yılın MAE'yi ciddi bozması mümkün.")

    out_md = REPORTS_DIR / "cp25_anomaly_validation.md"
    out_md.write_text("\n".join(md), encoding="utf-8")
    logger.info("anomaly report → %s", out_md)

    # JSON summary too
    summary_clean = {k: {kk: vv for kk, vv in v.items() if kk != "predictions"}
                     for k, v in summary.items()}
    (REPORTS_DIR / "cp25_anomaly_summary.json").write_text(
        json.dumps(summary_clean, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()

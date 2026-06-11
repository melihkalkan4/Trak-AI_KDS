"""
TRAK-AI — LOILO MAPE Bootstrap %95 Güven Aralığı (n=213, 1000 resample)
=======================================================================

Amaç
-----
Layer C şampiyon modelinin (XGBoost, bugday, LOILO CV) elde ettiği
nokta-MAPE değeri (=%10.561) için bootstrap %95 GA hesaplamak ve
"≤%10 hedefine ne kadar yakın" iddiasını sağlamlaştırmak.

Yöntem
------
1. ``data/processed/calibration_features_layerC.csv`` — bugday alt-kümesi (n=213).
2. ``LeaveOneGroupOut(groups=ilce_id)`` ile 29 ilçe katlamı.
3. Her katlamada XGBoost (Layer C konfigürasyonu) eğitilir, kalan ilçe
   tahmin edilir → tahmin vektörü ``y_pred`` (boyut n=213).
4. Gözlem-tabanlı bootstrap: 1000 yeniden örnekleme (replacement=True).
   Her örneklemede ``MAPE = mean(|y - y_pred| / |y|) * 100`` hesaplanır.
5. %95 GA = [2.5. persantil, 97.5. persantil].

Çıktı
-----
``reports/cp25/13_loilo_mape_bootstrap_bugday.{md,json}``
Konsol özet ve eşik karşılaştırması.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import LeaveOneGroupOut
from xgboost import XGBRegressor

# ── Repo kökü ──
THIS_DIR     = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent
DATA_PATH    = PROJECT_ROOT / "data" / "processed" / "calibration_features_layerC.csv"
REPORT_DIR   = PROJECT_ROOT / "reports" / "cp25"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

OUT_MD   = REPORT_DIR / "13_loilo_mape_bootstrap_bugday.md"
OUT_JSON = REPORT_DIR / "13_loilo_mape_bootstrap_bugday.json"

SEED    = 42
N_BOOT  = 1000
TARGET  = 10.0     # ≤%10 hedefi
ALPHA   = 0.05     # %95 GA → (2.5, 97.5) persantil

# ── Layer C özellik tanımı (07_layer_c_full.py ile birebir) ──
FEATURES_A = [
    "gdd_cum_season", "gdd_flowering", "vernalization_days",
    "tp_season_sum", "tp_winter_sum", "tp_flowering", "tp_grain_fill",
    "aridity_index", "heat_stress_days",
    "t2m_flowering_mean", "t2m_flowering_max", "tdiff_mean",
    "ssr_flowering_sum", "ssr_season_sum",
]
FEATURES_NDVI = ["ndvi_max", "ndvi_mean_season", "ndvi_integral",
                  "ndvi_flowering", "ndvi_grain_fill", "ndvi_spring_slope",
                  "greenness_days"]
FEATURES_SOIL = ["clay_0-5cm", "sand_0-5cm", "silt_0-5cm",
                  "phh2o_0-5cm", "soc_0-5cm", "awc_0-5cm"]
FEATURES_C = FEATURES_A + FEATURES_NDVI + FEATURES_SOIL


def _impute(X: pd.DataFrame) -> pd.DataFrame:
    X = X.replace([np.inf, -np.inf], np.nan)
    for c in X.columns:
        med = X[c].median()
        X[c] = X[c].fillna(0.0 if np.isnan(med) else med)
    return X


def _xgb() -> XGBRegressor:
    """07_layer_c_full.py içindekiyle birebir hiperparametreler."""
    return XGBRegressor(
        n_estimators=200, max_depth=4, learning_rate=0.05,
        random_state=SEED, n_jobs=-1, verbosity=0,
    )


def _loilo_predict(X: pd.DataFrame, y: np.ndarray, groups: np.ndarray) -> np.ndarray:
    """Leave-One-Ilçe-Out: her katlamada XGB eğit + dışta bırakılan ilçeye tahmin."""
    preds = np.full_like(y, fill_value=np.nan, dtype=float)
    logo = LeaveOneGroupOut()
    for tr, te in logo.split(X, y, groups=groups):
        X_tr, X_te = X.iloc[tr].values, X.iloc[te].values
        m = _xgb().fit(X_tr, y[tr])
        preds[te] = m.predict(X_te)
    assert not np.isnan(preds).any(), "LOILO tahmininde NaN kalan örnek var."
    return preds


def _mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """MAPE (%). y_true sıfır içermiyorsa güvenli."""
    eps = 1e-9
    return float(np.mean(np.abs(y_true - y_pred) / np.maximum(np.abs(y_true), eps)) * 100.0)


def _bootstrap_mape(y_true: np.ndarray, y_pred: np.ndarray,
                    n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    rng = np.random.default_rng(seed)
    n = len(y_true)
    boot_mapes = np.empty(n_boot)
    for b in range(n_boot):
        idx = rng.integers(low=0, high=n, size=n)  # with replacement
        boot_mapes[b] = _mape(y_true[idx], y_pred[idx])
    p25, p50, p975 = np.percentile(boot_mapes, [2.5, 50.0, 97.5])
    return {
        "point_mape_pct":  _mape(y_true, y_pred),
        "boot_mean_mape":  float(np.mean(boot_mapes)),
        "boot_median_mape": float(p50),
        "ci95_lower":      float(p25),
        "ci95_upper":      float(p975),
        "boot_std":        float(np.std(boot_mapes, ddof=1)),
        "n_obs":           int(n),
        "n_bootstraps":    int(n_boot),
        "p_below_target":  float(np.mean(boot_mapes <= TARGET)),
    }


def main() -> None:
    if not DATA_PATH.exists():
        print(f"[HATA] Bulunamadı: {DATA_PATH}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(DATA_PATH)
    sub = df[df["crop"] == "bugday"].copy().reset_index(drop=True)
    n = len(sub)
    n_ilce = sub["ilce_id"].nunique()
    print(f"[VERİ] bugday n={n}, n_ilce={n_ilce}")
    if n == 0:
        print("[HATA] bugday alt-kümesi boş.", file=sys.stderr); sys.exit(1)

    X = _impute(sub[FEATURES_C].astype(float))
    y = sub["verim_kg_da"].astype(float).values
    groups = sub["ilce_id"].astype(int).values

    print(f"[LOILO] {n_ilce} katlamada XGBoost eğitiliyor…")
    y_pred = _loilo_predict(X, y, groups)
    point_mape = _mape(y, y_pred)
    print(f"[LOILO] nokta-MAPE = %{point_mape:.3f}")

    print(f"[BOOT]  {N_BOOT} yeniden örnekleme (seed={SEED}, n={n})…")
    res = _bootstrap_mape(y, y_pred, n_boot=N_BOOT, seed=SEED)

    # Eşik analizi
    target_pass = res["ci95_upper"] <= TARGET
    point_pass  = res["point_mape_pct"] <= TARGET
    margin      = TARGET - res["point_mape_pct"]   # +: hedefin altında / -: hedefin üstünde

    # Sonuçlar
    out = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "crop":          "bugday",
        "cv":            "LOILO",
        "model":         "xgboost",
        "layer":         "C",
        "target_mape_pct": TARGET,
        "ci_alpha":      ALPHA,
        "results":       res,
        "decisions": {
            "point_mape_within_target": bool(point_pass),
            "ci95_upper_within_target": bool(target_pass),
            "distance_to_target_pct":   float(margin),
            "share_resamples_below_target": float(res["p_below_target"]),
        },
    }
    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    # Markdown rapor
    md = [
        "# ÇP-2.5 — Görev 13: LOILO MAPE Bootstrap %95 Güven Aralığı (bugday)",
        "",
        f"_Üretildi: {out['generated_utc']}_  |  Layer C  |  Model: **XGBoost**  |  CV: **LOILO**",
        "",
        "## Yöntem",
        "",
        f"- Veri: `data/processed/calibration_features_layerC.csv` → bugday alt-kümesi (n={n}, {n_ilce} ilçe).",
        "- `LeaveOneGroupOut(groups=ilce_id)` ile her ilçe için dışarıda bırakılarak XGBoost eğitildi.",
        f"- Hiperparametreler: `n_estimators=200, max_depth=4, lr=0.05, seed={SEED}` (07_layer_c_full.py birebir).",
        f"- Bootstrap: {N_BOOT} yeniden örnekleme (with replacement), tohum={SEED}.",
        "- MAPE eşik (literatür/saha kriteri): **≤%10**.",
        "",
        "## Sonuçlar",
        "",
        "| Metrik | Değer |",
        "|---|---|",
        f"| Nokta MAPE | **%{res['point_mape_pct']:.3f}** |",
        f"| Bootstrap ortalaması | %{res['boot_mean_mape']:.3f} |",
        f"| Bootstrap medyanı | %{res['boot_median_mape']:.3f} |",
        f"| %95 GA alt sınır (2.5p) | **%{res['ci95_lower']:.3f}** |",
        f"| %95 GA üst sınır (97.5p) | **%{res['ci95_upper']:.3f}** |",
        f"| Bootstrap std | %{res['boot_std']:.3f} |",
        f"| %{TARGET:.0f} eşiğin altındaki resample oranı | %{res['p_below_target']*100:.1f} |",
        f"| n_obs | {res['n_obs']} |",
        f"| n_bootstraps | {res['n_bootstraps']} |",
        "",
        "## Yorum — \"≤%10 Hedefe Yakınlık\" İddiası",
        "",
        f"- **Nokta tahmin** ({res['point_mape_pct']:.3f}%) hedefin {'**ALTINDA**' if point_pass else 'üstünde'}.",
        f"- **%95 GA üst sınırı** %{res['ci95_upper']:.3f} → hedef {'**içeride**' if target_pass else '**dışarıda** (üst sınır > %10)'}.",
        f"- Nokta tahmin ile %10 hedefi arasındaki mesafe: **{margin:+.3f} puan** (negatif değer hedefin üstünde demek).",
        f"- Bootstrap resample'larının **%{res['p_below_target']*100:.1f}**'i hedefi tutturuyor.",
        "",
        "### Hipotez İfadesi",
        "",
        "> **H_LOILO≤10:** Layer C XGBoost LOILO MAPE bugday için ≤%10.",
        f"> **Karar:** {('PASS ✅' if target_pass else 'KORUMA ALTINDA (yakın)' if (res['ci95_lower'] <= TARGET <= res['ci95_upper']) else 'RED ❌')}",
        "",
        "## Şampiyon Modelin (Pre-bootstrap) Layer C LOILO Tablosu",
        "",
        "Karşılaştırma için 07_layer_c_results.csv'deki bugday LOILO satırları (n=213) — bu",
        "tablo Layer C orijinal raporundan birebir alınmıştır:",
        "",
        "| Model | R² | RMSE | MAPE % |",
        "|---|---|---|---|",
        "| pls | +0.210 | 62.6 | 12.415 |",
        "| elastic_net | +0.180 | 63.8 | 12.941 |",
        "| random_forest | +0.392 | 54.9 | 11.458 |",
        "| **xgboost** | **+0.427** | **53.3** | **10.561** |",
        "| gpr | +0.342 | 57.2 | 11.753 |",
        "",
        "Bootstrap analizi yalnızca **xgboost** üzerinde yapıldı; çünkü 07_layer_c_results.csv'de",
        "şampiyon (en düşük RMSE/MAPE) olarak listelenen LOILO modeli odur.",
        "",
    ]
    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    print(f"[ÇIKIŞ] {OUT_JSON.name}")
    print(f"[ÇIKIŞ] {OUT_MD.name}")
    print()
    print("=== SONUÇ ===")
    print(f"Nokta MAPE                  : %{res['point_mape_pct']:.3f}")
    print(f"%95 GA                       : [%{res['ci95_lower']:.3f}, %{res['ci95_upper']:.3f}]")
    print(f"≤%10 hedef → nokta           : {'PASS' if point_pass else 'FAIL'}")
    print(f"≤%10 hedef → %95 GA üst       : {'PASS' if target_pass else 'FAIL'}")
    print(f"Resample'ların %{res['p_below_target']*100:.1f}'i hedefi tutturuyor")


if __name__ == "__main__":
    main()

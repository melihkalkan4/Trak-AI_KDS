"""ÇP-2.5 — uçtan uca akademik smoke test.

Senaryo: Tekirdağ 2023 ayçiçeği (kuraklık, gerçek=115 kg/da, z=-2.12).
Bu yıl train set'in içinde — MAE bandını test eder (LOOCV MAE+CI içinde
olmalı).  Ayrıca normal yıl Edirne 2021 buğday=474 kg/da bonus test.

Çalıştırma:
    python tests/test_cp25_end_to_end.py
"""
from __future__ import annotations

import sys
import logging
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

logging.basicConfig(level=logging.WARNING)

from cp25_calibration.inference import predict_yield_kg_da  # type: ignore  # noqa: E402

MFM = pd.read_csv(PROJECT_ROOT / "data" / "processed" /
                  "master_feature_matrix_2017_2024.csv",
                  parse_dates=["date"])


def _ctx_for_year(year: int, *, prev_year_too: bool = False) -> pd.DataFrame:
    """MFM slice for inference. Bugday needs t-1 Oct..; pass ``prev_year_too``."""
    if prev_year_too:
        return MFM[MFM["date"].dt.year.isin([year - 1, year])].copy()
    return MFM[MFM["date"].dt.year == year].copy()


def _print_result(label: str, r: dict, real: float, tolerance_kg_da: float) -> bool:
    pred = r["yield_kg_da"]
    err = abs(pred - real)
    ok = err <= tolerance_kg_da
    print(f"\n=== {label} ===")
    print(f"  Gerçek (TÜİK) : {real:.0f} kg/da")
    print(f"  Tahmin        : {pred:.1f} kg/da (CI: {r['yield_kg_da_lower']:.0f}–"
          f"{r['yield_kg_da_upper']:.0f})")
    print(f"  Mutlak hata   : {err:.1f} kg/da  (toleranss: ±{tolerance_kg_da:.0f})")
    print(f"  Sapma % (22yo): {r.get('sapma_pct')}  → '{r['sapma_yorum']}'")
    print(f"  Confidence    : {r['confidence']:.2f}  (season={r['sezon_tamamlanma_pct']}%)")
    print(f"  Şampiyon model: {r['champion_model']}")
    print(f"  R² (LOOCV)    : {r['metrics_loocv']['r2']:+.3f}")
    print(f"  PASS' if ok else 'FAIL': {'PASS' if ok else 'FAIL'}")
    return ok


def main() -> int:
    print("=" * 70)
    print("ÇP-2.5 — uçtan uca akademik test")
    print("=" * 70)

    passed = 0
    total = 0

    # 1) Tekirdağ 2023 ayçiçeği — kuraklık anomalisi
    total += 1
    r1 = predict_yield_kg_da(
        predicted_ndvi_series=None,
        feature_context=_ctx_for_year(2023),
        il="Tekirdağ",
        crop="aycicegi_yaglik",
        current_date=pd.Timestamp("2023-09-30"),  # tam sezon sonu
    )
    if _print_result("Tekirdağ 2023 ayçiçeği (kuraklık)",
                     r1, real=115.0, tolerance_kg_da=70.0):
        passed += 1

    # 2) Bonus: Edirne 2021 buğday (normal-yüksek yıl)
    total += 1
    r2 = predict_yield_kg_da(
        predicted_ndvi_series=None,
        feature_context=_ctx_for_year(2021, prev_year_too=True),
        il="Edirne",
        crop="bugday",
        current_date=pd.Timestamp("2021-07-15"),
    )
    if _print_result("Edirne 2021 buğday (yüksek yıl)",
                     r2, real=474.0, tolerance_kg_da=120.0):
        passed += 1

    # 3) Bonus: Kırklareli 2022 buğday (normal yıl)
    total += 1
    r3 = predict_yield_kg_da(
        predicted_ndvi_series=None,
        feature_context=_ctx_for_year(2022, prev_year_too=True),
        il="Kırklareli",
        crop="bugday",
        current_date=pd.Timestamp("2022-07-15"),
    )
    real_3 = float(pd.read_csv(PROJECT_ROOT / "data" / "external" / "tuik" /
                                "tuik_trakya_yields_clean.csv")
                    .query("il=='Kırklareli' and year==2022 and crop=='bugday'")
                    ["verim_kg_da"].iloc[0])
    if _print_result("Kırklareli 2022 buğday (normal)",
                     r3, real=real_3, tolerance_kg_da=80.0):
        passed += 1

    print("\n" + "=" * 70)
    print(f"SONUÇ: {passed}/{total} test geçti")
    print("=" * 70)

    # Print one full dict for visibility
    print("\n--- Tekirdağ 2023 ayçiçeği sonuç sözlüğü (LLM context için) ---")
    import json
    print(json.dumps({k: v for k, v in r1.items() if k != "features_used"},
                     ensure_ascii=False, indent=2, default=str))

    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())

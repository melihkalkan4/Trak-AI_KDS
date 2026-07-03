# CHANGES_vs_old — reproduction & what moved

Reproduced 92 published metric rows (cp25 05/06/07_results).

- **Model metrics (RMSE, R²): max |Δ| = 0.0004973783036490431 at 3 dp** (point estimates identical; consistent with the Phase-0 fidelity gate, max |Δ|=0.0).
- **Skill score: max |Δ| = 0.0004973996244111503 at 3 dp** — this is the **3-decimal rounding floor**, not a value change: published SS and the recomputed matched-baseline RMSE are each stored to 3 dp, so SS = 1 − RMSE/RMSE_base can differ by ±0.001 at a rounding boundary.

## Genuine value changes (SS |Δ| > 0.0011, beyond rounding)

None.

## Reporting fix (#1/#15) — not a value change
Published Table 2 displayed the **full-sample** B0 RMSE (wheat 61.7, sunflower 50.0) next to **matched-sample** skill scores. The ledger now reports the **tier-specific matched baseline RMSE** used in each skill score, e.g. wheat tier B/C = 68.975 kg/da and sunflower tier B/C = 54.571 kg/da. The skill-score values themselves are unchanged; only the *reported* baseline RMSE (denominator) is corrected so readers can reproduce SS = 1 − model_rmse/baseline_rmse_matched.

## New columns added
- `baseline_rmse_matched`, `baseline_r2_matched` (tier-specific).
- `ss_ci_low/high_iid` and `ss_ci_low/high_clustered` (cluster-aware CI is primary; see R03).
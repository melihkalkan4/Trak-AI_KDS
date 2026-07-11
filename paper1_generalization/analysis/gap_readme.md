# Generalization Gap — methods & interpretation

## What is compared
- **LOYO** (Leave-One-Year-Out): predict a held-out *year* → **temporal** generalization.
- **LOILO** (Leave-One-İlçe-Out): predict a held-out *district* → **spatial** generalization.
- **Spatiotemporal**: 5 year-blocks × 5 spatial KMeans clusters (25 blocks).

Both LOYO and LOILO operate on the *same* observation set per layer×crop, so per-observation
errors are **paired** (same ilce_id+year), enabling a paired test.

## Two views
1. **Best-per-regime** (`r2_*_best`): the highest R² achievable in each CV scheme (across the
   5–6 models). `dR2_loilo_minus_loyo_best` is the headline gap.
2. **Fixed-model paired** (`*_fixed`): one model (the LOILO champion) evaluated under both
   schemes on identical observations. Paired Wilcoxon signed-rank on |error|; rank-biserial
   effect size; paired bootstrap (5000 resamples, seed 12345) for ΔR² 95% CI.

`generalization_gap_per_model.csv` shows ΔR² for *every* model → the gap is not model-specific.

## Honest reading
A large positive ΔR² (LOILO ≫ LOYO) means the model interpolates across space far better than it
extrapolates across time: it learns district-level structure but fails to anticipate the
year-to-year climate variability that actually drives yield anomalies. This is the central,
nuanced finding of the paper — spatial skill does NOT imply operational (forward-in-time) skill.

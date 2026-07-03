# Methods snippets (EN) — paste-ready for the manuscript

> British orthography, academic-technician passive voice. Numbers are placeholders pointing to the
> artefacts that hold them ([file]); do not hand-type values — read them from the CSVs.

## Matched-sample skill scores (#1/#2/#15)
"All model and baseline comparisons were computed on identical held-out observations within each
crop, feature tier, and cross-validation fold. The climatology baseline (B0) was defined per fold as
the leave-one-out district mean yield; its root-mean-square error is therefore tier-specific (the
matched sample). Reported skill scores are SS = 1 − RMSE_model / RMSE_baseline,matched, and the
matched baseline RMSE is tabulated alongside each skill score so that every value is reproducible
[master_ledger_summary.csv]."

## Cross-validation regimes (#11)
"Three cross-validation regimes were used. Leave-one-year-out (LOYO) holds out one calendar year at a
time (retrospective held-out-year generalization). Leave-one-district-out (LOILO) holds out one
district (spatial generalization). The spatiotemporal regime partitions the panel into five
year-blocks × five spatial (k-means lat/lon) clusters and holds out one block-cell at a time; because
other years of the held-out regions and other regions of the held-out years remain in training, this
regime is termed spatiotemporal block interpolation (Scenario A), and is distinct from strict
spatiotemporal extrapolation [spatiotemporal_blocks.csv, spatiotemporal_scenario.txt]."

## Rolling-origin forward evaluation (#3)
"To complement the retrospective LOYO analysis with a genuine forward-in-time evaluation, an
expanding-window (rolling-origin) protocol was applied to the climate tier (minimum seven training
years; test years 2011–2025). For each test year, standardization, imputation, model fitting and the
climatology baseline used only data preceding that year, so no future information could leak. Skill
relative to climatology was computed per test year [rolling_origin_results.csv]. Operational claims
are based solely on this forward-in-time evaluation; LOYO is reported as retrospective held-out-year
generalization. NDVI tiers (2017 onward) were evaluated with the same protocol but over only four
test years and are interpreted with caution."

## Tuning / leakage control (#4)
"Model hyperparameters were fixed and pre-specified (identical across crops, tiers, regimes and
folds; Supplementary [hyperparameter_protocol.csv]); test-fold outcomes never informed them, so the
reported skill is free of tuning leakage. The stacking meta-learner used internal 3-fold
cross-validated out-of-fold base predictions."

## Cluster-aware inference (#5/#6)
"Because district-year observations are not independent, inference was based on cluster-aware
procedures rather than observation-level tests. Temporal comparisons used year-level error
differences (≈22 clusters); spatial comparisons used district-level differences; significance was
assessed with signed-rank tests on cluster means and block-bootstrap confidence intervals. Skill-score
confidence intervals are reported with year-clustered resampling as primary and observation-level
(iid) resampling as Supplementary [clustered_inference.csv, master_ledger_summary.csv]. Where a
year-clustered interval included zero, this is reported explicitly as substantial across-year
uncertainty."

## Per-algorithm matched ablation (#10)
"The marginal contribution of NDVI (and of soil) was quantified per algorithm, holding the algorithm,
matched sample, folds, preprocessing and hyperparameters fixed: ΔR² = R²(climate+NDVI) −
R²(climate, matched). Results are summarised as the mean and median ΔR² across algorithms per crop and
regime [ablation_matched_by_algorithm.csv]."

## Forecast-issuance staged tiers (#7)
"Because several predictors (e.g. flowering-window NDVI, grain-fill precipitation) are unavailable
before harvest, a set of issuance-time models was constructed by restricting the feature set to
variables observable by each phenological stage (pre-season, vegetative, flowering, grain-fill,
end-of-season) on a constant matched sample, evaluated under LOYO against the climatology baseline
[staged_forecast_results.csv]. End-of-season corresponds to the full-feature estimation reported
elsewhere; earlier stages quantify genuine pre-harvest forecast skill."

## Global Moran's I (#12)
"Residual spatial autocorrelation was assessed with the global Moran's I statistic computed on the
district-mean leave-one-year-out residuals of the climate-tier champion, using k-nearest-neighbour
(k = 4) row-standardised spatial weights and 999 permutations. Robustness to the neighbourhood size
was confirmed for k = 3–6 [morans_i_sensitivity.csv]."

## Fold-wise permutation importance (#13)
"Permutation importance was computed within the cross-validation: for each held-out fold the model was
fitted on the training partition and feature values were permuted on the held-out partition, with
importance defined as the resulting increase in RMSE; per-feature importances were averaged across
folds and reported with bootstrap confidence intervals [permutation_importance_foldwise.csv].
Importance reflects predictive contribution consistent with agronomic expectations, not causation."

## Parcel per-stage validation (#9)
"At the parcel scale, the frozen NDVI forecaster was compared with a naïve persistence baseline both
overall and per phenological stage; because the coefficient of determination is unstable where
within-stage NDVI variance is small (early and senescent stages), mean and median absolute error and
RMSE are reported alongside R² [parcel_per_stage.csv]. The robust statement is the overall comparison,
in which persistence is not outperformed by the model in any season (year-… see clustered inference)."

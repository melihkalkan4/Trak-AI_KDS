# Figure captions (EN) — referee-revised

**fig1_study_area_workflow.** Study area and modelling/evaluation workflow. Left: the 29 Trakya districts (centroids; colour = spatial cross-validation cluster) and the 0.62 ha validation parcel near Vize. Right: data sources, feature tiers, models, and cross-validation regimes.

**fig2_pred_vs_actual_4panel.** Predicted versus observed district yields for the multimodal (tier C) best model under temporal (LOYO) and spatial (LOILO) cross-validation, per crop. The dashed line is 1:1.

**fig3_skill_by_tier.** Leave-one-year-out skill score relative to the matched climatology baseline (SS = 1 − RMSE_model/RMSE_baseline,matched) for the best model in each feature tier. Error bars are 95% year-clustered bootstrap intervals. Winter-wheat skill is negative at every tier; only sunflower tier C lies clearly above zero.

**fig4a_same_model_gap.** Same-model generalization gap: R² of the (fixed) LOILO-champion model under temporal (LOYO) versus spatial (LOILO) cross-validation, on identical observations. The spatial−temporal gap is large and significant for every crop and tier (see table3).

**fig4b_best_per_regime.** Best-achievable R² in each cross-validation regime and tier (the winning model may differ per cell). Shown separately from the same-model gap (fig4a) to avoid conflating the two.

**fig5_parcel_per_stage.** Per-phenological-stage NDVI t+7 forecast error (MAE) at the real parcel (2025), frozen model versus naïve persistence. Persistence is not outperformed at most stages; R²/RMSE/median errors are tabulated in table5 (R² is unstable where within-stage NDVI variance is small).

**fig6_global_morans_i.** Global Moran's I of climate-tier LOYO residuals (district means; KNN row-standardised weights, 999 permutations). Maps for k=4 (left, centre) and sensitivity to k=3–6 (right). Wheat residuals show significant positive global spatial autocorrelation across all k; sunflower residuals do not.

**fig7_foldwise_importance.** Fold-wise permutation importance (computed on held-out folds; metric = increase in RMSE), tiers A and C, both crops, mean ± 95% bootstrap CI across folds. Importance reflects predictive contribution consistent with agronomic expectations, not causation.

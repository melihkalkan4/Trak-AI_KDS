<!--
============================================================================
SECTION 3 — RESULTS / SYSTEM EVALUATION  (deliverable 2 of the body)
TRAK-AI DSS system paper. English manuscript text.
Every value is traced to a source file (inline [src: ...]). Citation tags:
[V] verified against the source file this session / [P] provisional /
[N] needs check / [D] DOI missing. Author-date citation placeholders →
renumber to Elsevier [n] at assembly. Result numbers appear ONLY here (not in §2).
============================================================================
-->

# 3. Results: system evaluation

The evaluation reports component-level performance (Section 3.1), end-to-end latency and offline
operation (Section 3.2), the field reconnaissance campaign (Section 3.3), and — because it is central to
the system's design stance — an explicit transparency assessment covering forward-skill, hypothesis
status and disclosed non-operational components (Section 3.4). Unless noted, retrospective model figures
are taken verbatim from the frozen result tables shipped with the project; the cross-validated yield and
generalization-gap results are cited from the companion methods paper rather than re-derived here.

## 3.1. Component performance

**NDVI forecasting.** For the seven-day-ahead residual-delta forecast, the stacked LSTM was the per-crop
champion on held-out coefficient of determination: winter wheat R² = 0.752 (MAE 0.045, RMSE 0.057) and
sunflower R² = 0.796 (0.7957; MAE 0.041, RMSE 0.051) [V; outputs/tables/cp2_model_karsilastirma.csv]. The
full model race is close, and is reported in full rather than only for the winner: for wheat, Conv-LSTM
0.715, Attention-LSTM 0.702 and XGBoost 0.701; for sunflower, XGBoost 0.791, Attention-LSTM 0.790 and
Conv-LSTM 0.777 [V; same file]. We note one honesty caveat: when the same models are ranked by validation
*loss* rather than R², the sunflower ordering flips (XGBoost attains a lower validation loss than the
LSTM) [V; src/cp2_model/training_results.json]; the champion is selected on R²/MAE/RMSE, and the margin
over XGBoost for sunflower is therefore narrow.

**Yield estimation.** District-scale yield was assessed with the layered pipeline under temporal
(leave-one-year-out, LOYO) and spatial (leave-one-district-out, LOILO) cross-validation on the
NDVI-era panel (n = 213 wheat, 209 sunflower district-years) [V; reports/cp25/07_layer_c_results.csv].
The best Layer-C mean absolute percentage errors were, for wheat, 16.4 % (LOYO) and 10.6 % (LOILO), and
for sunflower, 17.8 % (LOYO) and 13.5 % (LOILO) [V; same file: bugday xgboost 16.364/10.561; aycicegi gpr
17.755/13.488]. The temporal (LOYO) errors are markedly larger than the spatial (LOILO) errors, and under
LOYO the wheat models carry negative R² (e.g. Layer-C XGBoost R² = −0.311) — i.e. they do not out-predict
a per-district climatological mean out-of-year. Consistent with this, the operational LOYO champion for
wheat is the climatology baseline itself (R² = 0.213), which no machine-learning configuration beats,
whereas for sunflower a multimodal Layer-C model does add skill (Gaussian-process regression R² = 0.386,
skill score +0.225) [V; reports/cp25/12_master_comparison.csv]. The spatial-versus-temporal interpretation
of this pattern — that spatial cross-validation systematically overstates the forward skill an operational
forecast needs — is established and quantified in the companion methods paper and is cited, not re-derived,
here [V-status; Kalkan and Çavdaroğlu, 2026b, under review].

» Transparency note (do not delete): an earlier project test ledger reports a much smaller yield MAPE of
5.1 % (wheat) and 7.3 % (sunflower) [V; outputs/reports/test_raporu.md]. Those figures come from an
in-sample aggregate model fitted on only eight province-year points with negative R²
(−0.47 / −0.36) [V; src/cp2_model/yield_meta_{wheat,sunflower}.json] and are **not** used as headline
accuracy here; the cross-validated district-level MAPEs above are the operative figures.

**Crop-health image classification.** The fog-tier YOLOv8s-cls model reached 94.9 % top-1 accuracy on the
held-out validation set, with per-class accuracies of 98.0 % (healthy wheat), 100.0 % (healthy sunflower),
91.0 % (rust), 99.1 % (downy mildew) and 85.2 % (nutrient stress) [V; outputs/reports/test_raporu.md].
**The drought-stress class reached 100.0 % but is flagged as overfit**: it was evaluated on only 360
images and is marked for re-training with data augmentation [V; same file, "stres_kuraklık overfit … veri
artırma gerekli"]. This caveat is carried wherever the classifier is used. On real field imagery
(distinct from the validation set), the deployed model classified field photographs at a mean confidence
of 82.6 % [V; docs/TEZ_RAPORU_FINAL.md §4.1].

## 3.2. End-to-end latency and offline operation

The advisory pipeline was measured against a < 120 s end-to-end target and met it with margin: a full
rover-telemetry-to-Turkish-advisory cycle completed in **27.1 s on CPU only**, using the locally hosted
Gemma-3-4B model [V; outputs/reports/test_raporu.md]. The retrieval corpus comprises 64 source documents
chunked into 17,065 passages [V; src/cp4_rag/faiss_index/chunks_meta.json — actual store size; the
project test headline states 17,059, a −6 discrepancy]. Retrieval returned the expected source for all ten
evaluation queries (10/10) [V; outputs/reports/test_raporu.md; outputs/tables/rag_retrieval_testleri.csv].
Two RAG evaluations remain open and are reported as pending rather than passed: the five-scenario
hallucination-resistance test and the blinded expert farmer-language assessment [V; halusinasyon_testleri.csv].
Because inference, retrieval, generation and storage are all local (Sections 2.9, 2.11), the full loop was
verified to run with no external service once inputs are cached.

## 3.3. Field reconnaissance (EVR_01, 27 May 2026)

A hardware field reconnaissance was carried out at the pilot parcel EVR_01 (Evrenli, Vize) on 27 May 2026.
The rover produced 163 telemetry records (soil moisture, air temperature/humidity, obstacle distance and
GPS), captured over MQTT and ingested into the SQLite store, and 105 field images were captured and
classified by the fog-tier model [V; scripts/rover_log_27may2026.txt = 163 `rover/data` lines;
data/rover_images/27may2026/ = 105 JPEGs; data/rover_images/classified/]. This campaign is a
single-session operational reconnaissance rather than a controlled accuracy trial; it demonstrates the
end-to-end acquisition-to-storage path on real hardware and provides the field-image set used for the
82.6 % mean-confidence classification reported in Section 3.1. » Note: the three additional rows in the
telemetry table beyond the 163 field records are manual test inserts and are labelled as such
[V; docs/RAPOR_2026-05-27.md].

## 3.4. Transparency and honesty evaluation

Consistent with the design premise (Section 2.1, 2.6), the system is evaluated for what it does *not*
reliably do, not only for its successes.

**Forward skill versus persistence.** In forward-looking operational validation on the real surveyed
parcel, the frozen NDVI forecaster did **not** beat a naïve persistence baseline in any window
[V; paper1_generalization/analysis/prospective_overall_real.csv]: for 2025 the model reached R² = 0.775
(raw Sentinel-2 actuals) and 0.783 (interpolated) against persistence R² = 0.899 and 0.911; for the
partial 2026 season the model fell to R² = −0.191 and −1.319 against persistence 0.540 and 0.490. Model
absolute error exceeded persistence in every case, and a one-sided Wilcoxon test never favoured the model
(p ≈ 1.0). This result is reported transparently and is consistent with the companion paper's forward-skill
finding [V-status; Kalkan and Çavdaroğlu, 2026b].

**Hypothesis and test status.** The project's thesis-level hypotheses stand at four confirmed and two
pending: hardware sufficiency, hybrid BBCH phenology consensus, field YOLOv8 confidence, and local-LLM
advisory are confirmed; the target of ≤ 10 % Layer-C wheat LOILO yield error is pending (point estimate
10.6 %, 95 % CI [9.1, 12.1] straddles the threshold) and the LLM hallucination-resistance / farmer-
satisfaction hypothesis is pending [V; docs/TEZ_RAPORU_FINAL.md §6]. At the system-test level, 22
integration tests resolve to 18 passed, 2 pending (hallucination test, blinded expert language
assessment) and 2 partial (planting-window 5/6; drought-stress overfit) [V; outputs/reports/test_raporu.md].
No hypothesis or test is reported as passed where the evidence is incomplete.

**Disclosed non-operational components.** Three components are prototypes or placeholders and are not
claimed as operational (detailed in Section 2): the ESP32-CAM on-device classifier is a placeholder, so
crop-health inference runs at the fog tier; the satellite-CNN modality of the cross-modal consensus is an
untrained stub, so that validator operates as a two-of-three consensus; and the language-model advisory
currently injects a fixed soil profile rather than a per-parcel one. Reporting these alongside the
performance figures is deliberate: the contribution of TRAK-AI is an honest, offline-first integration,
and its transparency about component maturity is part of that contribution.

<!--
============================================================================
END SECTION 3. Notes for assembly:
  - Tables to render from these numbers: T2 (canonical performance + source), and a
    yield LOYO/LOILO table; NDVI race table; YOLO per-class table.
  - All figures cited (F4 NDVI race, F6 YOLO confusion, F9 FLOV, F7 RAG gauge) exist under
    outputs/charts/ ; F10 field recon (EVR_01) to assemble.
  - Numbers verified this session against: cp2_model_karsilastirma.csv, 07_layer_c_results.csv,
    12_master_comparison.csv, prospective_overall_real.csv, test_raporu.md, chunks_meta.json,
    rover_log_27may2026.txt, TEZ_RAPORU_FINAL.md §6.
  - Chunk count stated as 17,065 (actual store) with the −6 test-headline discrepancy noted, per
    the "use real repo values" decision. Retrieval 10/10 (no 9.5/10 anywhere). Hypotheses = real
    thesis §6 (4 PASS/2 PENDING) + system-test 18/2/2. Yield MAPE = cross-validated quartet,
    in-sample 5.1/7.3% explicitly set aside.
============================================================================
-->

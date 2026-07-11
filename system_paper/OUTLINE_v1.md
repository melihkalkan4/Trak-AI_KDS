# TRAK-AI system paper — structured outline + figure/table plan (v1, for approval)

**Status:** STOP-for-approval draft. No sections written yet. Author decisions (2026-07-11): (i) prepare
for BOTH CEA and SAT — CEA-novelty framing primary, text pivotable to SAT; (ii) use REAL repo values for
the three flagged items (retrieval 10/10; hypotheses = thesis §6 = 4 PASS/2 PENDING + system-test 18/2/2;
chunks 17,065). No fabricated or placeholder metrics.

**Working title (CEA-novelty framing; SAT-compatible):**
"TRAK-AI: an offline-first Edge–Fog–Cloud decision-support system with honesty-aware yield advisories
for low-connectivity smallholder agriculture (winter wheat and sunflower, Trakya, Türkiye)"

**Target:** Computers and Electronics in Agriculture (primary, novelty-forward framing) with a
Smart Agricultural Technology (SAT) pivot kept ready. Article type: Original research paper.
Dual-journal note: CEA foregrounds the investigator-developed integration + honesty-aware design as the
innovation; the SAT variant reframes the same content as an applied integration/deployment contribution
(lower novelty bar). Section content is identical; only Introduction framing + title emphasis differ.

---

## 1. Introduction
- Problem: smallholder precision-ag decision support under intermittent connectivity; Trakya wheat+sunflower.
- Gap: DSS that assume cloud connectivity and that report cross-validated ML accuracy as if it were
  operational skill.
- **Design premise (cite IJEG paper1):** cross-validated accuracy ≠ operational forward skill → the
  system is deliberately built to fall back to climatology/persistence where ML does not beat baselines.
- Contributions (investigator-developed, to satisfy CEA novelty gate): (i) offline-first Edge–Fog–Cloud
  integration; (ii) honesty-aware advisory logic embedding the spatial≠temporal finding; (iii) Tri-RAG
  Turkish offline agronomic advisory with a local LLM; (iv) human-in-the-loop MQTT approval + SQLite
  offline store; (v) transparent multi-modal consensus with documented graceful degradation.

## 2. Materials and Methods (System Design)
- 2.1 Study area, users, requirements (offline-first, low-cost, Turkish-language).
- 2.2 Edge–Fog–Cloud architecture overview — **Fig. 2**.
- 2.3 Edge: field rover (ESP32) as data-acquisition node — **cite HardwareX paper** if submitted, else
  brief; **disclose** ESP32-CAM on-device classifier is a placeholder (capture/transmit only).
- 2.4 Multi-modal ETL: Sentinel-2 (GEE) + NASA POWER (MERRA-2) + SoilGrids fusion.
- 2.5 NDVI forecasting: LSTM/ConvLSTM/Attention-LSTM/XGBoost race, champion selection — **Fig. 4, Table 2**.
- 2.6 Yield estimation: layered climate→+NDVI→+soil champion; honest baselines (B0 climatology, B2
  persistence); **cite IJEG** for the LOYO/LOILO generalization gap as validation rationale.
- 2.7 Fog vision: YOLOv8s-cls crop-health (6 classes) — **disclose** stress_drought overfit + mock fallback.
- 2.8 Multi-modal consensus validation — **disclose** it operates 2-of-3 (satellite CNN is an untrained stub).
- 2.9 Tri-RAG advisory + offline LLM (Gemma-3-4B via Ollama), FAISS+BM25+merge-boost — **summary level;
  full treatment reserved for a separate RAG paper (cite as forthcoming).**
- 2.10 MQTT fog orchestration + rule-based anomaly engine + human-in-the-loop approval.
- 2.11 SQLite offline-first store + Streamlit dashboard deployment.

## 3. Results (System Evaluation)
- 3.1 Component performance — NDVI R² 0.752 wheat / 0.796 sunflower; yield MAPE 16.4/17.8 (LOYO),
  10.6/13.5 (LOILO) [cite IJEG/cp25]; YOLO 94.9% top-1 (+ overfit disclosure). **Table 2.**
- 3.2 End-to-end latency (27.1 s CPU-only) + verified offline operation. **Table / Fig.**
- 3.3 Field reconnaissance EVR_01 (2026-05-27): 163 telemetry readings, 105 classified images. **Fig. 10.**
- 3.4 **Transparency & honesty evaluation** — persistence beat the frozen champion in FLOV (cite IJEG,
  all p=1.000); hypothesis/test statuses reported as-is: thesis §6 = 4 PASS (H1–H4) / 2 PENDING
  (H_LOILO≤10, H6 hallucination) + system-test ledger 18 PASS / 2 PENDING / 2 PARTIAL; Tri-RAG retrieval
  10/10, 17,065 chunks, 27.1 s CPU; explicit mock-component disclosure. **Table 3.**

## 4. Discussion
- Honesty-aware DSS as a design stance; when to defer to climatology; limitations (prototype edge-vision,
  single region, placeholder coords); generalizability; path to deployment.

## 5. Conclusion

## Back matter
Highlights (3–5 ≤85 chars, separate file) · Graphical abstract · CRediT · Data availability (Mendeley
10.17632/f6d29w5zjk.1) · Code availability (GitHub + Zenodo 10.5281/zenodo.21308764) · Declaration of
generative-AI use · Competing interests · Acknowledgements (TÜBİTAK 2209-A) · References (40–60).

---

## Figure plan
| # | Figure | Source / status |
|---|---|---|
| F1 | Study area + workflow | exists: paper1 fig1_study_area_workflow.png (reuse/adapt) |
| F2 | Edge–Fog–Cloud architecture | exists: outputs/diagrams/mimari_edge_fog_cloud.png (**redraw in English**) |
| F3 | Rover hardware / node | from HardwareX figures (rover photo + wiring) |
| F4 | NDVI model race (R²) | exists: outputs/charts/cp2_model_karsilastirma_r2.png |
| F5 | Yield LOYO vs LOILO gap | cite IJEG; optional re-plot from T1_master_results.csv |
| F6 | YOLO confusion matrix + per-class | exists: outputs/charts/yolo_confusion_matrix.png, yolo_sinif_dogruluk.png |
| F7 | Tri-RAG pipeline + KB stats | exists: rag_performans_gauge.png, rag_bilgi_tabani_istatistik.png |
| F8 | Dashboard screenshots (offline) | **to capture** (streamlit run src/dashboard.py) |
| F9 | FLOV persistence-vs-champion | from paper1 prospective_overall_real.csv |
| F10 | EVR_01 field recon (map + photos) | **to assemble** from 2026-05-27 campaign (105 imgs) |

## Table plan
| # | Table | Source |
|---|---|---|
| T1 | Component inventory + real/mock status | repo map (this recon) |
| T2 | Canonical performance metrics + source file | cp2_model_karsilastirma.csv, cp25/07_layer_c_results.csv, test_raporu.md |
| T3 | Hypothesis / system-test status | TEZ_RAPORU_FINAL.md §6 + test_raporu.md (ACTUAL tallies) |
| T4 | Rover BOM summary | HardwareX BOM (~3,440 TL) — cite |

---

## Decisions — RESOLVED (2026-07-11)
1. **Journal/scope:** prepare for BOTH — CEA-novelty framing primary, SAT pivot ready. ✔
2. **Integrity flags:** use real repo values — retrieval 10/10; hypotheses thesis §6 (4 PASS/2 PENDING) +
   system-test 18/2/2; chunks 17,065. No fabricated/placeholder metrics. ✔

## Defaults I will proceed on unless you object
3. Authoritative artifact trees: reports/cp25/ + paper1_generalization/ (not the enrichment_v2/ mirrors).
4. HardwareX: cite as "manuscript in preparation" (not yet submitted) + brief rover description.
5. Yield MAPE headline = cp25 LOYO/LOILO quartet (16.4/17.8, 10.6/13.5); CP-2 aggregate 5.1/7.3%
   (n=8, in-sample, negative R²) explicitly set aside / not headlined.

## Awaiting your GO to start step 2 (section-by-section drafting)
Per your process, each section is a separate deliverable. Proposed drafting order:
2 (System Design) → 3 (Evaluation) → 1 (Introduction) → 4 (Discussion) → 5 (Conclusion) → back matter +
the 40–60 reference list with [V]/[P]/[N]/[D] tags. (Methods first because it anchors every number.)

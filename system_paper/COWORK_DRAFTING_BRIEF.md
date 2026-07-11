# TRAK-AI system paper — self-contained drafting brief (for Claude Cowork or any writing agent)

**Purpose.** This single file lets a writing agent that has NO access to this repo or this conversation
draft the TRAK-AI DSS system paper correctly. Every number below is verified against a named source file;
never invent, round favorably, or add a value not listed here. In Cowork, invoke the
`gis-academic-writer` skill, paste the relevant per-section prompt (§8), and give it this brief as context.

Chat in Turkish; **all manuscript text in English.** Deliver complete sections, not fragments.

---

## 1. Target & framing (dual-journal)
- **Primary:** Computers and Electronics in Agriculture (CEA/COMPAG, Elsevier, ISSN 0168-1699).
  CEA desk-rejects off-the-shelf integration lacking investigator novelty → **foreground the
  investigator-developed contributions**: (i) offline-first Edge–Fog–Cloud integration; (ii) honesty-aware
  advisory design that embeds the "spatial ≠ temporal skill" finding (system defers to
  climatology/persistence where ML fails); (iii) Tri-RAG Turkish offline agronomic advisory; (iv)
  human-in-the-loop MQTT approval; (v) transparent multi-modal consensus with documented degradation.
- **Fallback:** Smart Agricultural Technology (SAT, Elsevier, open access). Same content; Introduction
  reframed as an applied integration/deployment contribution (lower novelty bar).
- Article type: Original research paper. Abstract ≤250 words. Keywords 1–7. Highlights required
  (separate file, 3–5 bullets ≤85 chars). Graphical abstract encouraged. CRediT required. Generative-AI
  declaration required if AI used. Numbered sections; Elsevier numbered reference style. Editable .docx/.tex.

## 2. Authors & metadata
- Melih Kalkan* (corresponding) — ORCID 0009-0004-7719-5333 — melihkalkan4@outlook.com
  [DiB/CEA prefer an institutional @isikun.edu.tr address if available]
- Gülsüm Çiğdem Çavdaroğlu — ORCID 0000-0002-4875-4800
- Affiliation: Işık University, Department of Management Information Systems, İstanbul, Türkiye
  [add full postal address]
- Funding: TÜBİTAK 2209-A University Students Research Projects [add application/grant no.]

## 3. Integrity rules (non-negotiable)
1. Never fabricate data, statistics, citations or DOIs. Unverifiable → visible placeholder
   `[KAYNAK BULUNACAK]` / `[DEĞER DOĞRULANACAK]`.
2. Every number must match a source file in §5. Never round favorably.
3. Crop-specific results are primary; never headline aggregate figures.
4. Spatial CV skill ≠ temporal/forward skill — never conflate.
5. Never claim "better results" where rigor, not skill, improved.
6. Disclose every mock/placeholder component (§6) wherever relevant.
7. Draft citation tags [V] verified / [P] provisional / [N] needs check / [D] DOI missing; final pass
   removes only [V].

## 4. Cite-don't-duplicate boundary (IJEG companion paper)
The companion manuscript — Kalkan & Çavdaroğlu, "Spatial skill is not temporal skill: a cross-validation
audit of satellite-driven winter-wheat and sunflower yield prediction in Trakya, Türkiye" — is **under
review at IJEG** (International Journal of Engineering and Geosciences, DergiPark ID 1992083; submitted
2026-07-11). The system paper must **CITE** it for, and must NOT re-report as its own: the LOYO/LOILO/
spatiotemporal CV protocol; the six ΔR²(LOILO−LOYO) generalization-gap cells with CIs/Wilcoxon/rank-
biserial; the baseline-superiority result (no ML beats climatology for wheat, 0/16; sunflower Layer-C GPR
beats it); the matched-sample NDVI/soil ablation; the FLOV persistence-beats-champion result; Moran's I;
permutation feature importance. The system paper's lane = the DSS: architecture, edge/fog/cloud
integration, RAG/advisory, dashboard, deployment, field reconnaissance. Cite as "manuscript under review"
(never "in press"). Data-in-Brief dataset paper (Mendeley 10.17632/f6d29w5zjk.1) can also be cited.

## 5. VERIFIED NUMBERS (value — source file). Use exactly.
**NDVI 7-day forecast model race** — `outputs/tables/cp2_model_karsilastirma.csv`:
- Wheat R²: **LSTM 0.752 (champion)**, ConvLSTM 0.7151, Attention-LSTM 0.7015, XGBoost 0.701.
- Sunflower R²: **LSTM 0.7957 (champion)**, XGBoost 0.7909, Attention-LSTM 0.7896, ConvLSTM 0.7773.
- Honesty note: `src/cp2_model/training_results.json` ranks the same models by validation LOSS, and for
  sunflower the order flips (XGBoost loss 0.006634 < LSTM 0.007193). Headline the R² table; note the flip.

**District yield MAPE (cross-validated, Layer C)** — `reports/cp25/07_layer_c_results.csv`:
- Wheat: **LOYO (XGBoost) 16.4%** (16.364) · **LOILO 10.6%** (10.561).
- Sunflower: **LOYO (GPR) 17.8%** (17.755) · **LOILO 13.5%** (13.488).
- DO NOT headline the CP-2 aggregate yield MAPE 5.1%/7.3% (`src/cp2_model/yield_meta_{wheat,sunflower}.json`,
  n=8, in-sample, negative R² −0.467/−0.358) nor the cp25 calibration-holdout 9.7%/10.6%
  (`reports/cp25_calibration_metrics.json`, Ridge). Three different yield-MAPE numbers exist — use the LOYO/LOILO quartet.

**Yield champions & generalization gap (CITE IJEG, do not recompute)** —
`reports/cp25/12_master_comparison.csv`, `paper1_generalization/tables/T1_master_results.csv`:
- Wheat LOYO champion = **B0 climatology R²=0.213**; 0 of 16 ML configs beat it.
- Sunflower LOYO champion = **Layer C GPR R²=0.386**, skill score +0.224.
- ΔR²(LOILO−LOYO), climate tier: **wheat +0.639** [+0.545,+0.735], p=6.2e-26; **sunflower +0.580**
  [+0.490,+0.674], p=5.6e-28.

**YOLOv8s-cls crop-health (6 classes)** — `outputs/tables/tum_test_sonuclari.csv`, `outputs/reports/test_raporu.md`:
- **Top-1 = 94.9%.** Per-class: saglikli_bugday 98.0, saglikli_aycicegi 100.0, hastalik_pas 91.0,
  hastalik_mildiyo 99.1, stres_besin 85.2, **stres_kuraklik 100.0 → OVERFIT WARNING** (100% on only 360
  images, augmentation needed). Always disclose the stress_drought overfit.
- Field deployment (`docs/TEZ_RAPORU_FINAL.md` §4.1): 105 field photos, mean confidence 82.6%,
  model `models/crop_health_best.pt`.

**Tri-RAG advisory** — `src/cp4_rag/faiss_index/chunks_meta.json`, `outputs/tables/tum_test_sonuclari.csv`:
- **17,065 chunks** (actual FAISS store; thesis body agrees). [The "17,059" test-headline is −6 off; use 17,065.]
- **Retrieval 10/10 = 100%** (`outputs/tables/rag_retrieval_testleri.csv`). [There is NO "9.5/10" in the repo.]
- **LLM latency 27.1 s, CPU-only, Gemma-3-4B** via Ollama.
- Architecture: FAISS (intfloat/multilingual-e5-small) dense + BM25Okapi sparse + **merge/dedupe/boost**
  (NOT a neural cross-encoder reranker). FAISS_TOP_K=5, BM25_TOP_K=3, FINAL_TOP_K=2.
- Hallucination resistance test = **PENDING** (`outputs/tables/halusinasyon_testleri.csv`, 5 scenarios).
- Reserve full RAG treatment for a separate paper; summary level only here.

**Forward validation (FLOV) — persistence beats the frozen champion** —
`paper1_generalization/analysis/prospective_overall_real.csv` (real surveyed coords):
- 2025 raw-S2: model R² 0.7751 vs persistence 0.8986; 2025 unified 0.7831 vs 0.9109; 2026 raw-S2 −0.191
  vs 0.540; 2026 unified −1.319 vs 0.490. **All rows: model_beats_persistence = False**, Wilcoxon p≈1.0.
- (Thesis placeholder-coord version, `docs/TEZ_RAPORU_FINAL.md` §4.3: 0.70 vs 0.75, W=2603, p=0.40.)
- Report transparently; never soften.

**Crop-mask validation (IJEG headline, cite)** — `dib_submission/manuscript_dib.md`,
`mendeley_package/regenerate_tables.py`: Pearson **r=0.954 wheat / 0.615 sunflower, n=216** (27 districts × 8 years).

**Hypothesis / test status (use ACTUAL values):**
- Thesis `docs/TEZ_RAPORU_FINAL.md` §6: **H1–H4 PASS**, **H_LOILO≤10 PENDING** (point 10.56, 95% CI
  [9.14,12.10] straddles 10), **H6 hallucination PENDING** → 4 PASS / 2 PENDING. (No "H7" exists; H3 is PASS.)
- System-test ledger `outputs/reports/test_raporu.md`: **18 PASS / 2 PENDING / 2 PARTIAL** (partials =
  planting-window 5/6, stress_drought overfit).
- cp25 yield hypotheses `models/cp25/champion_metadata.json`: separate H1–H5, mixed per-crop verdicts.

**Rover / field campaign:** BOM ≈ **3,440 TL** (HardwareX paper, in preparation); EVR_01 field
reconnaissance **2026-05-27**, **163 telemetry readings, 105 classified images**; parcel 0.62 ha,
centroid **41.531191 N, 27.861465 E**, near Vize (Kırklareli). [Note a coordinate inconsistency across the
codebase — use the surveyed parcel coords above.]

**Deposits:** dataset Mendeley Data DOI **10.17632/f6d29w5zjk.1** (CC-BY-4.0; in moderation at time of
writing); code GitHub `melihkalkan4/trak-ai-crop-yield-cv-audit` + Zenodo concept DOI
**10.5281/zenodo.21308764** (MIT).

## 6. Mandatory mock/placeholder disclosures (rule 6)
- ESP32-CAM on-device classifier is a **placeholder** (JPEG byte-size → fake BBCH); the rover
  captures/transmits only — **YOLOv8 inference runs on the laptop/fog layer, not on the ESP32-CAM.**
- Cross-modal consensus is nominally 3-way but the **satellite ResNet50 modality is an untrained stub**
  (`models/visual/` empty) → the shipped system runs **2-of-3** (field YOLOv8 + numerical features).
- NDVI `inference_cp2.predict()` with no live data **falls back to the last training window** (test mode).
- YOLO `_mock_result()` random fallback fires only if the model is missing (logs "[MOCK]").
- A **hardcoded SoilGrids soil profile** is injected into every LLM advisory prompt.
- FLOV pilot-site coordinates in `prospective_validation/config.py` are **placeholders**.
- `docs/MOCK_DATA_AUDIT.md` §3.1 is **stale** (the DB mock seeders it lists were removed; schema v3).
- Real/trained components: ETL, NDVI-LSTM weights, cp25 yield champions, YOLO `crop_health_best.pt`,
  FAISS+BM25 over ~60 docs, Ollama gemma3:4b (offline), SQLite offline-first store, ESP32 rover firmware.

## 7. Outline (see also OUTLINE_v1.md)
1 Introduction · 2 Materials & Methods / System Design (2.1 study area/requirements, 2.2 Edge–Fog–Cloud
architecture, 2.3 edge rover + ESP32-CAM [disclose], 2.4 multi-modal ETL, 2.5 NDVI forecasting race,
2.6 yield estimation + honest baselines [cite IJEG], 2.7 YOLO fog vision [disclose overfit/mock],
2.8 multi-modal consensus [disclose 2-of-3], 2.9 Tri-RAG + offline LLM [summary; separate paper],
2.10 MQTT orchestration + human-in-the-loop, 2.11 SQLite offline-first + Streamlit) · 3 Results/System
Evaluation (3.1 component performance, 3.2 latency + offline operation, 3.3 EVR_01 field recon,
3.4 transparency/honesty evaluation) · 4 Discussion · 5 Conclusion · back matter.

Figures F1–F10 and Tables T1–T4 per OUTLINE_v1.md (architecture diagram
`outputs/diagrams/mimari_edge_fog_cloud.png` needs an English redraw; dashboard screenshots + EVR_01
field-map still to capture).

## 8. Ready-to-use per-section prompts (paste one at a time into gis-academic-writer)
- **§2 System Design:** "Using the TRAK-AI drafting brief, write Section 2 (Materials and Methods / System
  Design) of the CEA system paper in English, subsections 2.1–2.11 per §7. Describe the Edge–Fog–Cloud
  architecture and each subsystem. Use only numbers from §5 with their sources; disclose every §6 mock
  component in the relevant subsection; cite the IJEG paper (§4) for the validation rationale rather than
  re-reporting its metrics. Numbered sections, formal journal prose, [V]/[P]/[N] tags on citations."
- **§3 Evaluation:** "...write Section 3 (Results / System Evaluation), 3.1–3.4. Headline crop-specific
  values (NDVI R² 0.752/0.796; yield MAPE 16.4/17.8 LOYO, 10.6/13.5 LOILO; YOLO 94.9% + stress_drought
  overfit; latency 27.1 s; retrieval 10/10; 17,065 chunks). Report the FLOV persistence-beats-champion
  result and the honest hypothesis tallies (4 PASS/2 PENDING; 18/2/2) transparently. Cite IJEG for the
  generalization gap."
- **§1 Introduction:** "...write Section 1 (Introduction) with the CEA-novelty framing (§1 of the brief),
  motivating the design premise 'cross-validated accuracy ≠ operational skill' and citing the IJEG paper;
  end with an explicit contributions list. Also provide a 3-sentence SAT-framing variant of the opening."
- **§4 Discussion / §5 Conclusion / Abstract / Highlights / back matter:** analogous, per §1 and §7.

## 9. Reference seed (verified DOIs — extend to 40–60)
IJEG companion (under review, DergiPark 1992083) [V-status]; dataset Mendeley 10.17632/f6d29w5zjk.1 [P];
code Zenodo 10.5281/zenodo.21308764 [V]; SoilGrids 2.0 10.5194/soil-7-217-2021 [V]; MERRA-2
10.1175/JCLI-D-16-0758.1 [V]; ESA WorldCover 10.5281/zenodo.7254221 [V]; Saxton–Rawls 10.2136/sssaj2005.0117
[V]; nasapower 10.21105/joss.01035 [V]; Sentinel-2 10.1016/j.rse.2011.11.026 [V]; Google Earth Engine
10.1016/j.rse.2017.06.031 [V]. Still needed [N/D]: YOLOv8/Ultralytics, LSTM (Hochreiter & Schmidhuber
1997), FAISS (Johnson et al.), BM25/Okapi, Gemma / Ollama, RAG (Lewis et al. 2020), Streamlit, MQTT/OSI
standard, BBCH scale, crop-yield-ML reviews (van Klompenburg et al. 2020), spatial-CV leakage
(Roberts et al. 2017; Ploton et al. 2020), Moran's I — web-verify each DOI before use.

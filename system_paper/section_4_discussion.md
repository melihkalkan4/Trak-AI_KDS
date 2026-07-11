<!--
============================================================================
SECTION 4 — DISCUSSION  (deliverable 4 of the body)
Interpretive but grounded strictly in Sections 2–3 (no new numbers introduced
as findings; any figure restated carries its Section-3 source). Citation
placeholders author-date with tags. English manuscript text.
============================================================================
-->

# 4. Discussion

## 4.1. Honesty-aware design as the central contribution

The main lesson of TRAK-AI is that the validation rigour usually confined to a methods paper can, and
arguably should, be built into the decision-support system itself. Because the companion audit showed that
no machine-learning configuration out-predicts a climatology baseline for winter wheat out-of-year, while
a multimodal model does for sunflower (Section 3.1), the system does not present a single "AI yield" number
with implied authority. Instead it defaults winter-wheat yield to the climatology baseline, attaches
prediction intervals and a forward-skill caveat to machine-learning estimates, and — most tellingly —
reports a forward-validation result in which the frozen NDVI forecaster fails to beat naïve persistence on
the one real surveyed parcel (Section 3.4). A conventional system would have surfaced the 0.75–0.80 NDVI
R² (Section 3.1) as a headline capability; ours reports it alongside the persistence comparison that
contextualises it. This stance costs apparent performance but buys trustworthiness, which for a
non-specialist user base is the more valuable currency.

## 4.2. Offline-first integration for low-connectivity smallholder settings

The engineering contribution is the offline-first Edge–Fog–Cloud integration. By performing all inference,
hybrid retrieval and language generation locally on CPU-only hardware, and using the cloud tier only for
cache-backed acquisition, the system removes the continuous-connectivity assumption that limits many
precision-agriculture platforms in smallholder regions. The measured 27.1 s end-to-end latency
(Section 3.2) is acceptable for a field advisory that is consulted on the order of times per day rather
than continuously, and the store-and-forward telemetry buffer plus the read-only, last-cached dashboard
contract mean the system degrades gracefully rather than failing when the network or an upstream service is
unavailable. The human-in-the-loop approval queue keeps a person in control of what enters the record,
which is appropriate given the disclosed maturity limits of some components.

## 4.3. Limitations

We report limitations in full, consistent with the paper's stance.

*Prototype edge-vision.* Two vision components are not operational as designed and are disclosed as such
(Sections 2.3, 2.7, 2.8): the ESP32-CAM performs capture and transmission only — its on-device classifier
is a placeholder, so crop-health inference is done at the fog tier — and the satellite-CNN modality of the
cross-modal consensus is an untrained stub, so that validator runs as a two-of-three consensus. The
"tri-modal edge" description therefore reduces, in the shipped system, to fog-tier field-image
classification plus a numerical predictor.

*Evaluation coverage.* Two advisory evaluations remain pending rather than passed: the language model's
hallucination-resistance test and the blinded expert farmer-language assessment (Section 3.2, 3.4). The
drought-stress image class attains 100 % validation accuracy on only 360 images and is flagged as overfit
pending re-training with augmentation (Section 3.1). The advisory context builder currently injects a fixed
soil profile rather than a per-parcel one (Section 2.9). These are concrete, addressable gaps rather than
fundamental barriers.

*Scope and ground truth.* The retrospective panel is a single region over roughly two decades, which
constrains leave-one-year-out folds and widens year-cluster confidence intervals; district yields are
administrative aggregates rather than measured plot yields; and the only field-scale ground truth is the
single EVR_01 parcel, with the operational demonstration sites carried at disclosed placeholder
coordinates (Section 2.3). The system also uses two distinct climate reanalyses in separate roles —
ERA5-Land for the operational daily pipeline and NASA POWER (MERRA-2) for the retrospective district panel
(Section 2.4) — which are reported separately and not merged.

*Retrieval design.* The advisory retrieval uses a merge-and-boost heuristic over dense and sparse results
rather than a neural cross-encoder re-ranker (Section 2.9); a full treatment of the retrieval layer,
including its corpus, latency and hallucination evaluation, is deferred to a dedicated paper.

## 4.4. Generalizability and future work

The architecture is not specific to Trakya or to wheat and sunflower: the edge-acquisition node, the
offline fog-tier inference stack, the human-in-the-loop data plane and the honesty-aware advisory logic
transfer to other crops and low-connectivity regions given locally appropriate models and an agronomic
corpus. Priorities for future work follow directly from the limitations: training and deploying the
satellite-CNN modality to realise the full tri-modal consensus; separating crop-specific pixels rather
than using a generic cropland mask; completing the hallucination and expert-language evaluations of the
advisory layer; re-training the drought-stress class with augmentation; replacing the fixed soil profile
with a per-parcel lookup; and extending the single-parcel field reconnaissance to a multi-site, multi-season
trial. On the edge, migrating a compact classifier to on-device inference (e.g. TensorFlow-Lite-Micro on
the ESP32-CAM) would move part of the vision workload from fog to edge as originally intended.

<!--
============================================================================
FRONT & BACK MATTER — TRAK-AI system paper (CEA primary; SAT-compatible)
Title block, abstract, keywords, highlights, and all declarations.
Citation/DOI tags [V]/[P]/[N]/[D]; bracketed ALL-CAPS = author must supply.
============================================================================
-->

# TRAK-AI: an offline-first Edge–Fog–Cloud decision-support system with honesty-aware yield advisories for low-connectivity smallholder agriculture (winter wheat and sunflower, Trakya, Türkiye)

**Melih Kalkan** ^a,\*^, **Gülsüm Çiğdem Çavdaroğlu** ^a^

^a^ Işık University, Department of Management Information Systems, İstanbul, Türkiye
[DEĞER DOĞRULANACAK: full postal street address + postal code]

\* Corresponding author. E-mail: melihkalkan4@outlook.com (M. Kalkan)
[N: CEA prefers an institutional e-mail — substitute an @isikun.edu.tr address if available]

ORCID — M. Kalkan: 0009-0004-7719-5333 [V]; G. Ç. Çavdaroğlu: 0000-0002-4875-4800 [V]

---

## Abstract

<!-- CEA: ≤250 words; state purpose, principal results, major conclusions. Current ≈ 235 words. -->

Precision-agriculture decision-support systems are often reported with strong cross-validated model
accuracy, yet their operational value in smallholder regions is constrained by two under-examined factors:
whether that accuracy reflects genuine out-of-year forecasting skill, and whether the system can run in the
field without reliable connectivity. This paper presents TRAK-AI, an offline-first Edge–Fog–Cloud
decision-support system for winter wheat and oilseed sunflower across 29 districts of Trakya, Türkiye. A
low-cost ESP32 field rover acquires in-situ soil, atmospheric, positional and image data over MQTT; a
laptop-class fog tier performs seven-day NDVI forecasting, layered district-yield estimation, YOLOv8 crop-
health classification and a Turkish-language retrieval-augmented advisory with a locally hosted Gemma-3-4B
language model; and the cloud tier is used only for cache-backed acquisition of Sentinel-2, ERA5-Land and
SoilGrids inputs, so the full decision loop runs on CPU-only hardware without a network once inputs are
cached, completing end-to-end in 27.1 s. Guided by a companion cross-validation audit, the system encodes
an honesty-aware design: it defaults winter-wheat yield to a climatology baseline that no machine-learning
configuration beats out-of-year, reports NDVI forecasts (R² 0.75 wheat, 0.80 sunflower) alongside a
forward-validation result in which a naïve persistence baseline is not beaten, and discloses the prototype
or placeholder status of its edge-vision components. A single-session field reconnaissance on a real
surveyed parcel (163 telemetry records, 105 classified images) demonstrates the acquisition-to-advisory
path on hardware. TRAK-AI's contribution is an honest, deployable integration rather than a new
high-accuracy model.

## Keywords

decision-support system; offline-first edge computing; retrieval-augmented generation; low-cost agricultural robot; forward validation; smallholder precision agriculture

<!-- 1–7 keywords; avoid repeating title words. Current 6. -->

## Highlights

<!-- 3–5 bullets, each ≤85 characters INCLUDING SPACES. Verified within limit. -->

- Offline-first Edge–Fog–Cloud crop advisory runs on CPU with no network connection
- Honesty-aware design defers winter-wheat yield to a climatology baseline
- NDVI LSTM: R²=0.75 wheat, 0.80 sunflower; the full model race is reported
- Persistence beats the frozen forecaster on a real parcel; reported openly
- Turkish offline RAG advisory with a local LLM; 27 s end-to-end on CPU

---

## CRediT author statement

**Melih Kalkan:** Conceptualization, Methodology, Software, Formal analysis, Data curation, Writing –
original draft, Visualization. **Gülsüm Çiğdem Çavdaroğlu:** Supervision, Writing – review and editing.

## Declaration of competing interests

The authors declare that they have no known competing financial interests or personal relationships that
could have appeared to influence the work reported in this paper.

## Data availability

The derived dataset underlying the retrospective models is deposited on Mendeley Data under a CC-BY-4.0
licence, DOI 10.17632/f6d29w5zjk.1 [P; the record is in repository moderation at the time of writing and
resolves on publication — DEĞER DOĞRULANACAK]. TÜİK district statistics are publicly available official
statistics; Sentinel-2, ERA5-Land, NASA POWER and SoilGrids inputs are openly available from their
providers.

## Code availability

The cross-validation-audit reproducibility code is openly available on GitHub
(github.com/melihkalkan4/trak-ai-crop-yield-cv-audit) and archived on Zenodo, concept DOI
10.5281/zenodo.21308764 (MIT licence) [V]. [KAYNAK BULUNACAK: if the full TRAK-AI decision-support system
code (ETL, edge firmware, fog services, dashboard) is released as a separate repository/archive, add its
URL and DOI here — REPO DOI PENDING.]

## Declaration of generative AI and AI-assisted technologies in the manuscript preparation process

During the preparation of this work the author(s) used [NAME OF TOOL] in order to draft and copy-edit
manuscript text and to organise verified numerical results into tables. After using this tool, the
author(s) reviewed and edited the content as needed and take(s) full responsibility for the content of the
publication. [N: confirm whether to include and which tool(s) to name; delete if not applicable.]

## Acknowledgements

This work was carried out within a TÜBİTAK 2209-A University Students Research Projects support programme
[DEĞER DOĞRULANACAK: application/grant number and support period]. Climate data were obtained from the
NASA Langley Research Center (LaRC) POWER Project funded through the NASA Earth Science/Applied Science
Program. This work contains modified Copernicus Sentinel and ERA5-Land data. The authors acknowledge ESA,
NASA, ISRIC and TÜİK as data providers.

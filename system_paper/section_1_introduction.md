<!--
============================================================================
SECTION 1 — INTRODUCTION  (deliverable 3 of the body)
TRAK-AI DSS system paper. English manuscript text.
Citation placeholders are author-date with tags [V]/[P]/[N]/[D]; renumber to
Elsevier [n] at assembly once the reference list is finalised. A 3-sentence
SAT-framing variant of the opening is provided at the end for the fallback venue.
============================================================================
-->

# 1. Introduction

Satellite- and sensor-driven modelling of crop yield and crop condition has expanded rapidly, and
machine-learning models are now routinely reported with strong predictive accuracy across cereals and
oilseeds [P; van Klompenburg et al., 2020]. Yet the operational value of such models for a farmer or an
extension service depends less on their headline cross-validated accuracy than on two properties that are
often left implicit: whether the accuracy reflects genuine *forward* (out-of-year) skill rather than
spatial interpolation between neighbouring fields in the same season, and whether the system that delivers
the prediction can run where and when it is needed — in the field, on modest hardware, without a reliable
network connection. In the plains of Trakya (the European part of Türkiye), a principal wheat- and
sunflower-growing region of largely smallholder farms, both properties are binding constraints: cloud
connectivity is intermittent, per-farm budgets are small, and the users are non-specialist producers who
need an actionable answer in Turkish rather than a probability surface.

Two gaps motivate this work. First, a **validation gap**: spatial or random cross-validation lets a model
exploit structure shared between training and test locations within the same year, inflating apparent
skill relative to the leave-one-year-out setting that actually matters for forecasting [P; Roberts et al.,
2017; Ploton et al., 2020]. A companion methods paper audits this effect for the present region and crops
and shows, under matched temporal and spatial cross-validation, a large and significant
spatial-minus-temporal generalization gap, and that for winter wheat no machine-learning configuration
beats a simple climatology baseline out-of-year, whereas a multimodal model does add skill for sunflower
[V-status; Kalkan and Çavdaroğlu, 2026b, under review]. The practical implication — that a decision-support
system should not present cross-validated accuracy as operational skill, and should defer to transparent
statistical baselines where machine learning does not demonstrably beat them — has, to our knowledge, not
been embedded in the design of a deployed agricultural decision-support system. Second, a **deployment
gap**: many precision-agriculture decision-support systems assume continuous cloud connectivity and
server-side inference, which is a poor fit for low-connectivity smallholder settings and concentrates both
cost and failure risk off-farm.

This paper presents TRAK-AI, an offline-first Edge–Fog–Cloud decision-support system for winter wheat and
sunflower in Trakya that addresses both gaps. Its contributions are:

1. an **offline-first Edge–Fog–Cloud integration** in which a low-cost ESP32 field rover acquires in-situ
   data, a laptop-class fog tier performs all inference, retrieval and generation locally, and the cloud
   tier is used only for cache-backed acquisition of Earth-observation and reanalysis inputs — so the full
   decision loop runs without a network once inputs are cached;
2. an **honesty-aware advisory design** that operationalises the "cross-validated accuracy ≠ operational
   skill" finding: the yield component defaults to a climatology baseline for winter wheat, surfaces
   machine-learning estimates with prediction intervals and an explicit forward-skill caveat, and reports
   a forward-validation result in which a naïve persistence baseline is not beaten;
3. a **Turkish-language, offline retrieval-augmented advisory** combining hybrid dense/sparse retrieval
   over an agronomic corpus with a locally hosted large language model, producing actionable advice on
   CPU-only hardware;
4. a **human-in-the-loop, offline-first data plane** (MQTT orchestration with an approval queue and a
   local SQLite store) that keeps a person in control of the data of record; and
5. a **transparent evaluation** — including the disclosure of prototype and placeholder components — that
   treats honesty about component maturity as part of the contribution rather than a footnote.

The remainder of the paper describes the system design (Section 2), evaluates it at component and
end-to-end level including a field reconnaissance and an explicit transparency assessment (Section 3),
discusses design lessons and limitations (Section 4), and concludes (Section 5).

<!--
--------------------------------------------------------------------------
SAT-framing variant of the opening paragraph (use if submitting to Smart
Agricultural Technology instead of CEA; lower novelty bar, applied emphasis):

"Low-cost sensors, open Earth-observation data and small local language models now make it feasible to
assemble farm-scale decision-support systems from largely off-the-shelf parts. The engineering challenge
in low-connectivity smallholder regions such as Trakya (Türkiye) is not any single component but their
robust, offline-first integration and their honest presentation to non-specialist users. This paper
reports the design, deployment and field evaluation of TRAK-AI, an integrated Edge–Fog–Cloud
decision-support system for winter wheat and sunflower that runs its full inference-retrieval-advisory
loop on CPU-only hardware without a network connection."
--------------------------------------------------------------------------
-->

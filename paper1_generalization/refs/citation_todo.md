# Citation TODO — human verification required

> ZERO fabricated references/DOIs were produced. `references.bib` holds only
> well-known real anchor works, each marked `note={VERIFY ...}`. Every place in
> the manuscript that needs a citation but is not yet backed by a verified source
> is marked `[VERIFY: needs citation]`. This file lists everything to resolve.

## A. Verify bibliographic details of every `references.bib` entry
For each entry confirm exact authors, year, volume, issue, pages, and DOI from the
publisher/Crossref. Do NOT trust the skeleton's volume guesses. Highest priority
(load-bearing for the argument):
- [ ] `roberts2017crossval` — Ecography, block CV (frames the CV design).
- [ ] `ploton2020spatial` — Nat. Commun., spatial-CV optimism (frames the gap).
- [ ] `meyer2021aoa` — area of applicability (extrapolation framing).
- [ ] `kattenborn2022spatial` — spatial autocorrelation leakage (confirm exact title/venue).
- [ ] `vanklompenburg2020review` — CEA review (target-journal anchor).
- [ ] `bolton2013forecasting` — NDVI+phenology yield forecasting.
- [ ] `schwalbert2020soybean` — confirm full author list (currently abbreviated).

## B. Claims in the manuscript needing a citation (`[VERIFY: needs citation]`)
- [ ] Reported ML-yield-prediction R² values in the literature are often obtained
      under random k-fold CV (optimistic) rather than year-blocked CV. → needs a
      concrete supporting citation (candidate: roberts2017crossval, ploton2020spatial).
- [ ] NDVI saturates / loses information during senescence (grain-fill, maturity)
      for sunflower and cereals. → needs a phenology/remote-sensing citation.
- [ ] Winter wheat yield in semi-arid Mediterranean/Trakya climates is strongly
      governed by grain-fill-period precipitation and inter-annual climate
      variability. → needs an agronomy citation.
- [ ] Sunflower flowering-period canopy state (NDVI) is a strong yield predictor.
      → needs an agronomy/RS citation.
- [ ] Climatology / persistence as the standard skill benchmark in operational
      forecasting. → candidate: hyndman2006another (+ a forecasting-verification ref).
- [ ] TÜİK district-level (ilçe) crop-yield statistics — official data-source citation.
- [ ] Trakya region description (area, climate, cropping system) — regional citation.

## C. Anchor sources still MISSING from the skeleton (add real entries, no invention)
- [ ] Official TÜİK yield-statistics reference/URL.
- [ ] Köppen–Geiger or regional climate classification for Trakya (optional).
- [ ] A study explicitly contrasting temporal vs spatial extrapolation in crop-yield
      ML, if one exists (strengthens novelty positioning) — search before claiming none.

## D. Self-citation / project provenance
- [ ] The underlying thesis (Kalkan, 2026, TRAK-AI DSS) — cite as data/methods source.
- [ ] TÜBİTAK 2209-A program acknowledgement (grant id if available).

"""ÇP-2.5 — Sezonluk NDVI + iklim öznitelikleri üretici.

Girdi
-----
* ``data/processed/master_feature_matrix_2017_2024.csv``
  ÇP-1 ETL çıktısı; 2017-2024 günlük, tek konum (Vize / Kırklareli).
* ``data/external/tuik/tuik_trakya_yields_clean.csv``
  22 yıllık TÜİK verim hedefi (kg/dekar), 3 il × 2 ürün × 22 yıl.

Çıktı
-----
* ``data/processed/calibration_train_set_bugday.csv``      (n=21)
* ``data/processed/calibration_train_set_aycicegi.csv``    (n=24)
* ``data/processed/calibration_holdout_2025.csv``          (n=6  → 2025 test)

Akademik notlar
---------------
* MFM **tek bir merkez nokta** (Vize, 41.045 N / 27.205 E — Kırklareli ilçesi)
  için günlük zaman serisi. 3 il (Edirne, Kırklareli, Tekirdağ) hepsi aynı
  feature'ları paylaşır → MFM 3 il'e replike edilir ve ``il`` kategorik
  feature olarak modele girer.  Bu yapay olarak il-içi varyansı sıfırlar
  ama il-arası **sistematik ofset**i kategorik dummy üzerinden öğrenir.
  Sınırlama tezde açıkça raporlanır (centroid-proxy approximation).
* Buğday 2017 dışlanır: kışlık ekim 1 Ekim 2016'da başlar, MFM ise
  2017-01-01'den başlar — sezonun ilk 3 ayı eksik.
* 2025 yılı **hold-out** olarak ayrılır (true forecast test); MFM yok,
  bu yıl ETL backfill edildiğinde aktive edilir.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("trakai.cp25.build")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MFM_PATH    = PROJECT_ROOT / "data" / "processed" / "master_feature_matrix_2017_2024.csv"
YIELDS_PATH = PROJECT_ROOT / "data" / "external"  / "tuik" / "tuik_trakya_yields_clean.csv"
OUT_DIR     = PROJECT_ROOT / "data" / "processed"

# GDD (Growing Degree Days) base temperatures (°C). Source: FAO AquaCrop +
# Trakya field studies (Ozer 2003; Kaya 2017).
GDD_BASE = {"bugday": 0.0, "aycicegi_yaglik": 8.0}

# NDVI greenness threshold (Kogan 1990; widely used)
GREENNESS_THRESHOLD = 0.6


@dataclass(frozen=True)
class SeasonWindow:
    """Phenological season window (closed dates).

    ``year_offset`` is the offset applied to the FAO ``season_start`` year
    relative to the *harvest* year.  Winter-sown wheat: start = previous
    Oct → harvest = current July ⇒ ``year_offset = -1``.
    Summer-sown sunflower: start = current April ⇒ ``year_offset = 0``.
    """
    name: str
    season_start_md: tuple[int, int]
    season_end_md:   tuple[int, int]
    flowering_md:    tuple[tuple[int, int], tuple[int, int]]
    grain_fill_md:   tuple[tuple[int, int], tuple[int, int]]
    year_offset:     int


SEASON_WINDOWS: dict[str, SeasonWindow] = {
    "bugday": SeasonWindow(
        name="Buğday (kışlık)",
        season_start_md=(10, 1),
        season_end_md=(7, 15),
        flowering_md=((5, 1), (5, 31)),
        grain_fill_md=((6, 1), (6, 30)),
        year_offset=-1,
    ),
    "aycicegi_yaglik": SeasonWindow(
        name="Ayçiçeği (yağlık)",
        season_start_md=(4, 1),
        season_end_md=(9, 30),
        flowering_md=((7, 1), (7, 31)),
        grain_fill_md=((8, 1), (8, 31)),
        year_offset=0,
    ),
}


# ----------------------------------------------------------------------------
def _slice(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Return rows in [start, end] (inclusive both sides), sorted by date."""
    m = (df["date"] >= start) & (df["date"] <= end)
    return df.loc[m].sort_values("date")


def _safe_nan(x: float | None) -> float:
    return float("nan") if x is None else float(x)


def extract_seasonal_features(mfm: pd.DataFrame,
                              year: int,
                              window: SeasonWindow,
                              crop: str) -> Optional[dict]:
    """Compute 10 seasonal features for a given (year, crop) from MFM.

    Returns ``None`` if the season window falls outside the MFM coverage
    (e.g. wheat 2017 → needs Oct 2016, not present).
    """
    start = pd.Timestamp(year + window.year_offset, *window.season_start_md)
    end   = pd.Timestamp(year, *window.season_end_md)
    if start < mfm["date"].min() or end > mfm["date"].max():
        logger.debug("skip %s %d: window %s..%s outside MFM",
                     crop, year, start.date(), end.date())
        return None

    g = _slice(mfm, start, end)
    if len(g) < 30:
        logger.warning("skip %s %d: only %d rows in window", crop, year, len(g))
        return None

    # NDVI series — prefer gap-filled NDVI_int (no missing) over raw NDVI.
    ndvi = g["NDVI_int"].astype(float).values

    # Sub-windows (flowering and grain-fill always within current year)
    fl_start = pd.Timestamp(year, *window.flowering_md[0])
    fl_end   = pd.Timestamp(year, *window.flowering_md[1])
    gf_start = pd.Timestamp(year, *window.grain_fill_md[0])
    gf_end   = pd.Timestamp(year, *window.grain_fill_md[1])

    fl_slice = _slice(g, fl_start, fl_end)
    gf_slice = _slice(g, gf_start, gf_end)

    # ---- Climate features (over full season) ----
    gdd_base = GDD_BASE[crop]
    daily_gdd = (g["t2m_max"] + g["t2m_min"]) / 2.0 - gdd_base
    daily_gdd = daily_gdd.clip(lower=0.0)
    gdd_total = float(daily_gdd.sum())

    tp_total = float(g["tp_sum"].sum())

    # NDWI minimum during flowering (water-stress proxy)
    ndwi_min_flowering = (float(fl_slice["NDWI_int"].min())
                          if not fl_slice.empty else float("nan"))

    # Max-temperature mean during flowering (heat-stress proxy)
    t2m_max_fl = (float(fl_slice["t2m_max"].mean())
                  if not fl_slice.empty else float("nan"))

    return {
        "year":              year,
        "crop":              crop,
        # NDVI shape descriptors
        "ndvi_max":          float(np.nanmax(ndvi)),
        "ndvi_mean":         float(np.nanmean(ndvi)),
        "ndvi_integral":     float(np.nansum(ndvi)),
        "ndvi_flowering":    (float(fl_slice["NDVI_int"].mean())
                              if not fl_slice.empty else float("nan")),
        "ndvi_grain_fill":   (float(gf_slice["NDVI_int"].mean())
                              if not gf_slice.empty else float("nan")),
        "greenness_days":    int((ndvi > GREENNESS_THRESHOLD).sum()),
        # Climate features
        "gdd_cum_season":    gdd_total,
        "tp_season_sum":     tp_total,
        "ndwi_min_flowering":ndwi_min_flowering,
        "t2m_max_flowering_mean": t2m_max_fl,
        # Provenance
        "season_start":      str(start.date()),
        "season_end":        str(end.date()),
        "n_days_in_window":  int(len(g)),
    }


# ----------------------------------------------------------------------------
def build_for_crop(mfm: pd.DataFrame,
                   yields: pd.DataFrame,
                   crop: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build training set + 2025 hold-out for a single crop.

    Replicates the centroid features across the 3 provinces and joins with
    the per-province TÜİK label.
    """
    window = SEASON_WINDOWS[crop]
    y_sub = yields[yields["crop"] == crop].copy()
    iller = sorted(y_sub["il"].unique())

    # Years where the season window is fully inside MFM
    full_train_years: list[int] = []
    skipped: list[int] = []
    for y in sorted(y_sub["year"].unique()):
        start = pd.Timestamp(y + window.year_offset, *window.season_start_md)
        end   = pd.Timestamp(y, *window.season_end_md)
        if start >= mfm["date"].min() and end <= mfm["date"].max():
            full_train_years.append(int(y))
        else:
            skipped.append(int(y))
    logger.info("%s: in-MFM years = %s; skipped = %s",
                crop, full_train_years, skipped)

    train_rows: list[dict] = []
    holdout_rows: list[dict] = []
    for year in sorted(y_sub["year"].unique()):
        feats = extract_seasonal_features(mfm, year, window, crop)
        for il in iller:
            label_row = y_sub[(y_sub["year"] == year) & (y_sub["il"] == il)]
            if label_row.empty:
                continue
            yld = float(label_row["verim_kg_da"].iloc[0])
            if feats is None:
                # 2025 (or pre-MFM): no features, hold out for future test
                if year == 2025:
                    holdout_rows.append({
                        "il": il, "year": year, "crop": crop,
                        "yield_kg_da": yld, "has_features": False,
                    })
                continue
            row = dict(feats)
            row.update({"il": il, "yield_kg_da": yld, "has_features": True})
            train_rows.append(row)

    train_df   = pd.DataFrame(train_rows)
    holdout_df = pd.DataFrame(holdout_rows)
    logger.info("%s: train rows = %d, holdout rows = %d",
                crop, len(train_df), len(holdout_df))
    return train_df, holdout_df


# ----------------------------------------------------------------------------
def main() -> None:
    logger.info("loading MFM=%s yields=%s", MFM_PATH, YIELDS_PATH)
    mfm = pd.read_csv(MFM_PATH, parse_dates=["date"])
    yld = pd.read_csv(YIELDS_PATH)
    logger.info("MFM range %s..%s (%d rows); TÜİK range %d..%d (%d rows)",
                mfm["date"].min().date(), mfm["date"].max().date(), len(mfm),
                yld["year"].min(), yld["year"].max(), len(yld))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for crop in SEASON_WINDOWS:
        tr, ho = build_for_crop(mfm, yld, crop)
        crop_short = "bugday" if crop == "bugday" else "aycicegi"
        tr.to_csv(OUT_DIR / f"calibration_train_set_{crop_short}.csv", index=False)
        if not ho.empty:
            ho.to_csv(OUT_DIR / f"calibration_holdout_{crop_short}.csv", index=False)
        logger.info("%s: wrote %d train + %d holdout rows", crop_short, len(tr), len(ho))


if __name__ == "__main__":
    main()

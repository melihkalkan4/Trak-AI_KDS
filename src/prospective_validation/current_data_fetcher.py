"""
Top-level prospective-data orchestrator.

This is the single import surface other phases (predictor, validator,
alerts) should depend on.  It re-exports :func:`build_unified_features`
plus a small convenience class that bundles common parameters.

The orchestrator does NOT mutate any frozen artefact and writes only to
``data/prospective/<year>/``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

from . import config
from .feature_builder import build_unified_features
from .logging_setup import logger


@dataclass
class CurrentDataFetcher:
    """Light wrapper for repeated calls against the same date range."""
    start_date: date
    end_date: Optional[date] = None       # default = today
    force_refresh: bool = False
    save: bool = True

    def __post_init__(self) -> None:
        if self.end_date is None:
            self.end_date = datetime.now(timezone.utc).date()
        if self.end_date < self.start_date:
            raise ValueError("end_date precedes start_date")

    def fetch(self, site: config.Site) -> pd.DataFrame:
        return build_unified_features(
            site=site,
            start_date=self.start_date,
            end_date=self.end_date,
            force_refresh=self.force_refresh,
            save=self.save,
        )

    def fetch_many(self, sites=config.EVRENLI_SITES) -> dict[str, pd.DataFrame]:
        out: dict[str, pd.DataFrame] = {}
        for s in sites:
            logger.info("[orchestrator] === site {} ===", s.id)
            try:
                out[s.id] = self.fetch(s)
            except Exception as e:                # noqa: BLE001
                logger.exception("[orchestrator] site {} failed: {}", s.id, e)
                out[s.id] = pd.DataFrame()
        return out


__all__ = ["CurrentDataFetcher", "build_unified_features"]

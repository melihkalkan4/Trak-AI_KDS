"""
FLOV alert engine.

Inputs
------
    predictions_df : output of FrozenPredictor.predict_ndvi_series
                     (needs target_date, predicted_ndvi,
                      anomaly_vs_climatology, climatology_ndvi)
    site           : config.Site

Outputs
-------
    list[Alert]                       (sorted by target_date, severity desc)
    Alert.to_dict()                   → JSONL-ready
    persist_alerts(alerts)            → appends to logs/alerts.jsonl
    summarize(alerts) -> dict         → counts per severity (for dashboard badge)

Severity logic
--------------
The rule is anomaly-magnitude × phenology-criticality:

    base_severity from |anomaly_vs_climatology|:
        |a| >= 0.20  ⇒ CRITICAL
        |a| >= 0.10  ⇒ WARN
        |a| >= 0.05  ⇒ INFO
        else         ⇒ no alert

    stage_uplift: during flowering/grain_fill, escalate by 1 level
                  (e.g. WARN → CRITICAL) because yield sensitivity is highest

Messages are written for the smallholder farmer (Turkish primary, English
secondary).  Action hints reference the agro calendar conventions used
elsewhere in the project.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from . import config
from .logging_setup import logger


SEVERITY_ORDER = {"info": 0, "warn": 1, "critical": 2}
_STAGE_UPLIFT = {"flowering", "grain_fill"}

ANOM_INFO     = 0.05
ANOM_WARN     = 0.10
ANOM_CRITICAL = 0.20


@dataclass
class Alert:
    site_id: str
    target_date: str             # ISO YYYY-MM-DD
    severity: str                # info | warn | critical
    stage: str                   # sunflower phenology stage
    direction: str               # "below" | "above"
    predicted_ndvi: float
    climatology_ndvi: float
    anomaly: float               # predicted - climatology
    message_tr: str
    message_en: str
    action_tr: str
    action_en: str
    issued_utc: str = field(default_factory=lambda:
                            datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


def _severity_from_anomaly(anom_abs: float) -> Optional[str]:
    if anom_abs >= ANOM_CRITICAL:
        return "critical"
    if anom_abs >= ANOM_WARN:
        return "warn"
    if anom_abs >= ANOM_INFO:
        return "info"
    return None


def _escalate(sev: str) -> str:
    if sev == "info":
        return "warn"
    if sev == "warn":
        return "critical"
    return sev


def _messages(
    stage: str, direction: str, anom: float, pred: float, clim: float,
    target_date: str,
) -> tuple[str, str, str, str]:
    """Return (message_tr, message_en, action_tr, action_en)."""
    sign_tr = "altinda" if direction == "below" else "ustunde"
    sign_en = "below" if direction == "below" else "above"

    msg_tr = (
        f"{target_date} icin tahmini NDVI {pred:.2f}; "
        f"{stage} doneminin tarihsel ortalamasi {clim:.2f}, "
        f"yaklasik {abs(anom):.2f} {sign_tr}."
    )
    msg_en = (
        f"Forecast NDVI for {target_date} is {pred:.2f}; "
        f"historical mean for {stage} is {clim:.2f}, "
        f"about {abs(anom):.2f} {sign_en}."
    )

    if direction == "below":
        if stage in {"vegetative", "flowering", "grain_fill"}:
            action_tr = ("Bitki gelisimi normalin altinda gorunuyor. "
                         "Toprak nemini ve son sulama gecmisini kontrol "
                         "edin; gerekirse sulama planini one cekin.")
            action_en = ("Vegetation looks weaker than expected — check "
                         "soil moisture and last irrigation; consider "
                         "advancing the irrigation schedule.")
        elif stage == "emergence":
            action_tr = ("Cikis dusuk; ekim derinligi/tohum kalitesi ve "
                         "kabuk bagi ihtimalini gozden gecirin.")
            action_en = ("Weak emergence — review seeding depth, seed "
                         "quality, and soil crusting risk.")
        elif stage == "maturity":
            action_tr = ("Olgunlasma normalin altinda; hasat takvimini "
                         "verim haritasiyla birlikte yeniden gozden gecirin.")
            action_en = ("Below-normal maturity — re-check harvest "
                         "timeline against yield forecast.")
        else:
            action_tr = ("Tarihsel ortalamanin altinda bir egilim var; "
                         "sahada gozlem yapmaniz onerilir.")
            action_en = ("Below-baseline trend — consider a field visit.")
    else:  # above
        if stage in {"flowering", "grain_fill"}:
            action_tr = ("Bitki gelisimi tarihsel ortalamanin uzerinde; "
                         "verim potansiyeli iyi gorunuyor. Hastalik/yatma "
                         "icin gozlem yapin.")
            action_en = ("Vegetation above historical — yield potential "
                         "looks good. Scout for disease/lodging.")
        else:
            action_tr = ("Tarihsel ortalamanin uzerinde; bilgi amaclidir, "
                         "ek aksiyon gerekmiyor.")
            action_en = ("Above-baseline — informational only.")
    return msg_tr, msg_en, action_tr, action_en


def evaluate(
    predictions: pd.DataFrame,
    *,
    site: config.Site,
) -> list[Alert]:
    """
    Generate alerts for every prediction row that crosses a threshold.

    Required columns:
        target_date, predicted_ndvi, climatology_ndvi, anomaly_vs_climatology
    """
    required = {"target_date", "predicted_ndvi",
                "climatology_ndvi", "anomaly_vs_climatology"}
    missing = required - set(predictions.columns)
    if missing:
        raise ValueError(f"alerts.evaluate: predictions missing cols {missing}")

    if predictions.empty:
        return []

    df = predictions.copy()
    df["target_date"] = pd.to_datetime(df["target_date"])
    df = df.dropna(subset=["anomaly_vs_climatology"])

    alerts: list[Alert] = []
    for _, row in df.iterrows():
        anom = float(row["anomaly_vs_climatology"])
        sev = _severity_from_anomaly(abs(anom))
        if sev is None:
            continue
        doy = int(row["target_date"].dayofyear)
        stage = config.stage_for_doy(doy)
        if stage in _STAGE_UPLIFT and abs(anom) >= ANOM_WARN:
            sev = _escalate(sev)

        direction = "below" if anom < 0 else "above"
        target_iso = row["target_date"].date().isoformat()
        pred = float(row["predicted_ndvi"])
        clim = float(row["climatology_ndvi"])
        msg_tr, msg_en, act_tr, act_en = _messages(
            stage, direction, anom, pred, clim, target_iso,
        )
        alerts.append(Alert(
            site_id=site.id,
            target_date=target_iso,
            severity=sev,
            stage=stage,
            direction=direction,
            predicted_ndvi=pred,
            climatology_ndvi=clim,
            anomaly=anom,
            message_tr=msg_tr,
            message_en=msg_en,
            action_tr=act_tr,
            action_en=act_en,
        ))

    alerts.sort(key=lambda a: (a.target_date, -SEVERITY_ORDER[a.severity]))
    logger.info("[alerts] {}: generated {} alerts ({} critical, {} warn, {} info)",
                site.id, len(alerts),
                sum(a.severity == "critical" for a in alerts),
                sum(a.severity == "warn"     for a in alerts),
                sum(a.severity == "info"     for a in alerts))
    return alerts


def summarize(alerts: list[Alert]) -> dict[str, int]:
    out = {"total": len(alerts), "critical": 0, "warn": 0, "info": 0}
    for a in alerts:
        out[a.severity] = out.get(a.severity, 0) + 1
    return out


def to_dataframe(alerts: list[Alert]) -> pd.DataFrame:
    if not alerts:
        return pd.DataFrame(columns=[
            "site_id", "target_date", "severity", "stage", "direction",
            "predicted_ndvi", "climatology_ndvi", "anomaly",
            "message_tr", "action_tr",
        ])
    df = pd.DataFrame([a.to_dict() for a in alerts])
    return df


ALERTS_LOG: Path = config.LOGS_DIR / "alerts.jsonl"


def persist(alerts: list[Alert], *, path: Path = ALERTS_LOG) -> Path:
    """Append-only JSONL.  Caller owns deduping if it cares about idempotency."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for a in alerts:
            fh.write(json.dumps(a.to_dict(), ensure_ascii=False) + "\n")
    logger.info("[alerts] persisted {} alerts -> {}", len(alerts), path)
    return path


__all__ = [
    "Alert", "evaluate", "summarize", "to_dataframe", "persist",
    "ALERTS_LOG", "ANOM_INFO", "ANOM_WARN", "ANOM_CRITICAL",
]

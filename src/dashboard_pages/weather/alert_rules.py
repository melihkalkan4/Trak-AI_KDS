"""Weather alert rules — stage-aware thresholds for Trakya sunflower/wheat.

Rules are intentionally conservative; refinements live in
`docs/MULTIMODAL_VALIDATION_METHODOLOGY.md`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass
class WeatherAlert:
    severity: str           # "INFO" | "WARNING" | "CRITICAL"
    code: str               # short rule id
    message_tr: str
    message_en: str
    date: str               # YYYY-MM-DD

    def as_dict(self) -> dict:
        return {
            "severity": self.severity, "code": self.code,
            "message_tr": self.message_tr, "message_en": self.message_en,
            "date": self.date,
        }


def evaluate_forecast(daily: dict) -> list[WeatherAlert]:
    """Apply rules to an Open-Meteo `daily` dict and return alerts."""
    if not daily:
        return []
    dates = daily.get("time") or []
    tmax = daily.get("temperature_2m_max") or []
    tmin = daily.get("temperature_2m_min") or []
    psum = daily.get("precipitation_sum") or []
    wmax = daily.get("wind_speed_10m_max") or []

    alerts: list[WeatherAlert] = []
    for i, d in enumerate(dates):
        if i < len(tmin) and tmin[i] is not None and tmin[i] <= 0:
            alerts.append(WeatherAlert(
                "CRITICAL", "FROST",
                f"Don riski: min {tmin[i]:.1f}°C",
                f"Frost risk: min {tmin[i]:.1f}°C",
                d,
            ))
        if i < len(tmax) and tmax[i] is not None and tmax[i] >= 35:
            alerts.append(WeatherAlert(
                "WARNING", "HEAT",
                f"Sicak stres: max {tmax[i]:.1f}°C",
                f"Heat stress: max {tmax[i]:.1f}°C",
                d,
            ))
        if i < len(psum) and psum[i] is not None and psum[i] >= 30:
            alerts.append(WeatherAlert(
                "WARNING", "HEAVY_RAIN",
                f"Siddetli yagis: {psum[i]:.0f} mm",
                f"Heavy rainfall: {psum[i]:.0f} mm",
                d,
            ))
        if i < len(wmax) and wmax[i] is not None and wmax[i] >= 60:
            alerts.append(WeatherAlert(
                "WARNING", "HIGH_WIND",
                f"Kuvvetli ruzgar: {wmax[i]:.0f} km/s",
                f"High wind: {wmax[i]:.0f} km/h",
                d,
            ))
    return alerts


def summarize(alerts: Iterable[WeatherAlert]) -> dict:
    out = {"total": 0, "CRITICAL": 0, "WARNING": 0, "INFO": 0}
    for a in alerts:
        out["total"] += 1
        out[a.severity] = out.get(a.severity, 0) + 1
    return out


__all__ = ["WeatherAlert", "evaluate_forecast", "summarize"]

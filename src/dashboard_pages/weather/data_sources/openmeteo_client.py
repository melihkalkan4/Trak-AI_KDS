"""Open-Meteo API client — free, no signup, 7-day forecast + current.

Endpoints used:
    * https://api.open-meteo.com/v1/forecast       (current + daily)
"""
from __future__ import annotations

import logging
from typing import Optional

import requests


logger = logging.getLogger("trakai.weather.openmeteo")

_BASE = "https://api.open-meteo.com/v1/forecast"
_TIMEOUT = 8.0


def fetch_forecast(lat: float, lon: float,
                   days: int = 7,
                   timezone: str = "auto") -> Optional[dict]:
    """Return Open-Meteo current + daily forecast for `days` days, or None."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": ",".join([
            "temperature_2m", "relative_humidity_2m",
            "precipitation", "wind_speed_10m", "wind_direction_10m",
            "weather_code", "soil_moisture_0_to_1cm",
        ]),
        "daily": ",".join([
            "temperature_2m_max", "temperature_2m_min",
            "precipitation_sum", "wind_speed_10m_max",
            "weather_code", "uv_index_max",
        ]),
        "forecast_days": int(days),
        "timezone": timezone,
    }
    try:
        r = requests.get(_BASE, params=params, timeout=_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as exc:                                        # noqa: BLE001
        logger.warning("Open-Meteo fetch failed: %s", exc)
        return None


__all__ = ["fetch_forecast"]

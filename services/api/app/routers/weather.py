"""Weather for the dashboard home: current conditions, yesterday and the next days (Open-Meteo).

GET /api/v1/weather?lat=..&lon=.. returns one normalised shape, so the web app never parses
Open-Meteo itself. Results are kept 10 minutes per ~1 km cell, so a refresh does not call it again.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import requests
from fastapi import APIRouter, Depends, HTTPException, Query

router = APIRouter(prefix="/api/v1/weather", tags=["weather"])

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
CACHE_SECONDS = 600
USER_AGENT = "FARMLINK-API/0.1 (weather)"

Fetcher = Callable[[float, float], dict[str, Any]]


def open_meteo(lat: float, lon: float) -> dict[str, Any]:
    """Raw Open-Meteo forecast: current values, yesterday (past_days=1) and 6 days ahead."""
    params: dict[str, str | float] = {
        "latitude": lat,
        "longitude": lon,
        "timezone": "auto",
        "past_days": 1,
        "forecast_days": 6,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
        "shortwave_radiation_sum,precipitation_sum",
    }
    response = requests.get(
        OPEN_METEO_URL, params=params, timeout=15, headers={"User-Agent": USER_AGENT}
    )
    response.raise_for_status()
    data: dict[str, Any] = response.json()
    return data


def get_fetcher() -> Fetcher:
    return open_meteo


def condition(code: int | None) -> str:
    """WMO weather code -> one word the web app translates."""
    if code is None:
        return "unknown"
    if code == 0:
        return "clear"
    if code <= 2:
        return "partly"
    if code == 3:
        return "cloudy"
    if code <= 48:
        return "fog"
    if code <= 57:
        return "drizzle"
    if code <= 67 or 80 <= code <= 82:
        return "rain"
    if code <= 77 or code in (85, 86):
        return "snow"
    return "storm"


def normalise(raw: dict[str, Any], lat: float, lon: float) -> dict[str, Any]:
    cur = raw.get("current") or {}
    d = raw.get("daily") or {}
    dates: list[str] = d.get("time") or []

    def col(name: str, i: int) -> float | None:
        values = d.get(name) or []
        return values[i] if i < len(values) else None

    days: list[dict[str, Any]] = []
    for i, day in enumerate(dates):
        rad = col("shortwave_radiation_sum", i)  # MJ/m²/day
        code = col("weather_code", i)
        days.append(
            {
                "date": day,
                "weather_code": code,
                "condition": condition(int(code) if code is not None else None),
                "tmax_c": col("temperature_2m_max", i),
                "tmin_c": col("temperature_2m_min", i),
                "rain_mm": col("precipitation_sum", i),
                "radiation_kwh_m2": round(rad / 3.6, 2) if rad is not None else None,
            }
        )
    today = (cur.get("time") or "")[:10]
    past = [x for x in days if today and x["date"] < today]
    future = [x for x in days if not today or x["date"] >= today]
    code = cur.get("weather_code")
    return {
        "location": {"lat": lat, "lon": lon},
        "source": "open_meteo",
        "fetched_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "current": {
            "time": cur.get("time"),
            "temperature_c": cur.get("temperature_2m"),
            "humidity_pct": cur.get("relative_humidity_2m"),
            "wind_kmh": cur.get("wind_speed_10m"),
            "weather_code": code,
            "condition": condition(int(code) if code is not None else None),
        },
        "yesterday": past[-1] if past else None,
        "days": future,  # today first, then the next days
    }


_cache: dict[tuple[float, float], tuple[float, dict[str, Any]]] = {}
_lock = threading.Lock()


@router.get("")
def weather(
    lat: float = Query(ge=-90, le=90),
    lon: float = Query(ge=-180, le=180),
    fetch: Fetcher = Depends(get_fetcher),
) -> dict[str, Any]:
    """Current weather, yesterday and the next days at a point (Open-Meteo, cached 10 minutes)."""
    key = (round(lat, 2), round(lon, 2))
    with _lock:
        hit = _cache.get(key)
        if hit and time.monotonic() - hit[0] < CACHE_SECONDS and fetch is open_meteo:
            return hit[1]
    try:
        result = normalise(fetch(key[0], key[1]), key[0], key[1])
    except (requests.RequestException, ValueError, KeyError) as exc:
        raise HTTPException(status_code=503, detail="Weather service unavailable") from exc
    with _lock:
        _cache[key] = (time.monotonic(), result)
    return result

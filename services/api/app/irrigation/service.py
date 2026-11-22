"""Typed wrapper around the FARMLINK irrigation engine: live weather + farm recommendation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.irrigation.engine import data_sources
from app.irrigation.engine.crop_retrieval import load_database
from app.irrigation.engine.farm_runner import run_farm

HISTORY_DAYS = 45
USER_AGENT = "FARMLINK-API/0.1 (irrigation)"


@dataclass(frozen=True)
class Weather:
    """Daily weather for the engine: past days up to today, and an optional forecast after today."""

    history: pd.DataFrame
    forecast: pd.DataFrame | None
    source: str
    fallback_used: bool


WeatherProvider = Callable[[float, float, date], Weather]


class WeatherUnavailableError(RuntimeError):
    """No weather source answered (Open-Meteo and NASA POWER both failed)."""


def _session() -> requests.Session:
    # Retries on server errors only. HTTP 429 is not retried and Retry-After is ignored: Open-Meteo
    # answers 429 "daily limit exceeded" with a Retry-After of hours, which would block the request.
    retry = Retry(
        total=2,
        connect=2,
        read=2,
        status=2,
        backoff_factor=0.5,
        allowed_methods=("GET",),
        status_forcelist=(500, 502, 503, 504),
        respect_retry_after_header=False,
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers["User-Agent"] = USER_AGENT
    return session


def fetch_live_weather(lat: float, lon: float, today: date) -> Weather:
    """Last 45 days from Open-Meteo (NASA POWER as recorded fallback), plus the forecast."""
    session = _session()
    start = today - timedelta(days=HISTORY_DAYS)
    try:
        history, prov = data_sources.fetch_weather(
            lat,
            lon,
            start.isoformat(),
            today.isoformat(),
            session,
            order=("open_meteo", "nasa_power"),
            allow_fallback=True,
        )
    except data_sources.DownloadError as exc:
        raise WeatherUnavailableError(str(exc)) from exc
    forecast: pd.DataFrame | None
    try:
        forecast, _ = data_sources.open_meteo_daily(
            lat, lon, today.isoformat(), today.isoformat(), session, forecast=True
        )
        forecast = forecast[pd.to_datetime(forecast["date"]).dt.date > today]
        if forecast.empty:
            forecast = None
    except (data_sources.DownloadError, ValueError, KeyError):
        forecast = None  # the engine then uses the current depletion only, and says so
    return Weather(history, forecast, str(prov["source_used"]), bool(prov["fallback_used"]))


def recommend_farm(
    farm: dict[str, Any], weather: Weather, today: date, available_water_m3: float | None
) -> dict[str, Any]:
    """Run the engine for every zone, rank the zones and split the available water."""
    result: dict[str, Any] = run_farm(
        farm,
        weather.history,
        today.isoformat(),
        weather.forecast,
        weather_source=weather.source,
        available_water_m3=available_water_m3,
    )
    return result


def list_crops() -> list[dict[str, Any]]:
    """Crops of the FAO-56 knowledge base, with French and Arabic names for the farmer's picker."""
    crops: list[dict[str, Any]] = []
    for crop in load_database()["crops"]:
        names = crop.get("names") or {}
        crops.append(
            {
                "id": crop["id"],
                "name_fr": names.get("fr") or crop["id"],
                "name_ar": names.get("ar"),
                "name_en": names.get("en"),
                "category": crop.get("category"),
                "perennial": bool(crop.get("perennial")),
                "irrigation_ready": bool(crop.get("irrigation_ready")),
            }
        )
    return crops

from collections.abc import AsyncIterator, Iterator
from datetime import date, timedelta
from typing import Any

import httpx
import numpy as np
import pandas as pd
import pytest

from app.irrigation import service
from app.irrigation.engine.farm_runner import run_farm
from app.main import app
from app.routers.irrigation import get_weather_provider

TODAY = date(2026, 11, 21)


def synthetic_weather(lat: float, lon: float, today: date) -> service.Weather:
    """Deterministic, labelled test weather (no network): mild late-autumn days, one rain day."""
    days = pd.date_range(today - timedelta(days=45), today, freq="D")
    n = len(days)
    tmax = 24 + 3 * np.sin(np.arange(n) / 5)
    tmin = tmax - 9
    history = pd.DataFrame(
        {
            "date": days,
            "tmin": tmin,
            "tmax": tmax,
            "tmean": (tmin + tmax) / 2,
            "rh_mean": 60.0,
            "u2": 2.2,
            "rs": 12.5,
            "rain_mm": [8.0 if i == 10 else 0.0 for i in range(n)],
        }
    )
    fdays = pd.date_range(today + timedelta(days=1), periods=7, freq="D")
    forecast = history.tail(7).copy()
    forecast["date"] = fdays
    return service.Weather(history, forecast, "test_weather", False)


def failing_weather(lat: float, lon: float, today: date) -> service.Weather:
    raise service.WeatherUnavailableError("all sources down")


DEMO_FARM: dict[str, Any] = {
    "farm_id": "demo",
    "location": {"lat": 35.918, "lon": 10.558, "elevation_m": 10},
    "available_water_m3": 1500,
    "on_date": TODAY.isoformat(),
    "zones": [
        {
            "zone_id": "Z1",
            "crop": "blé dur",
            "area_ha": 2.0,
            "planting_date": (TODAY - timedelta(days=20)).isoformat(),
            "soil": {"fc": 0.30, "wp": 0.15},
            "irrigation": {"method": "sprinkler"},
            "current_depletion_mm": 40,
        },
        {
            "zone_id": "Z2",
            "crop": "olive",
            "area_ha": 1.0,
            "stage_override": "mid_season",
            "soil": {"fc": 0.22, "wp": 0.10},
            "irrigation": {"method": "drip"},
            "current_depletion_mm": 118,
        },
        {
            "zone_id": "Z3",
            "crop": "tomato",
            "area_ha": 0.5,
            "stage_override": "mid_season",
            "soil": {"fc": 0.25, "wp": 0.11},
            "irrigation": {"method": "drip"},
            "last_refill_date": (TODAY - timedelta(days=10)).isoformat(),
        },
        {"zone_id": "Z4", "crop": "potato", "area_ha": 0.3, "stage_override": "development"},
    ],
}


@pytest.fixture
def weather_override() -> Iterator[None]:
    app.dependency_overrides[get_weather_provider] = lambda: synthetic_weather
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_crops_lists_the_fao56_knowledge_base(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/irrigation/crops")
    assert response.status_code == 200
    crops = {c["id"]: c for c in response.json()}
    assert len(crops) >= 37
    assert crops["tomato"]["name_fr"] == "Tomate"
    assert crops["durum_wheat"]["irrigation_ready"] is True


@pytest.mark.usefixtures("weather_override")
async def test_farm_recommendation_per_zone(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/v1/irrigation/farm", json=DEMO_FARM)
    assert response.status_code == 200
    body = response.json()
    zones = {z["zone_id"]: z for z in body["zones"]}
    assert zones["Z2"]["status"] == "OK"
    assert zones["Z2"]["timing"] == "irrigate_now"
    assert zones["Z2"]["volumes"]["m3"] > 0
    assert zones["Z3"]["depletion_source"] == "water_balance_from_refill_date"
    assert zones["Z4"]["status"] == "MISSING_SOIL_PARAMS"
    assert zones["Z4"]["volumes"] is None
    assert [r["zone_id"] for r in body["ranking"]][0] == "Z2"
    assert body["needs_data"][0]["zone_id"] == "Z4"
    assert body["allocation"]["available_m3"] == 1500
    assert body["allocation"]["allocated_m3"] <= 1500
    assert body["weather"] == {"source": "test_weather", "fallback_used": False, "forecast_days": 7}


@pytest.mark.usefixtures("weather_override")
async def test_api_returns_exactly_the_engine_result(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/v1/irrigation/farm", json=DEMO_FARM)
    weather = synthetic_weather(0, 0, TODAY)
    farm = {k: DEMO_FARM[k] for k in ("farm_id", "location", "zones")}
    expected = run_farm(
        farm,
        weather.history,
        TODAY.isoformat(),
        weather.forecast,
        weather_source=weather.source,
        available_water_m3=1500,
    )
    body = response.json()
    body.pop("weather")
    assert body == expected


async def test_unknown_crop_is_reported_not_guessed(
    client: httpx.AsyncClient, weather_override: None
) -> None:
    farm = {**DEMO_FARM, "zones": [{**DEMO_FARM["zones"][1], "crop": "banana-xyz"}]}
    response = await client.post("/api/v1/irrigation/farm", json=farm)
    assert response.status_code == 200
    assert response.json()["zones"][0]["status"] == "UNKNOWN_CROP"


async def test_weather_outage_returns_503(client: httpx.AsyncClient) -> None:
    app.dependency_overrides[get_weather_provider] = lambda: failing_weather
    try:
        response = await client.post("/api/v1/irrigation/farm", json=DEMO_FARM)
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 503


@pytest.mark.parametrize(
    "zone_change",
    [
        {"soil": {"fc": 0.10, "wp": 0.20}},
        {"area_ha": 0},
        {"current_depletion_mm": -5},
        {"stage_override": "flowering"},
        {"irrigation": {"method": "drip", "ea": 1.5}},
    ],
)
async def test_invalid_zone_is_rejected(
    client: httpx.AsyncClient, weather_override: None, zone_change: dict[str, Any]
) -> None:
    farm = {**DEMO_FARM, "zones": [{**DEMO_FARM["zones"][1], **zone_change}]}
    response = await client.post("/api/v1/irrigation/farm", json=farm)
    assert response.status_code == 422


async def test_duplicate_zone_ids_are_rejected(
    client: httpx.AsyncClient, weather_override: None
) -> None:
    farm = {**DEMO_FARM, "zones": [DEMO_FARM["zones"][1], DEMO_FARM["zones"][1]]}
    response = await client.post("/api/v1/irrigation/farm", json=farm)
    assert response.status_code == 422

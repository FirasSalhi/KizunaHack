"""GET /api/v1/weather: normalised Open-Meteo answer, no network (the fetcher is replaced)."""

from collections.abc import AsyncIterator, Iterator
from typing import Any

import httpx
import pytest
import requests

from app.main import app
from app.routers.weather import condition, get_fetcher

RAW: dict[str, Any] = {
    "current": {
        "time": "2026-11-22T10:00",
        "temperature_2m": 17.4,
        "relative_humidity_2m": 78,
        "wind_speed_10m": 12.2,
        "weather_code": 1,
    },
    "daily": {
        "time": ["2026-11-21", "2026-11-22", "2026-11-23"],
        "weather_code": [3, 1, 61],
        "temperature_2m_max": [20.1, 21.0, 18.5],
        "temperature_2m_min": [12.0, 13.2, 14.0],
        "shortwave_radiation_sum": [10.8, 12.6, 5.4],
        "precipitation_sum": [0.0, 0.0, 6.2],
    },
}


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


@pytest.fixture
def fake_weather() -> Iterator[list[tuple[float, float]]]:
    calls: list[tuple[float, float]] = []

    def fetch(lat: float, lon: float) -> dict[str, Any]:
        calls.append((lat, lon))
        return RAW

    app.dependency_overrides[get_fetcher] = lambda: fetch
    yield calls
    app.dependency_overrides.clear()


async def test_weather_is_normalised(
    client: httpx.AsyncClient, fake_weather: list[tuple[float, float]]
) -> None:
    r = await client.get("/api/v1/weather", params={"lat": 35.9183, "lon": 10.5584})
    assert r.status_code == 200
    body = r.json()
    assert fake_weather == [(35.92, 10.56)]
    assert body["current"]["temperature_c"] == 17.4 and body["current"]["condition"] == "partly"
    assert body["yesterday"]["date"] == "2026-11-21"
    assert [d["date"] for d in body["days"]] == ["2026-11-22", "2026-11-23"]
    assert body["days"][0]["radiation_kwh_m2"] == 3.5  # 12.6 MJ/m² / 3.6
    assert body["days"][1]["condition"] == "rain"


async def test_outage_returns_503(client: httpx.AsyncClient) -> None:
    def down(lat: float, lon: float) -> dict[str, Any]:
        raise requests.ConnectionError("no network")

    app.dependency_overrides[get_fetcher] = lambda: down
    try:
        r = await client.get("/api/v1/weather", params={"lat": 36.8, "lon": 10.2})
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 503


async def test_bad_coordinates_are_rejected(
    client: httpx.AsyncClient, fake_weather: list[tuple[float, float]]
) -> None:
    r = await client.get("/api/v1/weather", params={"lat": 120, "lon": 10})
    assert r.status_code == 422


def test_condition_codes() -> None:
    assert [condition(c) for c in (0, 2, 3, 45, 53, 63, 81, 71, 95, None)] == [
        "clear",
        "partly",
        "cloudy",
        "fog",
        "drizzle",
        "rain",
        "rain",
        "snow",
        "storm",
        "unknown",
    ]

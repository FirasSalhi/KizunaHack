"""Field-unit sensor feed (app/sensors/feed.py): payloads from firmware/README.md, no network."""

import json
from collections.abc import Iterator

import httpx
import pytest

from app.main import app
from app.sensors.feed import feed, light_pct, parse_reading

TOPIC = "farmlink/v2/kizunahack-field-unit-1/readings"
NOW = 1_763_800_100.0


def _payload(values: dict, status: str = "good", t: int = 1_763_800_000) -> bytes:
    """The exact shape the gateway publishes (README section 4)."""
    return json.dumps(
        {
            "v": 2,
            "sent_at": t,
            "samples": [{"t": t, "values": values}],
            "seq": 5,
            "field_status": status,
            "rssi": -58,
            "snr": 9.5,
        }
    ).encode()


@pytest.fixture(autouse=True)
def _empty_feed() -> Iterator[None]:
    feed.clear()
    yield
    feed.clear()


def test_readme_example_is_parsed() -> None:
    values = {
        "soil_raw": 1840,
        "light_raw": 3090,
        "soil_moisture": 45,
        "air_temp": 24.3,
        "air_humidity": 55.1,
    }
    [row] = parse_reading(TOPIC, _payload(values), NOW)
    assert row["device_id"] == "kizunahack-field-unit-1"
    assert row["soil_moisture"] == 45
    assert row["air_temp"] == 24.3
    assert row["air_humidity"] == 55.1
    assert row["light"] == light_pct(3090) == 25  # same scale as the field unit's OLED
    assert row["field_status"] == "good"
    assert row["ts"] == 1_763_800_000


def test_failed_sensors_stay_empty_instead_of_fake_values() -> None:
    # DHT22 failure: no air keys; soil fault: no soil_moisture (README section 4)
    [row] = parse_reading(TOPIC, _payload({"light_raw": 500}, status="sensor_fault"), NOW)
    assert row["air_temp"] is None and row["air_humidity"] is None
    assert row["soil_moisture"] is None
    assert row["field_status"] == "sensor_fault"


def test_out_of_range_values_are_dropped() -> None:
    values = {"soil_moisture": 250, "air_temp": -99, "air_humidity": "55", "light_raw": 9000}
    [row] = parse_reading(TOPIC, _payload(values, status="weird"), NOW)
    assert row["soil_moisture"] is None
    assert row["air_temp"] is None  # the old firmware's -99 error value
    assert row["air_humidity"] is None
    assert row["light"] is None
    assert row["field_status"] is None


def test_missing_clock_uses_receive_time() -> None:
    [row] = parse_reading(TOPIC, _payload({"soil_moisture": 40}, t=0), NOW)
    assert row["ts"] == NOW


def test_bad_topic_or_json_is_rejected() -> None:
    with pytest.raises(ValueError):
        parse_reading("farmlink/v2/x/other", _payload({}), NOW)
    with pytest.raises(ValueError):
        parse_reading(TOPIC, b"not json", NOW)


def test_unknown_devices_on_the_public_broker_are_ignored() -> None:
    [row] = parse_reading("farmlink/v2/someone-else/readings", _payload({"soil_moisture": 9}), NOW)
    feed.add(row)
    feed.set_gateway("someone-else", "online")
    assert feed.snapshot(NOW)["devices"] == []


def test_snapshot_has_latest_age_gateway_and_trend() -> None:
    for i, soil in enumerate([50, 48, 46]):
        t = 1_763_800_000 + i * 30
        feed.add(
            parse_reading(TOPIC, _payload({"soil_moisture": soil, "air_temp": 24.0}, t=t), NOW)[0]
        )
    feed.set_gateway("kizunahack-field-unit-1", "online")
    [dev] = feed.snapshot(NOW)["devices"]
    assert dev["gateway"] == "online"
    assert dev["latest"]["soil_moisture"] == 46
    assert dev["age_s"] == 40  # NOW - last sample (t = ...060)
    assert dev["trend"]["soil_moisture"] == -4  # 46 now vs 50 a minute ago
    assert dev["trend"]["air_temp"] == 0
    assert dev["trend"]["air_humidity"] is None


async def test_latest_endpoint_needs_no_account() -> None:
    feed.add(parse_reading(TOPIC, _payload({"soil_moisture": 33}, status="low"), NOW)[0])
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        res = await c.get("/api/v1/sensors/latest")
    assert res.status_code == 200
    body = res.json()
    assert set(body) == {"broker_connected", "devices"}
    assert body["devices"][0]["latest"]["field_status"] == "low"

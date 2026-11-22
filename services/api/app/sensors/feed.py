"""Live readings from the FARMLINK field unit (firmware/field-unit), received over MQTT.

The ESP32 field unit sends a reading every 5 s over LoRa to the gateway, which publishes it to the
HiveMQ broker (see firmware/README.md):

    farmlink/v2/<device_id>/readings   one JSON reading
    farmlink/v2/<device_id>/gateway    "online" / "offline" (retained, last will)

This module subscribes in a background thread and keeps the latest reading of each device in
memory, plus a few minutes of history for the trend arrows. The dashboard reads it through
/api/v1/sensors/latest.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import deque
from typing import Any

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

from app.core.config import settings

log = logging.getLogger("farmlink.sensors")

HISTORY_SECONDS = 15 * 60  # kept per device, for trends
TREND_WINDOW_SECONDS = 60  # a trend compares the latest value with the one about a minute ago

# Same light scale as the field unit's OLED (LIGHT_DARK_RAW / LIGHT_BRIGHT_RAW in field-unit.ino):
# the LDR reads LOWER when it is BRIGHTER.
LIGHT_DARK_RAW = 4000
LIGHT_BRIGHT_RAW = 300

FIELD_STATUSES = {"good", "low", "critical", "sensor_fault"}


def light_pct(raw: int) -> int:
    pct = 100 * (LIGHT_DARK_RAW - raw) / (LIGHT_DARK_RAW - LIGHT_BRIGHT_RAW)
    return round(max(0.0, min(100.0, pct)))


def _number(value: Any, lo: float, hi: float) -> float | None:
    """A sensor value within its physical range, else None (missing or bogus)."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value) if lo <= value <= hi else None


def parse_reading(
    topic: str, payload: bytes | bytearray, received_at: float
) -> list[dict[str, Any]]:
    """One clean row per sample. Missing sensors stay None (the firmware leaves failed keys out)."""
    parts = topic.split("/")
    if len(parts) != 4 or parts[3] != "readings":
        raise ValueError(f"unexpected topic {topic}")
    device_id = parts[2]
    msg = json.loads(payload)
    if not isinstance(msg, dict):
        raise ValueError("payload is not an object")
    status = msg.get("field_status")
    rows = []
    for sample in msg.get("samples") or []:
        values = sample.get("values") or {}
        t = sample.get("t")
        # t = 0 when the gateway has no internet time yet: use the receive time instead
        ts = float(t) if isinstance(t, int | float) and t > 1_600_000_000 else received_at
        soil = _number(values.get("soil_moisture"), 0, 100)
        light_raw = _number(values.get("light_raw"), 0, 4095)
        rows.append(
            {
                "device_id": device_id,
                "ts": min(ts, received_at),  # never in the future
                "soil_moisture": None if soil is None else round(soil),
                "air_temp": _number(values.get("air_temp"), -40, 85),
                "air_humidity": _number(values.get("air_humidity"), 0, 100),
                "light": None if light_raw is None else light_pct(int(light_raw)),
                "field_status": status if status in FIELD_STATUSES else None,
            }
        )
    return rows


class SensorFeed:
    """Latest readings per device, filled by the MQTT thread and read by the API."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._history: dict[str, deque[dict[str, Any]]] = {}
        self._gateway: dict[str, str] = {}
        self._client: mqtt.Client | None = None
        self.connected = False

    # --- data -------------------------------------------------------------------------------
    def add(self, row: dict[str, Any]) -> None:
        allowed = settings.SENSOR_DEVICE_IDS
        if allowed and row["device_id"] not in allowed:
            return  # the public broker is open: ignore devices that aren't ours
        with self._lock:
            hist = self._history.setdefault(row["device_id"], deque())
            hist.append(row)
            while hist and row["ts"] - hist[0]["ts"] > HISTORY_SECONDS:
                hist.popleft()

    def set_gateway(self, device_id: str, state: str) -> None:
        allowed = settings.SENSOR_DEVICE_IDS
        if state in ("online", "offline") and (not allowed or device_id in allowed):
            with self._lock:
                self._gateway[device_id] = state

    def snapshot(self, now: float | None = None) -> dict[str, Any]:
        now = time.time() if now is None else now
        devices = []
        with self._lock:
            ids = sorted(set(self._history) | set(self._gateway))
            for device_id in ids:
                hist = list(self._history.get(device_id, ()))
                latest = hist[-1] if hist else None
                devices.append(
                    {
                        "device_id": device_id,
                        "gateway": self._gateway.get(device_id, "unknown"),
                        "latest": latest,
                        "age_s": None if latest is None else round(now - latest["ts"]),
                        "trend": _trend(hist),
                    }
                )
        return {"broker_connected": self.connected, "devices": devices}

    def clear(self) -> None:
        with self._lock:
            self._history.clear()
            self._gateway.clear()

    # --- MQTT ---------------------------------------------------------------------------------
    def start(self) -> None:
        if not settings.SENSOR_FEED_ENABLED or self._client is not None:
            return
        client = mqtt.Client(CallbackAPIVersion.VERSION2)
        client.tls_set()  # the system CA store verifies the broker's certificate
        if settings.SENSOR_MQTT_USERNAME:
            client.username_pw_set(settings.SENSOR_MQTT_USERNAME, settings.SENSOR_MQTT_PASSWORD)
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message
        client.reconnect_delay_set(min_delay=1, max_delay=60)
        # connect_async: the API starts even when the broker or the network is unreachable
        client.connect_async(settings.SENSOR_MQTT_HOST, settings.SENSOR_MQTT_PORT, keepalive=30)
        client.loop_start()
        self._client = client
        log.info("Sensor feed: connecting to %s", settings.SENSOR_MQTT_HOST)

    def stop(self) -> None:
        if self._client is not None:
            self._client.loop_stop()
            self._client.disconnect()
            self._client = None
            self.connected = False

    def _on_connect(self, client: mqtt.Client, _u: Any, _f: Any, reason: Any, _p: Any) -> None:
        self.connected = not reason.is_failure
        if self.connected:  # subscribe here so it happens again after every reconnect
            prefix = settings.SENSOR_TOPIC_PREFIX
            client.subscribe([(f"{prefix}/+/readings", 1), (f"{prefix}/+/gateway", 1)])
            log.info("Sensor feed: connected, listening on %s/+/readings", prefix)
        else:
            log.warning("Sensor feed: broker refused the connection (%s)", reason)

    def _on_disconnect(self, _c: mqtt.Client, _u: Any, _f: Any, _reason: Any, _p: Any) -> None:
        self.connected = False

    def _on_message(self, _c: mqtt.Client, _u: Any, msg: mqtt.MQTTMessage) -> None:
        try:
            if msg.topic.endswith("/gateway"):
                self.set_gateway(msg.topic.split("/")[2], msg.payload.decode(errors="ignore"))
                return
            for row in parse_reading(msg.topic, msg.payload, time.time()):
                self.add(row)
        except (ValueError, AttributeError, TypeError, IndexError) as exc:
            log.debug("Sensor feed: skipped a bad message on %s: %s", msg.topic, exc)


def _trend(hist: list[dict[str, Any]]) -> dict[str, float | None]:
    """Change of each value over about the last minute (None when there isn't enough data)."""
    out: dict[str, float | None] = {}
    if len(hist) < 2:
        return {k: None for k in ("soil_moisture", "air_temp", "air_humidity", "light")}
    latest = hist[-1]
    target = latest["ts"] - TREND_WINDOW_SECONDS
    past = min(hist[:-1], key=lambda r: abs(r["ts"] - target))
    for key in ("soil_moisture", "air_temp", "air_humidity", "light"):
        a, b = past.get(key), latest.get(key)
        out[key] = None if a is None or b is None else round(b - a, 1)
    return out


feed = SensorFeed()

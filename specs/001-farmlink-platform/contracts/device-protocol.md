# Contract: Device Protocol v2 (ESP32 ↔ backend)

Replaces the reference's single-device protocol (`is9ini/telemetry`, global `DEVICE_KEY`) with
per-device identity. A v1 adapter keeps the reference payload working during transition.

## Identity and keys

- Each device has `device_id` (UUID) and a 32-byte secret `K_dev`, shown once at registration.
- **Inbound** (device → server): HMAC-SHA256 over the raw JSON body with `K_dev`.
- **Outbound** (server → device): HMAC-SHA256 over `"{cmd}|{value}|{ts}|{seq}"` with
  `K_cmd = HMAC-SHA256(K_dev, "farmlink-command-v2")` (derived so one secret is provisioned).

## Transport

| | MQTT (preferred, TLS 8883) | HTTP fallback |
|---|---|---|
| Readings | `farmlink/v2/{device_id}/readings` | `POST /api/v1/device/readings` |
| Status | `farmlink/v2/{device_id}/status` | `POST /api/v1/device/status` |
| Events | `farmlink/v2/{device_id}/events` | `POST /api/v1/device/events` |
| Commands to device | `farmlink/v2/{device_id}/cmd` (QoS 1) | `POST /api/v1/device/commands/poll` |
| Command ack | `farmlink/v2/{device_id}/ack` | `POST /api/v1/device/commands/{seq}/ack` |

MQTT messages wrap the body: `{"body": "<json string>", "sig": "<hex>"}`. HTTP sends the body
raw with headers `X-Device-Id` and `X-Signature`. Broker ACLs restrict each device's MQTT user to
its own topic prefix.

## Payloads

**Readings** (batch allowed, ≤ 100 samples):

```json
{"v": 2, "sent_at": 1763740000, "samples": [
  {"t": 1763739995, "values": {"soil": 41.5, "air_temp": 27.1, "tank_main": 63.0, "ph": 7.2}}
]}
```

Keys are `Channel.key`. Unknown keys on a known device are stored as *pending channels* for the
owner to confirm, not discarded and not charted. Values outside `Channel.valid_min/max` are
rejected individually and logged as `security`/`device` events.

**Status**:

```json
{"v": 2, "t": 1763739995, "mood": "thirsty", "mood_confidence": 0.82,
 "pump_on": false, "mode": "auto", "water_today_ml": 120}
```

**Event**: `{"v": 2, "t": …, "type": "string ≤ 32", "message": "≤ 200 chars", "data": {}}`

## Commands

```json
{"cmd": "water_now" | "set_mode" | "settings", "value": "", "ts": 1763740001, "seq": 1042, "sig": "hex"}
```

Device MUST:
1. verify `sig` with `K_cmd`;
2. reject if `|now − ts| > 5 s` (live) — HTTP-polled commands carry their own `ts` and the
   server only returns unexpired ones;
3. reject if `seq ≤ last_seq` (persist `last_seq` in flash);
4. enforce its own hard limits regardless of command or settings content (Principle I);
5. ack with `{"seq": 1042, "result": "done" | "refused", "reason": "soil_wet" | …}`.

The server persists `seq` per device (`Device.next_command_seq`), so restarts and multiple API
instances never reuse a sequence number.

## v1 compatibility

`POST /api/v1/device/telemetry` and MQTT `is9ini/telemetry` accept the reference body
(`soil, temp, hum, light, mood, confidence, pump, water_today, mode`) signed with the device key,
for devices registered with `protocol_version = 1`; the adapter maps fields to channels
`soil_moisture, air_temp, air_humidity, light` and to a `DeviceStatus`. Commands to v1 devices use
the reference format `"{cmd}|{value}|{ts}|{n}"` with `n = seq`.

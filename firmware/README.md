# FARMLINK firmware and MQTT data feed

How sensor data gets from the field to your backend, and how to read it there.

```
ESP32 #1 field unit ──LoRa 433 MHz──► ESP32 #2 gateway ──Wi-Fi, MQTT over TLS──► HiveMQ broker
 (soil, DHT22, LDR,                    (adds time, signal,                        │
  OLED, LEDs, buzzer)                   publishes JSON)                           ├──► your backend (Python, port 8883)
                                                                                  └──► web page (WebSocket, port 8884)
```

| Folder | Board | What it does |
|---|---|---|
| [`field-unit/`](field-unit/field-unit.ino) | ESP32 #1 | Reads sensors every 5 s, shows them on the OLED, lights the traffic-light LEDs, beeps when soil is critical, sends a CSV packet over LoRa. |
| [`gateway/`](gateway/gateway.ino) | ESP32 #2 | Receives LoRa, turns each packet into JSON, publishes it to HiveMQ. |

## 1. Flash the boards

Arduino IDE libraries (Library Manager):

| Library | Needed by |
|---|---|
| LoRa (Sandeep Mistry) | both |
| DHT22 (dvarrel) | field unit |
| Adafruit GFX, Adafruit SSD1306 | field unit |
| PubSubClient (Nick O'Leary) | gateway |

1. Field unit: open `firmware/field-unit/field-unit.ino`, upload to ESP32 #1. Calibrate
   `DRY_RAW` / `WET_RAW` (soil) and `LIGHT_DARK_RAW` / `LIGHT_BRIGHT_RAW` (light) from the raw
   values shown in the Serial Monitor.
2. Gateway: copy `firmware/gateway/secrets.example.h` to `secrets.h` (same folder), fill it in,
   then open `firmware/gateway/gateway.ino` and upload to ESP32 #2. Open the `.ino` from the
   repo folder: the IDE needs `secrets.h` and `hivemq_ca.h` next to it.

`secrets.h` is gitignored. Never commit it.

Gateway Serial Monitor (115200) should show `Wi-Fi ... OK`, `Time synced`, `MQTT ... OK`, then
`MQTT: published` every 5 s. If MQTT fails it prints a state code: `-2` = host/network/TLS
problem, `4`/`5` = wrong username or password.

## 2. The broker

The demo uses HiveMQ's **public broker**. No account, no login.

| Who connects | Host | Port | Transport |
|---|---|---|---|
| Gateway (ESP32) | `broker.hivemq.com` | 8883 | MQTT over TLS |
| Backend (Python, Node server) | `broker.hivemq.com` | 8883 | MQTT over TLS |
| Browser page / web client | `broker.hivemq.com` | 8884 | WebSocket over TLS, path `/mqtt` (`wss://broker.hivemq.com:8884/mqtt`) |

All three are the same broker: a message the gateway publishes on 8883 reaches WebSocket
subscribers on 8884.

> **The public broker is open to everyone.** Anyone who knows the topic can read the data or
> publish fake readings. Fine for the hackathon demo. For anything real, use a HiveMQ Cloud
> cluster (section 6).

### Check it without writing code

1. Open <https://www.hivemq.com/demos/websocket-client/>.
2. Connect with the defaults (host `broker.hivemq.com`, port 8884, SSL on, no username).
3. Add a subscription: `farmlink/v2/kizunahack-field-unit-1/#`.
4. A message appears every 5 s while both boards run.

## 3. Topics

`<DEVICE_ID>` comes from `secrets.h` (currently `kizunahack-field-unit-1`).

| Topic | Payload | Retained |
|---|---|---|
| `farmlink/v2/<DEVICE_ID>/readings` | one JSON reading every 5 s (section 4) | no |
| `farmlink/v2/<DEVICE_ID>/gateway` | `online` or `offline` | yes |

`gateway` is retained and `offline` is the gateway's last will: the broker publishes it by
itself when the gateway drops off. A backend that subscribes gets the current state at once.
Use it for an online/offline indicator.

Subscribe to `farmlink/v2/+/readings` to receive every device; take the device ID from the
second topic level.

## 4. Reading payload

```json
{
  "v": 2,
  "sent_at": 1763800000,
  "samples": [
    {
      "t": 1763800000,
      "values": {
        "soil_raw": 1840,
        "light_raw": 3090,
        "soil_moisture": 45,
        "air_temp": 24.3,
        "air_humidity": 55.1
      }
    }
  ],
  "seq": 5,
  "field_status": "good",
  "rssi": -58,
  "snr": 9.5
}
```

| Field | Type | Meaning |
|---|---|---|
| `v` | int | payload version, always `2` |
| `sent_at`, `samples[].t` | int | Unix time in seconds, UTC. `0` if the gateway has no internet time yet: use your receive time instead. |
| `samples` | array | always one sample for now; loop over it anyway |
| `values.soil_moisture` | int, % 0–100 | calibrated soil moisture |
| `values.air_temp` | float, °C | DHT22 temperature |
| `values.air_humidity` | float, % | DHT22 humidity |
| `values.soil_raw` | int, 0–4095 | raw ADC, lower = wetter (for calibration/debug) |
| `values.light_raw` | int, 0–4095 | raw ADC from the LDR, **lower = brighter** |
| `seq` | int | packet counter from the field unit; restarts at 0 when it reboots. A jump means LoRa packets were lost. |
| `field_status` | string | `good`, `low` (moisture ≤ 35 %), `critical` (≤ 20 %), `sensor_fault` (soil sensor unplugged/shorted) |
| `rssi`, `snr` | int dBm, float dB | LoRa signal quality between the two boards |

**A failed sensor's key is left out**, not sent as `null` or `-99`:
- DHT22 failure: no `air_temp` / `air_humidity`.
- Soil sensor fault: no `soil_moisture` and `field_status` is `sensor_fault`.

Always read values with a default (`values.get("air_temp")` in Python, `values.air_temp ?? null`
in JS). The moisture thresholds are demo values, not agronomy.

## 5. Read it in your backend

### Python (paho-mqtt, already a dependency of `services/api`)

```python
import json
import time

import paho.mqtt.client as mqtt

BROKER = "broker.hivemq.com"
TOPICS = [("farmlink/v2/+/readings", 1), ("farmlink/v2/+/gateway", 1)]


def parse_reading(topic: str, payload: bytes) -> list[dict]:
    """One dict per sample: device_id, ts, the sensor values, status and link quality."""
    device_id = topic.split("/")[2]
    msg = json.loads(payload)
    rows = []
    for sample in msg.get("samples", []):
        values = sample.get("values", {})
        rows.append({
            "device_id": device_id,
            "ts": sample.get("t") or int(time.time()),  # t=0 -> gateway had no clock yet
            "soil_moisture": values.get("soil_moisture"),  # None if the sensor failed
            "air_temp": values.get("air_temp"),
            "air_humidity": values.get("air_humidity"),
            "light_raw": values.get("light_raw"),
            "soil_raw": values.get("soil_raw"),
            "field_status": msg.get("field_status"),
            "seq": msg.get("seq"),
            "rssi": msg.get("rssi"),
        })
    return rows


def on_connect(client, userdata, flags, reason_code, properties):
    print("connected:", reason_code)
    client.subscribe(TOPICS)  # subscribe here so it happens again after a reconnect


def on_message(client, userdata, msg):
    if msg.topic.endswith("/gateway"):
        print(msg.topic.split("/")[2], "gateway is", msg.payload.decode())
        return
    try:
        for row in parse_reading(msg.topic, msg.payload):
            print(row)  # <- save to your database / push to the dashboard here
    except (ValueError, AttributeError) as e:  # bad JSON or wrong shape: skip, don't crash
        print("bad message on", msg.topic, e)


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.tls_set()  # system CA store verifies the broker's certificate
# client.username_pw_set("user", "password")   # only for HiveMQ Cloud (section 6)
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, 8883)
client.loop_forever()  # reconnects on its own
```

Run it with `python subscriber.py` and power the boards: one line per reading.

**Inside FastAPI:** start the client in the app's lifespan with `client.loop_start()` (runs in
a background thread) instead of `loop_forever()`, and `client.loop_stop()` on shutdown. Callbacks
run on that thread, so hand rows to the async side (a queue, or `asyncio.run_coroutine_threadsafe`)
before touching async database sessions.

### JavaScript (browser or Node, `mqtt` package)

```js
import mqtt from "mqtt";

const client = mqtt.connect("wss://broker.hivemq.com:8884/mqtt"); // Node server: "mqtts://broker.hivemq.com:8883"

client.on("connect", () => client.subscribe("farmlink/v2/+/readings"));

client.on("message", (topic, payload) => {
  const deviceId = topic.split("/")[2];
  const msg = JSON.parse(payload.toString());
  for (const s of msg.samples ?? []) {
    const v = s.values ?? {};
    console.log({
      deviceId,
      ts: s.t || Math.floor(Date.now() / 1000),
      soilMoisture: v.soil_moisture ?? null,
      airTemp: v.air_temp ?? null,
      airHumidity: v.air_humidity ?? null,
      status: msg.field_status,
    });
  }
});
```

A browser connected straight to the broker skips your backend. Fine for a live demo widget;
anything stored or shown to other users should go through the backend.

## 6. Switch to a private HiveMQ Cloud cluster

1. Create a free cluster at <https://console.hivemq.cloud>.
2. **Overview** tab: copy the cluster URL, e.g. `abc123.s1.eu.hivemq.cloud`.
3. **Access Management**: create one user for the gateway and one for the backend.
4. Gateway `secrets.h`: set `MQTT_HOST` to the cluster URL, `MQTT_USER` / `MQTT_PASSWORD` to the
   gateway user. Re-upload. The certificate bundle in `hivemq_ca.h` already covers HiveMQ Cloud.
5. Backend: same host, port 8883, `client.username_pw_set(...)` with the backend user. Browser:
   `wss://<cluster-url>:8884/mqtt` with a username and password.

## 7. Limits of this demo

- Messages are **not signed**. The platform's Device Protocol v2
  ([contracts/device-protocol.md](../specs/001-farmlink-platform/contracts/device-protocol.md))
  adds HMAC signatures; do that before the backend ever sends commands (pump control).
- If the gateway loses Wi-Fi or the broker, readings in that gap are dropped (printed on the
  Serial Monitor only).
- The LoRa link is unencrypted, at 433 MHz. Check that this band is allowed for your use.

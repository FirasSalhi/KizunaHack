// FARMLINK gateway (ESP32 #2)
// Receives the field unit's LoRa packets and publishes them over Wi-Fi to a HiveMQ Cloud
// MQTT broker (TLS, port 8883), so the website backend can subscribe to them.
// Also prints each reading on the Serial Monitor (115200).
//
// Libraries: LoRa (Sandeep Mistry), PubSubClient (Nick O'Leary).
// Setup: copy secrets.example.h to secrets.h and fill in Wi-Fi + HiveMQ credentials.
//
// LoRa packet from field unit: seq,rawSoil,moisture,temp,hum,lightRaw,status
//   status: 0 good, 1 low, 2 critical, 3 soil sensor fault. temp/hum = -99 on DHT error.
//
// MQTT topics (DEVICE_ID from secrets.h):
//   farmlink/v2/<DEVICE_ID>/readings   one JSON message per LoRa packet (see publishReading)
//   farmlink/v2/<DEVICE_ID>/gateway    "online" / "offline" (retained, offline = last will)
//
// ponytail: payload follows the Device Protocol v2 readings shape but is NOT HMAC-signed;
// the broker login is the only authentication. Add the {"body","sig"} wrapper from
// specs/001-farmlink-platform/contracts/device-protocol.md before using this for control.
// ponytail: readings that arrive while MQTT is down are dropped (printed only). Fine for a
// 5 s stream; add a small ring buffer if gaps in history matter.

#include <SPI.h>
#include <LoRa.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <time.h>
#include "secrets.h"
#include "hivemq_ca.h"

#define LORA_SCK    18
#define LORA_MISO   19
#define LORA_MOSI   23
#define LORA_SS     5
#define LORA_RST    21   // your wiring
#define LORA_DIO0   22   // your wiring
#define LORA_FREQ   433E6  // must match the field unit

WiFiClientSecure tls;
PubSubClient mqtt(tls);

String topicReadings, topicGateway, clientId;

unsigned long lastSeq = 0;
bool haveSeq = false;
unsigned long lastPacketAt = 0;
bool warnedSilent = false;
unsigned long lastMqttTry = 0;

const char* statusText(int s) {
  switch (s) {
    case 0: return "good";
    case 1: return "low";
    case 2: return "critical";
    case 3: return "sensor_fault";
    default: return "unknown";
  }
}

void connectWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Wi-Fi connecting");
  for (int i = 0; i < 40 && WiFi.status() != WL_CONNECTED; i++) { delay(500); Serial.print("."); }
  if (WiFi.status() == WL_CONNECTED) { Serial.print(" OK, IP "); Serial.println(WiFi.localIP()); }
  else Serial.println(" failed (will keep retrying in background)");
}

// Real timestamps for "t"/"sent_at". If NTP isn't reachable we send 0 and the backend
// should use its receive time.
void syncTime() {
  configTime(0, 0, "pool.ntp.org", "time.google.com");
  for (int i = 0; i < 20 && time(nullptr) < 1700000000; i++) delay(250);
  Serial.println(time(nullptr) > 1700000000 ? "Time synced (UTC)" : "Time not synced, sending t=0");
}

long nowEpoch() {
  time_t t = time(nullptr);
  return t > 1700000000 ? (long)t : 0;
}

// Non-blocking: tries at most every 5 s so LoRa keeps being serviced.
void ensureMqtt() {
  if (mqtt.connected() || WiFi.status() != WL_CONNECTED) return;
  if (millis() - lastMqttTry < 5000) return;
  lastMqttTry = millis();

  Serial.print("MQTT connecting to "); Serial.print(MQTT_HOST); Serial.print(" ... ");
  // Empty user = no login (public broker.hivemq.com).
  const char* user = strlen(MQTT_USER) ? MQTT_USER : nullptr;
  const char* pass = strlen(MQTT_USER) ? MQTT_PASSWORD : nullptr;
  bool ok = mqtt.connect(clientId.c_str(), user, pass,
                         topicGateway.c_str(), 1, true, "offline");
  if (ok) {
    mqtt.publish(topicGateway.c_str(), "online", true);
    Serial.println("OK");
  } else {
    // -2 usually = TLS/network problem, 4 = bad username/password, 5 = not authorized.
    Serial.printf("failed, state %d\n", mqtt.state());
  }
}

void publishReading(unsigned long seq, int raw, int moisture, float t, float h,
                    int light, int status, int rssi, float snr) {
  long ts = nowEpoch();
  char values[160];
  int n = snprintf(values, sizeof values, "\"soil_raw\":%d,\"light_raw\":%d", raw, light);
  if (status != 3) n += snprintf(values + n, sizeof values - n, ",\"soil_moisture\":%d", moisture);
  if (t != -99) n += snprintf(values + n, sizeof values - n, ",\"air_temp\":%.1f", t);
  if (h != -99) n += snprintf(values + n, sizeof values - n, ",\"air_humidity\":%.1f", h);

  char payload[400];
  snprintf(payload, sizeof payload,
           "{\"v\":2,\"sent_at\":%ld,\"samples\":[{\"t\":%ld,\"values\":{%s}}],"
           "\"seq\":%lu,\"field_status\":\"%s\",\"rssi\":%d,\"snr\":%.1f}",
           ts, ts, values, seq, statusText(status), rssi, snr);

  Serial.printf("JSON: %s\n", payload);
  if (!mqtt.connected()) { Serial.println("MQTT: not connected, reading dropped"); return; }
  Serial.println(mqtt.publish(topicReadings.c_str(), payload) ? "MQTT: published" : "MQTT: publish failed");
}

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\nFARMLINK GATEWAY");

  topicReadings = String("farmlink/v2/") + DEVICE_ID + "/readings";
  topicGateway  = String("farmlink/v2/") + DEVICE_ID + "/gateway";
  clientId      = String("farmlink-gw-") + String((uint32_t)ESP.getEfuseMac(), HEX);

  SPI.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_SS);
  LoRa.setPins(LORA_SS, LORA_RST, LORA_DIO0);
  if (!LoRa.begin(LORA_FREQ)) {
    Serial.println("LoRa init failed: check wiring (RST 21, DIO0 22), 3.3 V and antenna.");
    while (true) delay(1000);
  }
  // Must match the field unit exactly.
  LoRa.setSyncWord(0x12);
  LoRa.setSpreadingFactor(7);
  LoRa.setSignalBandwidth(125E3);
  LoRa.setCodingRate4(5);
  Serial.println("LoRa OK");

  connectWifi();
  syncTime();

  tls.setCACert(HIVEMQ_ROOT_CA);
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setBufferSize(512);  // default 256 is too small for our JSON
  mqtt.setKeepAlive(30);

  Serial.println("Ready, waiting for field data...");
  lastPacketAt = millis();
}

void loop() {
  ensureMqtt();
  mqtt.loop();

  // Field unit sends every 5 s; say so if it goes quiet for 30 s.
  if (!warnedSilent && millis() - lastPacketAt > 30000) {
    Serial.println("!! No packet for 30 s: field unit off, out of range, or LoRa settings differ.");
    warnedSilent = true;
  }

  int size = LoRa.parsePacket();
  if (!size) return;

  char buf[80];
  int n = 0;
  while (LoRa.available() && n < (int)sizeof buf - 1) buf[n++] = (char)LoRa.read();
  while (LoRa.available()) LoRa.read();  // drop anything oversized
  buf[n] = '\0';

  int rssi = LoRa.packetRssi();
  float snr = LoRa.packetSnr();
  lastPacketAt = millis();
  warnedSilent = false;

  unsigned long seq;
  int raw, moisture, light, status;
  float t, h;
  if (sscanf(buf, "%lu,%d,%d,%f,%f,%d,%d", &seq, &raw, &moisture, &t, &h, &light, &status) != 7) {
    Serial.print("Invalid packet: "); Serial.println(buf);
    return;
  }

  if (haveSeq && seq > lastSeq + 1) {
    Serial.printf("(lost %lu packet(s) over LoRa)\n", seq - lastSeq - 1);
  }
  lastSeq = seq;
  haveSeq = true;

  Serial.println("===== FARMLINK DATA =====");
  Serial.printf("Seq:      %lu\n", seq);
  Serial.printf("Soil:     %d%% (raw %d)\n", moisture, raw);
  if (t == -99) Serial.println("Temp:     sensor error"); else Serial.printf("Temp:     %.1f C\n", t);
  if (h == -99) Serial.println("Humidity: sensor error"); else Serial.printf("Humidity: %.1f %%\n", h);
  Serial.printf("Light:    raw %d\n", light);
  Serial.printf("Status:   %s\n", statusText(status));
  Serial.printf("Signal:   RSSI %d dBm, SNR %.1f dB\n", rssi, snr);

  publishReading(seq, raw, moisture, t, h, light, status, rssi, snr);
}

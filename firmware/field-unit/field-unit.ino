// FARMLINK field unit (ESP32 #1)
// Reads soil, DHT22 and LDR, shows them on the OLED, drives the traffic-light LEDs and
// buzzer, and sends a CSV packet over LoRa to the gateway (ESP32 #2) every 5 s.
// Local alerts keep working even if LoRa fails to start.
//
// Libraries: LoRa (Sandeep Mistry), DHT22 (dvarrel), Adafruit GFX, Adafruit SSD1306.
//
// Packet: seq,rawSoil,moisture,temp,hum,lightRaw,status
//   status: 0 good, 1 low, 2 critical, 3 soil sensor fault. temp/hum = -99 on DHT error.
//
// ponytail: plain CSV, no HMAC. The gateway adds Device Protocol v2 signing when it
// forwards to the API; LoRa itself is unauthenticated (fine for the demo, not for control).

#include <SPI.h>
#include <LoRa.h>
#include <Wire.h>
#include <DHT22.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// ---------- Pins ----------
#define SOIL_PIN    34
#define LIGHT_PIN   35
#define DHT_PIN     4
#define GREEN_LED   13
#define YELLOW_LED  16
#define RED_LED     17
#define BUZZER_PIN  25   // through NPN transistor, active buzzer

#define LORA_SCK    18
#define LORA_MISO   19
#define LORA_MOSI   23
#define LORA_SS     5
#define LORA_RST    14
#define LORA_DIO0   26
#define LORA_FREQ   433E6  // must match the module and the gateway

#define OLED_ADDR   0x3C   // try 0x3D if the screen stays blank

// ---------- Calibration (measure yours!) ----------
// Read "Soil raw" on the OLED/Serial with the sensor in dry air/soil and in wet soil.
#define DRY_RAW        3000
#define WET_RAW        1500
#define CRITICAL_LEVEL 20   // % moisture, demo value
#define LOW_LEVEL      35   // % moisture, demo value

// Read "Light raw" with the LDR covered by your finger (dark) and under a phone torch or
// sunlight (bright).
#define LIGHT_DARK_RAW   4000
#define LIGHT_BRIGHT_RAW 300

const unsigned long SEND_INTERVAL = 5000;
const unsigned long BEEP_EVERY    = 3000;
const unsigned long BEEP_LENGTH   = 200;

DHT22 dht(DHT_PIN);
Adafruit_SSD1306 display(128, 64, &Wire, -1);

// DHT22: max one read per 2 s, and single reads fail now and then on ESP32.
// Keep the last good value and only report an error after 3 failures in a row.
const int DHT_MAX_FAILS = 3;
float lastTemp = NAN, lastHum = NAN;
int dhtFails = 0;

void readDht(float &t, float &h) {
  // dvarrel DHT22: getTemperature() does the read; getHumidity() within 2.1 s reuses it.
  // Check getLastError() right after the real read, because a second call inside the
  // 2.1 s window always reports OK even if the first read failed.
  float nt = dht.getTemperature();
  bool ok = dht.getLastError() == DHT22::OK;
  float nh = ok ? dht.getHumidity() : NAN;
  if (!ok) {
    dhtFails++;
    Serial.printf("DHT22 read failed (%d in a row)\n", dhtFails);
  } else {
    dhtFails = 0;
    lastTemp = nt;
    lastHum = nh;
  }
  bool stale = dhtFails >= DHT_MAX_FAILS;
  t = stale ? NAN : lastTemp;
  h = stale ? NAN : lastHum;
}

bool loraOk = false;
bool oledOk = false;
unsigned long seq = 0;
unsigned long lastSend = 0;
unsigned long lastBeep = 0;
int status = 0;

int readAverage(int pin) {
  long total = 0;
  for (int i = 0; i < 10; i++) { total += analogRead(pin); delay(5); }
  return total / 10;
}

int moisturePct(int raw) {
  float pct = 100.0 * (DRY_RAW - raw) / (DRY_RAW - WET_RAW);
  return (int)constrain(pct, 0, 100);
}

// MH-series LDR: AO goes DOWN as light goes UP.
// Map between YOUR measured dark and bright raw values (not 0..4095) so the % uses the
// whole scale. Narrower range = more sensitive. Works in either direction.
int lightPct(int raw) {
  float pct = 100.0 * (LIGHT_DARK_RAW - raw) / (LIGHT_DARK_RAW - LIGHT_BRIGHT_RAW);
  return (int)constrain(pct, 0, 100);
}

bool soilFault(int raw) { return raw < 100 || raw > 4000; }  // unplugged / shorted

int computeStatus(int raw, int moisture) {
  if (soilFault(raw)) return 3;
  if (moisture <= CRITICAL_LEVEL) return 2;
  if (moisture <= LOW_LEVEL) return 1;
  return 0;
}

void setLeds(int s) {
  digitalWrite(GREEN_LED,  s == 0);
  digitalWrite(YELLOW_LED, s == 1);
  digitalWrite(RED_LED,    s >= 2);
}

// Non-blocking beep while critical or faulted.
void updateBuzzer() {
  unsigned long now = millis();
  if (status < 2) { digitalWrite(BUZZER_PIN, LOW); return; }
  if (now - lastBeep >= BEEP_EVERY) lastBeep = now;
  digitalWrite(BUZZER_PIN, now - lastBeep < BEEP_LENGTH);
}

const char* statusText(int s) {
  switch (s) {
    case 0: return "GOOD";
    case 1: return "LOW";
    case 2: return "CRITICAL";
    default: return "SOIL ERR";
  }
}

void showReadings(int raw, int moisture, float t, float h, int light) {
  if (!oledOk) return;
  display.clearDisplay();
  display.setCursor(0, 0);
  display.println("FARMLINK FIELD UNIT");
  display.print("Soil: "); display.print(moisture); display.print("% ("); display.print(raw); display.println(")");
  display.print("Temp: "); if (isnan(t)) display.println("err"); else { display.print(t, 1); display.println(" C"); }
  display.print("Hum:  "); if (isnan(h)) display.println("err"); else { display.print(h, 0); display.println(" %"); }
  display.print("Light: "); display.print(light); display.println("%");
  display.print("Status: "); display.println(statusText(status));
  display.print("LoRa: "); display.println(loraOk ? "OK" : "OFF");
  display.display();
}

void sendPacket(int raw, int moisture, float t, float h, int lightRaw) {
  char packet[64];
  snprintf(packet, sizeof packet, "%lu,%d,%d,%.1f,%.1f,%d,%d",
           seq++, raw, moisture, isnan(t) ? -99.0 : t, isnan(h) ? -99.0 : h, lightRaw, status);
  Serial.println("----- FARMLINK reading -----");
  Serial.printf("Reading #:  %lu\n", seq - 1);
  Serial.printf("Soil:       %d %% (raw %d)\n", moisture, raw);
  if (isnan(t)) Serial.println("Temp:       sensor error"); else Serial.printf("Temp:       %.1f C\n", t);
  if (isnan(h)) Serial.println("Humidity:   sensor error"); else Serial.printf("Humidity:   %.1f %%\n", h);
  Serial.printf("Light:      %d %% (raw %d)\n", lightPct(lightRaw), lightRaw);
  Serial.printf("Status:     %s\n", statusText(status));
  Serial.printf("LoRa:       %s\n", loraOk ? "sent" : "OFF (not sent)");
  Serial.printf("Packet:     %s\n", packet);
  if (!loraOk) return;
  LoRa.beginPacket();
  LoRa.print(packet);
  LoRa.endPacket();
}

void setup() {
  Serial.begin(115200);

  pinMode(GREEN_LED, OUTPUT);
  pinMode(YELLOW_LED, OUTPUT);
  pinMode(RED_LED, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);

  analogReadResolution(12);
  analogSetPinAttenuation(SOIL_PIN, ADC_11db);
  analogSetPinAttenuation(LIGHT_PIN, ADC_11db);

  // DHT22 needs no begin(); first read happens after SEND_INTERVAL (5 s), past its 2 s warm-up.

  Wire.begin(21, 22);
  oledOk = display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR);
  if (!oledOk) Serial.println("OLED not found (check wiring / address 0x3C vs 0x3D)");
  else {
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.clearDisplay();
    display.setCursor(0, 0);
    display.println("FARMLINK starting...");
    display.display();
  }

  SPI.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_SS);
  LoRa.setPins(LORA_SS, LORA_RST, LORA_DIO0);
  loraOk = LoRa.begin(LORA_FREQ);
  if (loraOk) {
    LoRa.setSyncWord(0x12);
    LoRa.setSpreadingFactor(7);
    LoRa.setSignalBandwidth(125E3);
    LoRa.setCodingRate4(5);
    LoRa.setTxPower(17);
    Serial.println("LoRa OK");
  } else {
    Serial.println("LoRa init failed: running local-only (check wiring, 3.3 V, antenna)");
  }

  // LED self-test so you can see all three work at boot.
  for (int p : {GREEN_LED, YELLOW_LED, RED_LED}) { digitalWrite(p, HIGH); delay(250); digitalWrite(p, LOW); }
}

void loop() {
  updateBuzzer();

  if (millis() - lastSend < SEND_INTERVAL) return;
  lastSend = millis();

  int raw = readAverage(SOIL_PIN);
  int moisture = moisturePct(raw);
  int lightRaw = readAverage(LIGHT_PIN);
  float t, h;
  readDht(t, h);

  status = computeStatus(raw, moisture);
  setLeds(status);
  showReadings(raw, moisture, t, h, lightPct(lightRaw));
  sendPacket(raw, moisture, t, h, lightRaw);
}

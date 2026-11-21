# Ported unchanged from RaziSnihaa/is9ini backend/simulator.py at commit 2aaac4ad73eee1aae11c890086b92f322611da45
# (team-owned code, reuse confirmed 2026-11-21, research.md OQ-6). Paths inside still refer to
# the reference layout (backend/...); later FARMLINK tasks adapt them.
"""Fake ESP32 for testing the backend and the app without hardware.

It behaves like the real firmware will: sends signed telemetry every 2 s, checks signed commands
(HMAC, age < 5 s, counter always growing) and enforces the water caps itself.

    python simulator.py                 # normal plant that slowly dries
    python simulator.py --dry           # start with dry soil (watering demo)
    python simulator.py --hot           # heat wave (Too hot demo)
"""
import argparse
import hashlib
import hmac
import json
import math
import random
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, ".")
from app import config  # noqa: E402  (reads the same .env as the backend)

FLOW_ML_PER_S = 25          # calibrated pump flow
PERIOD_S = 2


class FakeEsp32:
    def __init__(self, url: str, dry: bool, hot: bool):
        self.url = url.rstrip("/")
        self.soil = 30.0 if dry else 62.0
        self.hot = hot
        self.mode = "auto"
        self.settings = {"max_per_watering_ml": 150, "max_per_day_ml": 600, "soil_dry_pct": 35, "soil_wet_pct": 80,
                         "temp_max_c": 32, "temp_min_c": 12}
        self.pump = False
        self.watering_ml = 0.0
        self.water_today = 0.0
        self.last_n = 0
        self.t0 = time.time()

    # --- signed HTTP ----------------------------------------------------------------
    def post(self, path: str, payload: dict) -> dict:
        body = json.dumps(payload, separators=(",", ":")).encode()
        sig = hmac.new(config.DEVICE_KEY.encode(), body, hashlib.sha256).hexdigest()
        req = urllib.request.Request(self.url + path, data=body, method="POST",
                                     headers={"Content-Type": "application/json", "X-Signature": sig})
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())

    def event(self, type_: str, message: str) -> None:
        print(f"  event: {message}")
        self.post("/api/device/event", {"type": type_, "message": message})

    # --- commands -------------------------------------------------------------------
    def check_command(self, c: dict) -> bool:
        expected = hmac.new(config.COMMAND_KEY.encode(), f"{c['cmd']}|{c['value']}|{c['ts']}|{c['n']}".encode(),
                            hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, c.get("sig", "")):
            self.event("security", "Rejected command: bad signature")
            return False
        if abs(time.time() - c["ts"]) > config.COMMAND_MAX_AGE_S:
            self.event("security", "Rejected command: too old (replay?)")
            return False
        if c["n"] <= self.last_n:
            self.event("security", "Rejected command: replayed counter")
            return False
        self.last_n = c["n"]
        return True

    def handle_commands(self) -> None:
        for c in self.post("/api/device/commands", {"device_id": config.DEVICE_ID, "ts": int(time.time())})["commands"]:
            if not self.check_command(c):
                continue
            if c["cmd"] == "set_mode":
                self.mode = c["value"]
                self.event("mode", f"Mode set to {self.mode}")
            elif c["cmd"] == "settings":
                self.settings.update({k: v for k, v in json.loads(c["value"]).items() if k in self.settings})
                self.event("settings", "New settings applied")
            elif c["cmd"] == "water_now":
                if self.soil >= self.settings["soil_wet_pct"]:
                    self.event("refused", "Water now refused: soil is wet")
                elif self.water_today >= self.settings["max_per_day_ml"]:
                    self.event("refused", "Water now refused: daily cap reached")
                else:
                    self.start_pump()

    # --- plant physics + safety ------------------------------------------------------
    def start_pump(self) -> None:
        if not self.pump:
            self.pump, self.watering_ml = True, 0.0

    def read_sensors(self) -> dict:
        t = time.time() - self.t0
        temp = 26 + 2 * math.sin(t / 120) + (9 if self.hot else 0) + random.uniform(-0.2, 0.2)
        hum = 58 - 6 * math.sin(t / 120) + random.uniform(-0.5, 0.5)
        light = max(0.0, 850 + 150 * math.sin(t / 90) + random.uniform(-20, 20))
        return {"temp": round(temp, 1), "hum": round(hum, 1), "light": round(light)}

    def step(self) -> dict:
        s = self.settings
        if self.pump:
            dose = FLOW_ML_PER_S * PERIOD_S
            self.watering_ml += dose
            self.water_today += dose
            self.soil = min(100.0, self.soil + dose * 0.08)
            if (self.watering_ml >= s["max_per_watering_ml"] or self.water_today >= s["max_per_day_ml"]
                    or self.soil >= s["soil_wet_pct"]):
                self.pump = False
        else:
            self.soil = max(0.0, self.soil - random.uniform(0.15, 0.35))

        sensors = self.read_sensors()
        if sensors["temp"] > s["temp_max_c"]:
            mood = "too_hot"
        elif self.soil >= s["soil_wet_pct"]:
            mood = "drowning"
        elif self.soil < s["soil_dry_pct"]:
            mood = "thirsty"
        else:
            mood = "happy"
        if mood == "thirsty" and self.mode == "auto" and self.water_today < s["max_per_day_ml"]:
            self.start_pump()
        return {"soil": round(self.soil, 1), **sensors, "mood": mood, "confidence": round(random.uniform(0.82, 0.97), 2),
                "pump": self.pump, "water_today": round(self.water_today), "mode": self.mode}

    def run(self) -> None:
        print(f"Fake ESP32 sending to {self.url} every {PERIOD_S}s (Ctrl+C to stop)")
        while True:
            try:
                data = self.step()
                self.post("/api/device/telemetry", data)
                self.handle_commands()
                print(f"soil {data['soil']:5.1f}%  temp {data['temp']:4.1f}C  mood {data['mood']:9s} "
                      f"pump {'ON ' if data['pump'] else 'off'}  water {data['water_today']} ml  mode {self.mode}")
            except (urllib.error.URLError, ConnectionError) as exc:
                print("backend not reachable:", exc)
            time.sleep(PERIOD_S)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://127.0.0.1:8000")
    p.add_argument("--dry", action="store_true")
    p.add_argument("--hot", action="store_true")
    a = p.parse_args()
    FakeEsp32(a.url, a.dry, a.hot).run()

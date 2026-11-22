"""Download NASA POWER monthly climatology (long-term means) for each Tunisian governorate seat.

Usage: python download_climate.py <out_dir>
Coordinates are the governorate seats (chef-lieu), rounded to 0.01 degree.
"""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

GOVERNORATES = {
    "Tunis": (36.81, 10.18), "Ariana": (36.86, 10.19), "Ben Arous": (36.75, 10.22), "Manouba": (36.81, 10.10),
    "Nabeul": (36.45, 10.73), "Zaghouan": (36.40, 10.14), "Bizerte": (37.27, 9.87), "Béja": (36.73, 9.18),
    "Jendouba": (36.50, 8.78), "Le Kef": (36.17, 8.71), "Siliana": (36.08, 9.37), "Sousse": (35.83, 10.64),
    "Monastir": (35.78, 10.83), "Mahdia": (35.50, 11.06), "Sfax": (34.74, 10.76), "Kairouan": (35.68, 10.10),
    "Kasserine": (35.17, 8.83), "Sidi Bouzid": (35.04, 9.48), "Gabès": (33.88, 10.10), "Médenine": (33.35, 10.50),
    "Tataouine": (32.93, 10.45), "Gafsa": (34.43, 8.78), "Tozeur": (33.92, 8.13), "Kébili": (33.70, 8.97),
}
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
s = requests.Session(); s.headers["User-Agent"] = "FARMLINK-research/0.1"
result = {"source": "NASA POWER climatology API (community AG)",
          "url": "https://power.larc.nasa.gov/api/temporal/climatology/point",
          "parameters": "T2M_MAX, T2M_MIN, T2M, PRECTOTCORR (mm/day monthly means)",
          "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "governorates": {}}
for name, (lat, lon) in GOVERNORATES.items():
    for a in range(4):
        try:
            r = s.get(result["url"], params={"parameters": "T2M_MAX,T2M_MIN,T2M,PRECTOTCORR", "community": "AG",
                                             "latitude": lat, "longitude": lon, "format": "JSON"}, timeout=90)
            r.raise_for_status(); break
        except requests.RequestException:
            if a == 3: raise
            time.sleep(5)
    data = r.json()
    result["governorates"][name] = {"lat": lat, "lon": lon, "header": data.get("header"),
                                    "parameter": data["properties"]["parameter"]}
    print("ok", name)
(out / "nasa_power_climatology_governorates.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")

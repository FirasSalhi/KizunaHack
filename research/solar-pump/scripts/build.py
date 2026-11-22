"""Build the solar-pump simulation page.

1. Downloads (once) the NASA POWER monthly climatology for the 24 governorate seats:
   solar radiation (all-sky and clear-sky; the AG community returns MJ/m2/day, converted to kWh/m2/day),
   temperatures and rain. Resolution is about 0.5 degree: nearby seats (Tunis, Nabeul) can share a cell.
2. Computes monthly reference evapotranspiration (Hargreaves, FAO-56) and effective rain.
3. Writes data/solar_climate.json and html/solaire_3d.html (template + data).

Usage (from research/solar-pump):  python scripts/build.py   [--refresh to re-download]
"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "nasa_power_solar_climatology.json"
GOV = {
    "Tunis": (36.81, 10.18), "Ariana": (36.86, 10.19), "Ben Arous": (36.75, 10.22), "Manouba": (36.81, 10.10),
    "Nabeul": (36.45, 10.73), "Zaghouan": (36.40, 10.14), "Bizerte": (37.27, 9.87), "Béja": (36.73, 9.18),
    "Jendouba": (36.50, 8.78), "Le Kef": (36.17, 8.71), "Siliana": (36.08, 9.37), "Sousse": (35.83, 10.64),
    "Monastir": (35.78, 10.83), "Mahdia": (35.50, 11.06), "Sfax": (34.74, 10.76), "Kairouan": (35.68, 10.10),
    "Kasserine": (35.17, 8.83), "Sidi Bouzid": (35.04, 9.48), "Gabès": (33.88, 10.10), "Médenine": (33.35, 10.50),
    "Tataouine": (32.93, 10.45), "Gafsa": (34.43, 8.78), "Tozeur": (33.92, 8.13), "Kébili": (33.70, 8.97),
}
PARAMS = "ALLSKY_SFC_SW_DWN,CLRSKY_SFC_SW_DWN,T2M,T2M_MAX,T2M_MIN,PRECTOTCORR"
MK = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
DAYS = [31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
URL = "https://power.larc.nasa.gov/api/temporal/climatology/point"


def download() -> dict:
    s = requests.Session(); s.headers["User-Agent"] = "FARMLINK-research/0.1"
    out = {"source": "NASA POWER climatology API (community AG)", "url": URL, "parameters": PARAMS,
           "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "governorates": {}}
    for name, (lat, lon) in GOV.items():
        r = s.get(URL, params={"parameters": PARAMS, "community": "AG", "latitude": lat, "longitude": lon,
                               "format": "JSON"}, timeout=120)
        r.raise_for_status()
        out["governorates"][name] = {"lat": lat, "lon": lon, "parameter": r.json()["properties"]["parameter"]}
        print("ok", name)
    RAW.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def ra_mm_day(lat: float, doy: int) -> float:
    phi = math.radians(lat); dr = 1 + 0.033 * math.cos(2 * math.pi * doy / 365)
    d = 0.409 * math.sin(2 * math.pi * doy / 365 - 1.39); ws = math.acos(-math.tan(phi) * math.tan(d))
    return 0.408 * 24 * 60 / math.pi * 0.0820 * dr * (ws * math.sin(phi) * math.sin(d) + math.cos(phi) * math.cos(d) * math.sin(ws))


def main() -> None:
    raw = download() if "--refresh" in sys.argv or not RAW.exists() else json.loads(RAW.read_text(encoding="utf-8"))
    govs = {}
    for name, g in raw["governorates"].items():
        p = g["parameter"]; months = []
        for i, k in enumerate(MK):
            tmax, tmin, tmean = p["T2M_MAX"][k], p["T2M_MIN"][k], p["T2M"][k]
            eto = 0.0023 * ra_mm_day(g["lat"], int(15 + 30.4 * i)) * (tmean + 17.8) * math.sqrt(max(tmax - tmin, 0))
            rain = p["PRECTOTCORR"][k] * DAYS[i]
            eff = rain * (125 - 0.2 * rain) / 125 if rain <= 250 else 125 + 0.1 * rain
            months.append({"ghi": round(p["ALLSKY_SFC_SW_DWN"][k] / 3.6, 2), "ghi_clear": round(p["CLRSKY_SFC_SW_DWN"][k] / 3.6, 2),  # MJ -> kWh
                           "tmax": round(tmax, 1), "tmin": round(tmin, 1), "eto": round(eto, 2),
                           "eff_rain_day": round(eff / DAYS[i], 2)})
        govs[name] = {"lat": g["lat"], "lon": g["lon"], "months": months}
    data = {"governorates": govs, "source": raw["source"], "retrieved_at": raw["retrieved_at"],
            "units": {"ghi": "kWh/m²/jour (rayonnement global horizontal, moyenne mensuelle)", "eto": "mm/jour (Hargreaves)",
                      "eff_rain_day": "mm/jour (pluie efficace USDA-SCS)"}}
    js = json.dumps(data, ensure_ascii=False)
    (ROOT / "data" / "solar_climate.json").write_text(js, encoding="utf-8")
    tpl = (ROOT / "scripts" / "template.html").read_text(encoding="utf-8")
    (ROOT / "html" / "solaire_3d.html").write_text(tpl.replace("__DATA__", js), encoding="utf-8")
    print("built", len(govs), "governorates")


if __name__ == "__main__":
    main()

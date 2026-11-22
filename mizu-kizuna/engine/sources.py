"""Accès aux données externes, avec cache disque.

- NASA POWER : météo journalière historique (1991 → année dernière), communauté AG
- SoilGrids (ISRIC) : composition du sol 0-30 cm
- Open-Meteo : prévisions 16 jours
- Nominatim (OpenStreetMap) : recherche de lieux
"""
import hashlib
import json
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

CACHE = Path(__file__).resolve().parent.parent / "cache"
CACHE.mkdir(exist_ok=True)
UA = "MIZU-KIZUNA/2.0 (hackathon KIZUNA 2026, ESPRIT)"


class SourceUnavailable(Exception):
    pass


def _get_json(url, timeout=60, cache_days=None):
    key = CACHE / (hashlib.sha1(url.encode()).hexdigest() + ".json")
    if cache_days is not None and key.exists() and time.time() - key.stat().st_mtime < cache_days * 86400:
        return json.loads(key.read_text(encoding="utf-8"))
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
    except Exception as e:
        if key.exists():  # dernier recours : ancienne copie en cache
            return json.loads(key.read_text(encoding="utf-8"))
        raise SourceUnavailable(f"{urllib.parse.urlparse(url).netloc} : {e}") from e
    if cache_days is not None:
        key.write_text(json.dumps(data), encoding="utf-8")
    return data


# ---------------------------------------------------------------- NASA POWER
POWER_PARAMS = "T2M_MAX,T2M_MIN,T2M,PRECTOTCORR,ALLSKY_SFC_SW_DWN,RH2M,WS2M"


def nasa_power_daily(lat, lon, start_year=1991, end_year=None):
    """Séries journalières. Retourne dict(dates, elev, tmax, tmin, tmean, rain, rs, rh, wind)."""
    end_year = end_year or date.today().year - 1
    url = ("https://power.larc.nasa.gov/api/temporal/daily/point"
           f"?parameters={POWER_PARAMS}&community=AG&longitude={lon:.3f}&latitude={lat:.3f}"
           f"&start={start_year}0101&end={end_year}1231&format=JSON")
    d = _get_json(url, timeout=120, cache_days=365)
    p = d["properties"]["parameter"]
    days = sorted(p["T2M_MAX"].keys())

    def col(k):
        return [None if p[k][x] in (-999, -999.0) else p[k][x] for x in days]
    return {"dates": days, "elev": d["geometry"]["coordinates"][2],
            "tmax": col("T2M_MAX"), "tmin": col("T2M_MIN"), "tmean": col("T2M"),
            "rain": col("PRECTOTCORR"), "rs": col("ALLSKY_SFC_SW_DWN"),
            "rh": col("RH2M"), "wind": col("WS2M"),
            "source": f"NASA POWER, données journalières {start_year}-{end_year}"}


# ---------------------------------------------------------------- SoilGrids
SOIL_PROPS = ["clay", "sand", "silt", "phh2o", "soc", "cec", "bdod", "nitrogen"]


def soilgrids(lat, lon):
    q = "&".join([f"property={p}" for p in SOIL_PROPS] +
                 [f"depth={d}" for d in ("0-5cm", "5-15cm", "15-30cm", "30-60cm")] + ["value=mean"])
    url = f"https://rest.isric.org/soilgrids/v2.0/properties/query?lon={lon:.4f}&lat={lat:.4f}&{q}"
    d = _get_json(url, timeout=60, cache_days=3650)
    out = {}
    for layer in d["properties"]["layers"]:
        f = layer["unit_measure"]["d_factor"]
        depth_vals = {}
        for dep in layer["depths"]:
            v = dep["values"]["mean"]
            if v is not None:
                depth_vals[dep["label"]] = v / f
        if depth_vals:
            top = [depth_vals[k] for k in ("0-5cm", "5-15cm", "15-30cm") if k in depth_vals]
            out[layer["name"]] = {"topsoil": round(sum(top) / len(top), 2) if top else None,
                                  "by_depth": {k: round(v, 2) for k, v in depth_vals.items()}}
    if not {"clay", "sand", "phh2o"} <= out.keys() or out["clay"]["topsoil"] is None:
        raise SourceUnavailable("SoilGrids : pas de données à ce point (zone urbaine ou eau ?)")
    return out


# ---------------------------------------------------------------- Open-Meteo
def forecast16(lat, lon):
    url = ("https://api.open-meteo.com/v1/forecast"
           f"?latitude={lat:.3f}&longitude={lon:.3f}"
           "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,et0_fao_evapotranspiration"
           "&forecast_days=16&timezone=auto")
    d = _get_json(url, timeout=30)["daily"]
    return {"dates": d["time"], "tmax": d["temperature_2m_max"], "tmin": d["temperature_2m_min"],
            "rain": d["precipitation_sum"], "et0": d["et0_fao_evapotranspiration"],
            "source": "Open-Meteo, prévision 16 jours"}


# ---------------------------------------------------------------- Nominatim
def geocode(q, country_codes="tn,jp", limit=6, lang="fr"):
    url = ("https://nominatim.openstreetmap.org/search?format=jsonv2&addressdetails=0"
           f"&limit={limit}&countrycodes={country_codes}&accept-language={lang}&q={urllib.parse.quote(q)}")
    res = _get_json(url, timeout=20, cache_days=30)
    return [{"name": r["display_name"], "lat": float(r["lat"]), "lon": float(r["lon"]),
             "bbox": [float(x) for x in r["boundingbox"]]} for r in res]

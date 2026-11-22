"""Network clients: DGACTA (CKAN) sensor data and weather (Open-Meteo primary, NASA POWER fallback, optional ERA5-Land).

Honesty rules implemented here:
  * every call returns a provenance record (url, attempts, status, cache use, sha256, timestamps);
  * a failed request raises/returns an explicit failure - nothing is fabricated;
  * a cached copy is used only when ``allow_cache=True`` and is flagged ``from_cache=True`` with its age;
  * weather source fallback happens only when ``allow_fallback=True`` and is recorded (``fallback_used``);
  * DGACTA channels keep their units: millivolts are NEVER relabelled as VWC; depth comes from resource metadata only.
The HTTP contracts below follow the public documentation and were NOT exercised against the live services from the
build sandbox (no outbound access); they are tested against a local mock server (tests/test_data_sources.py).
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

CKAN_BASE = "https://catalog.data.gov.tn/api/3/action/package_show"
STATIONS = {
    "el_alaa": {"name": "El Alâa", "package_id": "771dc061-9d84-426f-915e-b1e02403f9cb"},
    "sbikha": {"name": "Sbikha", "package_id": "6b6067ed-a005-46c5-be3d-98ec9d0cab2c"},
    "rayhana": {"name": "Rayhana", "package_id": "617e938d-c59a-4108-84e7-d634d98e1152"},
    "bargou": {"name": "Bargou", "package_id": "4d6a078a-c041-479a-845b-5a682ad12dd3"},
    "chott_meriam": {"name": "Chott Meriam", "package_id": "90e0a429-1b92-43ba-bf5c-3604c8de9e0f"},
}
OPEN_METEO_ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
OPEN_METEO_FORECAST = "https://api.open-meteo.com/v1/forecast"
NASA_POWER = "https://power.larc.nasa.gov/api/temporal/daily/point"
KAGGLE_INTERNET_HELP = ("Internet is disabled for this notebook. On Kaggle: open the notebook, right-hand panel 'Session options' (or Settings) -> "
                        "set 'Internet' to ON (phone verification of the Kaggle account is required). Then restart the session and re-run.")


class DownloadError(RuntimeError):
    def __init__(self, msg, provenance=None):
        super().__init__(msg); self.provenance = provenance or {}


def make_session(retries: int = 4, backoff: float = 1.0, user_agent: str = "FARMLINK-Module5/2.0") -> requests.Session:
    s = requests.Session()
    r = Retry(total=retries, connect=retries, read=retries, status=retries, backoff_factor=backoff, allowed_methods=("GET",),
              status_forcelist=(429, 500, 502, 503, 504), respect_retry_after_header=True)
    s.mount("https://", HTTPAdapter(max_retries=r)); s.mount("http://", HTTPAdapter(max_retries=r))
    s.headers["User-Agent"] = user_agent
    return s


def _now(): return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _get(url: str, session: requests.Session, params=None, timeout=(10, 60), cache_path: Optional[Path] = None, allow_cache: bool = False,
         verify: bool = True) -> (bytes, Dict):
    prov = {"url": url, "params": params, "requested_utc": _now(), "from_cache": False, "status": None, "error": None}
    try:
        resp = session.get(url, params=params, timeout=timeout, allow_redirects=True, verify=verify)
        prov.update(status=resp.status_code, final_url=resp.url, redirects=len(resp.history), content_type=resp.headers.get("Content-Type"))
        resp.raise_for_status()
        content = resp.content
        if cache_path is not None:
            cache_path.parent.mkdir(parents=True, exist_ok=True); cache_path.write_bytes(content)
        prov["sha256"] = hashlib.sha256(content).hexdigest(); prov["bytes"] = len(content)
        return content, prov
    except (requests.RequestException, OSError) as e:
        prov["error"] = f"{type(e).__name__}: {e}"
        if allow_cache and cache_path is not None and cache_path.exists():
            content = cache_path.read_bytes()
            prov.update(from_cache=True, cache_age_hours=round((time.time() - cache_path.stat().st_mtime) / 3600, 1), sha256=hashlib.sha256(content).hexdigest(), bytes=len(content))
            return content, prov
        raise DownloadError(f"GET {url} failed: {prov['error']}. {KAGGLE_INTERNET_HELP if 'Connection' in prov['error'] or 'Name' in prov['error'] or 'resolve' in prov['error'] else ''}".strip(), prov)


# ---------------------------------------------------------------- DGACTA ---
_DEPTH_RE = re.compile(r"(?<![\d.])(\d{1,3})\s*(?:cm|centim)", re.I)
_DEPTH_RE2 = re.compile(r"(?:prof(?:ondeur)?|depth|niveau)[\s_:-]*(\d{1,3})(?!\d)", re.I)


def parse_depth_cm(*texts: str) -> Optional[int]:
    """Depth from resource metadata (name/description/filename) ONLY. None when not stated - never defaulted."""
    for t in texts:
        if not t: continue
        for rx in (_DEPTH_RE, _DEPTH_RE2):
            m = rx.search(str(t))
            if m: return int(m.group(1))
    return None


def classify_channel(*texts: str) -> str:
    t = " ".join(str(x) for x in texts if x).casefold()
    if re.search(r"\bmv\b|milli ?volt|tension|voltage|volt", t): return "voltage_mv"
    if re.search(r"temp", t) and re.search(r"sol|soil|ground", t): return "soil_temperature_c"
    if re.search(r"humidit|moisture|vwc|teneur en eau|humid", t) and re.search(r"sol|soil", t): return "soil_vwc_percent"
    if re.search(r"pluie|rain|precip", t): return "rain"
    if re.search(r"humectation|leaf", t): return "leaf_wetness"
    return "unknown"


def fetch_station_package(station_key: str, session: requests.Session, cache_dir: Path, allow_cache: bool = True, base: str = CKAN_BASE) -> Dict:
    pid = STATIONS[station_key]["package_id"]
    content, prov = _get(base, session, params={"id": pid}, cache_path=Path(cache_dir) / f"package_{station_key}.json", allow_cache=allow_cache)
    try:
        pkg = json.loads(content.decode("utf-8"))
    except Exception as e:
        raise DownloadError(f"CKAN response for {station_key} is not JSON: {e}", prov)
    if not isinstance(pkg, dict) or pkg.get("success") is not True or "result" not in pkg or "resources" not in pkg["result"]:
        raise DownloadError(f"CKAN response for {station_key} failed validation (success!=true or no result.resources).", prov)
    return {"station": station_key, "package": pkg["result"], "provenance": prov}


def discover_resources(pkg_result: Dict) -> pd.DataFrame:
    rows = []
    for r in pkg_result.get("resources", []):
        name, desc, url = r.get("name") or "", r.get("description") or "", r.get("url") or ""
        fname = url.rsplit("/", 1)[-1] if url else ""
        fmt = (r.get("format") or "").upper()
        rows.append({"resource_id": r.get("id"), "name": name, "format": fmt, "url": url, "filename": fname, "last_modified": r.get("last_modified") or r.get("metadata_modified"),
                     "size": r.get("size"), "depth_cm": parse_depth_cm(name, fname, desc), "channel": classify_channel(name, fname, desc),
                     "is_tabular": fmt in ("CSV", "TSV") or fname.lower().endswith((".csv", ".tsv"))})
    return pd.DataFrame(rows)


def download_resource(res: Dict, session: requests.Session, cache_dir: Path, allow_cache: bool = True, max_bytes: int = 200_000_000) -> (Path, Dict):
    url = res["url"]
    if not url: raise DownloadError("resource has no url")
    p = Path(cache_dir) / f"{res.get('resource_id') or hashlib.md5(url.encode()).hexdigest()}.csv"
    content, prov = _get(url, session, cache_path=p, allow_cache=allow_cache, timeout=(10, 120))
    head = content[:512].lstrip().lower()
    if head.startswith(b"<!doctype html") or head.startswith(b"<html"):
        raise DownloadError(f"{url} returned an HTML page, not data.", prov)
    if len(content) > max_bytes: raise DownloadError(f"{url}: {len(content)} bytes exceeds max_bytes", prov)
    if len(content) == 0: raise DownloadError(f"{url}: empty file", prov)
    return p, prov


def parse_sensor_csv(path: Path, resource_meta: Dict) -> Dict:
    """Parse one DGACTA resource CSV into a long, unit-preserving frame. Column semantics are detected, not assumed."""
    raw = Path(path).read_bytes()
    df = None
    for sep in (",", ";", "\t"):
        try:
            cand = pd.read_csv(io.BytesIO(raw), sep=sep, engine="python")
            if cand.shape[1] >= 2: df = cand; break
        except Exception: continue
    if df is None: raise DownloadError(f"cannot parse {path} as delimited text")
    cols = {c: str(c).strip().casefold() for c in df.columns}
    tcol = next((c for c, n in cols.items() if re.search(r"date|time|horodat|heure|timestamp", n)), None)
    if tcol is None: raise DownloadError(f"{path}: no timestamp column among {list(df.columns)}")
    vcols = [c for c in df.columns if c != tcol and pd.to_numeric(df[c], errors="coerce").notna().mean() >= 0.5]   # tolerate a few bad cells
    if not vcols: raise DownloadError(f"{path}: no numeric value column")
    vcol = vcols[0]
    out = pd.DataFrame({"timestamp": pd.to_datetime(df[tcol], errors="coerce", utc=True), "value": pd.to_numeric(df[vcol], errors="coerce")})
    n_bad_t = int(out["timestamp"].isna().sum())
    out = out.dropna(subset=["timestamp"]).sort_values("timestamp").drop_duplicates("timestamp")
    ch = resource_meta.get("channel", "unknown")
    notes = []
    if ch == "voltage_mv": notes.append("values are millivolts: NOT volumetric water content; a calibration curve is required before conversion")
    if ch == "soil_vwc_percent": notes.append("VWC as reported by the provider; field calibration/validation status unknown")
    if resource_meta.get("depth_cm") is None: notes.append("depth not stated in resource metadata: do not assume (e.g. 10 cm)")
    if ch == "unknown": notes.append("channel could not be identified from metadata")
    out["channel"] = ch; out["depth_cm"] = resource_meta.get("depth_cm"); out["source_resource"] = resource_meta.get("resource_id")
    return {"data": out, "value_column": str(vcol), "rows": len(out), "bad_timestamps": n_bad_t, "channel": ch, "depth_cm": resource_meta.get("depth_cm"),
            "calibration_status": "uncalibrated_millivolts" if ch == "voltage_mv" else ("provider_reported_unverified" if ch == "soil_vwc_percent" else "n/a"), "notes": notes}


# --------------------------------------------------------------- weather ---
def wind10_to_2(u10: pd.Series) -> pd.Series:
    """FAO-56 Eq. 47: u2 = u_z * 4.87 / ln(67.8 z - 5.42), z = 10 m."""
    return u10 * 4.87 / math.log(67.8 * 10 - 5.42)


def _std_frame(df: pd.DataFrame, source: str) -> pd.DataFrame:
    cols = ["date", "tmin", "tmax", "tmean", "rh_mean", "u2", "rs", "rain_mm"]
    for c in cols:
        if c not in df.columns: df[c] = np.nan
    df["weather_source"] = source
    return df[cols + ["weather_source"] + [c for c in df.columns if c not in cols + ["weather_source"]]]


def open_meteo_daily(lat: float, lon: float, start: str, end: str, session: requests.Session, forecast: bool = False, model: Optional[str] = None,
                     cache_dir: Optional[Path] = None, allow_cache: bool = False, url: Optional[str] = None) -> (pd.DataFrame, Dict):
    daily = "temperature_2m_max,temperature_2m_min,temperature_2m_mean,relative_humidity_2m_mean,wind_speed_10m_mean,shortwave_radiation_sum,precipitation_sum,et0_fao_evapotranspiration"
    params = {"latitude": lat, "longitude": lon, "daily": daily, "timezone": "UTC", "wind_speed_unit": "ms"}
    if forecast:
        params["forecast_days"] = 16
    else:
        params.update(start_date=start, end_date=end)
    if model: params["models"] = model
    base = url or (OPEN_METEO_FORECAST if forecast else OPEN_METEO_ARCHIVE)
    cp = Path(cache_dir) / f"openmeteo_{'fc' if forecast else 'hist'}_{lat:.3f}_{lon:.3f}_{start}_{end}_{model or 'default'}.json" if cache_dir else None
    content, prov = _get(base, session, params=params, cache_path=cp, allow_cache=allow_cache)
    j = json.loads(content.decode("utf-8"))
    if "daily" not in j or "time" not in j["daily"]:
        raise DownloadError(f"Open-Meteo response lacks daily.time: {str(j)[:200]}", prov)
    d = j["daily"]; df = pd.DataFrame({"date": pd.to_datetime(d["time"])})
    mp = {"tmax": "temperature_2m_max", "tmin": "temperature_2m_min", "tmean": "temperature_2m_mean", "rh_mean": "relative_humidity_2m_mean",
          "rs": "shortwave_radiation_sum", "rain_mm": "precipitation_sum", "eto_openmeteo_mm": "et0_fao_evapotranspiration"}
    for k, v in mp.items(): df[k] = pd.to_numeric(pd.Series(d.get(v, [np.nan] * len(df))), errors="coerce")
    df["u2"] = wind10_to_2(pd.to_numeric(pd.Series(d.get("wind_speed_10m_mean", [np.nan] * len(df))), errors="coerce"))
    units = j.get("daily_units", {}); prov["units"] = units
    if units.get("shortwave_radiation_sum") not in (None, "MJ/m²", "MJ/m2"):
        raise DownloadError(f"unexpected radiation unit {units.get('shortwave_radiation_sum')} (expected MJ/m²)", prov)
    prov.update(source="open-meteo-forecast" if forecast else "open-meteo-archive", model=model, rows=len(df), lat=lat, lon=lon,
                elevation_m_reported=j.get("elevation"), contract_verified_live=False)
    return _std_frame(df, "open_meteo_forecast" if forecast else ("open_meteo_" + (model or "archive"))), prov


def nasa_power_daily(lat: float, lon: float, start: str, end: str, session: requests.Session, cache_dir: Optional[Path] = None,
                     allow_cache: bool = False, url: Optional[str] = None) -> (pd.DataFrame, Dict):
    params = {"parameters": "T2M,T2M_MAX,T2M_MIN,RH2M,WS2M,ALLSKY_SFC_SW_DWN,PRECTOTCORR", "community": "AG", "latitude": lat, "longitude": lon,
              "start": start.replace("-", ""), "end": end.replace("-", ""), "format": "JSON"}
    cp = Path(cache_dir) / f"nasapower_{lat:.3f}_{lon:.3f}_{start}_{end}.json" if cache_dir else None
    content, prov = _get(url or NASA_POWER, session, params=params, cache_path=cp, allow_cache=allow_cache, timeout=(10, 120))
    j = json.loads(content.decode("utf-8"))
    try:
        par = j["properties"]["parameter"]
    except KeyError:
        raise DownloadError(f"NASA POWER response lacks properties.parameter: {str(j)[:200]}", prov)
    dates = sorted(par["T2M"].keys())
    df = pd.DataFrame({"date": pd.to_datetime(dates, format="%Y%m%d")})
    def col(n):
        s = pd.Series([par[n].get(d, np.nan) for d in dates], dtype=float); return s.where(s > -990)   # -999 = fill value -> NaN
    df["tmean"], df["tmax"], df["tmin"], df["rh_mean"], df["u2"], df["rain_mm"] = col("T2M"), col("T2M_MAX"), col("T2M_MIN"), col("RH2M"), col("WS2M"), col("PRECTOTCORR")
    rs = col("ALLSKY_SFC_SW_DWN")
    unit = (j.get("parameters", {}).get("ALLSKY_SFC_SW_DWN", {}) or {}).get("units", "")
    if "kw" in unit.lower(): rs = rs * 3.6
    elif unit and "mj" not in unit.lower(): raise DownloadError(f"unexpected NASA POWER radiation unit '{unit}'", prov)
    elif not unit: prov["radiation_unit_note"] = "unit not reported; AG community is documented as MJ/m2/day (assumed)"
    df["rs"] = rs
    prov.update(source="nasa_power", rows=len(df), lat=lat, lon=lon, contract_verified_live=False, n_fill_values=int(sum(df[c].isna().sum() for c in ("tmean", "rain_mm"))))
    return _std_frame(df, "nasa_power"), prov


def fetch_weather(lat: float, lon: float, start: str, end: str, session: Optional[requests.Session] = None, order=("open_meteo", "nasa_power"),
                  allow_fallback: bool = True, cache_dir: Optional[Path] = None, allow_cache: bool = False, urls: Optional[Dict] = None) -> (pd.DataFrame, Dict):
    """Try sources in order. The returned provenance lists every attempt, the source actually used and whether a fallback occurred."""
    s = session or make_session(); urls = urls or {}
    attempts, used = [], None
    for i, src in enumerate(order):
        if i > 0 and not allow_fallback: break
        try:
            if src == "open_meteo": df, prov = open_meteo_daily(lat, lon, start, end, s, cache_dir=cache_dir, allow_cache=allow_cache, url=urls.get("open_meteo"))
            elif src == "era5_land": df, prov = open_meteo_daily(lat, lon, start, end, s, model="era5_land", cache_dir=cache_dir, allow_cache=allow_cache, url=urls.get("open_meteo"))
            elif src == "nasa_power": df, prov = nasa_power_daily(lat, lon, start, end, s, cache_dir=cache_dir, allow_cache=allow_cache, url=urls.get("nasa_power"))
            else: raise ValueError(f"unknown weather source {src}")
            attempts.append({"source": src, "ok": True, **{k: prov.get(k) for k in ("from_cache", "rows", "sha256", "requested_utc")}}); used = src
            return df, {"source_used": used, "fallback_used": i > 0, "attempts": attempts, "detail": prov}
        except (DownloadError, ValueError, json.JSONDecodeError) as e:
            attempts.append({"source": src, "ok": False, "error": str(e)[:300]})
    raise DownloadError("All weather sources failed: " + " | ".join(f"{a['source']}: {a.get('error')}" for a in attempts), {"attempts": attempts})

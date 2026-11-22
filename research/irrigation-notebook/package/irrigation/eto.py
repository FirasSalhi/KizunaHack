"""Reference evapotranspiration (FAO-56).

* ``eto_penman_monteith``  FAO-56 Eq. 6 (daily), preferred when Tmin, Tmax, Tmean, RH, u2 and Rs exist.
* ``eto_hargreaves``       Hargreaves-Samani (FAO-56 Eq. 52), explicit fallback needing only temperatures.
* ``compute_eto``          row-wise selection; the method used is returned for every day.

Units: temperature degC, RH %, wind m/s at 2 m, Rs MJ m-2 day-1, ETo mm day-1.
Missing inputs are never replaced by defaults: the day is computed with a lower-ranked
method if allowed, otherwise ETo is NaN.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

GSC = 0.0820          # MJ m-2 min-1
SIGMA = 4.903e-9      # MJ K-4 m-2 day-1
NASA_FILL = -999.0


def svp(t):
    """Saturation vapour pressure (kPa), FAO-56 Eq. 11."""
    t = np.asarray(t, dtype=float)
    return 0.6108 * np.exp(17.27 * t / (t + 237.3))


def extraterrestrial_radiation(lat_deg, doy):
    """Ra (MJ m-2 day-1), FAO-56 Eq. 21."""
    phi = np.radians(lat_deg)
    doy = np.asarray(doy, dtype=float)
    dr = 1.0 + 0.033 * np.cos(2.0 * np.pi * doy / 365.0)
    delta = 0.409 * np.sin(2.0 * np.pi * doy / 365.0 - 1.39)
    ws = np.arccos(np.clip(-np.tan(phi) * np.tan(delta), -1.0, 1.0))
    return (24.0 * 60.0 / np.pi) * GSC * dr * (
        ws * np.sin(phi) * np.sin(delta) + np.cos(phi) * np.cos(delta) * np.sin(ws))


def eto_penman_monteith(tmin, tmax, tmean, rh_mean, u2, rs, lat_deg, doy, elevation_m, ea_kpa=None):
    """FAO-56 Penman-Monteith daily ETo (mm/day). G = 0 for daily steps.

    ``ea_kpa`` can be supplied directly; otherwise ea = RHmean/100 * (e(Tmax)+e(Tmin))/2 (Eq. 19).
    """
    tmin, tmax, tmean = (np.asarray(x, dtype=float) for x in (tmin, tmax, tmean))
    u2, rs = np.asarray(u2, dtype=float), np.asarray(rs, dtype=float)
    z = float(elevation_m)
    p = 101.3 * ((293.0 - 0.0065 * z) / 293.0) ** 5.26
    gamma = 0.000665 * p
    delta = 4098.0 * svp(tmean) / (tmean + 237.3) ** 2
    es = (svp(tmax) + svp(tmin)) / 2.0
    ea = np.asarray(ea_kpa, dtype=float) if ea_kpa is not None else np.asarray(rh_mean, dtype=float) / 100.0 * es
    ra = extraterrestrial_radiation(lat_deg, doy)
    rso = (0.75 + 2e-5 * z) * ra
    rns = (1.0 - 0.23) * rs
    ratio = np.clip(rs / np.where(rso > 0, rso, np.nan), 0.0, 1.0)
    rnl = SIGMA * ((tmax + 273.16) ** 4 + (tmin + 273.16) ** 4) / 2.0 * (0.34 - 0.14 * np.sqrt(ea)) * (1.35 * ratio - 0.35)
    rn = rns - rnl
    num = 0.408 * delta * rn + gamma * 900.0 / (tmean + 273.0) * u2 * (es - ea)
    den = delta + gamma * (1.0 + 0.34 * u2)
    return np.maximum(num / den, 0.0)


def eto_hargreaves(tmin, tmax, tmean, lat_deg, doy):
    """Hargreaves-Samani ETo (mm/day) = 0.0023 (Tmean+17.8) sqrt(Tmax-Tmin) Ra/2.45."""
    tmin, tmax, tmean = (np.asarray(x, dtype=float) for x in (tmin, tmax, tmean))
    ra = extraterrestrial_radiation(lat_deg, doy)
    return np.maximum(0.0023 * (tmean + 17.8) * np.sqrt(np.maximum(tmax - tmin, 0.0)) * ra / 2.45, 0.0)


def standardize_nasa_power(df: pd.DataFrame) -> pd.DataFrame:
    """Map the notebook's NASA POWER columns to generic names; -999 fill values become NaN."""
    m = {"nasa_tmin_C": "tmin", "nasa_tmax_C": "tmax", "nasa_tmean_C": "tmean", "nasa_rh2m_pct": "rh_mean",
         "nasa_wind_ms": "u2", "nasa_solar_MJ": "rs", "nasa_precip_mm": "rain_mm"}
    missing = [c for c in ("date", *m) if c not in df.columns]
    if missing:
        raise ValueError(f"NASA POWER dataframe lacks columns {missing}")
    out = df[["date", *m]].rename(columns=m).copy()
    out["date"] = pd.to_datetime(out["date"])
    for c in m.values():
        out[c] = pd.to_numeric(out[c], errors="coerce").replace(NASA_FILL, np.nan)
    out["source"] = df["provenance"].values if "provenance" in df.columns else "unspecified"
    return out.sort_values("date").reset_index(drop=True)


def compute_eto(weather: pd.DataFrame, lat_deg: float, elevation_m: float, method: str = "auto") -> pd.DataFrame:
    """Add ``eto_mm`` and ``eto_method`` columns (never silent about the method).

    method: 'auto' (PM if complete else Hargreaves if temperatures complete else NaN),
            'pm' (PM only), 'hargreaves' (HS only).
    """
    if method not in ("auto", "pm", "hargreaves"):
        raise ValueError("method must be 'auto', 'pm' or 'hargreaves'")
    need = ["date", "tmin", "tmax", "tmean"]
    miss = [c for c in need if c not in weather.columns]
    if miss:
        raise ValueError(f"weather lacks columns {miss}")
    w = weather.copy()
    doy = pd.to_datetime(w["date"]).dt.dayofyear.values
    temps_ok = w[["tmin", "tmax", "tmean"]].notna().all(axis=1) & (w["tmin"] <= w["tmax"])
    pm_cols = [c for c in ("rh_mean", "u2", "rs") if c in w.columns]
    pm_ok = temps_ok & (len(pm_cols) == 3) & (w[pm_cols].notna().all(axis=1) if len(pm_cols) == 3 else False)
    if len(pm_cols) == 3:
        pm_ok = pm_ok & (w["rs"] >= 0) & (w["u2"] >= 0) & w["rh_mean"].between(0, 100)
    eto = np.full(len(w), np.nan)
    used = np.array(["unavailable"] * len(w), dtype=object)
    if method in ("auto", "pm") and len(pm_cols) == 3:
        idx = pm_ok.values
        if idx.any():
            eto[idx] = eto_penman_monteith(w.loc[idx, "tmin"], w.loc[idx, "tmax"], w.loc[idx, "tmean"],
                                           w.loc[idx, "rh_mean"], w.loc[idx, "u2"], w.loc[idx, "rs"],
                                           lat_deg, doy[idx], elevation_m)
            used[idx] = "FAO56_Penman_Monteith"
    if method in ("auto", "hargreaves"):
        idx = (temps_ok.values) & np.isnan(eto)
        if idx.any():
            eto[idx] = eto_hargreaves(w.loc[idx, "tmin"], w.loc[idx, "tmax"], w.loc[idx, "tmean"], lat_deg, doy[idx])
            used[idx] = "Hargreaves_Samani(fallback)"
    w["eto_mm"] = eto
    w["eto_method"] = used
    return w

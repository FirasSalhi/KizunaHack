"""Climat historique journalier → ETo FAO-56 Penman-Monteith, tableaux numpy.

Si NASA POWER est inaccessible, un historique de DÉMONSTRATION est synthétisé à partir
des normales mensuelles de la station de référence la plus proche (clairement signalé).
"""
import math
from datetime import date, timedelta

import numpy as np

from .sources import SourceUnavailable, nasa_power_daily

# Normales approximatives (Tmax, Tmin, pluie mm/mois) — SECOURS HORS LIGNE uniquement
FALLBACK_STATIONS = {
    "Bizerte":  (37.27, 9.87,  [16,16,18,20,24,28,31,32,29,25,21,17], [8,8,9,11,14,18,21,22,20,16,12,9], [95,75,60,45,25,10,3,8,40,70,90,105]),
    "Tunis":    (36.85, 10.22, [16,17,19,22,26,30,33,33,30,26,21,17], [7,8,9,12,15,19,22,23,21,17,12,8], [65,55,45,40,20,10,3,8,35,55,60,70]),
    "Béja":     (36.73, 9.18,  [14,16,18,21,26,31,35,35,31,25,19,15], [5,5,7,9,12,16,19,20,18,14,9,6], [90,80,65,55,35,15,4,8,35,60,80,100]),
    "Nabeul":   (36.45, 10.73, [16,17,19,21,25,29,32,33,29,26,21,17], [8,8,10,12,15,19,22,23,21,17,13,9], [60,50,45,35,20,8,3,8,45,60,60,65]),
    "Kairouan": (35.68, 10.10, [17,19,21,25,30,35,38,38,33,28,22,18], [5,6,8,11,15,19,22,23,20,15,10,6], [25,25,30,25,20,10,3,8,30,30,25,25]),
    "Sfax":     (34.74, 10.76, [17,18,20,23,26,30,32,33,31,27,22,18], [7,7,9,12,15,19,22,23,21,17,12,8], [20,15,20,15,10,3,1,3,25,35,25,20]),
    "Gafsa":    (34.42, 8.78,  [16,18,22,25,30,35,38,38,33,27,21,17], [4,5,8,11,15,19,22,22,19,14,9,5], [15,15,20,15,15,8,2,5,15,15,15,15]),
    "Tozeur":   (33.92, 8.13,  [17,20,23,27,32,37,40,40,35,29,22,18], [5,6,9,13,17,22,25,25,22,16,10,6], [10,8,12,8,5,2,0,2,5,10,10,8]),
    "Médenine": (33.35, 10.50, [17,19,22,25,29,33,36,36,33,28,23,18], [7,8,10,13,17,21,23,24,22,18,12,8], [20,15,20,10,6,1,0,1,10,25,20,20]),
    "Sapporo":  (43.06, 141.35, [-1,0,4,11,17,21,25,26,22,16,8,2], [-7,-7,-3,3,8,13,18,19,14,7,1,-4], [110,95,80,55,55,60,90,125,135,110,105,115]),
    "Sendai":   (38.27, 140.87, [6,7,10,15,20,23,27,29,25,20,14,9], [-1,-1,1,6,11,16,20,22,18,12,6,1], [40,55,90,100,110,145,180,165,190,150,65,40]),
    "Mito":     (36.37, 140.47, [9,10,13,18,22,25,29,31,27,21,16,11], [-2,-1,2,7,12,17,21,22,18,12,5,0], [55,60,110,120,135,150,135,120,180,170,80,50]),
    "Niigata":  (37.92, 139.05, [6,7,10,16,21,25,29,31,27,21,15,9], [0,0,2,7,12,17,21,23,19,13,7,3], [185,125,115,95,95,125,190,140,155,155,200,215]),
    "Shizuoka": (34.98, 138.40, [12,12,15,19,23,26,30,31,28,23,18,14], [2,3,6,11,15,19,23,24,21,15,9,4], [80,105,200,220,215,280,280,180,280,215,140,85]),
    "Osaka":    (34.69, 135.50, [10,10,14,20,25,28,32,34,29,23,17,12], [3,3,6,11,16,20,25,26,22,16,10,5], [45,60,105,105,145,185,155,90,160,110,70,45]),
    "Kagoshima":(31.56, 130.56, [13,14,17,22,25,28,32,33,30,25,20,15], [5,5,8,12,17,21,25,25,23,17,12,7], [80,110,160,195,205,450,320,210,210,100,105,75]),
}


def _demo_history(lat, lon, years=range(1991, 2025)):
    name, (slat, slon, tx, tn, pr) = min(
        FALLBACK_STATIONS.items(), key=lambda kv: (kv[1][0] - lat) ** 2 + ((kv[1][1] - lon) * math.cos(math.radians(lat))) ** 2)
    rng = np.random.default_rng(int(abs(slat * 1000 + slon)))
    dates, tmax, tmin, rain = [], [], [], []
    d = date(years[0], 1, 1)
    end = date(years[-1], 12, 31)
    year_anom = {y: rng.normal(0, 0.8) for y in years}
    month_rain_factor = {}
    while d <= end:
        m = d.month - 1
        key = (d.year, m)
        if key not in month_rain_factor:
            month_rain_factor[key] = rng.gamma(2.0, 0.5)
        a = year_anom[d.year] + rng.normal(0, 2.2)
        tmax.append(tx[m] + a + rng.normal(0, 1.0))
        tmin.append(tn[m] + a + rng.normal(0, 1.0))
        p_day = pr[m] * month_rain_factor[key]
        wet_p = min(0.6, 0.05 + pr[m] / 300)
        rain.append(rng.exponential(p_day / (30 * wet_p)) if rng.random() < wet_p else 0.0)
        dates.append(d.strftime("%Y%m%d"))
        d += timedelta(days=1)
    return {"dates": dates, "elev": 50.0, "tmax": tmax, "tmin": tmin,
            "tmean": [(a + b) / 2 for a, b in zip(tmax, tmin)], "rain": rain,
            "rs": [None] * len(dates), "rh": [None] * len(dates), "wind": [None] * len(dates),
            "source": f"HISTORIQUE DE DÉMONSTRATION ({name})", "station": name}


def _ra(lat, doy):
    phi = math.radians(lat)
    dr = 1 + 0.033 * np.cos(2 * np.pi * doy / 365)
    dl = 0.409 * np.sin(2 * np.pi * doy / 365 - 1.39)
    ws = np.arccos(np.clip(-math.tan(phi) * np.tan(dl), -1, 1))
    return (24 * 60 / np.pi) * 0.0820 * dr * (ws * np.sin(phi) * np.sin(dl) + np.cos(phi) * np.cos(dl) * np.sin(ws))


def eto_penman_monteith(tmax, tmin, rs, rh, u2, lat, elev, doy):
    """FAO-56 éq. 6, pas de temps journalier. Rs en MJ/m²/j, u2 en m/s, rh en %."""
    tmean = (tmax + tmin) / 2
    P = 101.3 * ((293 - 0.0065 * elev) / 293) ** 5.26
    gamma = 0.000665 * P
    es_t = lambda t: 0.6108 * np.exp(17.27 * t / (t + 237.3))
    es = (es_t(tmax) + es_t(tmin)) / 2
    ea = es * rh / 100
    delta = 4098 * es_t(tmean) / (tmean + 237.3) ** 2
    ra = _ra(lat, doy)
    rso = (0.75 + 2e-5 * elev) * ra
    rns = 0.77 * rs
    sigma = 4.903e-9
    rnl = sigma * (((tmax + 273.16) ** 4 + (tmin + 273.16) ** 4) / 2) * (0.34 - 0.14 * np.sqrt(np.clip(ea, 0, None))) \
        * (1.35 * np.clip(rs / np.where(rso > 0, rso, np.nan), 0, 1) - 0.35)
    rn = rns - rnl
    eto = (0.408 * delta * rn + gamma * 900 / (tmean + 273) * u2 * (es - ea)) / (delta + gamma * (1 + 0.34 * u2))
    return np.clip(eto, 0, None)


def eto_hargreaves(tmax, tmin, lat, doy):
    ra = 0.408 * _ra(lat, doy)
    return np.clip(0.0023 * ra * ((tmax + tmin) / 2 + 17.8) * np.sqrt(np.clip(tmax - tmin, 0, None)), 0, None)


def load_history(lat, lon, online=True):
    """Retourne un dict de tableaux numpy alignés jour par jour + métadonnées."""
    raw, demo = None, False
    if online:
        try:
            raw = nasa_power_daily(lat, lon)
        except SourceUnavailable:
            raw = None
    if raw is None:
        raw, demo = _demo_history(lat, lon), True

    arr = lambda k: np.array([np.nan if v is None else v for v in raw[k]], dtype=float)
    tmax, tmin, rain = arr("tmax"), arr("tmin"), arr("rain")
    rs, rh, wind = arr("rs"), arr("rh"), arr("wind")
    dates = raw["dates"]
    year = np.array([int(d[:4]) for d in dates])
    month = np.array([int(d[4:6]) for d in dates])
    doy = np.array([date(int(d[:4]), int(d[4:6]), int(d[6:])).timetuple().tm_yday for d in dates])
    # interpolation des rares trous
    for a in (tmax, tmin, rain):
        bad = np.isnan(a)
        if bad.any() and (~bad).any():
            a[bad] = np.interp(np.flatnonzero(bad), np.flatnonzero(~bad), a[~bad])
    rain = np.clip(rain, 0, None)
    pm_ok = ~(np.isnan(rs) | np.isnan(rh) | np.isnan(wind))
    eto = eto_hargreaves(tmax, tmin, lat, doy)
    if pm_ok.any():
        eto[pm_ok] = eto_penman_monteith(tmax[pm_ok], tmin[pm_ok], rs[pm_ok], rh[pm_ok],
                                         wind[pm_ok], lat, raw["elev"], doy[pm_ok])
    method = "pm" if pm_ok.mean() > 0.9 else "hg"
    return {"year": year, "month": month, "doy": doy, "tmax": tmax, "tmin": tmin,
            "tmean": (tmax + tmin) / 2, "rain": rain, "eto": eto,
            "years": sorted(set(year.tolist())), "elev": raw["elev"],
            "source": raw["source"], "eto_method": method, "demo": demo, "station": raw.get("station")}


def monthly_normals(h):
    out = {"tmax": [], "tmin": [], "rain": [], "eto": []}
    ny = len(h["years"])
    for m in range(1, 13):
        s = h["month"] == m
        out["tmax"].append(round(float(h["tmax"][s].mean()), 1))
        out["tmin"].append(round(float(h["tmin"][s].mean()), 1))
        out["rain"].append(round(float(h["rain"][s].sum() / ny), 1))
        out["eto"].append(round(float(h["eto"][s].sum() / ny), 1))
    return out

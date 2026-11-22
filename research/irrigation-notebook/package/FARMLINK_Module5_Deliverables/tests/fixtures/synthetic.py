"""SYNTHETIC demo/test data. Never real observations; used only by tests and clearly labelled demos."""
import numpy as np
import pandas as pd


def synthetic_weather(start="2026-04-20", days=45, seed=0, rain_days=()):
    rng = np.random.default_rng(seed)
    d = pd.date_range(start, periods=days)
    doy = d.dayofyear.values
    tmean = 17 + 8 * np.sin((doy - 100) / 365 * 2 * np.pi) + rng.normal(0, 1, days)
    df = pd.DataFrame({"date": d, "tmean": tmean, "tmax": tmean + 6, "tmin": tmean - 6, "rh_mean": 55 + rng.normal(0, 5, days),
                       "u2": 2.0 + rng.normal(0, .3, days).clip(-1, 1), "rs": 22 + rng.normal(0, 2, days), "rain_mm": 0.0})
    for i in rain_days: df.loc[i, "rain_mm"] = 8.0
    df["weather_source"] = "SYNTHETIC_FIXTURE"
    return df

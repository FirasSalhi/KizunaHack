"""Market, production and price KPIs computed from the processed tables.

Vocabulary: "arrivals" are tonnes entering the Tunis wholesale market. They are not national
production and not consumer purchases.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from . import crops as C

PROCESSED = Path(__file__).resolve().parents[1] / "data" / "processed"
MONTHS_FR = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]
AGGREGATES = {"total_vegetables", "total_fruits", "other_vegetables", "other_fruits"}


@dataclass
class Data:
    veg: pd.DataFrame
    arrivals: pd.DataFrame
    retail: pd.DataFrame
    faostat: pd.DataFrame
    sidi_bouzid: pd.DataFrame
    fruits: pd.DataFrame
    climate: pd.DataFrame
    cpi: pd.DataFrame
    smag: pd.DataFrame
    tariff: pd.DataFrame


def load(folder: Path = PROCESSED) -> Data:
    r = lambda n, **k: pd.read_csv(folder / f"{n}.csv", **k)  # noqa: E731
    return Data(
        veg=r("national_vegetables"),
        arrivals=r("tunis_wholesale_arrivals", parse_dates=["date"]),
        retail=r("tunis_retail_prices", parse_dates=["date"]),
        faostat=r("faostat_tunisia"),
        sidi_bouzid=r("sidi_bouzid_market", parse_dates=["date"]),
        fruits=r("national_fruits"),
        climate=r("climate_governorates"),
        cpi=r("cpi"),
        smag=r("smag"),
        tariff=r("water_tariff_secadenord"),
    )


def name_fr(crop_id: str) -> str:
    special = {"total_vegetables": "Total légumes", "total_fruits": "Total fruits",
               "other_vegetables": "Autres légumes", "other_fruits": "Autres fruits",
               "citrus_total": "Agrumes (total)", "orange_navel": "Orange navel", "mandarin": "Mandarine",
               "olive_oil_olive": "Olive à huile", "table_olive": "Olive de table", "grape_wine": "Raisin de cuve",
               "almond_dry": "Amande sèche", "quince": "Coing", "loquat_cherry": "Nèfle et cerise",
               "pistachio": "Pistache"}
    return special.get(crop_id) or (C.BY_ID[crop_id].fr if crop_id in C.BY_ID else crop_id)


# ------------------------------------------------------------------ seasons
def season_of(date: pd.Timestamp) -> str:
    """Agricultural campaign September -> August, e.g. 2024/25."""
    start = date.year if date.month >= 9 else date.year - 1
    return f"{start}/{str(start + 1)[-2:]}"


def season_months(season: str) -> list[pd.Timestamp]:
    start = int(season[:4])
    return list(pd.date_range(f"{start}-09-01", f"{start + 1}-08-01", freq="MS"))


def with_season(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["season"] = df.date.map(season_of)
    return df


def season_coverage(arrivals: pd.DataFrame) -> pd.DataFrame:
    """Months with a published figure per season (based on the vegetable total row)."""
    t = with_season(arrivals[arrivals.crop_id == "total_vegetables"])
    cov = t.groupby("season").agg(months_reported=("status", lambda s: int((s == "ok").sum())),
                                  months_in_data=("status", "size")).reset_index()
    cov["missing_months"] = cov.season.map(
        lambda s: [d.strftime("%Y-%m") for d in season_months(s)
                   if not ((t.date == d) & (t.status == "ok")).any()])
    cov["complete"] = cov.months_reported == 12
    return cov


def latest_complete_season(arrivals: pd.DataFrame) -> str | None:
    cov = season_coverage(arrivals)
    full = cov[cov.complete]
    return full.season.max() if len(full) else None


# ------------------------------------------------------------------ KPI group A: Tunis market
def _monthly_arrivals(arrivals: pd.DataFrame) -> pd.DataFrame:
    """'///' (no arrivals that month) counts as 0 t; '…' (not available) stays missing."""
    a = with_season(arrivals)
    a["t"] = np.where(a.status == "no_arrivals", 0.0, a.arrivals_t)
    return a


def arrivals_kpis(arrivals: pd.DataFrame, season: str, previous: str | None = None) -> pd.DataFrame:
    a = _monthly_arrivals(arrivals)
    if previous is None:
        start = int(season[:4]) - 1
        previous = f"{start}/{str(start + 1)[-2:]}"
    cur, prev = a[a.season == season], a[a.season == previous]
    rows = []
    for (crop, section), g in cur.groupby(["crop_id", "section"]):
        g = g.sort_values("date")
        known = g.dropna(subset=["t"])
        if known.empty:
            continue
        pos = known[known.t > 0]
        p = prev[prev.crop_id == crop].dropna(subset=["t"])
        common = set(known.date.dt.month) & set(p.date.dt.month)
        cur_c = known[known.date.dt.month.isin(common)].t.sum()
        prev_c = p[p.date.dt.month.isin(common)].t.sum()
        yoy = (cur_c - prev_c) / prev_c * 100 if prev_c > 0 and len(common) >= 9 else np.nan
        rows.append({
            "crop_id": crop, "crop": name_fr(crop), "category": section,
            "total_t": known.t.sum(), "months_reported": len(known),
            "months_with_arrivals": len(pos),
            "avg_monthly_t": known.t.sum() / len(known),
            "avg_monthly_when_present_t": pos.t.mean() if len(pos) else np.nan,
            "peak_month": pos.loc[pos.t.idxmax(), "date"] if len(pos) else pd.NaT,
            "peak_t": pos.t.max() if len(pos) else np.nan,
            "low_month": pos.loc[pos.t.idxmin(), "date"] if len(pos) else pd.NaT,
            "low_t": pos.t.min() if len(pos) else np.nan,
            "yoy_pct": yoy, "yoy_months_compared": len(common), "previous_season": previous,
        })
    return pd.DataFrame(rows)


def top_by_arrivals(k: pd.DataFrame, category: str, n: int = 5) -> pd.DataFrame:
    d = k[(k.category == category) & ~k.crop_id.isin(AGGREGATES)]
    return d.sort_values("total_t", ascending=False).head(n)


def arrival_movers(k: pd.DataFrame, min_tonnes: float = 2000, n: int = 5) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Strongest increase / decline vs previous season, ignoring small volumes (noise)."""
    d = k[~k.crop_id.isin(AGGREGATES) & k.yoy_pct.notna() & (k.total_t >= min_tonnes)]
    return (d.sort_values("yoy_pct", ascending=False).head(n),
            d[d.yoy_pct < 0].sort_values("yoy_pct").head(n))


def seasonality(arrivals: pd.DataFrame, crop_id: str) -> pd.DataFrame:
    """Average tonnes per calendar month over all seasons with data."""
    a = _monthly_arrivals(arrivals)
    g = a[a.crop_id == crop_id].dropna(subset=["t"])
    out = g.groupby(g.date.dt.month).t.agg(["mean", "count"]).reindex(range(1, 13)).reset_index()
    out.columns = ["month", "avg_t", "n_years"]
    out["month_name"] = [MONTHS_FR[m - 1] for m in out.month]
    return out


# ------------------------------------------------------------------ KPI group C: prices
def retail_kpis(retail: pd.DataFrame, season: str) -> pd.DataFrame:
    r = with_season(retail)
    start = int(season[:4]) - 1
    previous = f"{start}/{str(start + 1)[-2:]}"
    rows = []
    for crop, g in r.groupby("crop_id"):
        cur = g[(g.season == season)].dropna(subset=["retail_price_dt_kg"])
        prev = g[(g.season == previous)].dropna(subset=["retail_price_dt_kg"])
        if cur.empty:
            continue
        common = set(cur.date.dt.month) & set(prev.date.dt.month)
        yoy = (cur[cur.date.dt.month.isin(common)].retail_price_dt_kg.mean()
               / prev[prev.date.dt.month.isin(common)].retail_price_dt_kg.mean() - 1) * 100 if len(common) >= 6 else np.nan
        rows.append({"crop_id": crop, "crop": name_fr(crop), "avg_dt_kg": cur.retail_price_dt_kg.mean(),
                     "min_dt_kg": cur.retail_price_dt_kg.min(), "max_dt_kg": cur.retail_price_dt_kg.max(),
                     "cv_pct": cur.retail_price_dt_kg.std(ddof=0) / cur.retail_price_dt_kg.mean() * 100,
                     "months": len(cur), "yoy_pct": yoy, "yoy_months_compared": len(common)})
    return pd.DataFrame(rows)


def deflate(values: pd.Series, years: pd.Series, cpi: pd.DataFrame, to_year: int | None = None) -> pd.Series:
    """Express nominal DT in constant DT of `to_year` (default: latest CPI year)."""
    c = cpi.set_index("year").cpi
    to_year = to_year or int(c.index.max())
    factor = years.map(lambda y: c.get(to_year) / c.get(y) if y in c.index else np.nan)
    return values * factor


def _slope_pct(years: pd.Series, values: pd.Series) -> float:
    """Average yearly change (%) from a log-linear fit."""
    m = values.notna() & (values > 0)
    if m.sum() < 4:
        return np.nan
    b = np.polyfit(years[m].astype(float), np.log(values[m].astype(float)), 1)[0]
    return (np.exp(b) - 1) * 100


def producer_price_kpis(veg: pd.DataFrame, cpi: pd.DataFrame, last_n: int = 10) -> pd.DataFrame:
    v = veg.dropna(subset=["producer_price_dt_t"]).copy()
    v["real_price_dt_t"] = deflate(v.producer_price_dt_t, v.year, cpi)
    rows = []
    for crop, g in v.groupby("crop_id"):
        g = g.sort_values("year")
        w = g[g.year > g.year.max() - last_n]
        last = g.iloc[-1]
        prev = g[g.year == last.year - 1]
        rows.append({
            "crop_id": crop, "crop": name_fr(crop), "last_year": int(last.year),
            "price_dt_kg": last.producer_price_dt_t / 1000,
            "yoy_pct": (last.producer_price_dt_t / prev.producer_price_dt_t.iloc[0] - 1) * 100 if len(prev) else np.nan,
            "nominal_trend_pct_yr": _slope_pct(w.year, w.producer_price_dt_t),
            "real_trend_pct_yr": _slope_pct(w.year, w.real_price_dt_t),
            "volatility_pct": (np.log(w.producer_price_dt_t).diff().std() * 100) if len(w) > 3 else np.nan,
            "years": f"{int(w.year.min())}-{int(w.year.max())}",
        })
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ KPI group B: production
def production_kpis(veg: pd.DataFrame, last_n: int = 10) -> pd.DataFrame:
    rows = []
    for crop, g in veg.groupby("crop_id"):
        g = g.sort_values("year")
        w = g[g.year > g.year.max() - last_n]
        last = g.dropna(subset=["production_t"]).iloc[-1]
        prev = g[g.year == last.year - 1]
        rows.append({
            "crop_id": crop, "crop": name_fr(crop), "last_year": int(last.year),
            "production_t": last.production_t, "area_ha": last.area_ha, "yield_t_ha": last.yield_t_ha,
            "production_yoy_pct": (last.production_t / prev.production_t.iloc[0] - 1) * 100 if len(prev) else np.nan,
            "production_trend_pct_yr": _slope_pct(w.year, w.production_t),
            "area_trend_pct_yr": _slope_pct(w.year, w.area_ha),
            "yield_trend_pct_yr": _slope_pct(w.year, w.yield_t_ha),
            "yield_cv_pct": w.yield_t_ha.std() / w.yield_t_ha.mean() * 100 if w.yield_t_ha.notna().sum() > 2 else np.nan,
            "years": f"{int(w.year.min())}-{int(w.year.max())}",
        })
    return pd.DataFrame(rows)


def price_gap(veg: pd.DataFrame, retail: pd.DataFrame, crop_id: str, retail_crop: str | None = None) -> pd.DataFrame:
    """Tunis retail average minus national producer price, by calendar year.

    This is a difference between two price levels measured in different places; it is not a
    farmer profit or a retailer margin.
    """
    r = retail[retail.crop_id == (retail_crop or crop_id)].dropna(subset=["retail_price_dt_kg"])
    ry = r.groupby(r.date.dt.year).agg(retail_dt_kg=("retail_price_dt_kg", "mean"), months=("retail_price_dt_kg", "size"))
    p = veg[veg.crop_id == crop_id].set_index("year").producer_price_dt_t / 1000
    out = ry[ry.months >= 10].join(p.rename("producer_dt_kg"), how="inner").reset_index(names="year")
    out["difference_dt_kg"] = out.retail_dt_kg - out.producer_dt_kg
    return out

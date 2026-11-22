"""Export the few farmer-facing KPIs as JSON and build the simple visual page.

Usage (from research/market-advisor):  python scripts/build_simple_dashboard.py
Writes  data/processed/dashboard_kpis.json   (for the main FARMLINK dashboard)
        html/marche_simple.html               (stand-alone page, data embedded)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from farmlink_market import advisor as A  # noqa: E402
from farmlink_market import crops as C  # noqa: E402
from farmlink_market import kpis as K  # noqa: E402

AR_EXTRA = {"total_vegetables": "مجموع الخضر", "total_fruits": "مجموع الغلال"}


def r(x, n=0):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), n)


def crop_names(cid: str) -> dict:
    c = C.BY_ID.get(cid)
    return {"id": cid, "fr": K.name_fr(cid), "ar": c.ar if c else AR_EXTRA.get(cid, "")}


def best_months(d: K.Data) -> dict:
    """Seasonal retail-price index (Tunis): month price / that season's average, averaged over seasons."""
    out = {}
    ret = K.with_season(d.retail.dropna(subset=["retail_price_dt_kg"]))
    arr = K._monthly_arrivals(d.arrivals)
    for cid, g in ret.groupby("crop_id"):
        g = g.copy()
        g["idx"] = g.retail_price_dt_kg / g.groupby("season").retail_price_dt_kg.transform("mean")
        full = g.groupby("season").filter(lambda s: len(s) >= 10)
        if full.season.nunique() < 2:
            continue
        idx = full.groupby(full.date.dt.month).idx.mean().reindex(range(1, 13))
        last12 = g[g.date > g.date.max() - pd.DateOffset(months=12)].retail_price_dt_kg.mean()
        a = arr[arr.crop_id == cid].dropna(subset=["t"])
        am = a.groupby(a.date.dt.month).t.mean().reindex(range(1, 13))
        out[cid] = {**crop_names(cid),
                    "price_index": [r(v * 100) for v in idx],
                    "typical_price": [r(v * last12, 2) if not np.isnan(v) else None for v in idx],
                    "arrivals_t": [r(v) for v in am],
                    "seasons": int(full.season.nunique()),
                    "best_month": int(idx.idxmax()), "worst_month": int(idx.idxmin())}
    return out


def main() -> None:
    d = K.load()
    season = K.latest_complete_season(d.arrivals)
    k = K.arrivals_kpis(d.arrivals, season)
    totals = {row.crop_id: {"tonnes": r(row.total_t), "change_pct": r(row.yoy_pct, 1)}
              for row in k[k.crop_id.isin(["total_vegetables", "total_fruits"])].itertuples()}
    top = {}
    for cat in ("vegetable", "fruit"):
        top[cat] = [{**crop_names(x.crop_id), "tonnes": r(x.total_t), "change_pct": r(x.yoy_pct, 1),
                     "peak_month": int(x.peak_month.month)} for x in K.top_by_arrivals(k, cat).itertuples()]
    prices = [{**crop_names(x.crop_id), "price_dt_kg": r(x.price_dt_kg, 2), "year": x.last_year,
               "real_trend_pct_yr": r(x.real_trend_pct_yr, 1), "years": x.years}
              for x in K.producer_price_kpis(d.veg, d.cpi).itertuples() if x.crop_id != "other_vegetables"]
    advice = {}
    for gov in sorted(d.climate.governorate.unique()):
        advice[gov] = {}
        for w in ("limited", "moderate", "abundant"):
            table, res = A.recommend(d, A.FarmerInput(governorate=gov, area_ha=1, water=w))
            by = {x["crop_id"]: x for x in res if x["status"] == "OK"}
            advice[gov][w] = [{**crop_names(c), "score": r(by[c]["score"]),
                               "revenue_ha": {k2: r(v, -2) for k2, v in by[c]["revenue_ha"].items()},
                               "water_m3_ha": r(by[c]["water"]["gross_m3_ha"], -1) if by[c]["water"] else None,
                               "price_trend_pct_yr": r(by[c]["real_price_trend_pct_yr"], 1),
                               "planting_month": by[c]["water"]["planting_month"] if by[c]["water"] else None}
                              for c in table.crop_id]
    out = {
        "season": season, "season_months": "septembre → août",
        "market": "Marché de gros de Tunis (apports, pas la consommation)",
        "totals": totals, "top": top, "best_months": best_months(d), "producer_prices": prices,
        "advice": advice,
        "sources": {
            "arrivals": "INS, Bulletin mensuel de la statistique, tableau 9.5 (Marché de gros de Tunis)",
            "retail": "INS, Bulletin mensuel, tableau 9.1 (prix de détail à Tunis)",
            "producer": "Ministère de l'Agriculture, data.gov.tn (séries nationales 2004-2025)",
            "water": "FAO-56 + climat NASA POWER par gouvernorat (estimation, goutte-à-goutte)",
        },
        "notes": ["Scores relatifs entre les 6 cultures qui ont assez de données officielles.",
                  "Revenus = fourchette 2016-2025 en dinars constants, sans les coûts de production.",
                  "Prix = prix payé au producteur (national), pas le prix au marché."],
    }
    js = json.dumps(out, ensure_ascii=False, indent=1)
    (ROOT / "data" / "processed" / "dashboard_kpis.json").write_text(js, encoding="utf-8")
    tpl = (ROOT / "scripts" / "simple_dashboard_template.html").read_text(encoding="utf-8")
    (ROOT / "html").mkdir(exist_ok=True)
    (ROOT / "html" / "marche_simple.html").write_text(tpl.replace("__DATA__", js), encoding="utf-8")
    print("season", season, "| best-month crops", len(out["best_months"]), "| governorates", len(advice))


if __name__ == "__main__":
    main()

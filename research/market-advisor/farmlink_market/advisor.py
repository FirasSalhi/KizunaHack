"""Transparent crop investment advisor.

Revenue  = expected yield (t/ha) x expected producer price (DT/t) x area
Cost     = seeds + fertilisers + pesticides + labour + water + energy + equipment + other   (per ha x area)
Profit   = revenue - cost ;  profit per ha = profit / area

Scenarios come from the crop's own history (last 10 years of national yield x producer price,
expressed in constant dinars of the latest CPI year): pessimistic = 20th percentile, expected =
median, optimistic = 80th percentile of yearly revenue per hectare. These are historical ranges,
not forecasts.

Scores are relative: each criterion is min-max normalised across the crops being compared
(0 = weakest of the list, 100 = strongest). Weights are design assumptions, adjustable by the user.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from . import crops as C
from .kpis import Data, _slope_pct, deflate, name_fr

REFERENCE = Path(__file__).resolve().parents[1] / "data" / "raw" / "reference" / "fao56_crop_database.json"
DEFAULT_WEIGHTS = {"market": 0.30, "productivity": 0.25, "profitability": 0.25, "water": 0.20}
WATER_WEIGHT_FACTOR = {"limited": 1.5, "moderate": 1.0, "abundant": 0.5}
# FAO irrigation application efficiencies (FAO Irrigation & Drainage Paper 24 / 56 ranges, mid values)
IRRIGATION_EFFICIENCY = {"drip": 0.90, "sprinkler": 0.75, "surface": 0.60}
IRRIGATION_FR = {"drip": "goutte-à-goutte", "sprinkler": "aspersion", "surface": "gravitaire"}
MONTHS_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
             "novembre", "décembre"]
COST_KEYS = ["seeds", "fertilisers", "pesticides", "labour", "energy", "equipment", "other"]
MONTHS = {"jan": 1, "feb": 2, "fév": 2, "mar": 3, "apr": 4, "avr": 4, "april": 4, "may": 5, "mai": 5, "jun": 6,
          "june": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12, "déc": 12, "january": 1,
          "november": 11, "october": 10, "december": 12, "march": 3}


# ------------------------------------------------------------------ water requirement (FAO-56)
def _fao56() -> dict[str, dict]:
    return {c["id"]: c for c in json.loads(REFERENCE.read_text(encoding="utf-8"))["crops"]}


def default_planting_month(fao56_id: str) -> int | None:
    c = _fao56().get(fao56_id)
    txt = ((c or {}).get("stage_lengths_days") or {}).get("plant_date") or ""
    for tok in txt.replace("/", " ").replace(";", " ").lower().split():
        if tok[:3] in MONTHS or tok in MONTHS:
            return MONTHS.get(tok, MONTHS.get(tok[:3]))
    return None


@dataclass
class WaterNeed:
    crop_et_mm: float
    effective_rain_mm: float
    net_irrigation_mm: float
    gross_m3_ha: float
    season_days: int
    planting_month: int
    efficiency: float
    method: str = "FAO-56 single Kc x Hargreaves ETo (NASA POWER climatology); USDA-SCS effective rain"


def water_need(fao56_id: str | None, climate_gov: pd.DataFrame, planting_month: int | None,
               efficiency: float) -> WaterNeed | None:
    """Seasonal irrigation need for one crop, governorate and planting month. None if FAO-56 data are missing."""
    c = _fao56().get(fao56_id or "")
    if not c:
        return None
    st = c.get("stage_lengths_days") or {}
    if not all(st.get(k) for k in ("ini", "dev", "mid", "late")):
        return None
    pm = planting_month or default_planting_month(fao56_id)
    if not pm:
        return None
    kc = c["kc"]
    ini, dev, mid, late = (int(st[k]) for k in ("ini", "dev", "mid", "late"))
    total = ini + dev + mid + late
    cl = climate_gov.set_index("month")
    days_in = {m: (31 if m in (1, 3, 5, 7, 8, 10, 12) else 30 if m != 2 else 28.25) for m in range(1, 13)}
    et = rain = 0.0
    start = pd.Timestamp(2001, pm, 1)
    for d in range(total):
        if d < ini:
            k = kc["ini"]
        elif d < ini + dev:
            k = kc["ini"] + (kc["mid"] - kc["ini"]) * (d - ini) / dev
        elif d < ini + dev + mid:
            k = kc["mid"]
        else:
            k = kc["mid"] + (kc["end"] - kc["mid"]) * (d - ini - dev - mid) / late
        m = (start + pd.Timedelta(days=d)).month
        et += k * cl.loc[m, "eto_mm"] / days_in[m]
        rain += cl.loc[m, "eff_rain_mm"] / days_in[m]
    net = max(0.0, et - rain)
    return WaterNeed(et, rain, net, net * 10 / efficiency, total, pm, efficiency)


# ------------------------------------------------------------------ evidence per crop
@dataclass
class Evidence:
    crop_id: str
    level: str  # "A" official national series | "B" FAOSTAT official-flag values | "insufficient"
    history: pd.DataFrame  # year, yield_t_ha, price_dt_t, real_price_dt_t, real_revenue_dt_ha
    sources: list[str]
    reason: str = ""


def evidence(data: Data, crop_id: str, window: int = 10, min_years: int = 5) -> Evidence:
    crop = C.BY_ID.get(crop_id)
    if crop and crop.perennial:
        return Evidence(crop_id, "insufficient", pd.DataFrame(), [],
                        "Culture pérenne : coûts d'installation et années avant la première récolte non disponibles "
                        "dans les sources officielles ; un calcul sur une seule saison serait trompeur.")
    v = data.veg[data.veg.crop_id == crop_id].dropna(subset=["yield_t_ha", "producer_price_dt_t"])
    if len(v) >= min_years:
        h = v[["year", "yield_t_ha", "producer_price_dt_t"]].rename(columns={"producer_price_dt_t": "price_dt_t"})
        level, src = "A", ["Ministère de l'Agriculture (data.gov.tn) : rendement et prix à la production, national"]
    else:
        f = data.faostat[(data.faostat.crop_id == crop_id) & (data.faostat.flag == "A")]
        y = f[f.element == "yield_t_ha"].set_index("year").value.rename("yield_t_ha")
        p = f[f.element == "producer_price_dt_t"].set_index("year").value.rename("price_dt_t")
        h = pd.concat([y, p], axis=1, join="inner").reset_index(names="year")
        level, src = "B", ["FAOSTAT (valeurs officielles, drapeau A) : rendement et prix à la production, Tunisie"]
    latest = int(data.veg.year.max())  # most recent official agricultural year in the data
    h = h[h.year > latest - window] if len(h) else h
    if len(h) < min_years:
        return Evidence(crop_id, "insufficient", h, [],
                        f"Moins de {min_years} années entre {latest - window + 1} et {latest} avec à la fois un "
                        f"rendement et un prix à la production officiels.")
    h = h.sort_values("year").copy()
    h["real_price_dt_t"] = deflate(h.price_dt_t, h.year, data.cpi)
    h["real_revenue_dt_ha"] = h.yield_t_ha * h.real_price_dt_t
    return Evidence(crop_id, level, h, src)


# ------------------------------------------------------------------ farmer inputs and results
@dataclass
class FarmerInput:
    governorate: str
    area_ha: float
    budget_dt: float | None = None
    water: str = "moderate"  # limited | moderate | abundant
    water_available_m3: float | None = None
    irrigation: str = "drip"
    category: str | None = None  # vegetable | fruit | None
    candidates: list[str] | None = None
    costs_per_ha: dict[str, dict[str, float]] = field(default_factory=dict)  # crop -> {cost key: DT/ha}
    planting_month: dict[str, int] = field(default_factory=dict)
    water_tariff_dt_m3: float | None = None
    weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))


ADVISABLE = ["tomato", "potato", "onion", "pepper", "watermelon_melon", "artichoke", "carrot", "cabbage",
             "cauliflower", "cucumber", "squash", "spinach", "faba_bean", "pea", "lettuce", "garlic", "melon",
             "watermelon", "strawberry", "apricot", "peach", "apple", "lemon", "orange", "date", "grape", "olive"]


def default_tariff(data: Data) -> tuple[float, str]:
    t = data.tariff[data.tariff.agricultural_client]
    y = int(t.year.max())
    return float(t[t.year == y].tariff_dt_m3.median()), f"médiane des tarifs SECADENORD aux CRDA, {y} (nord du pays)"


def analyse_crop(data: Data, fi: FarmerInput, crop_id: str) -> dict:
    crop = C.BY_ID[crop_id]
    ev = evidence(data, crop_id)
    out: dict = {"crop_id": crop_id, "crop": name_fr(crop_id), "category": crop.category, "evidence": ev.level,
                 "sources": ev.sources, "reason": ev.reason, "missing": [], "assumptions": [], "risks": []}
    if ev.level == "insufficient":
        out["status"] = "Insufficient evidence"
        return out
    h = ev.history
    out["years"] = f"{int(h.year.min())}-{int(h.year.max())}"
    out["n_years"] = len(h)
    rev = h.real_revenue_dt_ha
    out["revenue_ha"] = {"pessimistic": float(np.percentile(rev, 20)), "expected": float(np.median(rev)),
                         "optimistic": float(np.percentile(rev, 80))}
    out["yield_t_ha"] = float(h.yield_t_ha.tail(5).median())
    out["price_dt_kg"] = float(h.real_price_dt_t.tail(5).median() / 1000)
    out["real_price_trend_pct_yr"] = _slope_pct(h.year, h.real_price_dt_t)
    out["price_volatility_pct"] = float(np.log(h.price_dt_t).diff().std() * 100)
    out["yield_trend_pct_yr"] = _slope_pct(h.year, h.yield_t_ha)
    out["yield_cv_pct"] = float(h.yield_t_ha.std() / h.yield_t_ha.mean() * 100)
    cpi_year = int(data.cpi.year.max())
    out["assumptions"] += [
        f"Rendement et prix = moyennes nationales {out['years']} ; votre parcelle peut différer.",
        f"Prix exprimés en dinars constants {cpi_year} (indice des prix à la consommation, Banque mondiale).",
        "Scénarios = 20e, 50e et 80e percentiles du revenu historique par hectare (pas une prévision).",
    ]
    # water
    clim = data.climate[data.climate.governorate == fi.governorate]
    eff = IRRIGATION_EFFICIENCY.get(fi.irrigation, 0.75)
    wn = water_need(crop.fao56, clim, fi.planting_month.get(crop_id), eff) if len(clim) else None
    tariff, tariff_note = default_tariff(data)
    if fi.water_tariff_dt_m3 is not None and abs(fi.water_tariff_dt_m3 - tariff) > 5e-4:
        tariff, tariff_note = fi.water_tariff_dt_m3, "tarif saisi par l'utilisateur"
    if wn:
        out["water"] = wn.__dict__
        out["water_cost_ha"] = wn.gross_m3_ha * tariff
        out["assumptions"].append(
            f"Eau : besoin calculé pour {fi.governorate}, semis en {MONTHS_FR[wn.planting_month - 1]}, efficience "
            f"{eff:.0%} ({IRRIGATION_FR.get(fi.irrigation, fi.irrigation)}) ; prix de l'eau {tariff:.3f} DT/m³ ({tariff_note}).")
        if fi.water_available_m3 is not None and wn.gross_m3_ha * fi.area_ha > fi.water_available_m3:
            out["risks"].append(f"L'eau disponible ({fi.water_available_m3:.0f} m³) ne couvre que "
                                f"{fi.water_available_m3 / wn.gross_m3_ha:.1f} ha sur {fi.area_ha:g} ha.")
    else:
        out["water"] = None
        out["water_cost_ha"] = None
        out["missing"].append("Besoin en eau : durées de cycle FAO-56 non disponibles pour cette culture.")
    # costs
    user = {k: float(v) for k, v in (fi.costs_per_ha.get(crop_id) or {}).items() if v not in (None, "") and float(v) > 0}
    cost_ha = sum(user.values()) + (out["water_cost_ha"] or 0.0)
    out["costs_entered"] = bool(user)
    out["cost_ha"] = cost_ha
    out["cost_detail"] = {**user, "water (calculé)": out["water_cost_ha"]}
    if not user:
        out["missing"].append("Coûts de production : aucune source officielle par culture ; saisissez vos coûts "
                              "pour obtenir un bénéfice (seule l'eau est estimée).")
    out["scenarios"] = {}
    for s, r in out["revenue_ha"].items():
        revenue = r * fi.area_ha
        cost = cost_ha * fi.area_ha
        out["scenarios"][s] = {"revenue": revenue, "cost": cost,
                               "profit": revenue - cost if user else None,
                               "profit_ha": (revenue - cost) / fi.area_ha if user else None}
    if fi.budget_dt and user and cost_ha * fi.area_ha > fi.budget_dt:
        out["risks"].append(f"Coût total estimé ({cost_ha * fi.area_ha:.0f} DT) supérieur au budget ({fi.budget_dt:.0f} DT).")
    if out["price_volatility_pct"] > 25:
        out["risks"].append(f"Prix à la production instable : variation typique de ±{out['price_volatility_pct']:.0f} % d'une année à l'autre.")
    if out["real_price_trend_pct_yr"] < -1:
        out["risks"].append(f"Prix réel en baisse de {abs(out['real_price_trend_pct_yr']):.1f} %/an sur {out['years']}.")
    if out["yield_trend_pct_yr"] < -1:
        out["risks"].append(f"Rendement national en baisse de {abs(out['yield_trend_pct_yr']):.1f} %/an.")
    pess = out["scenarios"]["pessimistic"]["profit"]
    if pess is not None and pess < 0:
        out["risks"].append("Perte possible dans le scénario pessimiste.")
    if crop.group or crop_id in ("pepper", "watermelon_melon"):
        out["assumptions"].append("Série nationale publiée pour un groupe de cultures : "
                                  + "; ".join(crop.notes or ("voir la fiche culture",)))
    out["status"] = "OK"
    return out


def _norm(values: dict[str, float | None], higher_is_better: bool = True) -> dict[str, float | None]:
    xs = [v for v in values.values() if v is not None and not math.isnan(v)]
    if not xs:
        return {k: None for k in values}
    lo, hi = min(xs), max(xs)
    res = {}
    for k, v in values.items():
        if v is None or math.isnan(v):
            res[k] = None
        elif hi == lo:
            res[k] = 50.0
        else:
            s = (v - lo) / (hi - lo) * 100
            res[k] = s if higher_is_better else 100 - s
    return res


def _mean(*vals: float | None) -> float | None:
    v = [x for x in vals if x is not None]
    return sum(v) / len(v) if v else None


def recommend(data: Data, fi: FarmerInput) -> tuple[pd.DataFrame, list[dict]]:
    ids = fi.candidates or [c for c in ADVISABLE if fi.category in (None, C.BY_ID[c].category)]
    results = [analyse_crop(data, fi, c) for c in ids]
    ok = [r for r in results if r["status"] == "OK"]
    if not ok:
        return pd.DataFrame(), results
    g = lambda key: {r["crop_id"]: r.get(key) for r in ok}  # noqa: E731
    price_trend, price_stab = _norm(g("real_price_trend_pct_yr")), _norm(g("price_volatility_pct"), False)
    yield_trend, yield_stab = _norm(g("yield_trend_pct_yr")), _norm(g("yield_cv_pct"), False)
    profit_basis = {r["crop_id"]: (r["scenarios"]["expected"]["profit_ha"] if r["costs_entered"]
                                   else r["revenue_ha"]["expected"] - (r["water_cost_ha"] or 0)) for r in ok}
    profit = _norm(profit_basis)
    water = _norm({r["crop_id"]: (r["water"]["gross_m3_ha"] if r["water"] else None) for r in ok}, False)
    w = dict(fi.weights)
    w["water"] = w.get("water", 0) * WATER_WEIGHT_FACTOR.get(fi.water, 1.0)
    rows = []
    for r in ok:
        cid = r["crop_id"]
        comp = {"market": _mean(price_trend[cid], price_stab[cid]),
                "productivity": _mean(yield_trend[cid], yield_stab[cid]),
                "profitability": profit[cid], "water": water[cid]}
        if comp["water"] is None:
            comp["water"] = 50.0  # neutral: missing data neither rewarded nor penalised
            r["missing"].append("Score eau neutre (50/100) : besoin en eau non calculable pour cette culture.")
        used = {k: w[k] for k, v in comp.items() if v is not None and w.get(k, 0) > 0}
        total = sum(comp[k] * wk for k, wk in used.items()) / sum(used.values()) if used else None
        r["scores"] = comp
        r["score"] = total
        r["weights_used"] = used
        r["profit_basis"] = "bénéfice (coûts saisis)" if r["costs_entered"] else "revenu brut moins eau (coûts non saisis)"
        rows.append({"crop_id": cid, "Culture": r["crop"], "Score": total, "Marché": comp["market"],
                     "Productivité": comp["productivity"], "Rentabilité": comp["profitability"], "Eau": comp["water"],
                     "Revenu attendu (DT/ha)": r["revenue_ha"]["expected"],
                     "Eau (m³/ha)": r["water"]["gross_m3_ha"] if r["water"] else None,
                     "Preuves": r["evidence"], "Années": r["years"]})
    table = pd.DataFrame(rows).sort_values("Score", ascending=False).reset_index(drop=True)
    table.index += 1
    for i, cid in enumerate(table.crop_id, start=1):
        r = next(x for x in ok if x["crop_id"] == cid)
        r["rank"] = i
        r["why"] = explain(r)
    return table, results


LABELS = {"market": "marché (tendance et stabilité du prix)", "productivity": "productivité (tendance et stabilité du rendement)",
          "profitability": "rentabilité", "water": "faible besoin en eau"}


def explain(r: dict) -> str:
    comp = {k: v for k, v in r["scores"].items() if v is not None}
    best = sorted(comp, key=comp.get, reverse=True)
    strong = [LABELS[k] for k in best if comp[k] >= 60][:2]
    weak = [LABELS[k] for k in best[::-1] if comp[k] <= 40][:2]
    txt = []
    if strong:
        txt.append("Points forts dans cette comparaison : " + " et ".join(strong) + ".")
    if weak:
        txt.append("Points faibles : " + " et ".join(weak) + ".")
    n = lambda x: f"{x:,.0f}".replace(",", " ")  # noqa: E731
    txt.append(f"Revenu attendu {n(r['revenue_ha']['expected'])} DT/ha (fourchette historique "
               f"{n(r['revenue_ha']['pessimistic'])} à {n(r['revenue_ha']['optimistic'])} DT/ha, {r['years']}).")
    return " ".join(txt)


CHANGE_CONDITIONS = [
    "vos propres rendements ou prix de vente diffèrent nettement des moyennes nationales ;",
    "vos coûts réels (semences, engrais, main-d'œuvre, énergie) sont saisis ou modifiés ;",
    "la quantité d'eau disponible, la date de semis ou le mode d'irrigation changent ;",
    "les pondérations des critères sont modifiées.",
]

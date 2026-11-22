"""Adéquation des cultures sur 30+ années de météo réelle.

Méthode (facteur limitant, à la manière d'EcoCrop / GAEZ) :
  score = climat × sol × sel × eau × (1 − risque)
- climat : fonction trapèze EcoCrop sur la température moyenne de chaque mois de la saison,
           calculée pour CHAQUE année de l'historique, puis moyenne sur les années ;
- risque : probabilité (part des années) d'un gel létal ou d'une canicule pendant la saison ;
- eau    : besoin d'irrigation FAO-56 (ETc − pluie efficace) d'une année sèche (80e centile)
           comparé à l'eau disponible ;
- sol    : pH (trapèze EcoCrop) et texture (groupes EcoCrop) ;
- sel    : seuil FAO-29 de salinité sans perte de rendement.
Le meilleur mois de semis est choisi parmi la fenêtre usuelle du pays.
"""
import numpy as np

from .i18n import crop_name, family, region_name, t

SALINITY_ECE = {"non": 1.0, "un_peu": 3.5, "oui": 7.0}  # dS/m représentatifs
CAT = [(75, "tres"), (55, "adapte"), (35, "possible"), (0, "deconseille")]


def trapeze(x, lo, olo, ohi, hi):
    if lo is None or hi is None:
        return 1.0
    olo = lo if olo is None else olo
    ohi = hi if ohi is None else ohi
    if x <= lo or x >= hi:
        return 0.0
    if x < olo:
        return (x - lo) / max(1e-6, olo - lo)
    if x > ohi:
        return (hi - x) / max(1e-6, hi - ohi)
    return 1.0


def kc_daily(c):
    if c["type"] == "perennial":
        return np.full(365, c["kc_mid"])
    li, ld, lm, ll = c["l_ini"], c["l_dev"], c["l_mid"], c["l_late"]
    return np.concatenate([np.full(li, c["kc_ini"]), np.linspace(c["kc_ini"], c["kc_mid"], ld + 1)[1:],
                           np.full(lm, c["kc_mid"]), np.linspace(c["kc_mid"], c["kc_end"], ll + 1)[1:]])


def _season_index(h, year, sow_month, n_days):
    """Indices des jours de la saison commençant le 1er du mois de semis de l'année donnée."""
    start = np.flatnonzero((h["year"] == year) & (h["month"] == sow_month))
    if start.size == 0:
        return None
    i0 = start[0]
    if i0 + n_days > len(h["year"]):
        return None
    return np.arange(i0, i0 + n_days)


def _effective_rain_mm(rain, eto):
    """Pluie efficace journalière simple : pluies < 5 mm perdues, 80 % du reste, plafonné à l'ETo du jour + stockage."""
    eff = np.where(rain >= 5, 0.8 * rain, 0.0)
    return np.minimum(eff, 3 * eto + 10)


def evaluate_season(h, c, sow_month, irr_eff, country="tunisie"):
    eco = c["ecocrop"]
    kc = kc_daily(c)
    n = len(kc)
    kill = c.get("kill_temp")
    heat = eco.get("tmax")  # EcoCrop : limite sur la température MOYENNE
    per = c["type"] == "perennial"
    r_min, r_opt = eco.get("rmin"), eco.get("ropmn")
    if country == "tunisie" and c.get("rainfed_override_tn"):
        r_min, r_opt = c["rainfed_override_tn"]
    rainfed_ok = not (country == "tunisie" and not c.get("rainfed_possible_tn", True))
    res = {"temp": [], "need": [], "frost": [], "heat": [], "rain": [], "rain_suit": []}
    for y in h["years"]:
        idx = _season_index(h, y, sow_month, n)
        if idx is None:
            continue
        months = h["month"][idx]
        tm = h["tmean"][idx]
        # suitabilité thermique : mois de croissance (pour les pérennes : mars-octobre / saison chaude)
        # chaque mois est pondéré par le Kc moyen (le stade initial compte moins que la pleine croissance) ;
        # le minimum n'est pris que sur les mois de pleine croissance (Kc ≥ 80 % du Kc max)
        mvals, wts, core = [], [], []
        for m in np.unique(months):
            if per and m in (11, 12, 1, 2):
                continue
            sel = months == m
            v = trapeze(tm[sel].mean(), eco.get("tmin"), eco.get("topmn"), eco.get("topmx"), eco.get("tmax"))
            w = kc[sel].mean()
            mvals.append(v); wts.append(w)
            if w >= 0.8 * c["kc_mid"]:
                core.append(v)
        if not mvals:
            mvals, wts = [0.0], [1.0]
        wmean = float(np.average(mvals, weights=wts))
        # pérennes : moyenne de la saison chaude (pas de minimum : les arbres traversent les mois frais)
        tsuit = wmean if per else 0.6 * wmean + 0.4 * (min(core) if core else wmean)
        hu = c.get("heat_units")
        if hu:  # maturation des fruits : chaleur cumulée de l'année (palmier dattier)
            ysel = (h["year"] == y) & np.isin(h["month"], hu["months"])
            acc = float(np.clip(h["tmean"][ysel] - hu["base"], 0, None).sum())
            res.setdefault("hu", []).append(acc)
            # en dessous d'environ 70 % de la chaleur requise, les dattes ne mûrissent pas correctement
            tsuit = float(np.clip((acc / hu["required"] - 0.7) / 0.3, 0, 1))
        res["temp"].append(tsuit)
        etc = kc * h["eto"][idx]
        peff = _effective_rain_mm(h["rain"][idx], h["eto"][idx])
        net = np.clip(etc - peff, 0, None).sum()
        res["need"].append(net * 10 / irr_eff)  # m3/ha
        res["rain"].append(h["rain"][idx].sum())
        tmin_s, tmax_s = h["tmin"][idx], h["tmax"][idx]
        # gel destructeur : un jour avec Tmin ≤ température létale de la culture
        res["frost"].append(bool(kill is not None and (tmin_s <= kill).any()))
        # canicule : 3 jours consécutifs avec une température moyenne au-dessus du maximum absolu EcoCrop
        hot = (tm > heat) if heat is not None else np.zeros(n, bool)
        # culture en sec : EcoCrop exprime la pluie en total ANNUEL → pluie des 365 jours
        # précédant la fin de la saison (pérennes : moyenne sur 2 ans, réserve du sol profond)
        end = idx[-1] + 1
        yr_rain = h["rain"][max(0, end - 365):end].sum()
        if per:
            yr_rain = (yr_rain + h["rain"][max(0, end - 730):max(0, end - 365)].sum()) / 2 if end > 730 else yr_rain
        res["rain_suit"].append(trapeze(yr_rain, r_min, r_opt, eco.get("ropmx"), (eco.get("rmax") or 1e9) * 1.5)
                                if rainfed_ok else 0.0)
        res["rain_year"] = res.get("rain_year", []) + [yr_rain]
        res["heat"].append(bool(np.convolve(hot.astype(int), np.ones(3, int), "valid").max(initial=0) >= 3))
    if not res["temp"]:
        return None
    need = np.array(res["need"])
    return {"sow_month": sow_month, "season_days": n, "years": len(res["temp"]),
            "temp_suit": float(np.mean(res["temp"])),
            "p_frost": float(np.mean(res["frost"])), "p_heat": float(np.mean(res["heat"])),
            "need_p50": float(np.percentile(need, 50)), "need_p80": float(np.percentile(need, 80)),
            "rain_season_mm": float(np.mean(res["rain"])),
            "rainfed_suit": float(np.mean(res["rain_suit"])),
            "rain_year_mm": float(np.mean(res["rain_year"])),
            "rain_opt_mm": r_opt, "rainfed_ok": rainfed_ok,
            "heat_units": round(float(np.mean(res["hu"]))) if res.get("hu") else None}


def ph_factor(ph, eco):
    """Optimum → 1 ; entre optimum et limite EcoCrop → 1 à 0,9 ; au-delà → −0,3 par unité de pH (min 0,4).
    Les limites EcoCrop sont des plages de culture courante, pas des seuils de mort : beaucoup de
    cultures sont produites sur les sols calcaires (pH 7,5-8,3) avec une fertilisation adaptée."""
    lo, olo, ohi, hi = eco.get("phmin"), eco.get("phopmn"), eco.get("phopmx"), eco.get("phmax")
    if None in (lo, olo, ohi, hi):
        return 1.0
    if olo <= ph <= ohi:
        return 1.0
    if ph > ohi:
        if ph <= hi:
            return 1 - 0.1 * (ph - ohi) / max(0.1, hi - ohi)
        return max(0.4, 0.9 - 0.3 * (ph - hi))
    if ph >= lo:
        return 1 - 0.1 * (olo - ph) / max(0.1, olo - lo)
    return max(0.4, 0.9 - 0.3 * (lo - ph))


def soil_factor(c, soil):
    eco = c["ecocrop"]
    reasons = []
    f_ph = ph_factor(soil["ph"], eco)
    if f_ph < 0.85:
        reasons.append(t("r.ph_out", ph=soil["ph"], lo=eco.get("phopmn"), hi=eco.get("phopmx")))
    text = (eco.get("text") or "").lower()
    f_tex = 1.0
    if text and "wide" not in text and soil["group"] not in text:
        f_tex = 0.7
        pref = ", ".join(t("tex." + k) for k in ("light", "medium", "heavy", "organic") if k in text)
        reasons.append(t("r.texture", soil=t("s.group." + soil["group"]), pref=pref))
    return f_ph * f_tex, reasons


def salt_factor(c, salinity):
    ece = SALINITY_ECE.get(salinity or "non", 1.0)
    thr = c["salt_threshold_ece"]
    if ece <= thr:
        return 1.0, []
    loss = min(0.9, (ece - thr) * 0.1)  # pente moyenne ~10 %/dS/m (FAO-29), approximation
    return 1 - loss, [t("r.salt", thr=thr, loss=round(loss * 100))]


def water_factor(need, water_per_ha):
    if water_per_ha is None:  # quantité inconnue : pas de pénalité, le besoin est affiché
        return 1.0, ([t("r.water_big", need=f"{round(need, -2):,.0f}".replace(",", " "))] if need > 10000 else [])
    if need <= water_per_ha:
        return 1.0, []
    if water_per_ha <= 0:
        f = 1.0 if need < 300 else max(0.0, 1 - need / 2500)
        return f, [t("r.needs_irrig")] if f < 0.6 else []
    f = max(0.0, water_per_ha / need)
    return f, [t("r.water_short", need=f"{round(need):,}".replace(",", " "), avail=f"{round(water_per_ha):,}".replace(",", " "))]


TREES = {"olive", "date_palm", "orange", "mandarin_jp", "almond", "apricot", "grape", "fig", "pomegranate", "pistachio", "tea"}
FIELD = {"durum_wheat", "wheat", "barley", "rice", "faba_bean", "chickpea", "pea", "soybean", "alfalfa"}


AROMATIC = {"mint", "rosemary", "thyme", "basil"}


def category(cid, c):
    return ("arbres" if cid in TREES else "grandes_cultures" if cid in FIELD
            else "aromatiques" if cid in AROMATIC else "legumes")


_REF_CACHE = {}


def _climate_from_normals(c, tmean_m, sow):
    """Adéquation thermique approchée à partir de 12 moyennes mensuelles (même logique que le score)."""
    eco, per, kc = c["ecocrop"], c["type"] == "perennial", kc_daily(c)
    hu = c.get("heat_units")
    if hu:
        acc = sum(max(0.0, tmean_m[m - 1] - hu["base"]) * 30.4 for m in hu["months"])
        return min(1.0, acc / hu["required"])
    vals, wts = [], []
    for d in range(0, len(kc), 30):
        m = ((sow - 1 + d // 30) % 12) + 1
        if per and m in (11, 12, 1, 2):
            continue
        vals.append(trapeze(tmean_m[m - 1], eco.get("tmin"), eco.get("topmn"), eco.get("topmx"), eco.get("tmax")))
        wts.append(kc[d])
    return float(np.average(vals, weights=wts)) if vals else 0.0


def regional_reference(cid, c, country):
    """Médiane de l'adéquation thermique de la culture sur les stations de référence du pays."""
    key = (cid, country)
    if key not in _REF_CACHE:
        from .climate import FALLBACK_STATIONS
        box = {"tunisie": (30, 37.7, 7.4, 11.8), "japon": (24, 46, 122, 146.5)}[country]
        vals = []
        for lat, lon, tx, tn, _ in FALLBACK_STATIONS.values():
            if box[0] <= lat <= box[1] and box[2] <= lon <= box[3]:
                tm = [(a + b) / 2 for a, b in zip(tx, tn)]
                vals.append(max(_climate_from_normals(c, tm, m) for m in c["sowing_months"][country]))
        _REF_CACHE[key] = float(np.median(vals)) if vals else 0.5
    return _REF_CACHE[key]


# Cultures traditionnelles par grande région agricole (savoir agricole régional : à confirmer avec les
# statistiques Agridata / MAFF). Sert de critère secondaire dans le plan, jamais à exclure une culture.
REGIONS = {
 "tunisie": [
  ("nord-ouest", [(36.73, 9.18), (36.50, 8.78), (36.17, 8.70), (36.08, 9.37), (37.10, 9.70)],
   {"durum_wheat", "wheat", "barley", "faba_bean", "chickpea", "pea", "olive", "potato", "tomato"}),
  ("cap bon et nord-est", [(36.45, 10.73), (36.80, 10.18), (36.40, 10.14), (36.60, 10.50)],
   {"orange", "tomato", "pepper", "strawberry", "potato", "olive", "grape", "onion"}),
  ("sahel et Sfax", [(35.83, 10.60), (35.77, 10.83), (35.50, 11.06), (34.74, 10.76)],
   {"olive", "almond", "pepper", "tomato", "barley", "watermelon"}),
  ("centre", [(35.68, 10.10), (35.04, 9.48), (35.17, 8.83), (35.58, 9.83)],
   {"olive", "almond", "pistachio", "pepper", "tomato", "barley", "melon", "watermelon", "apricot"}),
  ("oasis du sud-ouest", [(33.92, 8.13), (33.70, 8.97), (34.42, 8.78), (33.88, 10.10)],
   {"date_palm", "pomegranate", "fig", "alfalfa", "onion", "carrot", "barley", "garlic"}),
  ("sud-est", [(33.35, 10.50), (32.93, 10.45)], {"olive", "barley", "fig", "almond"}),
 ],
 "japon": [
  ("Kantō (Ibaraki)", [(36.37, 140.47), (36.0, 140.0)], {"rice", "soybean", "sweet_potato", "melon", "lettuce", "cabbage", "daikon"}),
  ("Hokkaidō", [(43.06, 141.35)], {"potato", "wheat", "soybean", "onion"}),
  ("Tōhoku et Niigata", [(38.27, 140.87), (37.92, 139.05)], {"rice", "soybean"}),
  ("Shizuoka et Tōkai", [(34.98, 138.40)], {"tea", "mandarin_jp", "strawberry"}),
  ("Kansai", [(34.69, 135.50)], {"rice", "cabbage", "onion"}),
  ("Kyūshū", [(31.56, 130.56)], {"sweet_potato", "tea", "mandarin_jp"}),
 ],
}


def regional_practice(country, lat, lon):
    best = None
    for name, pts, crops_set in REGIONS.get(country, []):
        d = min((plat - lat) ** 2 + ((plon - lon) * np.cos(np.radians(lat))) ** 2 for plat, plon in pts)
        if best is None or d < best[0]:
            best = (d, name, crops_set)
    return (best[1], best[2]) if best else (None, set())


def rank(h, crops, country, soil, water_per_ha, salinity, irr_eff, kinds="all", lat=None, lon=None):
    rows = []
    region_label, traditional = regional_practice(country, lat, lon) if lat is not None else (None, set())
    for cid, c in crops.items():
        sows = c["sowing_months"].get(country)
        if not sows:
            continue
        if kinds == "annual" and c["type"] != "annual" or kinds == "perennial" and c["type"] != "perennial":
            continue
        evals = [e for e in (evaluate_season(h, c, m, irr_eff, country) for m in sows) if e]
        if not evals:
            continue
        f_soil, r_soil = soil_factor(c, soil)
        f_salt, r_salt = salt_factor(c, salinity)
        best = None
        for e in evals:
            if water_per_ha == 0:  # culture en sec : pluviométrie EcoCrop
                f_w = e["rainfed_suit"]
                if not e["rainfed_ok"]:
                    r_w = [t("r.needs_irrig")]
                else:
                    r_w = [] if f_w >= 0.6 else [t("r.rain_low", rain=round(e["rain_year_mm"]), opt=round(e["rain_opt_mm"] or 0))]
            else:
                # l'irrigation complète la pluie : une culture qui tient en sec n'est pas pénalisée
                f_irr, r_w = water_factor(e["need_p80"], water_per_ha)
                f_w = e["rainfed_suit"] + (1 - e["rainfed_suit"]) * f_irr
                if f_w >= 0.8:
                    r_w = []
            risk = max(e["p_frost"], e["p_heat"])
            score = 100 * e["temp_suit"] * f_soil * f_salt * f_w * (1 - 0.8 * risk)
            cand = (score, e, f_w, r_w, risk)
            if best is None or score > best[0]:
                best = cand
        score, e, f_w, r_w, risk = best
        reasons_neg = r_soil + r_salt + r_w
        if e["p_frost"] >= 0.1:
            reasons_neg.append(t("r.frost", pct=round(e["p_frost"] * 100)))
        if e["p_heat"] >= 0.1:
            reasons_neg.append(t("r.heat", pct=round(e["p_heat"] * 100)))
        if e["temp_suit"] < 0.6:
            reasons_neg.append(t("r.temp_far"))
        reasons_pos = []
        if e.get("heat_units") and c.get("heat_units"):
            hu_req = c["heat_units"]["required"]
            (reasons_pos if e["heat_units"] >= hu_req else reasons_neg).append(
                t("r.heat_units", hu=e["heat_units"], req=hu_req))
        if e["temp_suit"] >= 0.8:
            reasons_pos.append(t("p.temp_good"))
        if risk < 0.05:
            reasons_pos.append(t("p.no_risk", n=e["years"]))
        if f_soil >= 0.95:
            reasons_pos.append(t("p.soil_ok"))
        if c["n_fixer"]:
            reasons_pos.append(t("p.nfix"))
        level = next(lv for th, lv in CAT if score >= th)
        agronomic = 100 * e["temp_suit"] * f_soil * f_salt * (1 - 0.8 * risk)
        advantage = max(0.0, e["temp_suit"] - regional_reference(cid, c, country))
        if advantage >= 0.2:
            reasons_pos.insert(0, t("p.regional", crop=crop_name(c)))
        if cid in traditional:
            reasons_pos.insert(0, t("p.traditional", region=region_name(region_label)))
        rows.append({
            "crop": cid, "name": crop_name(c), "family": family(c["family"]), "type": c["type"],
            "category": category(cid, c),
            "score": round(score), "level": level, "label": t("lvl." + level),
            "best_sowing_month": e["sow_month"], "season_days": e["season_days"],
            "water_m3_ha_typical": round(e["need_p50"], -1), "water_m3_ha_dry_year": round(e["need_p80"], -1),
            "rain_season_mm": round(e["rain_season_mm"]),
            "risk": {"frost_pct": round(e["p_frost"] * 100), "heat_pct": round(e["p_heat"] * 100)},
            "factors": {"climat": round(e["temp_suit"] * 100), "sol": round(f_soil * 100),
                        "sel": round(f_salt * 100), "eau": round(f_w * 100), "risque": round(risk * 100)},
            "years_analyzed": e["years"], "value_class": c.get("value_class", 1.5),
            "agronomic": round(agronomic), "regional_advantage": round(advantage, 2),
            "traditional": cid in traditional,
            "pros": reasons_pos, "cons": reasons_neg,
        })
    return sorted(rows, key=lambda r: -r["score"])

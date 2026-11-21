"""Orchestration : de la parcelle dessinée aux recommandations (fr / tn / ja)."""
import json
import math
from datetime import date
from pathlib import Path

from shapely.geometry import Polygon

from . import combos, planner, satellite
from .climate import load_history, monthly_normals
from .companion import companions_for
from .i18n import LANG, LANGS, crop_name, months, t
from .soil import get_soil
from .sources import SourceUnavailable, forecast16
from .suitability import rank

ROOT = Path(__file__).resolve().parent.parent
CROPS = json.loads((ROOT / "data" / "crops.json").read_text(encoding="utf-8"))
IRR_EFF = {"goutte_a_goutte": 0.9, "aspersion": 0.75, "gravitaire": 0.6}


class FarmError(ValueError):
    pass


def ring_of(farm):
    g = farm.get("geometry", farm)
    if g.get("type") != "Polygon":
        raise FarmError(t("e.polygon"))
    pts = [tuple(p[:2]) for p in g["coordinates"][0]]
    if pts[0] == pts[-1]:
        pts = pts[:-1]
    if len(pts) < 3:
        raise FarmError(t("e.corners"))
    return pts


def area_ha(ring):
    lat0 = sum(p[1] for p in ring) / len(ring)
    k = math.cos(math.radians(lat0))
    xy = [(lon * 111320 * k, lat * 110540) for lon, lat in ring]
    return abs(Polygon(xy).area) / 1e4


def country_of(lat, lon):
    if 30.0 <= lat <= 37.7 and 7.4 <= lon <= 11.8:
        return "tunisie"
    if 24.0 <= lat <= 46.0 and 122.0 <= lon <= 146.5:
        return "japon"
    raise FarmError(t("e.zone"))


def forecast_advice(lat, lon, alloc, online):
    """Conseils sur 16 jours, uniquement pour les cultures du plan à semer/planter ce mois-ci ou le suivant."""
    if not online:
        return {"available": False, "advice": []}
    try:
        f = forecast16(lat, lon)
    except SourceUnavailable:
        return {"available": False, "advice": [t("f.na")]}
    tmin, tmax = min(f["tmin"]), max(f["tmax"])
    tmean = [(a + b) / 2 for a, b in zip(f["tmax"], f["tmin"])]
    rain = round(sum(x or 0 for x in f["rain"]), 1)
    advice = [t("f.sum", tmin=round(tmin), tmax=round(tmax), rain=rain)]
    now = date.today().month
    seen = set()
    for a in alloc:
        c = CROPS[a["crop"]]
        if a["crop"] in seen or a["sowing_month"] not in (now, now % 12 + 1):
            continue
        seen.add(a["crop"])
        act = t("act.plant" if c["type"] == "perennial" else "act.sow")
        kill = c.get("kill_temp")
        hot_lim = c["ecocrop"].get("tmax")  # limite EcoCrop sur la température MOYENNE
        hot3 = hot_lim is not None and any(all(x > hot_lim for x in tmean[i:i + 3]) for i in range(len(tmean) - 2))
        if kill is not None and tmin <= kill + 1:
            advice.append(t("f.frost", crop=a["name"], t=round(tmin), act=act))
        elif hot3:
            advice.append(t("f.heat", crop=a["name"], t=round(max(tmean))))
        else:
            advice.append(t("f.good", crop=a["name"], act=act))
    if rain >= 15:
        advice.append(t("f.rain"))
    return {"available": True, "tmin": tmin, "tmax": tmax, "rain_mm": rain, "advice": advice, "source": f["source"]}


def analyze(req, online=True):
    token = LANG.set(req.get("lang") if req.get("lang") in LANGS else "fr")
    try:
        return _analyze(req, online)
    finally:
        LANG.reset(token)


def _analyze(req, online):
    ring = ring_of(req["farm"])
    poly = Polygon(ring)
    lon, lat = poly.centroid.x, poly.centroid.y
    area = round(area_ha(ring), 2)
    if area < 0.05:
        raise FarmError(t("e.small"))
    if area > 2000:
        raise FarmError(t("e.big"))
    country = country_of(lat, lon)

    water = req.get("water") or {}
    source = water.get("source", "puits")
    irr_eff = IRR_EFF.get(water.get("method", "goutte_a_goutte"), 0.9)
    water_m3 = 0.0 if source == "pluie" else water.get("volume_m3")
    water_per_ha = None if water_m3 is None else water_m3 / area

    hist = load_history(lat, lon, online)
    soil = get_soil(lat, lon, req.get("soil_type"), online, country)
    sat = satellite.analyze({"type": "Polygon", "coordinates": [[list(p) for p in ring] + [list(ring[0])]]},
                            online=online and req.get("use_satellite", True))
    kinds = req.get("kinds", "all")
    salinity = req.get("salinity", "non")

    ranking = rank(hist, CROPS, country, soil, water_per_ha, salinity, irr_eff, kinds, lat, lon)
    chosen = planner.select(ranking, CROPS, k_max=req.get("max_crops", 4), rainfed=source == "pluie",
                            water_m3=water_m3, area_ha=area)
    alloc = planner.allocate(chosen, area, water_m3)
    rainfed_ranking = ranking if source == "pluie" else None
    left = area - sum(a["area_ha"] for a in alloc)
    if source != "pluie" and left > 0.05 * area:
        # l'eau ne suffit pas pour toute la ferme : le reste en cultures pluviales adaptées
        rainfed_ranking = rank(hist, CROPS, country, soil, 0.0, salinity, irr_eff, kinds, lat, lon)
        taken = {a["crop"] for a in alloc}
        pool = [r for r in rainfed_ranking if r["score"] >= 40 and r["crop"] not in taken]
        dry = planner.select(pool, CROPS, k_max=2, rainfed=True) if pool else []
        alloc += planner.allocate(dry, left, 0, irrigated=False)
    if rainfed_ranking is None and source != "pluie":
        rainfed_ranking = rank(hist, CROPS, country, soil, 0.0, salinity, irr_eff, "all", lat, lon)
    full_ranking = ranking if kinds == "all" else rank(hist, CROPS, country, soil, water_per_ha, salinity, irr_eff, "all", lat, lon)
    combinations = combos.evaluate(country, CROPS, None if source == "pluie" else full_ranking,
                                   full_ranking if source == "pluie" else rainfed_ranking, source, water_m3, area)
    zones = sat.get("vigor_zones") if sat.get("available") else None
    farm_map = planner.place(ring, alloc, CROPS, zones, farm_area=area)

    # cultures intercalaires sous les arbres : évaluées dans le même régime d'eau que l'arbre
    inter = {}
    for a in alloc:
        base = ranking if a["irrigated"] or source == "pluie" else (rainfed_ranking or ranking)
        inter.update(planner.intercrops([a], CROPS, base))
    for a in alloc:
        a["intercrops"] = inter.get(a["crop"], [])
        a["perennial"] = CROPS[a["crop"]]["type"] == "perennial"

    warnings = []
    if hist["demo"]:
        warnings.append(t("w.demo"))
    if soil.get("default"):
        warnings.append(t("w.soil"))
    if not sat.get("available"):
        warnings.append(t("w.sat", x=sat.get("reason")))
    elif source == "pluie":
        sv = satellite.summer_ndvi(sat)
        if sv is not None and sv > 0.4:
            warnings.append(t("w.green_rainfed", ndvi=sv))

    mnames = months()
    used_typ = sum(a["water_m3_typical"] for a in alloc)
    used_dry = sum(a["water_m3_dry_year"] for a in alloc)
    candidates = [r["crop"] for r in ranking]
    clim_src = t("c.src.demo", x=hist["station"]) if hist["demo"] else t("c.src.power", a=hist["years"][0], b=hist["years"][-1])
    return {
        "lang": LANG.get(),
        "farm": {"lat": round(lat, 5), "lon": round(lon, 5), "area_ha": area, "country": country,
                 "water_source": source, "water_m3": water_m3, "irrigation_efficiency": irr_eff,
                 "irrigation_method": water.get("method", "goutte_a_goutte")},
        "summary": {
            "top": [{"crop": r["crop"], "name": r["name"], "score": r["score"], "level": r["level"], "label": r["label"]} for r in ranking[:5]],
            "plan_crops": [a["name"] for a in alloc],
            "water_typical_m3": used_typ, "water_dry_year_m3": used_dry,
            "area_irrigated_ha": round(sum(a["area_ha"] for a in alloc if a["irrigated"]), 2),
            "area_rainfed_ha": round(sum(a["area_ha"] for a in alloc if not a["irrigated"]), 2),
            "area_unplanted_ha": round(max(0, area - sum(a["area_ha"] for a in alloc)), 2),
        },
        "ranking": ranking,
        "plan": {"allocation": alloc, "associations": planner.associations(alloc, CROPS), "map": farm_map},
        "combinations": combinations,
        "companions": {r["crop"]: companions_for(r["crop"], CROPS, candidates, country=country) for r in ranking[:8]},
        "calendar": [{"crop": a["crop"], "name": a["name"], "sowing_month": a["sowing_month"],
                      "sowing_month_name": mnames[a["sowing_month"] - 1],
                      "season_days": next((r["season_days"] for r in (rainfed_ranking or []) + ranking if r["crop"] == a["crop"]), 120),
                      "perennial": a["perennial"]} for a in alloc],
        "land": {"soil": soil, "satellite": sat},
        "climate": {"source": clim_src, "eto_method": t("c." + hist["eto_method"]),
                    "years": [hist["years"][0], hist["years"][-1]], "elevation_m": hist["elev"],
                    "normals": monthly_normals(hist), "demo": hist["demo"]},
        "forecast": forecast_advice(lat, lon, alloc, online),
        "warnings": warnings,
        "method": t("method"),
        "generated": date.today().isoformat(),
    }


def crop_companions(cid, country, lang="fr"):
    token = LANG.set(lang if lang in LANGS else "fr")
    try:
        cands = [k for k, c in CROPS.items() if country in c["sowing_months"]]
        if cid not in cands:
            raise FarmError(t("e.crop"))
        return companions_for(cid, CROPS, cands, country=country)
    finally:
        LANG.reset(token)


def combo_catalogue(country, lang="fr"):
    token = LANG.set(lang if lang in LANGS else "fr")
    try:
        return combos.catalogue(country, CROPS)
    finally:
        LANG.reset(token)


def crop_list(country, lang="fr"):
    token = LANG.set(lang if lang in LANGS else "fr")
    try:
        return [{"id": k, "name": crop_name(c), "type": c["type"], "scientific_name": c["scientific_name"]}
                for k, c in CROPS.items() if country in c["sowing_months"]]
    finally:
        LANG.reset(token)

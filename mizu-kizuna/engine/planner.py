"""Plan de la parcelle : choix d'un assortiment compatible puis répartition des surfaces.

1. Sélection gloutonne de 2 à 4 cultures : meilleur score + bonus de compatibilité,
   jamais deux cultures incompatibles en place en même temps.
2. Répartition des surfaces (programmation linéaire) : maximiser Σ score × surface sous
   contrainte d'eau d'une année sèche, avec part minimale et maximale par culture.
3. Placement : les cultures les plus exigeantes vont sur la zone de plus forte vigueur
   (Sentinel-2), sinon bandes est-ouest.
"""
import math
from itertools import combinations, permutations

import numpy as np
from scipy.optimize import linprog
from shapely.affinity import rotate
from shapely.geometry import Polygon, box, mapping, shape
from shapely.ops import transform as shp_transform

from .companion import KNOWN, pair
from .i18n import crop_name, t

COMPANION_ONLY = {"mint", "rosemary", "thyme", "basil"}  # aromatiques : en accompagnement, pas en culture principale
PALETTE = ["#2f855a", "#d69e2e", "#c53030", "#6b46c1", "#2b6cb0", "#dd6b20", "#319795", "#97266d"]


def priority(r, rainfed):
    """Ordre de priorité du plan : adéquation (sans l'eau en irrigué, car l'eau est répartie ensuite)
    × valeur indicative × avantage régional (spécialité de la région, ex. palmier à Tozeur)."""
    base = r["score"] if rainfed else r.get("agronomic", r["score"])
    # la valeur ne fait que départager (×1,0 pour les céréales à ×1,4 pour les plus fortes valeurs) ;
    # l'avantage régional pèse davantage (spécialité de la région)
    return (base * (0.8 + 0.2 * r.get("value_class", 1.5)) * (1 + 2 * r.get("regional_advantage", 0))
            * (1.3 if r.get("traditional") else 1.0))


def select(ranking, crops, k_max=4, rainfed=False, water_m3=None, area_ha=None):
    ranking = [r for r in ranking if r["crop"] not in COMPANION_ONLY]
    key = (lambda r: r["score"]) if rainfed else (lambda r: r.get("agronomic", r["score"]))
    pool = [r for r in ranking if key(r) >= 55] or [r for r in ranking if key(r) >= 35]
    if water_m3 and area_ha and not rainfed:  # l'eau doit permettre au moins 5 % de la surface
        pool = [r for r in pool if r["water_m3_ha_dry_year"] <= 0 or water_m3 / r["water_m3_ha_dry_year"] >= 0.05 * area_ha]
    pool = sorted(pool, key=lambda r: -priority(r, rainfed))[:10]
    chosen = []
    sow = {r["crop"]: r["best_sowing_month"] for r in ranking}
    while pool and len(chosen) < k_max:
        best, best_val = None, -1e9
        for r in pool:
            pairs = [pair(crops[r["crop"]], crops[c["crop"]], sow[r["crop"]], sow[c["crop"]]) for c in chosen]
            if any(p["relation"] == "avoid" for p in pairs):
                continue
            val = priority(r, rainfed) + 0.25 * sum(p["score"] for p in pairs)
            if val > best_val:
                best, best_val = r, val
        if best is None:
            break
        chosen.append(best)
        pool.remove(best)
        if len(chosen) >= 2 and priority(best, rainfed) < 0.4 * priority(chosen[0], rainfed):
            break
    return chosen


def allocate(chosen, area_ha, water_m3, min_share=0.1, max_share=0.5, irrigated=True):
    """Répartition par priorité (logique de l'agriculteur) : la culture prioritaire reçoit d'abord
    sa surface (jusqu'à 50 %), dans la limite de l'eau d'une année sèche, puis la suivante, etc."""
    n = len(chosen)
    if n == 0:
        return []
    caps = [1.0] if n == 1 else [max_share] + [max(min_share, (1 - max_share) / (n - 1) + 0.1)] * (n - 1)
    left_area, left_water = area_ha, (None if not water_m3 else water_m3)
    out = []
    for r, cap in zip(chosen, caps):
        need = r["water_m3_ha_dry_year"] if (irrigated and water_m3) else 0
        a = min(cap * area_ha, left_area)
        if left_water is not None and need > 0:
            a = min(a, left_water / need)
        if a < 0.01:
            continue
        left_area -= a
        if left_water is not None and need > 0:
            left_water -= a * need
        out.append((r, a))
    # reste de surface (et d'eau) : on agrandit dans l'ordre de priorité
    for i, (r, a) in enumerate(out):
        if left_area < 0.01:
            break
        need = r["water_m3_ha_dry_year"] if (irrigated and water_m3) else 0
        extra = left_area if (left_water is None or need <= 0) else min(left_area, left_water / need)
        if extra > 0.01 and (a + extra) <= max(0.7, 1.0 if n == 1 else 0.7) * area_ha:
            out[i] = (r, a + extra)
            left_area -= extra
            if left_water is not None and need > 0:
                left_water -= extra * need
    return [{"crop": r["crop"], "name": r["name"], "score": r["score"], "area_ha": round(float(a), 2),
             "sowing_month": r["best_sowing_month"], "irrigated": irrigated and water_m3 != 0,
             "water_m3_typical": 0 if (water_m3 == 0 or not irrigated) else round(float(a) * r["water_m3_ha_typical"]),
             "water_m3_dry_year": 0 if (water_m3 == 0 or not irrigated) else round(float(a) * r["water_m3_ha_dry_year"])}
            for r, a in out]


def _to_m(lat0):
    k = math.cos(math.radians(lat0))
    return (lambda x, y, z=None: (x * 111320 * k, y * 110540)), (lambda x, y, z=None: (x / (111320 * k), y / 110540))


def _demand(a, crops):
    c = crops[a["crop"]]
    d = c["kc_mid"] * (1.0 if c["type"] == "annual" else 0.8)
    return d * (1.0 if a.get("irrigated", True) else 0.6)


def place(ring, allocation, crops, zones_fc, farm_area=None):
    """Découpe la parcelle en BLOCS CONTIGUS (bandes perpendiculaires à l'axe long du champ),
    un bloc par culture avec sa surface exacte. L'ordre des blocs est choisi pour mettre les
    cultures exigeantes sur les zones de plus forte vigueur Sentinel-2."""
    if not allocation:
        return {"type": "FeatureCollection", "features": [], "legend": [], "placement": t("m.place_strips")}
    lat0 = sum(p[1] for p in ring) / len(ring)
    fwd, back = _to_m(lat0)
    poly = shp_transform(fwd, Polygon(ring)).buffer(0)
    # axe long du champ
    mrr = list(poly.minimum_rotated_rectangle.exterior.coords)
    edges = [(mrr[i], mrr[i + 1]) for i in range(4)]
    (x1, y1), (x2, y2) = max(edges, key=lambda e: math.dist(*e))
    ang = math.degrees(math.atan2(y2 - y1, x2 - x1))
    c0 = poly.centroid
    pr = rotate(poly, -ang, origin=c0)
    minx, miny, maxx, maxy = pr.bounds
    total_m2 = pr.area
    # profil d'aire et de vigueur le long de l'axe
    n = 240
    xs = np.linspace(minx, maxx, n + 1)
    slice_area, slice_vig = np.zeros(n), np.zeros(n)
    zones = []
    for f in (zones_fc or {}).get("features", []):
        zp = rotate(shp_transform(fwd, shape(f["geometry"])).buffer(0), -ang, origin=c0)
        zones.append((f["properties"]["zone"], zp))
    for i in range(n):
        sl = pr.intersection(box(xs[i], miny - 1, xs[i + 1], maxy + 1))
        slice_area[i] = sl.area
        if zones and sl.area > 0:
            slice_vig[i] = sum(z * sl.intersection(zp).area for z, zp in zones) / sl.area
    cum = np.concatenate([[0], np.cumsum(slice_area)])

    def cut_at(target_m2):
        return float(np.interp(target_m2, cum, xs))

    def seg_vigor(a, b):
        ia, ib = np.searchsorted(xs, a), np.searchsorted(xs, b)
        w = slice_area[max(0, ia - 1):ib]
        v = slice_vig[max(0, ia - 1):ib]
        return float((w * v).sum() / w.sum()) if w.sum() > 0 else 0.0

    areas = [a["area_ha"] * 1e4 for a in allocation]
    scale = min(1.0, total_m2 / max(1, sum(areas)))
    areas = [x * scale for x in areas]
    orders = list(permutations(range(len(allocation)))) if len(allocation) <= 6 else [tuple(range(len(allocation)))]
    best, best_val = None, -1e18
    for order in orders:
        acc, bounds, val = 0.0, [], 0.0
        for k in order:
            a0 = cut_at(acc); acc += areas[k]; b0 = cut_at(acc)
            bounds.append((k, a0, b0))
            if zones:
                val += _demand(allocation[k], crops) * seg_vigor(a0, b0) * areas[k]
        if not zones:  # sans satellite : cultures irriguées d'un côté, pluviales de l'autre, arbres groupés
            val = -sum(i * _demand(allocation[k], crops) for i, k in enumerate(order))
        if val > best_val:
            best, best_val = bounds, val
    colors = {a["crop"]: PALETTE[i % len(PALETTE)] for i, a in enumerate(allocation)}
    feats = []
    unrot = lambda g: shp_transform(back, rotate(g, ang, origin=c0))
    for k, a0, b0 in best:
        piece = pr.intersection(box(a0, miny - 1, b0, maxy + 1))
        if piece.is_empty:
            continue
        a = allocation[k]
        g = unrot(piece)
        lab = g.representative_point()
        feats.append({"type": "Feature", "geometry": mapping(g),
                      "properties": {"crop": a["crop"], "name": a["name"], "area_ha": a["area_ha"],
                                     "irrigated": a.get("irrigated", True), "fill": colors[a["crop"]],
                                     "label": [lab.y, lab.x],
                                     "vigor": round(seg_vigor(a0, b0), 2) if zones else None}})
    end = cut_at(sum(areas))
    if end < maxx - 0.5 and total_m2 - sum(areas) > 0.02 * total_m2:
        rest = pr.intersection(box(end, miny - 1, maxx + 1, maxy + 1))
        if not rest.is_empty:
            g = unrot(rest)
            feats.append({"type": "Feature", "geometry": mapping(g),
                          "properties": {"crop": None, "name": t("m.unplanted"), "fill": "#cbd5e0",
                                         "area_ha": round(rest.area / 1e4, 2), "label": [g.representative_point().y, g.representative_point().x]}})
    return {"type": "FeatureCollection", "features": feats,
            "legend": [{"crop": a["crop"], "name": a["name"] + ("" if a.get("irrigated", True) else f" ({t('m.rainfed')})"),
                        "color": colors[a["crop"]]} for a in allocation],
            "placement": t("m.place_zones") if zones else t("m.place_strips"),
            "orientation_deg": round(ang, 1)}


def associations(allocation, crops):
    out = []
    for a, b in combinations(allocation, 2):
        p = pair(crops[a["crop"]], crops[b["crop"]], a["sowing_month"], b["sowing_month"])
        out.append({"crops": [a["name"], b["name"]], **p})
    return out


def intercrops(allocation, crops, ranking, min_score=25, k=2):
    """Pour chaque arbre du plan : cultures à semer entre les rangs (associations connues et sourcées),
    même si leur score seul est moyen — c'est la pratique (olivier + orge/fève, palmier + luzerne…)."""
    scores = {r["crop"]: r for r in ranking}
    out = {}
    for a in allocation:
        tree = crops[a["crop"]]
        if tree["type"] != "perennial" or tree["height_m"] < 2:
            continue
        cands = []
        for (x, y), rel in KNOWN.items():
            if rel["relation"] != "beneficial" or a["crop"] not in (x, y):
                continue
            other = y if x == a["crop"] else x
            r = scores.get(other)
            if not r or r["score"] < min_score or crops[other]["type"] == "perennial" and crops[other]["height_m"] >= 2:
                continue
            cands.append((r["score"] * {"high": 1.0, "medium": 0.85, "low": 0.7}[rel["confidence"]], other, rel, r))
        cands.sort(key=lambda z: -z[0])
        out[a["crop"]] = [{"crop": o, "name": r["name"], "score": r["score"], "level": r["level"], "label": r["label"],
                           "sowing_month": r["best_sowing_month"], "why": pair(tree, crops[o])["reasons"][0],
                           "where": t("co.intercrop")} for _, o, rel, r in cands[:k]]
    return out

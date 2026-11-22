"""Sentinel-2 L2A sur la parcelle exacte (Microsoft Planetary Computer, accès anonyme).

Produit :
- historique NDVI mensuel (24 mois) : la parcelle est-elle cultivée, avec quelle vigueur ;
- carte de vigueur de la dernière image claire, découpée en 3 zones (pour placer les cultures) ;
- indicateurs de sol nu (luminosité, ratio SWIR B11/B12 lié aux argiles) — indicatifs seulement.
Tout échec renvoie {"available": False, "reason": ...} : le reste du modèle continue.
"""
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

import numpy as np

from .i18n import t

CACHE = Path(__file__).resolve().parent.parent / "cache"
STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
VALID_SCL = {4, 5, 6, 7}  # végétation, sol nu, eau, non classé (exclut nuages, ombres, neige)


def _read_scene(item, geom_ll):
    import rasterio
    from pyproj import Transformer
    from rasterio.features import geometry_mask
    from rasterio.enums import Resampling
    from rasterio.windows import from_bounds
    from shapely.geometry import shape, mapping
    from shapely.ops import transform as shp_transform

    epsg = item.properties.get("proj:epsg") or int(str(item.properties.get("proj:code", "")).split(":")[-1])
    to_utm = Transformer.from_crs(4326, epsg, always_xy=True).transform
    g = shp_transform(to_utm, shape(geom_ll))
    minx, miny, maxx, maxy = g.bounds
    pad = 20
    bounds = (minx - pad, miny - pad, maxx + pad, maxy + pad)

    with rasterio.open(item.assets["SCL"].href) as src:
        win = from_bounds(*bounds, transform=src.transform).round_offsets().round_lengths()
        scl = src.read(1, window=win)
        tr = src.window_transform(win)
    shape_ = scl.shape
    # 10 m → grille 20 m pour aligner toutes les bandes
    bands = {}
    for b in ("B02", "B04", "B08", "B11", "B12"):
        with rasterio.open(item.assets[b].href) as src:
            w = from_bounds(*bounds, transform=src.transform).round_offsets().round_lengths()
            bands[b] = src.read(1, window=w, out_shape=shape_, resampling=Resampling.average).astype(float)
    offset = 1000 if str(item.properties.get("s2:processing_baseline", "0")) >= "04.00" else 0
    for b in bands:
        bands[b] = (bands[b] - offset) / 10000.0
    inside = ~geometry_mask([mapping(g)], out_shape=shape_, transform=tr, all_touched=True)
    valid = inside & np.isin(scl, list(VALID_SCL))
    if inside.sum() == 0 or valid.sum() / inside.sum() < 0.6:
        return None
    b2, b4, b8, b11, b12 = (bands[k] for k in ("B02", "B04", "B08", "B11", "B12"))
    with np.errstate(divide="ignore", invalid="ignore"):
        ndvi = (b8 - b4) / (b8 + b4)
        ndmi = (b8 - b11) / (b8 + b11)
        nbr2 = (b11 - b12) / (b11 + b12)
        bsi = ((b11 + b4) - (b8 + b2)) / ((b11 + b4) + (b8 + b2))
        clay_ratio = b11 / b12
    v = valid & np.isfinite(ndvi)
    bare = v & (ndvi < 0.2) & (nbr2 < 0.15)
    res = {"date": item.datetime.date().isoformat(),
           "ndvi": float(np.nanmean(ndvi[v])), "ndmi": float(np.nanmean(ndmi[v])),
           "bare_fraction": float(bare.sum() / v.sum())}
    if bare.sum() >= 5:
        res.update({"bare_bsi": float(np.nanmean(bsi[bare])), "bare_clay_ratio": float(np.nanmean(clay_ratio[bare])),
                    "bare_brightness": float(np.nanmean(((b2 + b4 + b8) / 3)[bare]))})
    res["_grid"] = (np.where(v, ndvi, np.nan), tr, epsg)
    return res


def _zones(grid, tr, epsg):
    """Découpe la parcelle en 3 zones de vigueur (tertiles NDVI) → GeoJSON lon/lat."""
    from pyproj import Transformer
    from rasterio.features import shapes
    from shapely.geometry import shape, mapping
    from shapely.ops import transform as shp_transform, unary_union

    vals = grid[np.isfinite(grid)]
    if vals.size < 9 or np.nanstd(vals) < 0.02:
        return None
    q1, q2 = np.nanpercentile(vals, [33.3, 66.6])
    cls = np.zeros(grid.shape, dtype=np.uint8)
    cls[np.isfinite(grid)] = 1
    cls[grid >= q1] = 2
    cls[grid >= q2] = 3
    cls[~np.isfinite(grid)] = 0
    to_ll = Transformer.from_crs(epsg, 4326, always_xy=True).transform
    feats = []
    for z, label in ((1, "faible"), (2, "moyenne"), (3, "forte")):
        polys = [shape(s) for s, val in shapes(cls, mask=cls == z, transform=tr) if val == z]
        if not polys:
            continue
        u = unary_union(polys)
        area_ha = u.area / 1e4
        feats.append({"type": "Feature", "geometry": mapping(shp_transform(to_ll, u)),
                      "properties": {"zone": z, "vigor": label, "area_ha": round(area_ha, 2),
                                     "ndvi_mean": round(float(np.nanmean(grid[cls == z])), 3)}})
    return {"type": "FeatureCollection", "features": feats}


def analyze(geom_ll, months=24, online=True):
    if not online:
        return {"available": False, "reason": t("sat.offline")}
    key = CACHE / ("s2_" + hashlib.sha1(json.dumps(geom_ll, sort_keys=True).encode()).hexdigest() + ".json")
    if key.exists():
        out = json.loads(key.read_text(encoding="utf-8"))
        out["interpretation"] = _interpret_from(out)
        return out
    try:
        import planetary_computer as pc
        from pystac_client import Client
    except ImportError as e:
        return {"available": False, "reason": t("sat.lib", x=e.name)}
    try:
        end = date.today()
        start = end - timedelta(days=30 * months)
        cat = Client.open(STAC, modifier=pc.sign_inplace)
        items = list(cat.search(collections=["sentinel-2-l2a"], intersects=geom_ll,
                                datetime=f"{start}/{end}", query={"eo:cloud_cover": {"lt": 40}},
                                max_items=400).items())
        if not items:
            return {"available": False, "reason": t("sat.none")}
        best = {}
        for it in items:  # meilleure image (moins nuageuse) par mois
            k = it.datetime.strftime("%Y-%m")
            if k not in best or it.properties["eo:cloud_cover"] < best[k].properties["eo:cloud_cover"]:
                best[k] = it
        picks = [best[k] for k in sorted(best)]
        with ThreadPoolExecutor(max_workers=8) as ex:
            scenes = [s for s in ex.map(lambda it: _safe(_read_scene, it, geom_ll), picks) if s]
    except Exception as e:
        return {"available": False, "reason": t("sat.down", x=type(e).__name__)}
    if not scenes:
        return {"available": False, "reason": t("sat.cloud")}

    scenes.sort(key=lambda s: s["date"])
    latest = max(scenes, key=lambda s: (s["date"], -s["bare_fraction"]))
    grid, tr, epsg = latest["_grid"]
    zones = _safe(_zones, grid, tr, epsg)
    series = [{"date": s["date"], "ndvi": round(s["ndvi"], 3), "ndmi": round(s["ndmi"], 3),
               "bare_fraction": round(s["bare_fraction"], 2)} for s in scenes]
    ndvis = np.array([s["ndvi"] for s in scenes])
    active = int((ndvis > 0.35).sum())
    bare_obs = [s for s in scenes if "bare_clay_ratio" in s]
    cv = float(np.nanstd(grid) / max(1e-6, abs(np.nanmean(grid))))
    out = {
        "available": True, "source": "Sentinel-2 L2A (ESA Copernicus) via Microsoft Planetary Computer",
        "scenes_used": len(scenes), "period": [series[0]["date"], series[-1]["date"]],
        "ndvi_series": series, "ndvi_peak": round(float(ndvis.max()), 2),
        "ndvi_mean": round(float(ndvis.mean()), 2),
        "months_active_vegetation": active,
        "latest_scene": latest["date"], "heterogeneity_cv": round(cv, 2),
        "vigor_zones": zones,
        "bare_soil": None if not bare_obs else {
            "observations": len(bare_obs),
            "brightness": round(float(np.mean([s["bare_brightness"] for s in bare_obs])), 3),
            "swir_clay_ratio": round(float(np.mean([s["bare_clay_ratio"] for s in bare_obs])), 3),
            "bsi": round(float(np.mean([s["bare_bsi"] for s in bare_obs])), 3)},
    }
    out["interpretation"] = _interpret_from(out)
    key.write_text(json.dumps(out), encoding="utf-8")
    return out


def _safe(fn, *a):
    try:
        return fn(*a)
    except Exception:
        return None


def summer_ndvi(out):
    vals = [p["ndvi"] for p in out.get("ndvi_series", []) if p["date"][5:7] in ("06", "07", "08")]
    return round(sum(vals) / len(vals), 2) if vals else None


def _interpret_from(out):
    msgs = []
    n, active, peak = out["scenes_used"], out["months_active_vegetation"], out["ndvi_peak"]
    msgs.append(t("sat.i.none") if active == 0 else t("sat.i.active", n=active, total=n))
    if peak > 0.7:
        msgs.append(t("sat.i.high"))
    elif peak < 0.4:
        msgs.append(t("sat.i.low"))
    sv = summer_ndvi(out)
    if sv is not None and sv > 0.4:
        msgs.append(t("sat.i.green_summer"))
    if out["heterogeneity_cv"] > 0.25:
        msgs.append(t("sat.i.het"))
    return msgs

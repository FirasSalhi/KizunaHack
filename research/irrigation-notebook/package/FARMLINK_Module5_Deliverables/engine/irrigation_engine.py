"""Zone-level irrigation recommendation (what / when / how much), notebook-independent, JSON-serialisable.

Depletion source priority (never silently switched; reported in `depletion_source`):
  1. calibrated multi-depth sensor + soil FC/WP        -> 'sensor'
  2. user-declared current depletion (mm)              -> 'user_declared'
  3. water balance from a declared last refill date    -> 'water_balance_from_refill_date'
  otherwise status MISSING_INPUTS, volume withheld.
"""
from __future__ import annotations

from typing import Dict, Optional

import numpy as np
import pandas as pd

from .crop_retrieval import CropIndex
from .crop_water_requirements import crop_requirements
from .soil import (SoilParams, depletion_from_theta, root_zone_theta, taw_mm, TYPICAL_EA)
from .water_balance import day_step, mm_to_volume, net_to_gross, simulate

SENSITIVE_STAGES = ("development", "mid_season")   # heuristic, not from Ky data (not retrieved)


def _soil(z: Dict) -> Optional[SoilParams]:
    s = z.get("soil")
    if not s or s.get("fc") is None or s.get("wp") is None:
        return None
    return SoilParams(fc=float(s["fc"]), wp=float(s["wp"]), texture=s.get("texture", "unknown"), source=s.get("source", "user_declared"), note=s.get("note", ""))


def _ea(z: Dict):
    ir = z.get("irrigation") or {}
    if ir.get("ea") is not None:
        return float(ir["ea"]), ir.get("source", "user_declared"), ir.get("method")
    m = ir.get("method")
    if m in TYPICAL_EA:
        return TYPICAL_EA[m], "typical_literature (method default, not measured)", m
    return None, "missing", m


def _eto_today(weather: pd.DataFrame, today: str):
    w = weather[pd.to_datetime(weather["date"]).dt.date.astype(str) <= today].dropna(subset=["eto_mm"])
    if w.empty: return None, None
    r = w.sort_values("date").iloc[-1]
    return float(r["eto_mm"]), str(pd.to_datetime(r["date"]).date())


def recommend_zone(zone: Dict, weather: pd.DataFrame, today: str, forecast: Optional[pd.DataFrame] = None,
                   horizon_days: int = 5, crops: Optional[CropIndex] = None, trigger_fraction: float = 1.0,
                   weather_source: str = "unspecified") -> Dict:
    """Return a dict. Volumes are present only when every required input exists."""
    ix = crops or CropIndex()
    res: Dict = {"zone_id": zone.get("zone_id"), "name": zone.get("name"), "date": today, "weather_source": weather_source,
                 "warnings": [], "missing_inputs": [], "volumes": None}
    try:
        crop = ix.get(zone["crop"])
    except Exception as e:
        res.update(status="UNKNOWN_CROP", message=str(e)); return res
    res["crop"] = crop["id"]; res["area_ha"] = zone.get("area_ha")
    eto, eto_date = _eto_today(weather, today)
    res["eto_mm"], res["eto_date"] = eto, eto_date
    if eto is None:
        res.update(status="MISSING_INPUTS", message="No valid ETo up to today."); res["missing_inputs"].append("eto"); return res
    if eto_date != today:
        res["warnings"].append(f"ETo is from {eto_date}, not {today} (weather age {(pd.Timestamp(today)-pd.Timestamp(eto_date)).days} d).")
    req = crop_requirements(crop, today, eto, zone.get("planting_date"), zone.get("stage_override"), zone.get("kc_variant"))
    res["requirements"] = req; res["warnings"] += req["warnings"]
    if req["status"] != "OK":
        res.update(status="MISSING_INPUTS" if req["status"] in ("NEEDS_PLANTING_DATE", "NO_STAGE_LENGTHS") else req["status"],
                   message=f"crop requirements unavailable: {req['status']}"); res["missing_inputs"] += req.get("missing", []); return res
    res.update(stage=req["stage"], stage_estimated=req["stage_info"]["estimated"], kc=req["kc"], etc_mm=req["etc_mm"], zr_m=req["zr_m"], p=req["p_adjusted"])
    soil = _soil(zone)
    if soil is None:
        res.update(status="MISSING_SOIL_PARAMS", message="FC/WP are required for depletion and volumes; none are invented.")
        res["missing_inputs"].append("soil.fc/wp"); return res
    taw = taw_mm(soil, req["zr_m"]); raw = req["p_adjusted"] * taw
    res.update(taw_mm=taw, raw_mm=raw, soil_source=soil.source)
    if soil.source == "illustrative_preset": res["warnings"].append("Soil FC/WP are an ILLUSTRATIVE preset, not a measured field soil.")
    # ---- depletion source
    dr, src, sens = None, None, zone.get("sensor")
    if sens and sens.get("theta_by_depth_cm"):
        if not sens.get("calibrated", False):
            res["warnings"].append("Sensor present but not flagged calibrated: not used for depletion (raw mV or uncalibrated VWC is never treated as truth).")
        elif sens.get("units") not in ("percent", "fraction"):
            res["warnings"].append("Sensor units are not 'percent'/'fraction' (e.g. mV): not converted to VWC.")
        else:
            rz = root_zone_theta({float(k): v for k, v in sens["theta_by_depth_cm"].items()}, req["zr_m"], sens["units"])
            d = depletion_from_theta(rz["theta_rz"], soil, req["zr_m"])
            res["sensor_root_zone"] = {"theta_rz": rz["theta_rz"], "coverage_fraction": rz["coverage_fraction"], "supported_depth_cm": rz["supported_depth_cm"]}
            res["warnings"] += rz["warnings"] + d["flags"]
            if any("below wilting point" in f for f in d["flags"]):
                res.update(status="INCONSISTENT_SENSOR_SOIL", message="Sensor below declared WP: volume withheld pending calibration.")
                res["missing_inputs"].append("sensor/soil calibration"); return res
            dr, src = d["dr_mm"], "sensor"
    if dr is None and zone.get("current_depletion_mm") is not None:
        dr, src = min(max(float(zone["current_depletion_mm"]), 0.0), taw), "user_declared"
    if dr is None and zone.get("last_refill_date"):
        past = weather[(pd.to_datetime(weather["date"]) > pd.Timestamp(zone["last_refill_date"])) & (pd.to_datetime(weather["date"]) <= pd.Timestamp(today))]
        try:
            sim = simulate(past, crop, soil, planting_date=zone.get("planting_date"), stage_override=zone.get("stage_override"),
                           initial_depletion_mm=0.0, applied_net_mm=zone.get("applied_net_mm"), on_gap="hold")
            sim = sim[~sim["gap"]] if "gap" in sim else sim
            dr = float(sim["dr_end_mm"].iloc[-1]) if len(sim) else 0.0; src = "water_balance_from_refill_date"
            res["warnings"].append("Depletion simulated assuming the soil was at field capacity on last_refill_date (declared by the user).")
        except ValueError as e:
            res["warnings"].append(f"water-balance estimate failed: {e}")
    if dr is None:
        res.update(status="MISSING_INPUTS", message="No depletion source (calibrated sensor, declared depletion, or last refill date).")
        res["missing_inputs"].append("current depletion source"); return res
    res.update(dr_mm=dr, depletion_source=src, dr_over_raw=dr / raw if raw > 0 else None)
    # ---- forecast projection with the same balance
    days_to_raw, ks_now = None, 1.0
    proj = []
    if forecast is not None and len(forecast):
        f = forecast.sort_values("date").head(horizon_days)
        d_ = dr
        for i, (_, r) in enumerate(f.iterrows(), 1):
            if pd.isna(r["eto_mm"]) or pd.isna(r["rain_mm"]):
                res["warnings"].append(f"forecast gap on {r['date']}: projection stopped."); break
            rq = crop_requirements(crop, str(pd.to_datetime(r["date"]).date()), r["eto_mm"], zone.get("planting_date"), zone.get("stage_override"), zone.get("kc_variant"))
            if rq["status"] != "OK": break
            tw = taw_mm(soil, rq["zr_m"]); rw = rq["p_adjusted"] * tw
            st = day_step(min(d_, tw), tw, rq["p_adjusted"], rq["kc"], r["eto_mm"], r["rain_mm"])
            d_ = st["dr_end"]
            proj.append({"date": str(pd.to_datetime(r["date"]).date()), "dr_end_mm": d_, "raw_mm": rw, "rain_mm": float(r["rain_mm"])})
            if days_to_raw is None and d_ >= rw: days_to_raw = i
    else:
        res["warnings"].append("No forecast supplied: timing uses current depletion only.")
    res["projection"] = proj; res["days_to_raw"] = 0 if dr >= raw else days_to_raw
    res["forecast_rain_mm"] = float(sum(p["rain_mm"] for p in proj)) if proj else None
    res["ks_now"] = float(np.clip((taw - dr) / ((1 - req["p_adjusted"]) * taw), 0, 1)) if dr > raw else 1.0
    # ---- decision
    ea, ea_src, method = _ea(zone)
    res.update(ea=ea, ea_source=ea_src, irrigation_method=method)
    if dr >= trigger_fraction * raw: timing = "irrigate_now"
    elif days_to_raw is not None: timing = f"irrigate_within_{days_to_raw}_days"
    else: timing = "no_irrigation_needed_within_horizon"
    res["timing"] = timing
    if timing == "no_irrigation_needed_within_horizon":
        res.update(status="OK", message="Depletion stays below RAW within the horizon.", net_mm=0.0, gross_mm=0.0)
        res["volumes"] = {"net_mm": 0.0, "gross_mm": 0.0, "m3": 0.0, "litres": 0.0}; return res
    net = dr if dr >= raw else (proj[days_to_raw - 1]["dr_end_mm"] if days_to_raw else dr)  # refill to field capacity at the time of irrigation
    res["net_mm"] = net
    if ea is None:
        res.update(status="MISSING_IRRIGATION_SYSTEM", message="Net requirement known; gross volume needs the irrigation method or Ea.")
        res["missing_inputs"].append("irrigation.method/ea"); return res
    gross = net_to_gross(net, ea)
    res.update(status="OK", ea=ea, ea_source=ea_src, irrigation_method=method, gross_mm=gross)
    if zone.get("area_ha"):
        v = mm_to_volume(gross, float(zone["area_ha"])); res["volumes"] = {"net_mm": net, "gross_mm": gross, **v}
    else:
        res["missing_inputs"].append("area_ha"); res["volumes"] = {"net_mm": net, "gross_mm": gross, "m3": None, "litres": None}
    res["message"] = f"{timing}: net {net:.1f} mm, gross {gross:.1f} mm (Ea {ea:.2f}, {ea_src})."
    return res

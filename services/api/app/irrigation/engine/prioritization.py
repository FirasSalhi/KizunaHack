"""Farm-wide ranking and limited-water allocation.

Ranking is rule-based and explainable (weights below are DESIGN CHOICES, not calibrated or learned).
Zones whose recommendation is not computable (status != OK) go to category NEEDS_DATA, never silently ranked low.

score = 0.50*min(Dr/RAW,1.5)/1.5            current stress proximity
      + 0.20*urgency(days_to_raw)           1 now, 0.75 <=1d, 0.5 <=3d, 0.25 <=5d, else 0
      + 0.15*stage_sensitivity              1 for development/mid-season (heuristic; Ky data not retrieved), 0.5 otherwise
      + 0.10*buffer_penalty                 1 - min(TAW/60,1): small TAW = little buffer
      - 0.15*rain_relief                    min(forecast rain/ net requirement,1) when irrigation is not yet needed
      - 0.10*data_penalty                   0.5 if depletion not from sensor/declared, + stage estimated / illustrative soil flags
Levels: HIGH if Dr>=RAW or days_to_raw<=1 ; MEDIUM if days_to_raw<=3 or Dr/RAW>=0.7 ; else LOW.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from .water_balance import mm_to_volume, volume_to_mm, net_to_gross

WEIGHTS = {"stress": 0.50, "urgency": 0.20, "stage": 0.15, "buffer": 0.10, "rain_relief": -0.15, "data_quality": -0.10}


def _urgency(d):
    if d is None: return 0.0
    return 1.0 if d <= 0 else 0.75 if d <= 1 else 0.5 if d <= 3 else 0.25 if d <= 5 else 0.0


def score_zone(r: Dict) -> Dict:
    ratio = r["dr_over_raw"]; dtr = r.get("days_to_raw")
    stage_s = 1.0 if r.get("stage") in ("development", "mid_season") else 0.5
    buffer = 1 - min(r["taw_mm"] / 60.0, 1.0)
    net = r.get("net_mm") or 0.0
    rain_relief = min((r.get("forecast_rain_mm") or 0.0) / net, 1.0) if (net > 0 and dtr not in (0,)) else 0.0
    dq = 0.0
    if r.get("depletion_source") == "water_balance_from_refill_date": dq += 0.5
    if r.get("stage_estimated"): dq += 0.25
    if r.get("soil_source") == "illustrative_preset": dq += 0.25
    comp = {"stress": min(ratio, 1.5) / 1.5, "urgency": _urgency(dtr), "stage": stage_s, "buffer": buffer, "rain_relief": rain_relief, "data_quality": min(dq, 1.0)}
    score = sum(WEIGHTS[k] * v for k, v in comp.items())
    level = "HIGH" if (ratio >= 1.0 or (dtr is not None and dtr <= 1)) else "MEDIUM" if ((dtr is not None and dtr <= 3) or ratio >= 0.7) else "LOW"
    why = [f"Dr/RAW = {ratio:.2f}", f"days to RAW: {'now' if dtr == 0 else dtr if dtr is not None else '>horizon'}", f"stage: {r.get('stage')}",
           f"TAW {r['taw_mm']:.0f} mm"]
    if rain_relief > 0: why.append(f"forecast rain {r.get('forecast_rain_mm'):.0f} mm lowers urgency")
    if dq: why.append("depletion/stage rests on assumptions (data-quality penalty)")
    return {"score": round(score, 4), "level": level, "components": {k: round(v, 3) for k, v in comp.items()}, "explanation": "; ".join(why)}


def rank_farm(recs: List[Dict]) -> Dict:
    ranked, needs = [], []
    for r in recs:
        if r.get("status") == "OK" and r.get("dr_over_raw") is not None:
            ranked.append({**r, "priority": score_zone(r)})
        else:
            needs.append({"zone_id": r.get("zone_id"), "name": r.get("name"), "category": "NEEDS_DATA", "status": r.get("status"),
                          "missing_inputs": r.get("missing_inputs"), "message": r.get("message")})
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    ranked.sort(key=lambda z: (order[z["priority"]["level"]], -z["priority"]["score"], str(z["zone_id"])))
    for i, z in enumerate(ranked, 1): z["rank"] = i
    return {"ranked": ranked, "needs_data": needs, "weights": WEIGHTS, "weights_note": "design choices, not calibrated"}


def allocate_limited_water(ranked: List[Dict], available_m3: float) -> Dict:
    """Two-phase, deterministic, documented strategy - NOT claimed optimal and NOT a yield model.

    Phase 1 (protect): in rank order give each zone the gross volume that restores Dr to RAW (the stress threshold):
        net = max(Dr - RAW, 0)  (zones not yet at RAW need nothing in phase 1).
    Phase 2 (refill): spend the remainder in rank order to move toward field capacity (net = Dr).
    A zone receives at most its full requirement; shortfalls are reported with the residual depletion.
    """
    if available_m3 < 0: raise ValueError("available water must be >= 0")
    left = float(available_m3)
    plan = {z["zone_id"]: {"zone_id": z["zone_id"], "rank": z["rank"], "level": z["priority"]["level"], "area_ha": z["area_ha"], "ea": z.get("ea"),
                           "full_need_gross_m3": z["volumes"]["m3"] if z.get("volumes") and z["volumes"].get("m3") is not None else None,
                           "allocated_m3": 0.0, "dr_mm": z["dr_mm"], "raw_mm": z["raw_mm"]} for z in ranked if z.get("ea") and z.get("area_ha")}
    skipped = [z["zone_id"] for z in ranked if z["zone_id"] not in plan]
    zs = {z["zone_id"]: z for z in ranked}
    for phase in (1, 2):
        for zid, p in plan.items():
            z = zs[zid]
            target_net = max(z["dr_mm"] - z["raw_mm"], 0.0) if phase == 1 else z["dr_mm"]
            already_net = p["allocated_m3"] / (z["area_ha"] * 10.0) * z["ea"]
            need_net = max(target_net - already_net, 0.0)
            need_m3 = mm_to_volume(net_to_gross(need_net, z["ea"]), z["area_ha"])["m3"] if need_net > 0 else 0.0
            give = min(need_m3, left); p["allocated_m3"] += give; left -= give
    for zid, p in plan.items():
        z = zs[zid]; net_applied = p["allocated_m3"] / (z["area_ha"] * 10.0) * z["ea"]
        p["net_mm_applied"] = net_applied; p["gross_mm_applied"] = p["allocated_m3"] / (z["area_ha"] * 10.0)
        p["residual_dr_mm"] = max(z["dr_mm"] - net_applied, 0.0); p["residual_dr_over_raw"] = p["residual_dr_mm"] / z["raw_mm"]
        p["still_beyond_raw"] = p["residual_dr_mm"] > z["raw_mm"]
        p["fully_satisfied"] = p["full_need_gross_m3"] is not None and p["allocated_m3"] >= p["full_need_gross_m3"] - 1e-9
    return {"available_m3": available_m3, "allocated_m3": round(available_m3 - left, 6), "unallocated_m3": round(left, 6), "plan": list(plan.values()),
            "zones_without_volume_inputs": skipped, "strategy": "two-phase protect-then-refill in priority order (heuristic; not optimised, no yield response)"}

"""Multi-zone farm registry with minimal farmer input. Nothing about soil is invented: missing properties stay None."""
from __future__ import annotations

import json
from typing import Dict, List, Optional

REQUIRED = ("zone_id", "crop", "area_ha")
OPTIONAL = ("name", "planting_date", "stage_override", "soil", "irrigation", "sensor", "last_refill_date", "current_depletion_mm", "kc_variant", "applied_net_mm", "notes")


def validate_zone(z: Dict) -> List[str]:
    errs = [f"missing required field '{k}'" for k in REQUIRED if z.get(k) in (None, "")]
    if z.get("area_ha") is not None:
        try:
            if float(z["area_ha"]) <= 0: errs.append("area_ha must be > 0")
        except (TypeError, ValueError): errs.append("area_ha must be a number")
    s = z.get("soil")
    if s:
        fc, wp = s.get("fc"), s.get("wp")
        if (fc is None) != (wp is None): errs.append("soil needs both fc and wp (or neither)")
        if fc is not None and wp is not None and not (0 < wp < fc < 0.7): errs.append("soil requires 0 < wp < fc < 0.7 (m3/m3)")
    ir = z.get("irrigation") or {}
    if ir.get("ea") is not None and not (0 < ir["ea"] <= 1): errs.append("irrigation.ea must be in (0,1]")
    unknown = set(z) - set(REQUIRED) - set(OPTIONAL)
    if unknown: errs.append(f"unknown fields {sorted(unknown)}")
    return errs


def load_farm(obj) -> Dict:
    farm = json.load(open(obj, encoding="utf-8")) if isinstance(obj, str) else obj
    problems = {}
    for z in farm.get("zones", []):
        e = validate_zone(z)
        if e: problems[z.get("zone_id", "?")] = e
    if problems: raise ValueError(f"invalid farm definition: {problems}")
    ids = [z["zone_id"] for z in farm["zones"]]
    if len(ids) != len(set(ids)): raise ValueError("duplicate zone_id")
    return farm


def correct_zone(zone: Dict, **changes) -> Dict:
    """Manual correction by the farmer (e.g. stage_override, planting_date). Returns a new dict; validates."""
    z = {**zone, **changes}; e = validate_zone(z)
    if e: raise ValueError(e)
    return z

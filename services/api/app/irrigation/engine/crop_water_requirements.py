"""Crop-specific quantities: growth stage from dates, Kc curve, root-depth development, adjusted p, ETc.

All numbers come from the crop database record (FAO-56 Tables 11/12/22). Nothing is guessed: when a required input
(planting date for an annual, stage for a perennial) is missing, the stage is reported as unknown and no Kc is returned.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Dict, Optional

import numpy as np

STAGES = ("initial", "development", "mid_season", "late_season")
_KEYS = {"initial": "ini", "development": "dev", "mid_season": "mid", "late_season": "late"}


def _d(x) -> date:
    if isinstance(x, datetime): return x.date()
    if isinstance(x, date): return x
    return datetime.strptime(str(x)[:10], "%Y-%m-%d").date()


def stage_lengths(crop: Dict, variant_index: Optional[int] = None) -> Optional[Dict]:
    if not crop.get("stage_lengths_days"):
        return None
    s = crop["stage_lengths_days"] if variant_index is None else crop["stage_length_variants"][variant_index]
    return {k: int(s[k]) for k in ("ini", "dev", "mid", "late")}


def growth_stage(crop: Dict, on_date, planting_date=None, stage_override: Optional[str] = None,
                 variant_index: Optional[int] = None) -> Dict:
    """Estimate the stage. Returns dict(status, stage, day_in_season, day_in_stage, stage_length, estimated, warnings).

    status: OK | MANUAL | NEEDS_PLANTING_DATE | NO_STAGE_LENGTHS | NOT_PLANTED | SEASON_ENDED | INVALID_STAGE
    A manual stage (farmer correction) always wins and is flagged estimated=False.
    """
    w = []
    if stage_override is not None:
        if stage_override not in STAGES:
            return {"status": "INVALID_STAGE", "stage": None, "estimated": False, "warnings": [f"stage '{stage_override}' not in {STAGES}"]}
        return {"status": "MANUAL", "stage": stage_override, "day_in_season": None, "estimated": False, "warnings": []}
    sl = stage_lengths(crop, variant_index)
    if sl is None:
        return {"status": "NO_STAGE_LENGTHS", "stage": None, "estimated": True,
                "warnings": [f"{crop['id']}: no FAO-56 stage lengths in the knowledge base; provide the stage manually."]}
    if planting_date is None:
        return {"status": "NEEDS_PLANTING_DATE", "stage": None, "estimated": True,
                "warnings": ["planting date (annual) or season start (perennial) is required to estimate the stage; or give the stage manually."]}
    day = (_d(on_date) - _d(planting_date)).days
    if day < 0:
        return {"status": "NOT_PLANTED", "stage": None, "day_in_season": day, "estimated": True, "warnings": ["date is before planting date"]}
    total = sum(sl.values())
    if day >= total:
        if crop["perennial"]:
            day = day % 365 if total >= 360 else day
            if day >= total:
                return {"status": "SEASON_ENDED", "stage": None, "day_in_season": day, "estimated": True,
                        "warnings": [f"day {day} beyond the {total}-day cycle."]}
        else:
            return {"status": "SEASON_ENDED", "stage": None, "day_in_season": day, "estimated": True,
                    "warnings": [f"day {day} beyond the published {total}-day cycle; harvested or season longer than the FAO-56 example."]}
    acc = 0
    for st in STAGES:
        L = sl[_KEYS[st]]
        if day < acc + L:
            w.append("Stage estimated from FAO-56 example stage lengths (region: %s); correct manually if the field differs."
                     % crop["stage_lengths_days"].get("region"))
            return {"status": "OK", "stage": st, "day_in_season": day, "day_in_stage": day - acc, "stage_length": L,
                    "estimated": True, "warnings": w}
        acc += L
    return {"status": "SEASON_ENDED", "stage": None, "day_in_season": day, "estimated": True, "warnings": ["beyond cycle"]}


def kc_on_day(crop: Dict, day_in_season: int, kc_variant: Optional[str] = None, variant_index: Optional[int] = None) -> float:
    """FAO-56 Fig. 34 piecewise Kc curve: flat ini; linear ini->mid over dev; flat mid; linear mid->end over late."""
    kc = _kc_values(crop, kc_variant)
    sl = stage_lengths(crop, variant_index)
    if sl is None:
        raise ValueError("no stage lengths")
    i, dv, m, l = sl["ini"], sl["dev"], sl["mid"], sl["late"]
    d = day_in_season
    if d < i: return kc["ini"]
    if d < i + dv: return kc["ini"] + (kc["mid"] - kc["ini"]) * (d - i) / dv
    if d < i + dv + m: return kc["mid"]
    if d < i + dv + m + l: return kc["mid"] + (kc["end"] - kc["mid"]) * (d - i - dv - m) / l
    return kc["end"]


def _kc_values(crop: Dict, variant: Optional[str] = None) -> Dict:
    k = crop.get("kc")
    if not k:
        raise ValueError(f"{crop['id']}: Kc not available in the knowledge base")
    if variant:
        for v in k.get("variants", []):
            if v["label"] == variant:
                return {"ini": v["ini"], "mid": v["mid"], "end": v["end"]}
        raise ValueError(f"unknown Kc variant '{variant}' for {crop['id']}")
    return {"ini": k["ini"], "mid": k["mid"], "end": k["end"]}


def kc_for_stage(crop: Dict, stage: str, kc_variant: Optional[str] = None) -> Dict:
    """Representative Kc for a manually chosen stage: ini->ini, mid->mid, late->mean(mid,end), dev->mean(ini,mid)."""
    v = _kc_values(crop, kc_variant)
    val = {"initial": v["ini"], "development": (v["ini"] + v["mid"]) / 2, "mid_season": v["mid"], "late_season": (v["mid"] + v["end"]) / 2}[stage]
    note = "stage-representative Kc (development/late are midpoints of the FAO-56 curve segment)" if stage in ("development", "late_season") else "FAO-56 table value"
    return {"kc": val, "note": note}


def root_depth(crop: Dict, stage_info: Dict, zr_choice: str = "scheduling", variant_index: Optional[int] = None) -> Dict:
    """Effective root depth (m). Annuals: linear from an ASSUMED 0.3 m at planting (FAO-56 Example 38 only) to the Table 22
    scheduling depth (smaller value of the range) at the end of the development stage. Perennials: constant."""
    rd = crop.get("root_depth")
    if not rd:
        raise ValueError(f"{crop['id']}: root depth not available")
    zr_max = rd["zr_min_m"] if zr_choice == "scheduling" else rd["zr_max_m"]
    if crop["perennial"]:
        return {"zr_m": zr_max, "basis": "Table 22 (perennial: constant)", "assumption": False}
    z0 = min(rd["development"]["initial_zr_m_assumption"], zr_max)
    sl = stage_lengths(crop, variant_index)
    day = stage_info.get("day_in_season")
    if stage_info.get("status") == "MANUAL" or sl is None or day is None:
        zr = {"initial": z0, "development": (z0 + zr_max) / 2}.get(stage_info.get("stage"), zr_max)
        return {"zr_m": zr, "basis": "manual stage: initial->%.2f m, development->midpoint, later->%.2f m" % (z0, zr_max), "assumption": True}
    t = min(1.0, max(0.0, day / float(sl["ini"] + sl["dev"])))
    return {"zr_m": z0 + (zr_max - z0) * t, "basis": f"linear {z0:.2f}->{zr_max:.2f} m over initial+development (start depth = FAO-56 Example 38 assumption)", "assumption": True}


def adjusted_p(p_table: float, etc_mm_day: float) -> float:
    """FAO-56 Table 22 note: p = p_table + 0.04 (5 - ETc), limited to 0.1-0.8."""
    return float(min(0.8, max(0.1, p_table + 0.04 * (5.0 - etc_mm_day))))


def crop_requirements(crop: Dict, on_date, eto_mm: float, planting_date=None, stage_override: Optional[str] = None,
                      kc_variant: Optional[str] = None, variant_index: Optional[int] = None, zr_choice: str = "scheduling") -> Dict:
    """Stage, Kc, ETc, Zr and adjusted p for one crop on one day. Returns status != 'OK' with missing list when inputs are absent."""
    out = {"crop": crop["id"], "date": str(_d(on_date)), "warnings": [], "missing": []}
    if not crop["irrigation_ready"]:
        out.update(status="CROP_PARAMETERS_UNAVAILABLE", missing=["kc", "root_depth", "p"]); return out
    si = growth_stage(crop, on_date, planting_date, stage_override, variant_index)
    out["stage_info"] = si
    out["warnings"] += si.get("warnings", [])
    if si["stage"] is None:
        out.update(status=si["status"], missing=["growth_stage"]); return out
    if si["status"] == "MANUAL":
        kc = kc_for_stage(crop, si["stage"], kc_variant)["kc"]
        out["kc_basis"] = "stage-representative"
    else:
        kc = kc_on_day(crop, si["day_in_season"], kc_variant, variant_index); out["kc_basis"] = "daily FAO-56 curve"
    zr = root_depth(crop, si, zr_choice, variant_index)
    out.update(status="OK", stage=si["stage"], kc=float(kc), zr_m=zr["zr_m"], zr_basis=zr["basis"])
    if crop["kc"]["ini_source"] == "FAO56_TABLE12_GROUP_DEFAULT" and si["stage"] == "initial":
        out["warnings"].append("Kc initial is the FAO-56 group default (crop-specific value not retrieved).")
    if crop["confidence"].get("kc") == "generic_crop_approximation":
        out["warnings"].append(f"{crop['id']}: generic-crop approximation (see crop notes).")
    if eto_mm is not None and not np.isnan(eto_mm):
        out["eto_mm"] = float(eto_mm); out["etc_mm"] = float(kc * eto_mm)
        out["p_adjusted"] = adjusted_p(crop["depletion_fraction_p"]["value"], out["etc_mm"])
    else:
        out["warnings"].append("ETo unavailable: ETc and adjusted p not computed.")
        out["p_adjusted"] = crop["depletion_fraction_p"]["value"]
    return out

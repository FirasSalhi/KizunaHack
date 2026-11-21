"""Crop knowledge base (FAO-56 primary reference).

Every numeric value carries a provenance tag so that nothing is silently
"universal":

  FAO56_TABLE        value printed in an FAO-56 table
  FAO56_RANGE_MID    midpoint of a range printed in FAO-56 (range kept in kc_low/kc_high)
  DERIVED_LINEAR     stage-mean obtained by linear interpolation between two
                     FAO-56 end-points (FAO-56 Fig. 34 construction)

Root depth and p are *maximum / typical* values and are local-condition dependent.
Soil hydraulic parameters (FC, WP), texture and application efficiency are NOT
crop properties and live in ``soil.py``.

References
----------
[1] Allen R.G., Pereira L.S., Raes D., Smith M. (1998). Crop evapotranspiration -
    Guidelines for computing crop water requirements. FAO Irrigation and Drainage
    Paper 56. Table 11 (stage lengths), Table 12 (Kc), Table 22 (Zr, p).
    https://www.fao.org/4/x0490e/x0490e00.htm
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

import pandas as pd

STAGES: Tuple[str, ...] = ("initial", "development", "mid_season", "late_season")

FAO56_TABLE = "FAO56_TABLE"
FAO56_RANGE_MID = "FAO56_RANGE_MID"
DERIVED_LINEAR = "DERIVED_LINEAR"


@dataclass(frozen=True)
class StageKc:
    """Kc for one growth stage.

    kc_start / kc_end are the Kc at the beginning / end of the stage (FAO-56
    construction); ``kc`` is the stage-mean used by the stage-based engine.
    ``kc_low`` / ``kc_high`` express published uncertainty where FAO-56 gives a range.
    """
    kc: float
    kc_start: float
    kc_end: float
    kc_low: float
    kc_high: float
    provenance: str


@dataclass(frozen=True)
class CropParams:
    key: str
    name_en: str
    name_fr: str
    stages: Dict[str, StageKc]
    root_depth_m: float                 # default used for scheduling (lower bound of Table 22 range)
    root_depth_range_m: Tuple[float, float]
    p_table: float                      # depletion fraction for ETc ~ 5 mm/day (Table 22)
    stage_lengths_days: Dict[str, int]  # Table 11, Mediterranean row (local calibration needed)
    stage_lengths_source: str
    irrigation_notes: Tuple[str, ...]
    approximations: Tuple[str, ...]
    references: Tuple[str, ...]
    aliases: Tuple[str, ...] = field(default_factory=tuple)


def _stage_table(kc_ini: float, kc_mid: float, kc_end_low: float, kc_end_high: float) -> Dict[str, StageKc]:
    kc_end = round((kc_end_low + kc_end_high) / 2.0, 4)
    dev = round((kc_ini + kc_mid) / 2.0, 4)
    late = round((kc_mid + kc_end) / 2.0, 4)
    return {
        "initial": StageKc(kc_ini, kc_ini, kc_ini, kc_ini, kc_ini, FAO56_TABLE),
        "development": StageKc(dev, kc_ini, kc_mid, min(kc_ini, kc_mid), max(kc_ini, kc_mid), DERIVED_LINEAR),
        "mid_season": StageKc(kc_mid, kc_mid, kc_mid, kc_mid, kc_mid, FAO56_TABLE),
        "late_season": StageKc(late, kc_mid, kc_end,
                               round((kc_mid + kc_end_low) / 2.0, 4),
                               round((kc_mid + kc_end_high) / 2.0, 4),
                               DERIVED_LINEAR),
    }


_REF = "FAO-56 (Allen et al., 1998), Tables 11, 12, 22"

CROPS: Dict[str, CropParams] = {
    "tomato": CropParams(
        key="tomato", name_en="Tomato", name_fr="Tomate",
        stages=_stage_table(kc_ini=0.60, kc_mid=1.15, kc_end_low=0.70, kc_end_high=0.90),
        root_depth_m=0.7, root_depth_range_m=(0.7, 1.5), p_table=0.40,
        stage_lengths_days={"initial": 30, "development": 40, "mid_season": 45, "late_season": 30},
        stage_lengths_source="FAO-56 Table 11, tomato, Mediterranean, planted April/May (145 d)",
        irrigation_notes=(
            "Kc ini 0.6 is the Solanum-family value printed in Table 12 (no separate tomato Kc ini).",
            "Table 12 footnote: tomatoes grown on stakes (1.5-2 m) may need a higher Kc mid; h should be increased.",
            "Table 22 lower Zr (0.7 m) is the value FAO-56 allows for irrigation scheduling; deeper (up to 1.5 m) for unrestricted soils.",
            "Protected (greenhouse) tomatoes have a different microclimate: ETo from outdoor weather does not apply directly.",
        ),
        approximations=(
            "Development and late-season Kc are stage means by linear interpolation (DERIVED_LINEAR), not table values.",
            "Late-season Kc end is the midpoint of the published range 0.70-0.90; kc_low/kc_high give the range.",
            "Actual active root depth is smaller than the tabulated maximum in initial/development stages.",
        ),
        references=(_REF,),
        aliases=("tomate", "tomatoes"),
    ),
    "olive": CropParams(
        key="olive", name_en="Olive", name_fr="Olivier",
        stages=_stage_table(kc_ini=0.65, kc_mid=0.70, kc_end_low=0.70, kc_end_high=0.70),
        root_depth_m=1.2, root_depth_range_m=(1.2, 1.7), p_table=0.65,
        stage_lengths_days={"initial": 30, "development": 90, "mid_season": 60, "late_season": 90},
        stage_lengths_source="FAO-56 Table 11, olives, Mediterranean, March (270 d; total printed '2705' in source is a typo)",
        irrigation_notes=(
            "Table 12 values represent about 40-60 % ground cover (footnote 24); sparse traditional groves need a cover-based reduction not applied here.",
            "FAO-56 footnote 24 also lists an alternative set (Kc ini 0.65, mid 0.45, end 0.65) for Spanish conditions.",
            "Evergreen tree crop: 'growth stages' are phenological phases with weak Kc contrast; deficit/regulated irrigation is common practice.",
        ),
        approximations=(
            "Kc values are for 40-60 % canopy cover only; real Tunisian orchards (density, cultivar, ground cover) differ.",
            "Stage lengths are from a single Mediterranean example row.",
        ),
        references=(_REF,),
        aliases=("olivier", "olives"),
    ),
    "durum_wheat": CropParams(
        key="durum_wheat", name_en="Durum wheat", name_fr="Blé dur",
        stages=_stage_table(kc_ini=0.70, kc_mid=1.15, kc_end_low=0.25, kc_end_high=0.40),
        root_depth_m=1.5, root_depth_range_m=(1.5, 1.8), p_table=0.55,
        stage_lengths_days={"initial": 30, "development": 140, "mid_season": 40, "late_season": 30},
        stage_lengths_source="FAO-56 Table 11, winter wheat, Mediterranean, November sowing (240 d)",
        irrigation_notes=(
            "FAO-56 gives no durum-specific row; values are the generic winter-wheat rows (non-frozen soils: Kc ini 0.7; spring wheat group header: 0.3).",
            "Kc ini is a function of wetting interval and evaporation power (Table 12 footnote 1): with infrequent wetting it can be much lower than 0.7; refine with FAO-56 Fig. 29-30.",
            "Kc end 0.25-0.40: the higher value is for hand-harvested crops (footnote 10).",
            "In Tunisia durum wheat is largely rainfed with supplementary irrigation; the engine only computes the atmospheric/soil demand, not yield response.",
        ),
        approximations=(
            "Kc ini 0.7 is a table value but is probably high for dry, infrequently wetted soil: use kc_override with a documented reason if local data exist.",
            "Zr 1.5 m is the lower end of the Table 22 range; early in the season the active root depth is far smaller (TAW overestimated).",
            "Development and late-season Kc are DERIVED_LINEAR stage means.",
        ),
        references=(_REF,),
        aliases=("wheat", "durum wheat", "durum", "ble dur", "blé dur", "blé", "ble"),
    ),
}


def list_crops() -> list:
    return sorted(CROPS)


def get_crop(name: str) -> CropParams:
    """Return crop parameters or raise ValueError. No silent fallback."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"Crop name must be a non-empty string; supported crops: {list_crops()}")
    token = name.strip().lower().replace("-", " ").replace("_", " ")
    for key, crop in CROPS.items():
        names = {key.replace("_", " "), crop.name_en.lower(), crop.name_fr.lower(), *crop.aliases}
        if token in {n.replace("_", " ") for n in names}:
            return crop
    raise ValueError(f"Unsupported crop '{name}'. Supported crops: {list_crops()}. No silent fallback is applied.")


def validate_stage(stage: str) -> str:
    if stage not in STAGES:
        raise ValueError(f"Unsupported growth stage '{stage}'. Supported stages: {list(STAGES)}.")
    return stage


def kc_for_stage(crop: str, stage: str, kc_override: Optional[float] = None) -> float:
    """Stage-mean Kc. ``kc_override`` must be a positive number the caller takes responsibility for."""
    c = get_crop(crop)
    validate_stage(stage)
    if kc_override is not None:
        if not (0.0 < float(kc_override) <= 1.6):
            raise ValueError(f"kc_override={kc_override} outside plausible range (0, 1.6].")
        return float(kc_override)
    return c.stages[stage].kc


def kc_on_day(crop: str, day_after_planting: float, stage_lengths: Optional[Dict[str, int]] = None) -> float:
    """Day-wise Kc curve (FAO-56 Fig. 34): constant Kc ini, linear rise to Kc mid,
    constant Kc mid, linear decline to Kc end. Day 0 = start of the initial stage."""
    c = get_crop(crop)
    L = stage_lengths or c.stage_lengths_days
    if any(k not in L or L[k] <= 0 for k in STAGES):
        raise ValueError(f"stage_lengths must define positive lengths for {STAGES}")
    kc_ini = c.stages["initial"].kc
    kc_mid = c.stages["mid_season"].kc
    kc_end = c.stages["late_season"].kc_end
    d = float(day_after_planting)
    total = sum(L[s] for s in STAGES)
    if d < 0 or d > total:
        raise ValueError(f"day_after_planting={d} outside the season (0-{total} d).")
    if d <= L["initial"]:
        return kc_ini
    d -= L["initial"]
    if d <= L["development"]:
        return kc_ini + d / L["development"] * (kc_mid - kc_ini)
    d -= L["development"]
    if d <= L["mid_season"]:
        return kc_mid
    d -= L["mid_season"]
    return kc_mid + d / L["late_season"] * (kc_end - kc_mid)


def crop_table() -> pd.DataFrame:
    """Flat table of every stage value with provenance (exported to CSV / shown in the notebook)."""
    rows = []
    for c in CROPS.values():
        for s in STAGES:
            k = c.stages[s]
            rows.append({
                "crop": c.key, "name_fr": c.name_fr, "stage": s,
                "kc_stage_mean": k.kc, "kc_start": k.kc_start, "kc_end": k.kc_end,
                "kc_low": k.kc_low, "kc_high": k.kc_high, "kc_provenance": k.provenance,
                "root_depth_m_default": c.root_depth_m,
                "root_depth_range_m": f"{c.root_depth_range_m[0]}-{c.root_depth_range_m[1]}",
                "p_table22_ETc5": c.p_table,
                "stage_length_days": c.stage_lengths_days[s],
                "reference": c.references[0],
            })
    return pd.DataFrame(rows)

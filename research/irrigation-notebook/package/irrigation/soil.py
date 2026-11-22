"""Soil, irrigation-system and multi-depth sensor handling.

FC, WP, texture and application efficiency are properties of the *field* and the
*irrigation system*, never of a crop. They must be measured (laboratory / field
calibration) or explicitly declared by the user.

Illustrative presets are limited to values that were verified in FAO-56 Example 36
(loamy sand, silt, silty clay; printed as approximate). The full FAO-56 Table 19
was not transcribed: enter FC/WP from Table 19 or a soil analysis via ``SoilParams``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Optional

SOIL_SOURCES = ("measured", "user_declared", "illustrative_preset")
EA_SOURCES = ("measured", "user_declared", "typical_literature")


@dataclass(frozen=True)
class SoilParams:
    """Hydraulic limits of the root-zone soil (volumetric, m3/m3)."""
    fc: float
    wp: float
    texture: Optional[str] = None
    source: str = "user_declared"
    note: str = ""

    def __post_init__(self):
        if self.source not in SOIL_SOURCES:
            raise ValueError(f"soil source must be one of {SOIL_SOURCES}")
        if not (0.0 <= self.wp < 1.0):
            raise ValueError(f"Wilting point WP={self.wp} must be in [0, 1) m3/m3 (not percent).")
        if not (0.0 < self.fc <= 1.0):
            raise ValueError(f"Field capacity FC={self.fc} must be in (0, 1] m3/m3 (not percent).")
        if self.fc <= self.wp:
            raise ValueError(f"Field capacity ({self.fc}) must be strictly greater than wilting point ({self.wp}).")

    @property
    def awc_mm_per_m(self) -> float:
        return 1000.0 * (self.fc - self.wp)


@dataclass(frozen=True)
class IrrigationSystem:
    """Field application efficiency Ea (fraction of applied water reaching the root zone)."""
    method: str
    ea: float
    source: str = "user_declared"

    def __post_init__(self):
        if self.source not in EA_SOURCES:
            raise ValueError(f"efficiency source must be one of {EA_SOURCES}")
        if not (0.0 < self.ea <= 1.0):
            raise ValueError(f"Application efficiency Ea={self.ea} must be in (0, 1].")


# FAO Irrigation Water Management training manual, Annex I Table 8 (Brouwer & Heibloem):
# surface 60 %, sprinkler 75 %, drip 90 % - indicative, lower with poor management.
TYPICAL_EA = {"surface": 0.60, "sprinkler": 0.75, "drip": 0.90}


def typical_system(method: str) -> IrrigationSystem:
    if method not in TYPICAL_EA:
        raise ValueError(f"Unknown irrigation method '{method}'. Choose from {sorted(TYPICAL_EA)} or build IrrigationSystem explicitly.")
    return IrrigationSystem(method, TYPICAL_EA[method], source="typical_literature")


# FAO-56 Example 36 values (printed with '~'): ILLUSTRATIVE ONLY, not site measurements.
ILLUSTRATIVE_SOILS: Dict[str, SoilParams] = {
    "loamy_sand": SoilParams(0.15, 0.06, "loamy sand", "illustrative_preset", "FAO-56 Example 36 (approximate)"),
    "silt": SoilParams(0.32, 0.15, "silt", "illustrative_preset", "FAO-56 Example 36 (approximate)"),
    "silty_clay": SoilParams(0.35, 0.23, "silty clay", "illustrative_preset", "FAO-56 Example 36 (approximate)"),
}


def get_illustrative_soil(name: str) -> SoilParams:
    if name not in ILLUSTRATIVE_SOILS:
        raise ValueError(f"No illustrative preset '{name}'. Available: {sorted(ILLUSTRATIVE_SOILS)}. "
                         "Provide measured FC/WP via SoilParams instead.")
    return ILLUSTRATIVE_SOILS[name]


# ---------------------------------------------------------------- units -----
def vwc_to_fraction(value: float, units: str = "percent") -> float:
    """Convert a volumetric water content to m3/m3 with an explicit unit declaration."""
    if units == "percent":
        v = float(value) / 100.0
    elif units == "fraction":
        v = float(value)
    else:
        raise ValueError("units must be 'percent' or 'fraction'")
    if not (0.0 <= v <= 1.0):
        raise ValueError(f"VWC {value} ({units}) is outside the physical range 0-1 m3/m3 - check units.")
    return v


def taw_mm(soil: SoilParams, zr_m: float) -> float:
    """Total available water, FAO-56 Eq. 82: TAW = 1000 (FC - WP) Zr  [mm]."""
    if zr_m <= 0:
        raise ValueError(f"Root depth Zr={zr_m} m must be > 0.")
    return 1000.0 * (soil.fc - soil.wp) * zr_m


# ---------------------------------------------------------- root zone -------
def root_zone_theta(theta_by_depth_cm: Mapping[float, float], zr_m: float, units: str = "percent") -> Dict:
    """Thickness-weighted root-zone mean VWC from point sensors at several depths.

    Each sensor is assumed to represent the layer around it (boundaries at mid-points
    between sensors; the first layer starts at the surface; the deepest layer is
    supported down to its sensor depth plus half the last sensor spacing).
    Below the supported depth the deepest reading is *extrapolated* - this is flagged
    in ``coverage_fraction`` / ``warnings``. This is a modelling assumption that needs
    site calibration; one sensor never represents the whole root zone.
    """
    if zr_m <= 0:
        raise ValueError("Root depth must be > 0 m")
    depths = sorted(float(d) for d in theta_by_depth_cm)
    if not depths:
        raise ValueError("At least one sensor depth is required.")
    if any(d <= 0 for d in depths):
        raise ValueError("Sensor depths must be positive (cm).")
    vals = {d: vwc_to_fraction(theta_by_depth_cm[d], units) for d in depths}
    zr_cm = zr_m * 100.0
    bounds = [0.0] + [(depths[i] + depths[i + 1]) / 2.0 for i in range(len(depths) - 1)]
    half_last = (depths[-1] - depths[-2]) / 2.0 if len(depths) > 1 else depths[-1]
    supported_to = depths[-1] + half_last
    layers = []
    for i, d in enumerate(depths):
        top = bounds[i]
        bottom = bounds[i + 1] if i + 1 < len(depths) else zr_cm
        top_c, bottom_c = min(top, zr_cm), min(bottom, zr_cm)
        if bottom_c > top_c:
            layers.append({"sensor_cm": d, "top_cm": top_c, "bottom_cm": bottom_c,
                           "thickness_cm": bottom_c - top_c, "theta": vals[d]})
    thick = sum(l["thickness_cm"] for l in layers)
    theta_rz = sum(l["theta"] * l["thickness_cm"] for l in layers) / thick
    coverage = min(1.0, supported_to / zr_cm)
    warnings = []
    if coverage < 1.0:
        warnings.append(f"Root zone ({zr_cm:.0f} cm) extends below the sensor-supported depth "
                        f"({supported_to:.0f} cm): deepest reading is extrapolated over "
                        f"{100*(1-coverage):.0f} % of the root zone.")
    if len(depths) == 1:
        warnings.append("Single sensor depth: root-zone mean is an extrapolation of one point.")
    return {"theta_rz": theta_rz, "layers": layers, "coverage_fraction": coverage,
            "supported_depth_cm": supported_to, "warnings": warnings}


def depletion_from_theta(theta_rz: float, soil: SoilParams, zr_m: float) -> Dict:
    """Dr = 1000 (FC - theta) Zr (FAO-56 Eq. 87), clipped to [0, TAW]; flags physical inconsistencies."""
    taw = taw_mm(soil, zr_m)
    raw_dr = 1000.0 * (soil.fc - theta_rz) * zr_m
    flags = []
    if theta_rz > soil.fc:
        flags.append("theta above field capacity (Dr set to 0): check FC or sensor calibration.")
    if theta_rz < soil.wp:
        flags.append("theta below wilting point (Dr set to TAW): sensor reading is inconsistent with the declared "
                     "soil (or the crop is at permanent wilting) - sensor/soil calibration required.")
    return {"dr_mm": min(max(raw_dr, 0.0), taw), "dr_unclipped_mm": raw_dr, "flags": flags}

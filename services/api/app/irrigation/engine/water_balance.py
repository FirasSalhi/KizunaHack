"""Daily root-zone water balance (FAO-56 Eqs. 82-87), crop-aware: Kc(t) and Zr(t) follow the growth stage.

  TAW = 1000 (FC - WP) Zr ; RAW = p TAW ; Ks = (TAW - Dr)/((1-p) TAW) when Dr > RAW
  Dr_end = Dr_start - Pe - I_net + ETa + DP   (closed exactly, see conservation_error_mm)
  ETa = min(Ks Kc ETo, TAW - Dr_start + Pe + I_net) ; DP = max(0, Pe + I_net - ETa - Dr_start)

Declared simplifications (also written to the output attrs): runoff = 0, capillary rise = 0,
Pe = max(0, P - interception_mm) with interception_mm = 2 (approximation, calibrate locally),
when Zr grows the depletion in mm is carried over unchanged (clipped to the new TAW).
"""
from __future__ import annotations

from typing import Dict, Mapping, Optional

import numpy as np
import pandas as pd

from .crop_water_requirements import adjusted_p, crop_requirements
from .soil import taw_mm

ASSUMPTIONS = ["runoff = 0", "capillary rise = 0", "effective rain = max(0, P - interception_mm) (approximation)",
               "Dr carried over unchanged (mm) when root depth grows", "irrigation applied/recommended refills toward field capacity"]


def effective_rainfall(p_mm: float, interception_mm: float = 2.0) -> float:
    if p_mm is None or np.isnan(p_mm) or p_mm < 0:
        raise ValueError(f"Rainfall must be a non-negative number, got {p_mm}")
    return max(0.0, p_mm - interception_mm)


def stress_coefficient(dr: float, taw: float, p: float) -> float:
    raw = p * taw
    return 1.0 if dr <= raw else float(max(0.0, (taw - dr) / ((1 - p) * taw)))


def net_to_gross(net_mm: float, ea: float) -> float:
    if not (0 < ea <= 1): raise ValueError(f"Ea={ea} must be in (0,1]")
    if net_mm < 0: raise ValueError("net irrigation must be >= 0")
    return net_mm / ea


def gross_to_net(gross_mm: float, ea: float) -> float:
    if not (0 < ea <= 1): raise ValueError(f"Ea={ea} must be in (0,1]")
    return gross_mm * ea


def mm_to_volume(mm: float, area_ha: float) -> Dict[str, float]:
    """1 mm over 1 ha = 10 m3. Returns m3 and litres."""
    if area_ha <= 0: raise ValueError("area must be > 0 ha")
    m3 = mm * area_ha * 10.0
    return {"m3": m3, "litres": m3 * 1000.0}


def volume_to_mm(m3: float, area_ha: float) -> float:
    if area_ha <= 0: raise ValueError("area must be > 0 ha")
    return m3 / (area_ha * 10.0)


def day_step(dr_start: float, taw: float, p: float, kc: float, eto: float, rain: float, i_net: float = 0.0,
             interception_mm: float = 2.0) -> Dict[str, float]:
    pe = effective_rainfall(rain, interception_mm)
    ks = stress_coefficient(dr_start, taw, p)
    etc_adj = ks * kc * eto
    eta = min(etc_adj, max(0.0, taw - dr_start) + pe + i_net)
    dp = max(0.0, pe + i_net - eta - dr_start)
    dr_end = min(max(dr_start - pe - i_net + eta + dp, 0.0), taw)
    closure = dr_start - pe - i_net + eta + dp - dr_end
    return {"ks": ks, "eta": eta, "pe": pe, "dp": dp, "dr_end": dr_end, "closure_mm": closure}


def simulate(weather: pd.DataFrame, crop: Dict, soil, *, planting_date=None, stage_override: Optional[str] = None,
             initial_depletion_mm: float, applied_net_mm: Optional[Mapping[str, float]] = None,
             kc_variant: Optional[str] = None, interception_mm: float = 2.0, on_gap: str = "error",
             zr_choice: str = "scheduling") -> pd.DataFrame:
    """Simulate day by day. weather needs date, eto_mm, rain_mm. on_gap: 'error' | 'hold' (Dr unchanged, row flagged)."""
    if on_gap not in ("error", "hold"): raise ValueError("on_gap must be 'error' or 'hold'")
    if soil is None: raise ValueError("soil parameters (FC, WP) are required for a water balance")
    for c in ("date", "eto_mm", "rain_mm"):
        if c not in weather.columns: raise ValueError(f"weather lacks '{c}'")
    applied_net_mm = dict(applied_net_mm or {})
    rows, dr = [], float(initial_depletion_mm)
    if dr < 0: raise ValueError("initial depletion must be >= 0")
    for _, r in weather.sort_values("date").iterrows():
        d = str(pd.to_datetime(r["date"]).date())
        eto, rain = r["eto_mm"], r["rain_mm"]
        if pd.isna(eto) or pd.isna(rain):
            if on_gap == "error":
                raise ValueError(f"weather gap on {d} (eto/rain missing); use on_gap='hold' to carry state with a flag")
            rows.append({"date": d, "gap": True, "dr_end_mm": dr}); continue
        req = crop_requirements(crop, d, eto, planting_date, stage_override, kc_variant, zr_choice=zr_choice)
        if req["status"] != "OK":
            raise ValueError(f"{d}: cannot determine crop requirements ({req['status']}: {req.get('missing')})")
        taw = taw_mm(soil, req["zr_m"]); dr = min(dr, taw)
        p = req["p_adjusted"]; raw = p * taw
        st = day_step(dr, taw, p, req["kc"], eto, rain, applied_net_mm.get(d, 0.0), interception_mm)
        rows.append({"date": d, "gap": False, "stage": req["stage"], "kc": req["kc"], "zr_m": req["zr_m"], "taw_mm": taw, "raw_mm": raw, "p": p,
                     "eto_mm": eto, "etc_mm": req["kc"] * eto, "rain_mm": rain, "dr_start_mm": dr, "irrigation_net_mm": applied_net_mm.get(d, 0.0),
                     "conservation_error_mm": st["closure_mm"], **{k: st[k] for k in ("ks", "eta", "pe", "dp")}, "dr_end_mm": st["dr_end"]})
        dr = st["dr_end"]
    out = pd.DataFrame(rows); out.attrs["assumptions"] = ASSUMPTIONS
    return out

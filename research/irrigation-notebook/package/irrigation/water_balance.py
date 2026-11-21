"""Daily root-zone water balance (FAO-56 Eqs. 82-87) with transparent bookkeeping.

State variable: root-zone depletion Dr (mm below field capacity), 0 <= Dr <= TAW.

  Dr_end = Dr_start - Pe - I_applied - I_recommended + ETa + DP          (closed exactly)

  ETa = min(Ks*Kc*ETo, TAW - Dr_start + Pe + I_applied)   (cannot extract more than is there)
  DP  = max(0, Pe + I_applied - ETa - Dr_start)           (water beyond field capacity drains)

Assumptions (all reported in the output ``attrs['assumptions']``):
  * runoff RO = 0, capillary rise CR = 0 (no shallow water table), flat uniform field
  * effective rainfall Pe = max(0, P - interception_mm) - an empirical approximation
    (default 2 mm/event-day); FAO-56 gives no universal daily rule, calibrate locally
  * Ks from FAO-56 Eq. 84 evaluated on start-of-day depletion
  * p adjusted for evaporative demand p = p_table + 0.04 (5 - ETc), limited to 0.1-0.8 (Table 22 note)
  * irrigation is recommended at the end of day when Dr_before_irrigation >= trigger * RAW
    and refills the root zone to field capacity (net = Dr).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional

import numpy as np
import pandas as pd

from .crop_database import get_crop, kc_for_stage, validate_stage
from .soil import IrrigationSystem, SoilParams, taw_mm


def effective_rainfall(p_mm: float, interception_mm: float = 2.0) -> float:
    if p_mm < 0 or np.isnan(p_mm):
        raise ValueError(f"Rainfall must be a non-negative number, got {p_mm}.")
    if interception_mm < 0:
        raise ValueError("interception_mm must be >= 0")
    return max(0.0, p_mm - interception_mm)


def adjusted_p(p_table: float, etc_mm: float) -> float:
    """FAO-56 Table 22 footnote: p = p_table + 0.04 (5 - ETc), 0.1 <= p <= 0.8."""
    return float(min(0.8, max(0.1, p_table + 0.04 * (5.0 - etc_mm))))


def stress_coefficient(dr_mm: float, taw: float, p: float) -> float:
    """FAO-56 Eq. 84: Ks = 1 if Dr <= RAW else (TAW - Dr) / ((1 - p) TAW), floored at 0."""
    raw = p * taw
    if dr_mm <= raw:
        return 1.0
    return float(max(0.0, (taw - dr_mm) / ((1.0 - p) * taw)))


def net_to_gross(net_mm: float, ea: float) -> float:
    if not (0.0 < ea <= 1.0):
        raise ValueError(f"Ea={ea} must be in (0, 1]")
    if net_mm < 0:
        raise ValueError("net irrigation must be >= 0")
    return net_mm / ea


def gross_to_net(gross_mm: float, ea: float) -> float:
    if not (0.0 < ea <= 1.0):
        raise ValueError(f"Ea={ea} must be in (0, 1]")
    if gross_mm < 0:
        raise ValueError("gross irrigation must be >= 0")
    return gross_mm * ea


@dataclass(frozen=True)
class IrrigationPolicy:
    trigger_fraction: float = 1.0      # irrigate when Dr >= trigger_fraction * RAW
    max_net_mm: Optional[float] = None  # optional cap per event (system capacity)
    enabled: bool = True

    def __post_init__(self):
        if not (0.0 < self.trigger_fraction <= 1.0):
            raise ValueError("trigger_fraction must be in (0, 1]")
        if self.max_net_mm is not None and self.max_net_mm <= 0:
            raise ValueError("max_net_mm must be > 0")


def _prepare_weather(w: pd.DataFrame, on_gap: str, eto_col: str, rain_col: str):
    if on_gap not in ("raise", "truncate"):
        raise ValueError("on_gap must be 'raise' or 'truncate'")
    for c in ("date", eto_col, rain_col):
        if c not in w.columns:
            raise ValueError(f"Weather input lacks required column '{c}'.")
    w = w.sort_values("date").reset_index(drop=True).copy()
    w["date"] = pd.to_datetime(w["date"])
    excluded = []
    bad = w[eto_col].isna() | w[rain_col].isna() | (w[rain_col] < 0) | (w[eto_col] < 0)
    gaps = w["date"].diff().dt.days.fillna(1) != 1
    stop = None
    for i in range(len(w)):
        if bad.iloc[i] or gaps.iloc[i]:
            stop = i
            break
    if stop is not None:
        reason = ("missing/invalid ETo or rainfall" if bad.iloc[stop] else "non-consecutive date") + \
                 f" at {w['date'].iloc[stop].date()}"
        if on_gap == "raise":
            raise ValueError(f"Weather series invalid: {reason}. No default value is substituted.")
        excluded = [{"date": str(d.date()), "reason": reason} for d in w["date"].iloc[stop:]]
        w = w.iloc[:stop].reset_index(drop=True)
    if len(w) == 0:
        raise ValueError("No valid consecutive weather days available.")
    return w, excluded


def simulate_water_balance(weather: pd.DataFrame, crop: str, stage: str, soil: SoilParams,
                           system: IrrigationSystem, *, initial_depletion_mm: float,
                           zr_m: Optional[float] = None, kc_override: Optional[float] = None,
                           applied_gross_mm: Optional[Mapping] = None, policy: IrrigationPolicy = IrrigationPolicy(),
                           adjust_p: bool = True, interception_mm: float = 2.0,
                           eto_col: str = "eto_mm", rain_col: str = "rain_mm", on_gap: str = "raise") -> pd.DataFrame:
    """Simulate daily root-zone depletion, stress and irrigation recommendations.

    ``initial_depletion_mm`` is mandatory (measured, or an explicitly declared assumption).
    ``applied_gross_mm`` maps date -> gross water applied by the farmer (converted to net with Ea).
    """
    c = get_crop(crop)
    validate_stage(stage)
    zr = float(zr_m) if zr_m is not None else c.root_depth_m
    taw = taw_mm(soil, zr)
    if not (0.0 <= initial_depletion_mm <= taw):
        raise ValueError(f"initial_depletion_mm={initial_depletion_mm} must be within [0, TAW={taw:.1f}] mm.")
    kc = kc_for_stage(crop, stage, kc_override)
    w, excluded = _prepare_weather(weather, on_gap, eto_col, rain_col)
    applied = {pd.Timestamp(k): float(v) for k, v in (applied_gross_mm or {}).items()}
    unknown = [d for d in applied if d not in set(w["date"])]
    if unknown:
        raise ValueError(f"applied_gross_mm contains dates outside the simulated weather series: {[str(d.date()) for d in unknown]}")

    rows, dr = [], float(initial_depletion_mm)
    for _, r in w.iterrows():
        eto, rain = float(r[eto_col]), float(r[rain_col])
        etc = eto * kc
        p = adjusted_p(c.p_table, etc) if adjust_p else c.p_table
        raw = p * taw
        ks = stress_coefficient(dr, taw, p)
        pe = effective_rainfall(rain, interception_mm)
        i_app_gross = applied.get(r["date"], 0.0)
        i_app = gross_to_net(i_app_gross, system.ea)
        eta = min(ks * etc, taw - dr + pe + i_app)
        dp = max(0.0, pe + i_app - eta - dr)
        dr_before = dr - pe - i_app + eta + dp
        i_rec = 0.0
        if policy.enabled and dr_before >= policy.trigger_fraction * raw:
            i_rec = dr_before if policy.max_net_mm is None else min(dr_before, policy.max_net_mm)
        dr_end = dr_before - i_rec
        rows.append({
            "date": r["date"], "eto_mm": eto, "kc": kc, "etc_mm": etc, "p_used": p, "TAW_mm": taw, "RAW_mm": raw,
            "ks": ks, "eta_mm": eta, "rain_mm": rain, "rain_effective_mm": pe,
            "irrigation_applied_gross_mm": i_app_gross, "irrigation_applied_net_mm": i_app,
            "deep_percolation_mm": dp, "dr_start_mm": dr, "dr_before_irrigation_mm": dr_before,
            "irrigation_net_mm": i_rec, "irrigation_gross_mm": net_to_gross(i_rec, system.ea),
            "dr_end_mm": dr_end,
            "balance_residual_mm": dr_end - (dr - pe - i_app - i_rec + eta + dp),
        })
        dr = dr_end
    out = pd.DataFrame(rows)
    out.attrs["excluded_weather"] = excluded
    out.attrs["assumptions"] = [
        "runoff=0, capillary rise=0, uniform flat field",
        f"effective rainfall = max(0, P - {interception_mm} mm) (empirical approximation)",
        "Ks from FAO-56 Eq. 84 on start-of-day depletion",
        "p adjusted for ETc (Table 22 note)" if adjust_p else "p not adjusted for ETc",
        f"irrigation at end of day when Dr >= {policy.trigger_fraction}*RAW, refill to field capacity" if policy.enabled else "irrigation recommendations disabled",
        f"initial depletion {initial_depletion_mm:.1f} mm (caller-supplied)",
        f"Zr={zr} m, Kc={kc} ({stage}), soil source={soil.source}, Ea={system.ea} ({system.source})",
    ]
    return out


def conservation_report(sim: pd.DataFrame, initial_depletion_mm: float) -> dict:
    """Cumulative closure: sum(inputs) - sum(ETa) - sum(DP) must equal the drop in depletion."""
    inputs = (sim["rain_effective_mm"] + sim["irrigation_applied_net_mm"] + sim["irrigation_net_mm"]).sum()
    lhs = inputs - sim["eta_mm"].sum() - sim["deep_percolation_mm"].sum()
    rhs = initial_depletion_mm - sim["dr_end_mm"].iloc[-1]
    return {"inputs_mm": float(inputs), "eta_mm": float(sim["eta_mm"].sum()),
            "deep_percolation_mm": float(sim["deep_percolation_mm"].sum()),
            "storage_change_mm": float(rhs), "closure_error_mm": float(lhs - rhs)}

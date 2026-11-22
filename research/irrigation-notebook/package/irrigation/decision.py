"""Single-day operational irrigation recommendation.

Combines: measured soil moisture (multi-depth), forecast soil moisture, crop water demand
(FAO-56 Kc x ETo), growth stage, rainfall (observed / forecast) and previous irrigation.

Readiness levels (never hidden):
  MISSING_INPUTS                       a required input is absent -> NO quantitative volume is produced
  ILLUSTRATIVE                         all numbers computable, but soil parameters are presets/assumed,
                                       the sensor is uncalibrated or the field/crop is undocumented
  CANDIDATE_REQUIRES_FIELD_VALIDATION  measured soil limits + calibrated sensor + documented field;
                                       still NOT validated on real farms
"""
from __future__ import annotations

from typing import Mapping, Optional, Sequence

import numpy as np

from .crop_database import CROPS, get_crop, kc_for_stage, validate_stage
from .soil import (IrrigationSystem, SoilParams, depletion_from_theta, root_zone_theta, taw_mm)
from .water_balance import adjusted_p, effective_rainfall, net_to_gross, stress_coefficient

NOT_VALIDATED = "Prototype: not validated on real Tunisian farms."


def recommend_irrigation(*, crop: str, stage: str,
                         soil: Optional[SoilParams] = None,
                         system: Optional[IrrigationSystem] = None,
                         theta_now_by_depth_cm: Optional[Mapping[float, float]] = None,
                         theta_units: str = "percent",
                         theta_forecast_by_depth_cm: Optional[Mapping[float, float]] = None,
                         forecast_horizon_h: Optional[float] = None,
                         depletion_mm_override: Optional[float] = None,
                         eto_mm_today: Optional[float] = None,
                         eto_mm_next_days: Optional[Sequence[float]] = None,
                         rain_forecast_mm_next_days: Optional[Sequence[float]] = None,
                         rain_last_24h_mm: Optional[float] = None,
                         last_irrigation: Optional[Mapping] = None,
                         zr_m: Optional[float] = None, kc_override: Optional[float] = None,
                         horizon_days: int = 1, interception_mm: float = 2.0, adjust_p: bool = True,
                         max_net_mm: Optional[float] = None,
                         sensor_calibrated: bool = False, field_documented: bool = False,
                         eto_method: str = "unspecified", weather_source: str = "unspecified",
                         weather_age_days: Optional[float] = None) -> dict:
    # --- hard validation (raises) -------------------------------------------------
    c = get_crop(crop)
    validate_stage(stage)
    if horizon_days < 1:
        raise ValueError("horizon_days must be >= 1")
    zr = float(zr_m) if zr_m is not None else c.root_depth_m
    if zr <= 0:
        raise ValueError(f"Root depth Zr={zr} must be > 0 m.")
    kc = kc_for_stage(crop, stage, kc_override)

    missing, warnings, expl = [], [], []
    res = {"crop": c.key, "crop_fr": c.name_fr, "stage": stage, "kc": kc,
           "kc_provenance": "USER_OVERRIDE" if kc_override is not None else c.stages[stage].provenance,
           "kc_low": c.stages[stage].kc_low, "kc_high": c.stages[stage].kc_high,
           "zr_m": zr, "zr_source": "USER" if zr_m is not None else "FAO56_TABLE22_lower_bound",
           "eto_mm": eto_mm_today, "eto_method": eto_method, "weather_source": weather_source,
           "etc_mm": None, "taw_mm": None, "raw_mm": None, "p_used": None, "theta_rz_now": None,
           "theta_rz_forecast": None, "dr_now_mm": None, "dr_forecast_sensor_mm": None,
           "dr_projected_mm": None, "ks_now": None, "irrigate": None, "timing": None,
           "net_mm": None, "gross_mm": None, "days_to_raw": None, "sensor_coverage_fraction": None}

    # --- crop demand -------------------------------------------------------------
    if eto_mm_today is None or not np.isfinite(eto_mm_today) or eto_mm_today < 0:
        missing.append("ETo today (mm/day)")
    else:
        res["etc_mm"] = eto_mm_today * kc
        res["p_used"] = adjusted_p(c.p_table, res["etc_mm"]) if adjust_p else c.p_table

    # --- required soil / system inputs ---------------------------------------------
    if soil is None:
        missing.append("soil field capacity & wilting point (FC, WP)")
    if system is None:
        missing.append("irrigation application efficiency (Ea)")
    if theta_now_by_depth_cm is None and depletion_mm_override is None:
        missing.append("current soil moisture (sensor profile) or water-balance depletion")

    if stage in ("initial", "development") and zr_m is None:
        warnings.append(f"Stage '{stage}': tabulated Zr ({zr} m) is the MAXIMUM root depth; the active root zone is "
                        "shallower now, so TAW/RAW are overestimated. Supply a measured zr_m.")
    if res["kc_provenance"] == "DERIVED_LINEAR":
        warnings.append(f"Kc for '{stage}' is a stage mean derived by linear interpolation between FAO-56 end-points "
                        f"(published range {res['kc_low']:.2f}-{res['kc_high']:.2f}).")
    if c.key == "durum_wheat" and stage == "initial" and kc_override is None:
        warnings.append("Durum wheat initial Kc (0.70) depends strongly on wetting frequency (FAO-56 Fig. 29-30); likely high for dry bare soil.")
    if eto_method.startswith("Hargreaves"):
        warnings.append("ETo from Hargreaves-Samani (fallback): less accurate than Penman-Monteith.")
    if "reanalysis" in weather_source.lower() or "nasa" in weather_source.lower():
        warnings.append("Weather is NASA POWER reanalysis (grid cell), not an on-site measurement.")
    if "fixture" in weather_source.lower() or "synthetic" in weather_source.lower():
        warnings.append("Weather is a TEST FIXTURE (synthetic) - not an observation.")

    if weather_age_days is not None and weather_age_days > 1:
        warnings.append(f"Weather inputs are {weather_age_days:g} days older than the soil-moisture reading (reanalysis latency).")
    res["missing_inputs"] = missing
    if missing:
        res.update(status="MISSING_INPUTS", readiness="MISSING_INPUTS", confidence="NONE")
        expl.append("Quantitative irrigation advice withheld - missing: " + "; ".join(missing) + ".")
        if res["etc_mm"] is not None:
            expl.append(f"Crop demand can still be stated: ETc = ETo {eto_mm_today:.2f} x Kc {kc:.2f} = {res['etc_mm']:.2f} mm/day.")
        res["warnings"], res["explanation"] = warnings + [NOT_VALIDATED], expl
        return res

    # --- root-zone status ----------------------------------------------------------
    taw = taw_mm(soil, zr)
    p = res["p_used"]
    raw = p * taw
    res.update(taw_mm=taw, raw_mm=raw)

    layers_below_wp = []
    if depletion_mm_override is not None:
        if not (0 <= depletion_mm_override <= taw):
            raise ValueError(f"depletion_mm_override must be within [0, TAW={taw:.1f}] mm")
        dr_now = float(depletion_mm_override)
        res["depletion_source"] = "water-balance simulation (no sensor)"
        profile_now = None
    else:
        prof = root_zone_theta(theta_now_by_depth_cm, zr, theta_units)
        dep = depletion_from_theta(prof["theta_rz"], soil, zr)
        dr_now, profile_now = dep["dr_mm"], prof
        res.update(theta_rz_now=prof["theta_rz"], sensor_coverage_fraction=prof["coverage_fraction"],
                   depletion_source="multi-depth sensor profile")
        warnings += prof["warnings"] + dep["flags"]
        for lay in prof["layers"]:
            if lay["theta"] < soil.wp:
                layers_below_wp.append(lay["sensor_cm"])
                warnings.append(f"Sensor at {lay['sensor_cm']:.0f} cm reads {100*lay['theta']:.1f} % < declared WP "
                                f"{100*soil.wp:.1f} % - this layer is physically inconsistent with the declared soil.")
        if prof["theta_rz"] < soil.wp:
            res.update(status="INCONSISTENT_SENSOR_SOIL", readiness="INCONSISTENT_INPUTS", confidence="NONE",
                       dr_now_mm=None, ks_now=None, dr_fraction_of_taw=None)
            expl.append(f"Root-zone mean VWC {100*prof['theta_rz']:.1f} % is below the declared wilting point "
                        f"{100*soil.wp:.1f} %. That is a sensor-calibration or soil-parameter problem, not evidence "
                        "of an agronomic need: no irrigation volume is issued. Calibrate the sensors against the soil "
                        "(FC/WP measured on site) and re-run.")
            res["warnings"], res["explanation"] = warnings + [NOT_VALIDATED], expl
            return res
    res["dr_now_mm"] = dr_now
    res["ks_now"] = stress_coefficient(dr_now, taw, p)
    res["dr_fraction_of_taw"] = dr_now / taw

    # --- forecast soil moisture (sensor model) -------------------------------------
    dr_fc = None
    if theta_forecast_by_depth_cm is not None and profile_now is not None:
        merged = {float(d): v for d, v in theta_now_by_depth_cm.items()}
        merged.update({float(d): v for d, v in theta_forecast_by_depth_cm.items()})
        prof_f = root_zone_theta(merged, zr, theta_units)
        dr_fc = depletion_from_theta(prof_f["theta_rz"], soil, zr)["dr_mm"]
        res.update(theta_rz_forecast=prof_f["theta_rz"], dr_forecast_sensor_mm=dr_fc)
        horizon_txt = f"{forecast_horizon_h:g} h" if forecast_horizon_h else "unspecified horizon"
        warnings.append(f"Soil-moisture forecast ({horizon_txt}) covers depths {sorted(theta_forecast_by_depth_cm)} cm only; "
                        "other depths are held at their current value.")
    elif theta_forecast_by_depth_cm is not None:
        warnings.append("Forecast soil moisture ignored: depletion comes from the water balance, not from sensors.")

    # --- weather projection ----------------------------------------------------------
    etos = list(eto_mm_next_days) if eto_mm_next_days is not None else None
    if etos is None or len(etos) < horizon_days:
        etos = [eto_mm_today] * horizon_days
        warnings.append("No ETo forecast for the horizon: today's ETo is assumed to persist (declared assumption).")
    rains = list(rain_forecast_mm_next_days) if rain_forecast_mm_next_days is not None else None
    if rains is None or len(rains) < horizon_days:
        rains = [0.0] * horizon_days
        warnings.append("No rainfall forecast supplied: 0 mm assumed over the horizon (may overstate irrigation need).")
    etc_proj = sum(e * kc for e in etos[:horizon_days])
    pe_proj = sum(effective_rainfall(r, interception_mm) for r in rains[:horizon_days])
    dr_proj = float(min(max(dr_now + etc_proj - pe_proj, 0.0), taw))
    res["dr_projected_mm"] = dr_proj

    if last_irrigation:
        h = last_irrigation.get("hours_ago")
        if h is not None and h < 24:
            warnings.append(f"Irrigation of {last_irrigation.get('gross_mm', '?')} mm (gross) applied {h:g} h ago: "
                            "sensors may not have equilibrated yet.")
    if rain_last_24h_mm and rain_last_24h_mm > 0:
        warnings.append(f"{rain_last_24h_mm:g} mm rain in the last 24 h is already reflected in sensor readings (not added again).")

    # --- decision ------------------------------------------------------------------------
    trigger = raw
    basis = max([x for x in (dr_proj, dr_fc) if x is not None])
    if dr_now >= trigger:
        timing, irrigate, need = "NOW", True, dr_now
        expl.append(f"Depletion {dr_now:.1f} mm >= RAW {raw:.1f} mm: crop is at/after the stress threshold (Ks={res['ks_now']:.2f}).")
    elif basis >= trigger:
        timing, irrigate, need = "WITHIN_HORIZON", True, basis
        src = "forecast soil moisture" if (dr_fc is not None and dr_fc >= trigger and dr_fc >= dr_proj) else "projected crop demand"
        expl.append(f"Depletion {dr_now:.1f} mm is below RAW {raw:.1f} mm now, but {src} reaches {basis:.1f} mm "
                    f"within {horizon_days} day(s): plan irrigation inside that window.")
    else:
        timing, irrigate, need = "NOT_NEEDED", False, 0.0
        etc_rate = max(res["etc_mm"], 1e-6)
        res["days_to_raw"] = (raw - dr_now) / etc_rate
        expl.append(f"Depletion {dr_now:.1f} mm < RAW {raw:.1f} mm and projected {dr_proj:.1f} mm over {horizon_days} day(s) "
                    f"stays below it; at ETc {res['etc_mm']:.2f} mm/day RAW is reached in ~{res['days_to_raw']:.1f} day(s) without rain.")
    net = 0.0 if not irrigate else (need if max_net_mm is None else min(need, max_net_mm))
    res.update(irrigate=irrigate, timing=timing, net_mm=net, gross_mm=net_to_gross(net, system.ea))
    expl.append(f"Crop: {c.name_en} / {stage}: Kc {kc:.2f} x ETo {eto_mm_today:.2f} = ETc {res['etc_mm']:.2f} mm/day; "
                f"TAW {taw:.0f} mm (Zr {zr} m), p {p:.2f}.")
    if irrigate:
        expl.append(f"Net {net:.1f} mm refills the root zone to field capacity; gross {res['gross_mm']:.1f} mm at Ea {system.ea:.2f}.")

    # --- readiness / confidence ---------------------------------------------------------
    reasons = []
    if soil.source != "measured":
        reasons.append(f"soil FC/WP source is '{soil.source}' (not measured)")
    if system.source != "measured":
        reasons.append(f"Ea source is '{system.source}'")
    if depletion_mm_override is None and not sensor_calibrated:
        reasons.append("soil-moisture sensors not calibrated for this soil")
    if not field_documented:
        reasons.append("crop/field not documented for the sensor location")
    if layers_below_wp:
        reasons.append(f"sensor layer(s) at {layers_below_wp} cm read below the declared WP (sensor/soil conflict)")
    if reasons:
        readiness, conf = "ILLUSTRATIVE", ("VERY_LOW" if layers_below_wp else "LOW")
        warnings.append("ILLUSTRATIVE ONLY - " + "; ".join(reasons) + ".")
    else:
        readiness, conf = "CANDIDATE_REQUIRES_FIELD_VALIDATION", "MEDIUM"
    if layers_below_wp:
        expl.append(f"CAUTION: sensor layer(s) at {layers_below_wp} cm read below the declared wilting point; "
                    "the volume above depends on a soil description the sensors contradict. Verify FC/WP on site before irrigating.")
    res["sensor_soil_conflict_layers_cm"] = layers_below_wp
    res.update(status="OK", readiness=readiness, confidence=conf,
               warnings=warnings + [NOT_VALIDATED], explanation=expl)
    return res

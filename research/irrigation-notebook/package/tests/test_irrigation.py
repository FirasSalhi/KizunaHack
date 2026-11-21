"""Unit tests for the crop-aware irrigation engine. Run: python -m unittest discover -s tests -v"""
import math
import unittest

import numpy as np
import pandas as pd

from irrigation import crop_database as cdb
from irrigation import eto as E
from irrigation import water_balance as wb
from irrigation.decision import recommend_irrigation
from irrigation.soil import (IrrigationSystem, SoilParams, depletion_from_theta, get_illustrative_soil,
                             root_zone_theta, taw_mm, typical_system, vwc_to_fraction)

SOIL = SoilParams(0.30, 0.12, "loam", "measured")
DRIP = IrrigationSystem("drip", 0.90, "measured")


def weather(n=20, eto=4.0, rain=None, start="2026-06-01"):
    d = pd.date_range(start, periods=n, freq="D")
    return pd.DataFrame({"date": d, "eto_mm": eto, "rain_mm": rain if rain is not None else 0.0})


class TestCropSelection(unittest.TestCase):
    def test_supported_and_aliases(self):
        self.assertEqual(cdb.get_crop("Tomato").key, "tomato")
        self.assertEqual(cdb.get_crop("OLIVIER").key, "olive")
        self.assertEqual(cdb.get_crop("Blé dur").key, "durum_wheat")
        self.assertEqual(cdb.get_crop("Wheat").key, "durum_wheat")

    def test_unsupported_crop_rejected(self):
        for bad in ("Banana", "", None, 5):
            with self.assertRaises(ValueError):
                cdb.get_crop(bad)
        with self.assertRaises(ValueError):
            recommend_irrigation(crop="Banana", stage="mid_season")


class TestStagesAndKc(unittest.TestCase):
    def test_invalid_stage(self):
        with self.assertRaises(ValueError):
            cdb.kc_for_stage("tomato", "flowering")

    def test_fao56_table_values(self):
        self.assertEqual(cdb.kc_for_stage("tomato", "initial"), 0.60)
        self.assertEqual(cdb.kc_for_stage("tomato", "mid_season"), 1.15)
        self.assertEqual(cdb.kc_for_stage("olive", "initial"), 0.65)
        self.assertEqual(cdb.kc_for_stage("olive", "mid_season"), 0.70)
        self.assertEqual(cdb.kc_for_stage("durum_wheat", "mid_season"), 1.15)

    def test_derived_stage_means(self):
        self.assertAlmostEqual(cdb.kc_for_stage("tomato", "development"), (0.60 + 1.15) / 2)
        self.assertAlmostEqual(cdb.kc_for_stage("tomato", "late_season"), (1.15 + 0.80) / 2)
        self.assertAlmostEqual(cdb.kc_for_stage("durum_wheat", "late_season"), (1.15 + 0.325) / 2)
        self.assertEqual(cdb.CROPS["tomato"].stages["development"].provenance, cdb.DERIVED_LINEAR)
        self.assertEqual(cdb.CROPS["tomato"].stages["mid_season"].provenance, cdb.FAO56_TABLE)

    def test_kc_curve_end_points_and_monotonic_dev(self):
        c = cdb.CROPS["tomato"]
        L = c.stage_lengths_days
        self.assertAlmostEqual(cdb.kc_on_day("tomato", 0), 0.60)
        self.assertAlmostEqual(cdb.kc_on_day("tomato", L["initial"] + L["development"]), 1.15)
        self.assertAlmostEqual(cdb.kc_on_day("tomato", sum(L.values())), 0.80)
        vals = [cdb.kc_on_day("tomato", d) for d in range(L["initial"], L["initial"] + L["development"] + 1)]
        self.assertTrue(all(b >= a for a, b in zip(vals, vals[1:])))
        with self.assertRaises(ValueError):
            cdb.kc_on_day("tomato", sum(L.values()) + 1)

    def test_kc_override_bounds(self):
        self.assertEqual(cdb.kc_for_stage("tomato", "initial", 0.5), 0.5)
        for bad in (0, -1, 2.0):
            with self.assertRaises(ValueError):
                cdb.kc_for_stage("tomato", "initial", bad)

    def test_crop_parameters_in_fao_ranges(self):
        for c in cdb.CROPS.values():
            lo, hi = c.root_depth_range_m
            self.assertTrue(lo <= c.root_depth_m <= hi)
            self.assertTrue(0.0 < c.p_table < 1.0)
            for s in cdb.STAGES:
                k = c.stages[s]
                self.assertTrue(k.kc_low <= k.kc <= k.kc_high + 1e-9)

    def test_crops_differ_under_same_eto(self):
        etc = {k: 4.0 * cdb.kc_for_stage(k, "mid_season") for k in cdb.CROPS}
        self.assertGreater(etc["tomato"], etc["olive"])
        self.assertGreater(etc["durum_wheat"], etc["olive"])


class TestSoilAndUnits(unittest.TestCase):
    def test_fc_greater_than_wp(self):
        for fc, wp in ((0.10, 0.10), (0.10, 0.20)):
            with self.assertRaises(ValueError):
                SoilParams(fc, wp)

    def test_percent_passed_as_fraction_rejected(self):
        with self.assertRaises(ValueError):
            SoilParams(30.0, 12.0)           # percent instead of m3/m3
        with self.assertRaises(ValueError):
            vwc_to_fraction(16.2, "fraction")  # 16.2 is not a fraction
        self.assertAlmostEqual(vwc_to_fraction(16.2, "percent"), 0.162)

    def test_positive_root_depth(self):
        for zr in (0, -0.5):
            with self.assertRaises(ValueError):
                taw_mm(SOIL, zr)
            with self.assertRaises(ValueError):
                root_zone_theta({10: 20}, zr)

    def test_taw_units_mm(self):
        self.assertAlmostEqual(taw_mm(SOIL, 1.0), 180.0)       # 1000 * 0.18 * 1 m
        self.assertAlmostEqual(taw_mm(SOIL, 0.5), 90.0)

    def test_depletion_valid_fraction_and_efficiency(self):
        with self.assertRaises(ValueError):
            IrrigationSystem("drip", 0.0)
        with self.assertRaises(ValueError):
            IrrigationSystem("drip", 1.2)
        self.assertEqual(IrrigationSystem("x", 1.0).ea, 1.0)
        self.assertAlmostEqual(wb.adjusted_p(0.4, 5.0), 0.4)
        self.assertAlmostEqual(wb.adjusted_p(0.4, 3.0), 0.48)
        self.assertEqual(wb.adjusted_p(0.4, 20.0), 0.1)   # floor
        self.assertEqual(wb.adjusted_p(0.65, 0.0), 0.8)   # cap
        self.assertEqual(wb.stress_coefficient(10, 100, 0.5), 1.0)
        self.assertAlmostEqual(wb.stress_coefficient(75, 100, 0.5), 0.5)
        self.assertEqual(wb.stress_coefficient(100, 100, 0.5), 0.0)

    def test_depletion_from_theta_and_flags(self):
        d = depletion_from_theta(0.21, SOIL, 1.0)
        self.assertAlmostEqual(d["dr_mm"], 90.0)
        self.assertEqual(depletion_from_theta(0.35, SOIL, 1.0)["dr_mm"], 0.0)
        self.assertTrue(depletion_from_theta(0.35, SOIL, 1.0)["flags"])
        self.assertAlmostEqual(depletion_from_theta(0.05, SOIL, 1.0)["dr_mm"], 180.0)
        self.assertTrue(depletion_from_theta(0.05, SOIL, 1.0)["flags"])

    def test_root_zone_weighting(self):
        r = root_zone_theta({10: 20.0, 30: 10.0, 60: 10.0}, 0.6)
        self.assertAlmostEqual(sum(l["thickness_cm"] for l in r["layers"]), 60.0)
        self.assertAlmostEqual(r["theta_rz"], (0.20 * 20 + 0.10 * 25 + 0.10 * 15) / 60)
        self.assertEqual(r["coverage_fraction"], 1.0)

    def test_sensor_extrapolation_flagged(self):
        r = root_zone_theta({10: 20.0, 30: 10.0, 60: 10.0}, 1.5)
        self.assertLess(r["coverage_fraction"], 1.0)
        self.assertTrue(r["warnings"])
        self.assertTrue(root_zone_theta({10: 20.0}, 0.7)["warnings"])


class TestRainAndIrrigationAccounting(unittest.TestCase):
    def test_effective_rainfall(self):
        self.assertEqual(wb.effective_rainfall(1.5), 0.0)
        self.assertEqual(wb.effective_rainfall(10.0), 8.0)
        self.assertEqual(wb.effective_rainfall(10.0, 0.0), 10.0)
        with self.assertRaises(ValueError):
            wb.effective_rainfall(-1)
        with self.assertRaises(ValueError):
            wb.effective_rainfall(float("nan"))

    def test_net_gross_conversion(self):
        self.assertAlmostEqual(wb.net_to_gross(18.0, 0.9), 20.0)
        self.assertAlmostEqual(wb.gross_to_net(20.0, 0.9), 18.0)
        self.assertAlmostEqual(wb.gross_to_net(wb.net_to_gross(33.3, 0.75), 0.75), 33.3)
        with self.assertRaises(ValueError):
            wb.net_to_gross(10, 0)

    def test_rain_reduces_depletion_exactly(self):
        w = weather(1, eto=0.0, rain=12.0)
        s = wb.simulate_water_balance(w, "tomato", "mid_season", SOIL, DRIP, initial_depletion_mm=30.0,
                                      policy=wb.IrrigationPolicy(enabled=False))
        self.assertAlmostEqual(s["dr_end_mm"].iloc[0], 30.0 - 10.0)   # 12 mm - 2 mm interception
        self.assertAlmostEqual(s["deep_percolation_mm"].iloc[0], 0.0)

    def test_previous_irrigation_uses_efficiency(self):
        w = weather(2, eto=0.0, rain=0.0)
        s = wb.simulate_water_balance(w, "tomato", "mid_season", SOIL, DRIP, initial_depletion_mm=30.0,
                                      applied_gross_mm={"2026-06-01": 20.0}, policy=wb.IrrigationPolicy(enabled=False))
        self.assertAlmostEqual(s["irrigation_applied_net_mm"].iloc[0], 18.0)
        self.assertAlmostEqual(s["dr_end_mm"].iloc[0], 12.0)

    def test_over_application_drains(self):
        w = weather(1, eto=0.0, rain=0.0)
        s = wb.simulate_water_balance(w, "tomato", "mid_season", SOIL, DRIP, initial_depletion_mm=10.0,
                                      applied_gross_mm={"2026-06-01": 50.0}, policy=wb.IrrigationPolicy(enabled=False))
        self.assertAlmostEqual(s["dr_end_mm"].iloc[0], 0.0)
        self.assertAlmostEqual(s["deep_percolation_mm"].iloc[0], 45.0 - 10.0)

    def test_applied_dates_outside_series_rejected(self):
        with self.assertRaises(ValueError):
            wb.simulate_water_balance(weather(3), "tomato", "mid_season", SOIL, DRIP, initial_depletion_mm=0.0,
                                      applied_gross_mm={"2030-01-01": 5.0})


class TestWaterBalanceConservation(unittest.TestCase):
    def _run(self, crop, stage, eto, rain, applied=None, init=20.0, **kw):
        w = weather(len(eto), start="2026-05-01")
        w["eto_mm"], w["rain_mm"] = eto, rain
        s = wb.simulate_water_balance(w, crop, stage, SOIL, DRIP, initial_depletion_mm=init,
                                      applied_gross_mm=applied, **kw)
        return s

    def test_closure_and_bounds_all_crops(self):
        rng = np.random.default_rng(0)
        eto = rng.uniform(0.5, 8.0, 60)
        rain = np.where(rng.random(60) < 0.2, rng.uniform(0, 30, 60), 0.0)
        for crop in cdb.CROPS:
            for stage in cdb.STAGES:
                s = self._run(crop, stage, eto, rain, applied={"2026-05-10": 25.0})
                self.assertLess(s["balance_residual_mm"].abs().max(), 1e-9)
                rep = wb.conservation_report(s, 20.0)
                self.assertAlmostEqual(rep["closure_error_mm"], 0.0, places=8)
                self.assertTrue((s["dr_end_mm"] >= -1e-9).all())
                self.assertTrue((s["dr_end_mm"] <= s["TAW_mm"] + 1e-9).all())
                self.assertTrue((s["eta_mm"] <= s["etc_mm"] + 1e-9).all())

    def test_closure_without_irrigation_with_stress(self):
        s = self._run("tomato", "mid_season", [6.0] * 40, [0.0] * 40, init=0.0, policy=wb.IrrigationPolicy(enabled=False))
        self.assertLess(s["ks"].min(), 1.0)                       # stress develops
        self.assertAlmostEqual(wb.conservation_report(s, 0.0)["closure_error_mm"], 0.0, places=8)
        self.assertLessEqual(s["dr_end_mm"].max(), s["TAW_mm"].iloc[0] + 1e-9)

    def test_irrigation_triggers_at_raw_and_refills(self):
        s = self._run("tomato", "mid_season", [5.0] * 30, [0.0] * 30, init=0.0)
        ev = s[s["irrigation_net_mm"] > 0]
        self.assertGreater(len(ev), 0)
        for _, r in ev.iterrows():
            self.assertGreaterEqual(r["dr_before_irrigation_mm"], r["RAW_mm"] - 1e-9)
            self.assertAlmostEqual(r["dr_end_mm"], 0.0)
            self.assertAlmostEqual(r["irrigation_gross_mm"], r["irrigation_net_mm"] / 0.9)
        no = s[s["irrigation_net_mm"] == 0]
        self.assertTrue((no["dr_before_irrigation_mm"] < no["RAW_mm"]).all())

    def test_max_net_cap(self):
        s = self._run("tomato", "mid_season", [5.0] * 30, [0.0] * 30, init=0.0, policy=wb.IrrigationPolicy(max_net_mm=10.0))
        self.assertLessEqual(s["irrigation_net_mm"].max(), 10.0 + 1e-9)
        self.assertLess(wb.conservation_report(s, 0.0)["closure_error_mm"], 1e-8)

    def test_stage_changes_demand(self):
        a = self._run("tomato", "initial", [4.0] * 10, [0.0] * 10)["etc_mm"].sum()
        b = self._run("tomato", "mid_season", [4.0] * 10, [0.0] * 10)["etc_mm"].sum()
        self.assertAlmostEqual(b / a, 1.15 / 0.60)


class TestMissingInputHandling(unittest.TestCase):
    def test_initial_depletion_is_mandatory(self):
        with self.assertRaises(TypeError):
            wb.simulate_water_balance(weather(3), "tomato", "mid_season", SOIL, DRIP)

    def test_initial_depletion_bounds(self):
        with self.assertRaises(ValueError):
            wb.simulate_water_balance(weather(3), "tomato", "mid_season", SOIL, DRIP, initial_depletion_mm=1e6)

    def test_nan_weather_raises_by_default(self):
        w = weather(5)
        w.loc[2, "rain_mm"] = np.nan
        with self.assertRaises(ValueError):
            wb.simulate_water_balance(w, "tomato", "mid_season", SOIL, DRIP, initial_depletion_mm=0.0)

    def test_nan_weather_truncates_and_logs(self):
        w = weather(5)
        w.loc[3, "eto_mm"] = np.nan
        s = wb.simulate_water_balance(w, "tomato", "mid_season", SOIL, DRIP, initial_depletion_mm=0.0, on_gap="truncate")
        self.assertEqual(len(s), 3)
        self.assertEqual(len(s.attrs["excluded_weather"]), 2)

    def test_date_gap_detected(self):
        w = weather(5).drop(index=2).reset_index(drop=True)
        with self.assertRaises(ValueError):
            wb.simulate_water_balance(w, "tomato", "mid_season", SOIL, DRIP, initial_depletion_mm=0.0)
        s = wb.simulate_water_balance(w, "tomato", "mid_season", SOIL, DRIP, initial_depletion_mm=0.0, on_gap="truncate")
        self.assertEqual(len(s), 2)

    def test_missing_column(self):
        with self.assertRaises(ValueError):
            wb.simulate_water_balance(weather(3).drop(columns=["rain_mm"]), "tomato", "mid_season", SOIL, DRIP, initial_depletion_mm=0.0)

    def test_decision_without_soil_withholds_volume(self):
        r = recommend_irrigation(crop="tomato", stage="mid_season", system=DRIP, eto_mm_today=4.0,
                                 theta_now_by_depth_cm={10: 20})
        self.assertEqual(r["status"], "MISSING_INPUTS")
        self.assertIsNone(r["net_mm"])
        self.assertIsNone(r["gross_mm"])
        self.assertIsNone(r["irrigate"])
        self.assertTrue(any("FC" in m for m in r["missing_inputs"]))
        self.assertAlmostEqual(r["etc_mm"], 4.0 * 1.15)          # demand can still be stated

    def test_decision_missing_each_required_input(self):
        base = dict(crop="olive", stage="mid_season", soil=SOIL, system=DRIP,
                    theta_now_by_depth_cm={10: 20, 30: 20}, eto_mm_today=3.0)
        self.assertEqual(recommend_irrigation(**base)["status"], "OK")
        for k in ("soil", "system", "theta_now_by_depth_cm", "eto_mm_today"):
            kw = dict(base)
            kw[k] = None
            r = recommend_irrigation(**kw)
            self.assertEqual(r["status"], "MISSING_INPUTS", k)
            self.assertIsNone(r["net_mm"], k)


class TestEto(unittest.TestCase):
    def test_extraterrestrial_radiation_fao_examples(self):
        self.assertAlmostEqual(float(E.extraterrestrial_radiation(50.80, 187)), 41.09, delta=0.1)   # Example 18
        self.assertAlmostEqual(float(E.extraterrestrial_radiation(45.72, 196)), 40.55, delta=0.15)  # Example 20

    def test_penman_monteith_fao56_example18(self):
        # Uccle: Tmax 21.5, Tmin 12.3, u2 2.078, Rs 22.07, ea 1.409 kPa, z 100 m -> ETo 3.88 mm/day
        eto = E.eto_penman_monteith(12.3, 21.5, 16.9, None, 2.078, 22.07, 50.80, 187, 100, ea_kpa=1.409)
        self.assertAlmostEqual(float(eto), 3.88, delta=0.05)

    def test_hargreaves_fao56_example20(self):
        eto = E.eto_hargreaves(14.8, 26.6, 20.7, 45.72, 196)
        self.assertAlmostEqual(float(eto), 5.0, delta=0.15)

    def test_method_label_and_no_silent_default(self):
        w = pd.DataFrame({"date": pd.date_range("2026-07-01", periods=3), "tmin": [18, 18, np.nan], "tmax": [32, 33, 34],
                          "tmean": [25, 25.5, 26], "rh_mean": [50, np.nan, 50], "u2": [2, 2, 2], "rs": [25, 25, 25]})
        out = E.compute_eto(w, 35.9, 10, "auto")
        self.assertEqual(out["eto_method"].tolist(), ["FAO56_Penman_Monteith", "Hargreaves_Samani(fallback)", "unavailable"])
        self.assertTrue(np.isnan(out["eto_mm"].iloc[2]))
        pm_only = E.compute_eto(w, 35.9, 10, "pm")
        self.assertEqual(pm_only["eto_method"].tolist(), ["FAO56_Penman_Monteith", "unavailable", "unavailable"])

    def test_nasa_fill_value_becomes_nan(self):
        df = pd.DataFrame({"date": ["2026-11-19"], "nasa_tmin_C": [-999.0], "nasa_tmax_C": [-999.0], "nasa_tmean_C": [-999.0],
                           "nasa_rh2m_pct": [-999.0], "nasa_wind_ms": [-999.0], "nasa_solar_MJ": [-999.0], "nasa_precip_mm": [-999.0]})
        out = E.standardize_nasa_power(df)
        self.assertTrue(out[["tmin", "rain_mm", "rs"]].isna().all().all())

    def test_pm_vs_hargreaves_same_order_of_magnitude(self):
        eto_pm = E.eto_penman_monteith(15, 30, 22.5, 50, 2.0, 22.0, 35.9, 180, 10)
        eto_hs = E.eto_hargreaves(15, 30, 22.5, 35.9, 180)
        self.assertLess(abs(float(eto_pm) - float(eto_hs)), 1.5)


class TestDecisionEngine(unittest.TestCase):
    base = dict(crop="tomato", stage="mid_season", soil=SOIL, system=DRIP, eto_mm_today=5.0, zr_m=0.6,
                sensor_calibrated=True, field_documented=True)

    def test_dry_soil_irrigate_now_with_gross_conversion(self):
        r = recommend_irrigation(theta_now_by_depth_cm={10: 14, 30: 14}, **self.base)
        self.assertTrue(r["irrigate"])
        self.assertEqual(r["timing"], "NOW")
        self.assertAlmostEqual(r["gross_mm"], r["net_mm"] / 0.9)
        self.assertAlmostEqual(r["net_mm"], r["dr_now_mm"])
        self.assertEqual(r["readiness"], "CANDIDATE_REQUIRES_FIELD_VALIDATION")

    def test_wet_soil_no_irrigation(self):
        r = recommend_irrigation(theta_now_by_depth_cm={10: 29, 30: 29}, **self.base)
        self.assertFalse(r["irrigate"])
        self.assertEqual(r["net_mm"], 0.0)
        self.assertGreater(r["days_to_raw"], 0)

    def test_forecast_or_demand_triggers_window(self):
        kw = dict(self.base)
        near = recommend_irrigation(theta_now_by_depth_cm={10: 22.5, 30: 22.5}, horizon_days=1, **kw)
        # choose moisture just above the trigger, so one more day of ETc crosses RAW
        taw = r_taw = near["taw_mm"]
        raw = near["raw_mm"]
        theta = 0.30 - (raw - 0.5 * near["etc_mm"]) / (1000 * 0.6)
        r = recommend_irrigation(theta_now_by_depth_cm={10: 100 * theta, 30: 100 * theta}, horizon_days=1, **kw)
        self.assertEqual(r["timing"], "WITHIN_HORIZON")
        self.assertTrue(r["irrigate"])
        # rain forecast cancels it
        r2 = recommend_irrigation(theta_now_by_depth_cm={10: 100 * theta, 30: 100 * theta}, horizon_days=1,
                                  rain_forecast_mm_next_days=[20.0], **kw)
        self.assertEqual(r2["timing"], "NOT_NEEDED")

    def test_sensor_forecast_used(self):
        kw = dict(self.base)
        now = {10: 26.0, 30: 22.0}
        r0 = recommend_irrigation(theta_now_by_depth_cm=now, **kw)
        r1 = recommend_irrigation(theta_now_by_depth_cm=now, theta_forecast_by_depth_cm={10: 10.0}, forecast_horizon_h=6, **kw)
        self.assertGreater(r1["dr_forecast_sensor_mm"], r0["dr_now_mm"])
        self.assertIsNotNone(r1["theta_rz_forecast"])

    def test_illustrative_and_uncalibrated_are_labelled(self):
        r = recommend_irrigation(crop="olive", stage="mid_season", soil=get_illustrative_soil("loamy_sand"),
                                 system=typical_system("drip"), theta_now_by_depth_cm={10: 10, 30: 10, 60: 10}, eto_mm_today=3.0)
        self.assertEqual(r["readiness"], "ILLUSTRATIVE")
        self.assertEqual(r["confidence"], "LOW")
        self.assertTrue(any("ILLUSTRATIVE" in w for w in r["warnings"]))
        self.assertTrue(any("validated" in w for w in r["warnings"]))

    def test_sensor_below_wp_withholds_volume(self):
        r = recommend_irrigation(crop="tomato", stage="mid_season", soil=get_illustrative_soil("silt"),
                                 system=typical_system("drip"), theta_now_by_depth_cm={10: 9, 30: 9, 60: 9}, eto_mm_today=2.0)
        self.assertEqual(r["status"], "INCONSISTENT_SENSOR_SOIL")
        self.assertIsNone(r["net_mm"])
        self.assertIsNone(r["irrigate"])

    def test_early_stage_root_warning_and_override(self):
        r = recommend_irrigation(theta_now_by_depth_cm={10: 20, 30: 20},
                                 **{**self.base, "stage": "initial", "zr_m": None})
        self.assertTrue(any("MAXIMUM root depth" in w for w in r["warnings"]))
        r2 = recommend_irrigation(theta_now_by_depth_cm={10: 20, 30: 20}, **{**self.base, "stage": "initial"})
        self.assertFalse(any("MAXIMUM root depth" in w for w in r2["warnings"]))

    def test_same_weather_different_crops(self):
        out = {}
        for crop in cdb.CROPS:
            out[crop] = recommend_irrigation(crop=crop, stage="mid_season", soil=SOIL, system=DRIP, eto_mm_today=5.0,
                                             theta_now_by_depth_cm={10: 22, 30: 22})["etc_mm"]
        self.assertAlmostEqual(out["tomato"], 5.75)
        self.assertAlmostEqual(out["olive"], 3.5)
        self.assertAlmostEqual(out["durum_wheat"], 5.75)

    def test_depletion_override_from_water_balance(self):
        r = recommend_irrigation(crop="tomato", stage="mid_season", soil=SOIL, system=DRIP, eto_mm_today=5.0,
                                 depletion_mm_override=60.0, zr_m=0.6)
        self.assertEqual(r["depletion_source"], "water-balance simulation (no sensor)")
        self.assertAlmostEqual(r["dr_now_mm"], 60.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

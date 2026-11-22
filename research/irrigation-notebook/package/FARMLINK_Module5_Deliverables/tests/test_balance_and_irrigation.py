import unittest
import numpy as np, pandas as pd
import _path  # noqa
from engine.crop_retrieval import CropIndex
from engine.soil import SoilParams, taw_mm
from engine import water_balance as W
from engine.irrigation_engine import recommend_zone
from fixtures.synthetic import synthetic_weather

ix = CropIndex(); SOIL = SoilParams(fc=0.25, wp=0.12, texture="loam", source="user_declared")


class Balance(unittest.TestCase):
    def test_taw_and_ks(self):
        self.assertAlmostEqual(taw_mm(SOIL, 0.5), 65.0)
        self.assertEqual(W.stress_coefficient(10, 65, 0.4), 1.0)
        self.assertAlmostEqual(W.stress_coefficient(50, 65, 0.4), (65 - 50) / (0.6 * 65)); self.assertEqual(W.stress_coefficient(65, 65, 0.4), 0.0)

    def test_mass_closure_over_a_season(self):
        w = synthetic_weather("2026-04-10", 120, rain_days=(10, 40, 41)); w = __import__("engine.eto", fromlist=["x"]).compute_eto(w, 36.8, 30)
        s = W.simulate(w, ix.by_id["tomato"], SOIL, planting_date="2026-04-10", initial_depletion_mm=0.0, applied_net_mm={"2026-05-20": 30.0})
        self.assertLess(s["conservation_error_mm"].abs().max(), 1e-9)
        self.assertTrue((s["dr_end_mm"] >= 0).all() and (s["dr_end_mm"] <= s["taw_mm"] + 1e-9).all())
        self.assertTrue((s["eta"] <= s["etc_mm"] + 1e-9).all())

    def test_rain_effective_and_drainage(self):
        self.assertEqual(W.effective_rainfall(1.5), 0.0); self.assertEqual(W.effective_rainfall(10), 8.0)
        st = W.day_step(5, 60, 0.4, 1.0, 4, 50)       # heavy rain -> deep percolation
        self.assertGreater(st["dp"], 0); self.assertEqual(st["dr_end"], 0.0)

    def test_gap_policy(self):
        w = pd.DataFrame({"date": pd.date_range("2026-05-01", periods=3), "eto_mm": [4, np.nan, 4], "rain_mm": 0.0})
        with self.assertRaises(ValueError): W.simulate(w, ix.by_id["tomato"], SOIL, planting_date="2026-04-01", initial_depletion_mm=0)
        s = W.simulate(w, ix.by_id["tomato"], SOIL, planting_date="2026-04-01", initial_depletion_mm=0, on_gap="hold")
        self.assertEqual(s["gap"].tolist(), [False, True, False])

    def test_no_soil_no_balance(self):
        with self.assertRaises(ValueError): W.simulate(pd.DataFrame({"date": [], "eto_mm": [], "rain_mm": []}), ix.by_id["tomato"], None, initial_depletion_mm=0)


class Units(unittest.TestCase):
    def test_m3_is_mm_times_ha_times_10(self):
        v = W.mm_to_volume(25, 2.0); self.assertEqual(v["m3"], 500.0); self.assertEqual(v["litres"], 500000.0)
        self.assertAlmostEqual(W.volume_to_mm(500, 2.0), 25.0)
        self.assertAlmostEqual(W.net_to_gross(18, 0.9), 20.0); self.assertAlmostEqual(W.gross_to_net(20, 0.9), 18.0)
        with self.assertRaises(ValueError): W.net_to_gross(5, 0); 
        with self.assertRaises(ValueError): W.mm_to_volume(5, 0)


def zone(**kw):
    z = {"zone_id": "A", "crop": "tomato", "planting_date": "2026-04-10", "area_ha": 0.5, "soil": {"fc": 0.25, "wp": 0.12, "source": "user_declared"},
         "irrigation": {"method": "drip"}, "current_depletion_mm": 30}
    z.update(kw); return z


def wx():
    from engine.eto import compute_eto
    return compute_eto(synthetic_weather("2026-05-01", 25), 36.8, 30)


class IrrigationCalc(unittest.TestCase):
    def test_numbers_consistent(self):
        r = recommend_zone(zone(current_depletion_mm=60), wx(), "2026-05-20")
        self.assertEqual(r["status"], "OK"); self.assertEqual(r["timing"], "irrigate_now")
        v = r["volumes"]; self.assertAlmostEqual(v["net_mm"], r["dr_mm"]); self.assertAlmostEqual(v["gross_mm"], v["net_mm"] / 0.9)
        self.assertAlmostEqual(v["m3"], v["gross_mm"] * 0.5 * 10); self.assertAlmostEqual(v["litres"], v["m3"] * 1000)
        self.assertAlmostEqual(r["raw_mm"], r["p"] * r["taw_mm"]); self.assertAlmostEqual(r["taw_mm"], 130 * r["zr_m"])

    def test_no_irrigation_when_wet(self):
        r = recommend_zone(zone(current_depletion_mm=2), wx(), "2026-05-20")
        self.assertEqual(r["volumes"]["gross_mm"], 0.0)

    def test_forecast_rain_defers_irrigation(self):
        f = synthetic_weather("2026-05-21", 5, rain_days=(0,)); f.loc[0, "rain_mm"] = 40
        from engine.eto import compute_eto
        f = compute_eto(f, 36.8, 30)
        near = recommend_zone(zone(current_depletion_mm=22), wx(), "2026-05-20", None)
        with_rain = recommend_zone(zone(current_depletion_mm=22), wx(), "2026-05-20", f)
        self.assertIn("days_to_raw", with_rain)
        if near["timing"] != "no_irrigation_needed_within_horizon":
            self.assertGreaterEqual(with_rain["projection"][0]["dr_end_mm"], 0)
            self.assertLess(with_rain["projection"][0]["dr_end_mm"], near["dr_mm"] + 10)


class MissingInputs(unittest.TestCase):
    def test_no_soil(self):
        r = recommend_zone(zone(soil=None), wx(), "2026-05-20")
        self.assertEqual(r["status"], "MISSING_SOIL_PARAMS"); self.assertIsNone(r["volumes"]); self.assertNotIn("dr_mm", r)

    def test_no_planting_date_for_annual(self):
        r = recommend_zone(zone(planting_date=None), wx(), "2026-05-20"); self.assertEqual(r["status"], "MISSING_INPUTS"); self.assertIsNone(r["volumes"])

    def test_no_depletion_source(self):
        z = zone(); del z["current_depletion_mm"]
        r = recommend_zone(z, wx(), "2026-05-20"); self.assertEqual(r["status"], "MISSING_INPUTS"); self.assertIn("current depletion source", r["missing_inputs"])

    def test_no_irrigation_system_gives_net_only(self):
        z = zone(current_depletion_mm=60); del z["irrigation"]
        r = recommend_zone(z, wx(), "2026-05-20"); self.assertEqual(r["status"], "MISSING_IRRIGATION_SYSTEM"); self.assertGreater(r["net_mm"], 0); self.assertIsNone(r["volumes"])

    def test_unknown_crop_and_unavailable_crop(self):
        self.assertEqual(recommend_zone(zone(crop="dragonfruit"), wx(), "2026-05-20")["status"], "UNKNOWN_CROP")
        self.assertEqual(recommend_zone(zone(crop="fig"), wx(), "2026-05-20")["status"], "CROP_PARAMETERS_UNAVAILABLE")

    def test_no_weather(self):
        w = wx().assign(eto_mm=np.nan); r = recommend_zone(zone(), w, "2026-05-20"); self.assertEqual(r["status"], "MISSING_INPUTS")

    def test_uncalibrated_or_mv_sensor_never_used(self):
        s = {"theta_by_depth_cm": {"10": 20.0, "30": 20.0}, "units": "percent", "calibrated": False}
        r = recommend_zone(zone(sensor=s, current_depletion_mm=30), wx(), "2026-05-20")
        self.assertEqual(r["depletion_source"], "user_declared"); self.assertTrue(any("not flagged calibrated" in w for w in r["warnings"]))
        s2 = {"theta_by_depth_cm": {"10": 450.0}, "units": "mV", "calibrated": True}
        r2 = recommend_zone(zone(sensor=s2, current_depletion_mm=30), wx(), "2026-05-20")
        self.assertTrue(any("mV" in w for w in r2["warnings"])); self.assertEqual(r2["depletion_source"], "user_declared")

    def test_sensor_used_with_extrapolation_flag_and_inconsistency_blocked(self):
        s = {"theta_by_depth_cm": {"10": 18.0, "30": 18.0, "60": 18.0}, "units": "percent", "calibrated": True}
        r = recommend_zone(zone(sensor=s), wx(), "2026-05-20"); self.assertEqual(r["depletion_source"], "sensor")
        self.assertTrue(any("sensor-supported depth" in w or "extrapolated" in w for w in r["warnings"]) or r["sensor_root_zone"]["coverage_fraction"] == 1.0)
        bad = {"theta_by_depth_cm": {"10": 5.0, "30": 5.0}, "units": "percent", "calibrated": True}
        rb = recommend_zone(zone(sensor=bad), wx(), "2026-05-20"); self.assertEqual(rb["status"], "INCONSISTENT_SENSOR_SOIL"); self.assertIsNone(rb["volumes"])

    def test_forecast_gap_stops_projection_with_warning(self):
        f = synthetic_weather("2026-05-21", 4); f["eto_mm"] = [4, np.nan, 4, 4]
        r = recommend_zone(zone(), wx(), "2026-05-20", f); self.assertEqual(len(r["projection"]), 1); self.assertTrue(any("forecast gap" in w for w in r["warnings"]))


if __name__ == "__main__":
    unittest.main()

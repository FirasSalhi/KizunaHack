import unittest
import _path  # noqa
from engine.prioritization import rank_farm, allocate_limited_water, score_zone
from engine.water_balance import mm_to_volume


def rec(zid, dr, raw, taw=100, dtr=None, stage="mid_season", rain=0, ea=0.9, ha=1.0, status="OK", src="user_declared"):
    net = dr; gross = net / ea
    return {"zone_id": zid, "status": status, "dr_mm": dr, "raw_mm": raw, "taw_mm": taw, "dr_over_raw": dr / raw, "days_to_raw": 0 if dr >= raw else dtr,
            "stage": stage, "forecast_rain_mm": rain, "ea": ea, "area_ha": ha, "net_mm": net, "depletion_source": src,
            "volumes": {"net_mm": net, "gross_mm": gross, **mm_to_volume(gross, ha)}}


class Ranking(unittest.TestCase):
    def test_levels_and_order(self):
        out = rank_farm([rec("low", 10, 40, dtr=None), rec("high", 50, 40), rec("med", 30, 40, dtr=2)])
        self.assertEqual([z["zone_id"] for z in out["ranked"]], ["high", "med", "low"])
        self.assertEqual([z["priority"]["level"] for z in out["ranked"]], ["HIGH", "MEDIUM", "LOW"])
        self.assertTrue(all(z["priority"]["explanation"] for z in out["ranked"]))

    def test_not_dr_over_raw_alone(self):
        a = rec("sens", 30, 40, taw=40, dtr=2, stage="mid_season"); b = rec("tol", 30, 40, taw=200, dtr=2, stage="late_season")
        self.assertGreater(score_zone(a)["score"], score_zone(b)["score"])         # same Dr/RAW, different buffer and stage
        wet = rec("rain", 30, 40, dtr=2, rain=30); dry = rec("dry", 30, 40, dtr=2, rain=0)
        self.assertLess(score_zone(wet)["score"], score_zone(dry)["score"])         # forecast rain lowers urgency
        self.assertLess(score_zone(rec("ass", 30, 40, dtr=2, src="water_balance_from_refill_date"))["score"], score_zone(dry)["score"])

    def test_stress_component_matters(self):
        a, b = rec("a", 45, 40), rec("b", 80, 40)           # both HIGH, everything else equal
        self.assertGreater(score_zone(b)["score"], score_zone(a)["score"])

    def test_incomputable_zones_go_to_needs_data_not_bottom_rank(self):
        out = rank_farm([rec("ok", 50, 40), {"zone_id": "bad", "status": "MISSING_SOIL_PARAMS", "missing_inputs": ["soil.fc/wp"]}])
        self.assertEqual(len(out["ranked"]), 1); self.assertEqual(out["needs_data"][0]["category"], "NEEDS_DATA")

    def test_deterministic(self):
        zs = [rec("a", 50, 40), rec("b", 50, 40)]
        self.assertEqual([z["zone_id"] for z in rank_farm(zs)["ranked"]], [z["zone_id"] for z in rank_farm(zs[::-1])["ranked"]])


class Allocation(unittest.TestCase):
    def setUp(self):
        self.r = rank_farm([rec("A", 60, 40, ha=1.0), rec("B", 55, 40, ha=1.0), rec("C", 20, 40, dtr=3, ha=1.0)])["ranked"]

    def test_budget_never_exceeded_and_unit_math(self):
        for budget in (0, 5, 20, 100, 10_000):
            a = allocate_limited_water(self.r, budget)
            self.assertLessEqual(sum(p["allocated_m3"] for p in a["plan"]), budget + 1e-9)
            self.assertAlmostEqual(a["allocated_m3"] + a["unallocated_m3"], budget, places=5)
            for p in a["plan"]: self.assertAlmostEqual(p["gross_mm_applied"] * p["area_ha"] * 10, p["allocated_m3"])

    def test_priority_order_and_protect_phase_first(self):
        a = allocate_limited_water(self.r, 20)
        p = {x["zone_id"]: x for x in a["plan"]}
        self.assertGreater(p["A"]["allocated_m3"], 0); self.assertEqual(p["C"]["allocated_m3"], 0)   # C is below RAW: no phase-1 need
        self.assertTrue(p["A"]["still_beyond_raw"])

    def test_ample_water_satisfies_everyone_fully(self):
        a = allocate_limited_water(self.r, 10_000)
        self.assertTrue(all(p["fully_satisfied"] and p["residual_dr_mm"] < 1e-6 for p in a["plan"]))
        self.assertGreater(a["unallocated_m3"], 0)

    def test_three_zone_twenty_m3_example(self):
        a = allocate_limited_water(self.r, 20.0)
        self.assertEqual(len(a["plan"]), 3); self.assertIn("not optimised", a["strategy"])
        self.assertAlmostEqual(a["allocated_m3"], 20.0)

    def test_negative_budget_rejected_and_zone_without_ea_skipped(self):
        with self.assertRaises(ValueError): allocate_limited_water(self.r, -1)
        noea = rec("N", 50, 40); noea["ea"] = None
        a = allocate_limited_water(rank_farm([noea])["ranked"], 10); self.assertEqual(a["zones_without_volume_inputs"], ["N"])


if __name__ == "__main__":
    unittest.main()

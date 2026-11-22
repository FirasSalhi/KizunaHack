import datetime
import unittest
import _path  # noqa
from engine.crop_retrieval import CropIndex
from engine.crop_water_requirements import growth_stage, root_depth

ix = CropIndex()


class T(unittest.TestCase):
    def test_boundaries_tomato_mediterranean(self):   # 30/40/45/30
        c = ix.by_id["tomato"]
        for d, st in ((0, "initial"), (29, "initial"), (30, "development"), (69, "development"), (70, "mid_season"), (114, "mid_season"), (115, "late_season"), (144, "late_season")):
            on = datetime.date(2026, 4, 1) + datetime.timedelta(days=d)
            self.assertEqual(growth_stage(c, on, "2026-04-01")["stage"], st, d)

    def test_before_planting_and_after_season(self):
        c = ix.by_id["tomato"]
        self.assertEqual(growth_stage(c, "2026-03-01", "2026-04-01")["status"], "NOT_PLANTED")
        self.assertEqual(growth_stage(c, "2026-12-01", "2026-04-01")["status"], "SEASON_ENDED")

    def test_missing_planting_date_not_guessed(self):
        r = growth_stage(ix.by_id["tomato"], "2026-05-01")
        self.assertEqual(r["status"], "NEEDS_PLANTING_DATE"); self.assertIsNone(r["stage"])

    def test_manual_override_wins_and_invalid_rejected(self):
        r = growth_stage(ix.by_id["tomato"], "2026-05-01", "2026-04-01", stage_override="late_season")
        self.assertEqual((r["stage"], r["status"], r["estimated"]), ("late_season", "MANUAL", False))
        self.assertEqual(growth_stage(ix.by_id["tomato"], "2026-05-01", stage_override="flowering")["status"], "INVALID_STAGE")

    def test_crop_without_stage_lengths(self):
        self.assertEqual(growth_stage(ix.by_id["garlic"], "2026-05-01", "2026-01-01")["status"], "NO_STAGE_LENGTHS")

    def test_root_depth_develops_for_annuals_constant_for_trees(self):
        t = ix.by_id["tomato"]
        z0 = root_depth(t, growth_stage(t, "2026-04-01", "2026-04-01"))["zr_m"]
        z1 = root_depth(t, growth_stage(t, "2026-05-01", "2026-04-01"))["zr_m"]
        z2 = root_depth(t, growth_stage(t, "2026-07-01", "2026-04-01"))["zr_m"]
        self.assertAlmostEqual(z0, 0.3); self.assertLess(z0, z1); self.assertLess(z1, z2); self.assertAlmostEqual(z2, 0.7)
        o = ix.by_id["olive"]
        self.assertEqual(root_depth(o, {"status": "MANUAL", "stage": "initial"})["zr_m"], 1.2)


if __name__ == "__main__":
    unittest.main()

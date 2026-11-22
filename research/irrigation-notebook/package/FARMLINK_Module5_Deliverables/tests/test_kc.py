import unittest
import _path  # noqa
from engine.crop_retrieval import CropIndex
from engine.crop_water_requirements import kc_on_day, kc_for_stage, crop_requirements, adjusted_p

ix = CropIndex()


class T(unittest.TestCase):
    def test_curve_anchor_points_tomato(self):   # ini 0.60, mid 1.15, end 0.80 ; 30/40/45/30
        c = ix.by_id["tomato"]
        self.assertAlmostEqual(kc_on_day(c, 0), 0.60); self.assertAlmostEqual(kc_on_day(c, 29), 0.60)
        self.assertAlmostEqual(kc_on_day(c, 30), 0.60); self.assertAlmostEqual(kc_on_day(c, 50), 0.60 + 0.55 * 20 / 40)
        self.assertAlmostEqual(kc_on_day(c, 70), 1.15); self.assertAlmostEqual(kc_on_day(c, 114), 1.15)
        self.assertAlmostEqual(kc_on_day(c, 115), 1.15); self.assertAlmostEqual(kc_on_day(c, 130), 1.15 + (0.80 - 1.15) * 15 / 30)

    def test_curve_monotone_segments_and_continuous(self):
        c = ix.by_id["potato"]; k = [kc_on_day(c, d) for d in range(0, 130)]
        self.assertTrue(all(abs(a - b) < 0.05 for a, b in zip(k, k[1:])))

    def test_stage_representative(self):
        c = ix.by_id["olive"]; self.assertEqual(kc_for_stage(c, "mid_season")["kc"], 0.70)
        self.assertAlmostEqual(kc_for_stage(ix.by_id["tomato"], "development")["kc"], (0.60 + 1.15) / 2)

    def test_variant(self):
        c = ix.by_id["citrus"]; self.assertEqual(kc_for_stage(c, "mid_season", "70% canopy")["kc"], 0.65)
        with self.assertRaises(ValueError): kc_for_stage(c, "mid_season", "bogus")

    def test_etc_equals_kc_times_eto(self):
        r = crop_requirements(ix.by_id["tomato"], "2026-06-10", 6.0, "2026-04-01")
        self.assertAlmostEqual(r["etc_mm"], r["kc"] * 6.0)

    def test_p_adjustment(self):
        self.assertAlmostEqual(adjusted_p(0.40, 5.0), 0.40); self.assertAlmostEqual(adjusted_p(0.40, 3.0), 0.48)
        self.assertEqual(adjusted_p(0.7, 0.0), 0.8); self.assertEqual(adjusted_p(0.2, 12.0), 0.1)

    def test_unavailable_crop_returns_status_not_numbers(self):
        r = crop_requirements(ix.by_id["fig"], "2026-06-10", 6.0, "2026-04-01")
        self.assertEqual(r["status"], "CROP_PARAMETERS_UNAVAILABLE"); self.assertNotIn("kc", r)

    def test_missing_eto_withholds_etc(self):
        r = crop_requirements(ix.by_id["tomato"], "2026-06-10", float("nan"), "2026-04-01")
        self.assertNotIn("etc_mm", r)


if __name__ == "__main__":
    unittest.main()

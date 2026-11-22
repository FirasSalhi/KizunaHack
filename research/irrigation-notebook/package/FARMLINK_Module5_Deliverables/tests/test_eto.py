import unittest
import numpy as np, pandas as pd
import _path  # noqa
from engine import eto as E


class T(unittest.TestCase):
    def test_ra_examples(self):
        self.assertAlmostEqual(float(E.extraterrestrial_radiation(50.80, 187)), 41.09, delta=0.1)
        self.assertAlmostEqual(float(E.extraterrestrial_radiation(45.72, 196)), 40.55, delta=0.15)

    def test_penman_monteith_fao56_example18(self):   # Uccle -> 3.88 mm/day
        self.assertAlmostEqual(float(E.eto_penman_monteith(12.3, 21.5, 16.9, None, 2.078, 22.07, 50.80, 187, 100, ea_kpa=1.409)), 3.88, delta=0.05)

    def test_hargreaves_fao56_example20(self):
        self.assertAlmostEqual(float(E.eto_hargreaves(14.8, 26.6, 20.7, 45.72, 196)), 5.0, delta=0.15)

    def test_method_recorded_and_no_silent_default(self):
        w = pd.DataFrame({"date": pd.date_range("2026-07-01", periods=3), "tmin": [18, 18, np.nan], "tmax": [32, 33, 34], "tmean": [25, 25.5, 26],
                          "rh_mean": [50, np.nan, 50], "u2": [2, 2, 2], "rs": [25, 25, 25]})
        o = E.compute_eto(w, 35.9, 10)
        self.assertEqual(o["eto_method"].tolist(), ["FAO56_Penman_Monteith", "Hargreaves_Samani(fallback)", "unavailable"])
        self.assertTrue(np.isnan(o["eto_mm"].iloc[2]))

    def test_monotone_in_radiation(self):
        a = E.eto_penman_monteith(15, 30, 22, 50, 2, 15, 36, 180, 20); b = E.eto_penman_monteith(15, 30, 22, 50, 2, 25, 36, 180, 20)
        self.assertGreater(float(b), float(a))


if __name__ == "__main__":
    unittest.main()

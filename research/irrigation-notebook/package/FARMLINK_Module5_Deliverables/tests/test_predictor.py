import json, tempfile, os, unittest
import numpy as np, pandas as pd
import _path  # noqa
from engine import soil_moisture_predictor as P


def series(kind, n=24 * 60, seed=0):
    rng = np.random.default_rng(seed); idx = pd.date_range("2026-01-01", periods=n, freq="h", tz="UTC")
    if kind == "walk": v = 20 + np.cumsum(rng.normal(0, 0.05, n))
    else: v = 20 + 2 * np.sin(2 * np.pi * np.arange(n) / 24) + rng.normal(0, 0.05, n)       # strong diurnal cycle, SYNTHETIC
    return pd.Series(v, index=idx)


class T(unittest.TestCase):
    def test_persistence_retained_when_it_wins(self):
        r = P.evaluate(series("walk"))
        for k in ("1h", "6h", "24h"): self.assertEqual(r["horizons"][k]["winner"], "persistence", k)
        self.assertTrue(all(r["horizons"][k]["model"] is None for k in r["horizons"]))

    def test_model_kept_when_it_clearly_wins(self):
        r = P.evaluate(series("diurnal")); h6 = r["horizons"]["6h"]
        self.assertEqual(h6["winner"], "ridge"); self.assertGreater(h6["improvement_vs_persistence"], 0.3); self.assertIsNotNone(h6["model"])

    def test_chronological_split_no_leakage(self):
        a, b, c = P.chronological_split(1000)
        self.assertEqual((a.stop, b.start, b.stop, c.start), (600, 600, 800, 800)); self.assertEqual(c.stop, 1000)
        r = P.evaluate(series("diurnal")); self.assertGreater(pd.Timestamp(r["horizons"]["1h"]["test_start"]), pd.Timestamp("2026-02-05", tz="UTC"))

    def test_gaps_are_not_bridged(self):
        s = series("diurnal"); s.iloc[700:760] = np.nan
        D = P.make_supervised(s, 6)
        gap_hours = s.index[700:760]
        for t in D.index:   # no row may use a missing hour as lag or target
            for l in P.LAGS: self.assertFalse(t - pd.Timedelta(hours=l) in gap_hours)
            self.assertFalse(t + pd.Timedelta(hours=6) in gap_hours)

    def test_insufficient_data(self):
        r = P.evaluate(series("walk", n=100)); self.assertEqual(r["horizons"]["1h"]["status"], "INSUFFICIENT_DATA"); self.assertEqual(r["horizons"]["1h"]["winner"], "persistence")

    def test_predict_roundtrip_and_metadata(self):
        s = series("diurnal"); r = P.evaluate(s)
        p = P.predict(r, "6h", s.iloc[:-6]); self.assertTrue(np.isfinite(p)); self.assertAlmostEqual(p, s.iloc[-1], delta=0.5)
        self.assertEqual(P.predict(P.evaluate(series("walk")), "1h", series("walk")), float(series("walk").iloc[-1]))
        f = os.path.join(tempfile.mkdtemp(), "m.json"); P.save_metadata(r, f, {"data_provenance": "SYNTHETIC test"}); self.assertIn("SYNTHETIC", json.load(open(f))["data_provenance"])

    def test_to_hourly_handles_unsorted_duplicates(self):
        df = pd.DataFrame({"t": ["2026-01-01 02:10", "2026-01-01 00:20", "2026-01-01 00:50", "2026-01-01 00:50"], "v": [3, 1, 2, 2]})
        h = P.to_hourly(df, "t", "v"); self.assertEqual(h.iloc[0], 1.5); self.assertTrue(np.isnan(h.iloc[1])); self.assertEqual(h.iloc[2], 3)


if __name__ == "__main__":
    unittest.main()

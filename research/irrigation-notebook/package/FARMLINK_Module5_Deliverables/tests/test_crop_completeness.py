import csv, json, unittest
import _path  # noqa
from engine.crop_retrieval import CropIndex, DEFAULT_DB

D = DEFAULT_DB.parent


class T(unittest.TestCase):
    db = json.load(open(DEFAULT_DB, encoding="utf-8"))
    ix = CropIndex()

    def test_required_priority_crops_present_and_ready(self):
        for c in ("tomato", "olive", "durum_wheat", "sweet_pepper", "potato", "citrus"):
            self.assertTrue(self.ix.by_id[c]["irrigation_ready"], c)

    def test_every_ready_crop_has_complete_core_parameters(self):
        for c in self.db["crops"]:
            if c["irrigation_ready"]:
                self.assertTrue(0 < c["kc"]["ini"] < 1.5 and 0 < c["kc"]["mid"] < 1.5 and 0 < c["kc"]["end"] < 1.5, c["id"])
                self.assertLess(c["root_depth"]["zr_min_m"], c["root_depth"]["zr_max_m"] + 1e-9, c["id"])
                self.assertTrue(0.1 <= c["depletion_fraction_p"]["value"] <= 0.8, c["id"])
                self.assertIn("kc", c["confidence"])

    def test_missing_parameters_are_explicit_not_filled(self):
        for cid in ("fig", "pomegranate"):
            c = self.ix.by_id[cid]
            self.assertFalse(c["irrigation_ready"]); self.assertIsNone(c["kc"]); self.assertIn("kc", c["missing"])
        for c in self.db["crops"]:
            self.assertIn("ecocrop_environmental_requirements", c["missing"])
            self.assertIsNone(c["climate_requirements"])   # not retrieved -> null, never invented

    def test_no_false_local_validation_label(self):
        txt = json.dumps(self.db)
        self.assertNotIn('"locally_validated"', txt)

    def test_durum_is_flagged_generic_winter_wheat(self):
        c = self.ix.by_id["durum_wheat"]
        self.assertEqual(c["confidence"]["kc"], "generic_crop_approximation")
        self.assertTrue(any("WINTER WHEAT" in n for n in c["irrigation_notes"]))

    def test_group_default_kc_ini_labelled(self):
        self.assertEqual(self.ix.by_id["tomato"]["kc"]["ini_source"], "FAO56_TABLE12_GROUP_DEFAULT")
        self.assertEqual(self.ix.by_id["tomato"]["confidence"]["kc"], "derived_from_published_reference")

    def test_published_values_spot_check(self):   # FAO-56 Table 12 / 22 as transcribed
        t = self.ix.by_id["tomato"]; self.assertEqual((t["kc"]["mid"], t["kc"]["end_low"], t["kc"]["end_high"]), (1.15, 0.70, 0.90))
        o = self.ix.by_id["olive"]; self.assertEqual((o["kc"]["ini"], o["kc"]["mid"], o["kc"]["end"], o["depletion_fraction_p"]["value"]), (0.65, 0.70, 0.70, 0.65))
        self.assertEqual(self.ix.by_id["potato"]["root_depth"]["zr_min_m"], 0.4)
        self.assertEqual(self.ix.by_id["citrus"]["kc"]["mid"], 0.60)

    def test_stage_length_totals_consistent(self):
        for c in self.db["crops"]:
            s = c["stage_lengths_days"]
            if s: self.assertEqual(s["total"], s["ini"] + s["dev"] + s["mid"] + s["late"], c["id"])

    def test_csv_matches_json(self):
        rows = {r["id"]: r for r in csv.DictReader(open(D / "crop_parameters.csv", encoding="utf-8-sig"))}
        self.assertEqual(set(rows), {c["id"] for c in self.db["crops"]})
        for c in self.db["crops"]:
            if c["irrigation_ready"]: self.assertAlmostEqual(float(rows[c["id"]]["kc_mid"]), c["kc"]["mid"])

    def test_sources_file_covers_cited_sources(self):
        src = json.load(open(D / "crop_sources.json"))
        for c in self.db["crops"]:
            for s in c["sources"]: self.assertIn(s, src["sources"])
        self.assertIn("FAO ECOCROP (environmental requirements)", src["not_retrieved"])

    def test_completeness_report(self):
        r = self.ix.completeness("tomato"); self.assertIn("kc", r["present"]); self.assertIn("climate_requirements", r["missing"])


if __name__ == "__main__":
    unittest.main()

import unittest
import _path  # noqa
from engine.crop_retrieval import CropIndex, CropNotFound


class T(unittest.TestCase):
    ix = CropIndex()

    def test_exact_aliases_multilingual(self):
        for q in ("tomato", "Tomate", "طماطم", "tomatoes", "Solanum lycopersicum"):
            self.assertEqual(self.ix.get(q)["id"], "tomato")
        self.assertEqual(self.ix.get("blé dur")["id"], "durum_wheat")
        self.assertEqual(self.ix.get("ble dur")["id"], "durum_wheat")
        self.assertEqual(self.ix.get("olivier")["id"], "olive")

    def test_unknown_raises_with_suggestions_never_guesses(self):
        with self.assertRaises(CropNotFound) as c:
            self.ix.get("tomatto")
        self.assertIn("tomato", str(c.exception))
        with self.assertRaises(CropNotFound):
            self.ix.get("dragonfruit")

    def test_search_and_autocomplete(self):
        self.assertEqual(self.ix.search("pota")[0]["id"], "potato")
        self.assertIn("Tomato", self.ix.autocomplete("tom"))
        self.assertEqual(self.ix.search(""), [])
        self.assertNotIn("grape_table", [r["id"] for r in self.ix.search("blé")])   # substring noise regression
        self.assertEqual(self.ix.search("fraise")[0]["id"], "strawberry")

    def test_sqlite_mirror(self):
        import tempfile, os, sqlite3
        p = os.path.join(tempfile.mkdtemp(), "x.db")
        n = self.ix.to_sqlite(p)
        self.assertGreater(n, 100)
        self.assertEqual(sqlite3.connect(p).execute("select crop_id from crop_terms where term='poivron'").fetchone()[0], "sweet_pepper")


if __name__ == "__main__":
    unittest.main()

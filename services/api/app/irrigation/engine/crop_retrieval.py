"""Lightweight crop retrieval and autocomplete over crop_knowledge/crop_database.json.

No LLM and no embeddings: normalised string matching over common/scientific/FR/AR names and synonyms.
Numbers always come from the structured database, never from free text.
"""
from __future__ import annotations

import difflib
import json
import sqlite3
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

DEFAULT_DB = Path(__file__).resolve().parent.parent / "crop_knowledge" / "crop_database.json"


class CropNotFound(KeyError):
    pass


def normalize(text: str) -> str:
    t = unicodedata.normalize("NFKD", str(text)).casefold().strip()
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    return " ".join(t.replace("-", " ").replace("_", " ").replace("(", " ").replace(")", " ").replace(",", " ").split())


@lru_cache(maxsize=4)
def load_database(path: str = str(DEFAULT_DB)) -> Dict:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Crop database not found: {p}")
    db = json.loads(p.read_text(encoding="utf-8"))
    if "crops" not in db or not db["crops"]:
        raise ValueError("crop_database.json has no crops")
    return db


class CropIndex:
    def __init__(self, db_path: Optional[str] = None):
        self.db = load_database(str(db_path or DEFAULT_DB))
        self.by_id = {c["id"]: c for c in self.db["crops"]}
        self.terms: Dict[str, str] = {}      # normalized term -> crop id
        self.term_kind: Dict[str, str] = {}
        for c in self.db["crops"]:
            n = c["names"]
            cand = [("id", c["id"]), ("en", n["en"]), ("scientific", n["scientific"]), ("fr", n["fr"]), ("ar", n["ar"])]
            cand += [("synonym", s) for s in n.get("synonyms", [])]
            for kind, t in cand:
                k = normalize(t)
                if k and k not in self.terms:
                    self.terms[k] = c["id"]; self.term_kind[k] = kind

    def get(self, name_or_id: str) -> Dict:
        """Exact (normalised) match on id/name/synonym; else raises CropNotFound with suggestions. Never guesses."""
        k = normalize(name_or_id)
        if k in self.terms:
            return self.by_id[self.terms[k]]
        sugg = self.suggest(name_or_id, 3)
        raise CropNotFound(f"Unknown crop '{name_or_id}'. Did you mean: {[s['id'] for s in sugg]}?")

    def search(self, query: str, limit: int = 8) -> List[Dict]:
        """Ranked: exact > prefix > substring > fuzzy (difflib >= 0.75)."""
        q = normalize(query)
        if not q:
            return []
        scored: Dict[str, float] = {}
        for term, cid in self.terms.items():
            if term == q: s = 1.0
            elif term.startswith(q): s = 0.9
            elif any(tok.startswith(q) for tok in term.split()): s = 0.8     # word-prefix, never an arbitrary substring ('ble' must not hit 'table')
            else:
                r = difflib.SequenceMatcher(None, q, term).ratio()
                s = r * 0.7 if r >= 0.75 else 0
            if s > scored.get(cid, 0): scored[cid] = s
        ranked = sorted(scored.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
        return [{"id": cid, "score": round(s, 3), "name_en": self.by_id[cid]["names"]["en"], "name_fr": self.by_id[cid]["names"]["fr"],
                 "name_ar": self.by_id[cid]["names"]["ar"], "irrigation_ready": self.by_id[cid]["irrigation_ready"]} for cid, s in ranked]

    suggest = lambda self, q, n=5: [self.by_id[r["id"]] for r in self.search(q, n)]

    def autocomplete(self, prefix: str, limit: int = 8) -> List[str]:
        q = normalize(prefix)
        out, seen = [], set()
        for term, cid in sorted(self.terms.items()):
            if term.startswith(q) and cid not in seen:
                out.append(self.by_id[cid]["names"]["en"]); seen.add(cid)
            if len(out) >= limit: break
        return out

    def completeness(self, crop_id: str) -> Dict:
        c = self.by_id[crop_id]
        fields = {"kc": c["kc"], "root_depth": c["root_depth"], "depletion_fraction_p": c["depletion_fraction_p"],
                  "stage_lengths_days": c["stage_lengths_days"], "planting_calendar": c["planting_calendar"],
                  "climate_requirements": c["climate_requirements"], "soil_requirements": c["soil_requirements"]}
        present = [k for k, v in fields.items() if v]
        missing = [k for k, v in fields.items() if not v]
        return {"crop": crop_id, "present": present, "missing": missing, "score": round(len(present) / len(fields), 2),
                "irrigation_ready": c["irrigation_ready"], "can_run_without_planting_date": bool(c["stage_lengths_days"]) is False}

    def to_sqlite(self, path: str) -> int:
        """Optional SQLite mirror (id, term, kind) for web apps that prefer SQL autocomplete."""
        con = sqlite3.connect(path)
        con.execute("DROP TABLE IF EXISTS crop_terms")
        con.execute("CREATE TABLE crop_terms (term TEXT, crop_id TEXT, kind TEXT)")
        con.executemany("INSERT INTO crop_terms VALUES (?,?,?)", [(t, c, self.term_kind[t]) for t, c in self.terms.items()])
        con.execute("CREATE INDEX idx_term ON crop_terms(term)")
        con.commit(); n = con.execute("SELECT COUNT(*) FROM crop_terms").fetchone()[0]; con.close()
        return n


def get_crop(name_or_id: str, db_path: Optional[str] = None) -> Dict:
    return CropIndex(db_path).get(name_or_id)

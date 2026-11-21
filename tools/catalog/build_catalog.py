# Ported unchanged from RaziSnihaa/is9ini backend/build_catalog.py at commit 2aaac4ad73eee1aae11c890086b92f322611da45
# (team-owned code, reuse confirmed 2026-11-21, research.md OQ-6). Paths inside still refer to
# the reference layout (backend/...); later FARMLINK tasks adapt them.
"""Build the plant catalogue used by the BioCLIP 2 identifier.

Sources (all in backend/models):
  - treeoflife/embeddings/txt_emb_species.json  (TreeOfLife-200M species list, CC0): taxonomy + English common names
  - ecocrop/EcoCrop_DB.csv                      (FAO EcoCrop via OpenCLIM): growing conditions of 2 568 crops
  - verdant-care-db/verdant_care.sqlite         (CC BY-SA 4.0): care sheets of 110 houseplants & herbs
  - bioclip-2                                   (MIT): the vision-language model

Output: models/catalog/classes.json + models/catalog/text_emb.npy (one BioCLIP text embedding per class)

    python build_catalog.py
"""
import csv
import json
import re
import sqlite3
from pathlib import Path

import numpy as np

MODELS = Path(__file__).resolve().parent / "models"
OUT = MODELS / "catalog"


def binomial(name: str) -> str | None:
    parts = re.findall(r"[A-Za-z\-]+", name or "")
    if len(parts) < 2 or not parts[0][0].isupper():
        return None
    return f"{parts[0]} {parts[1]}".lower()


def load_tol() -> dict[str, tuple[list[str], str]]:
    names = json.loads((MODELS / "treeoflife" / "embeddings" / "txt_emb_species.json").read_text(encoding="utf-8"))
    tol = {}
    for taxonomy, common in names:
        if taxonomy[0] != "Plantae" or not taxonomy[5] or not taxonomy[6]:
            continue
        key = f"{taxonomy[5]} {taxonomy[6]}".lower()
        if key not in tol or (common and not tol[key][1]):
            tol[key] = (taxonomy, common)
    return tol


def load_ecocrop() -> tuple[list[dict], dict[str, int]]:
    rows = list(csv.DictReader(open(MODELS / "ecocrop" / "EcoCrop_DB.csv", encoding="latin-1")))
    index: dict[str, int] = {}
    for i, r in enumerate(rows):  # accepted names first
        b = binomial(r["ScientificName"])
        if b and b not in index:
            index[b] = i
    for i, r in enumerate(rows):  # then synonyms
        for syn in (r["SYNO"] or "").split(","):
            b = binomial(syn.strip())
            if b and b not in index:
                index[b] = i
    # modern names missing from the synonym lists
    for modern, old in {"solanum lycopersicum": "lycopersicon esculentum"}.items():
        if old in index and modern not in index:
            index[modern] = index[old]
    return rows, index


def load_verdant() -> list[dict]:
    db = sqlite3.connect(MODELS / "verdant-care-db" / "verdant_care.sqlite")
    rows = db.execute("SELECT s.id, s.scientific_name, n.common_name FROM species s "
                      "LEFT JOIN species_name n ON n.species_id = s.id AND n.lang = 'en'").fetchall()
    return [{"id": r[0], "scientific": r[1], "common": r[2]} for r in rows]


def main() -> None:
    tol = load_tol()
    eco_rows, eco_index = load_ecocrop()
    verdant = load_verdant()
    genus_taxonomy = {t[5].lower(): t[:6] for t, _ in tol.values()}

    classes: dict[str, dict] = {}
    for key, (taxonomy, common) in tol.items():
        eco = eco_index.get(key)
        if common or eco is not None:
            classes[key] = {"key": key, "taxonomy": taxonomy, "common": common, "ecocrop": eco, "verdant": None}

    for v in verdant:
        b = binomial(v["scientific"])
        if b and b in classes:
            classes[b]["verdant"] = v["id"]
            classes[b]["common"] = classes[b]["common"] or v["common"]
            continue
        genus = (v["scientific"] or "").split()[0].lower()
        taxonomy = list(tol[b][0]) if b and b in tol else list(genus_taxonomy.get(genus, ["Plantae"])) + [""]
        key = b or f"verdant:{v['id']}"
        classes[key] = {"key": key, "taxonomy": taxonomy, "common": v["common"], "ecocrop": eco_index.get(b or ""), "verdant": v["id"]}

    ordered = sorted(classes.values(), key=lambda c: c["key"])
    for c in ordered:
        taxon = " ".join(t for t in c["taxonomy"] if t)
        c["text"] = f"a photo of {taxon} with common name {c['common']}." if c["common"] else f"a photo of {taxon}."
        c["scientific"] = " ".join(t for t in c["taxonomy"][5:7] if t) or c["key"]
        c["family"] = c["taxonomy"][4] if len(c["taxonomy"]) > 4 else ""

    OUT.mkdir(parents=True, exist_ok=True)
    stats = {"classes": len(ordered), "with_ecocrop": sum(c["ecocrop"] is not None for c in ordered),
             "with_verdant": sum(c["verdant"] is not None for c in ordered)}
    print(stats)

    import open_clip
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model, _, _ = open_clip.create_model_and_transforms(f"local-dir:{MODELS / 'bioclip-2'}")
    tokenizer = open_clip.get_tokenizer(f"local-dir:{MODELS / 'bioclip-2'}")
    model = model.to(device).eval()
    embs = []
    with torch.no_grad(), torch.autocast(device, enabled=device == "cuda"):
        for i in range(0, len(ordered), 256):
            tokens = tokenizer([c["text"] for c in ordered[i:i + 256]]).to(device)
            e = model.encode_text(tokens)
            embs.append(torch.nn.functional.normalize(e.float(), dim=-1).cpu().numpy().astype(np.float16))
            print(f"  embedded {min(i + 256, len(ordered))}/{len(ordered)}", end="\r")
    np.save(OUT / "text_emb.npy", np.concatenate(embs))
    (OUT / "classes.json").write_text(json.dumps({"stats": stats, "classes": ordered}, ensure_ascii=False), encoding="utf-8")
    print("\nCatalogue written to", OUT)


if __name__ == "__main__":
    main()

"""Download the plant scanner's models and databases, and build the BioCLIP 2 plant catalogue.

Ported from is9ini (github.com/RaziSnihaa/is9ini, backend/download_models.py and build_catalog.py).

    uv run python -m app.plants.catalog            # everything, ~2 GB (uv sync --extra bioclip)
    uv run python -m app.plants.catalog --small    # only verdant + the care databases (~35 MB)
    uv run python -m app.plants.catalog --build    # only (re)build the BioCLIP catalogue

Files go to PLANT_MODELS_DIR (default services/api/models/plants, not committed).
Licences: Pl@ntNet API terms, BioCLIP 2 (MIT), TreeOfLife-200M (CC0),
FAO EcoCrop via OpenCLIM (Open Government Licence), verdant-plant-model (Apache-2.0),
verdant-care-db (CC BY-SA 4.0).

Catalogue sources:
  - treeoflife/embeddings/txt_emb_species.json  taxonomy + English common names (TreeOfLife-200M)
  - ecocrop/EcoCrop_DB.csv                      growing conditions of 2 568 crops
  - verdant-care-db/verdant_care.sqlite         care sheets of 110 houseplants and herbs
Output: catalog/classes.json + catalog/text_emb.npy (one BioCLIP text embedding per plant).
"""

from __future__ import annotations

import csv
import json
import re
import sqlite3
import sys
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np

from app.core.config import settings


def models_dir() -> Path:
    return Path(settings.PLANT_MODELS_DIR)


def binomial(name: str) -> str | None:
    parts = re.findall(r"[A-Za-z\-]+", name or "")
    if len(parts) < 2 or not parts[0][0].isupper():
        return None
    return f"{parts[0]} {parts[1]}".lower()


def _load_tol(models: Path) -> dict[str, tuple[list[str], str]]:
    path = models / "treeoflife" / "embeddings" / "txt_emb_species.json"
    names = json.loads(path.read_text(encoding="utf-8"))
    tol: dict[str, tuple[list[str], str]] = {}
    for taxonomy, common in names:
        if taxonomy[0] != "Plantae" or not taxonomy[5] or not taxonomy[6]:
            continue
        key = f"{taxonomy[5]} {taxonomy[6]}".lower()
        if key not in tol or (common and not tol[key][1]):
            tol[key] = (taxonomy, common)
    return tol


def _load_ecocrop(models: Path) -> tuple[list[dict[str, str]], dict[str, int]]:
    with open(models / "ecocrop" / "EcoCrop_DB.csv", encoding="latin-1") as f:
        rows = list(csv.DictReader(f))
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


def _load_verdant(models: Path) -> list[dict[str, Any]]:
    db = sqlite3.connect(models / "verdant-care-db" / "verdant_care.sqlite")
    try:
        rows = db.execute(
            "SELECT s.id, s.scientific_name, n.common_name FROM species s "
            "LEFT JOIN species_name n ON n.species_id = s.id AND n.lang = 'en'"
        ).fetchall()
    finally:
        db.close()
    return [{"id": r[0], "scientific": r[1], "common": r[2]} for r in rows]


def build_catalog() -> None:
    """Embed every catalogue plant name with BioCLIP 2 (a few minutes on GPU, longer on CPU)."""
    models = models_dir()
    out = models / "catalog"
    tol = _load_tol(models)
    _eco_rows, eco_index = _load_ecocrop(models)
    verdant = _load_verdant(models)
    genus_taxonomy = {t[5].lower(): t[:6] for t, _ in tol.values()}

    classes: dict[str, dict[str, Any]] = {}
    for key, (taxonomy, common) in tol.items():
        eco = eco_index.get(key)
        if common or eco is not None:
            classes[key] = {
                "key": key,
                "taxonomy": taxonomy,
                "common": common,
                "ecocrop": eco,
                "verdant": None,
            }

    for v in verdant:
        b = binomial(v["scientific"])
        if b and b in classes:
            classes[b]["verdant"] = v["id"]
            classes[b]["common"] = classes[b]["common"] or v["common"]
            continue
        genus = (v["scientific"] or "").split()[0].lower()
        if b and b in tol:
            taxonomy = list(tol[b][0])
        else:
            taxonomy = list(genus_taxonomy.get(genus, ["Plantae"])) + [""]
        key = b or f"verdant:{v['id']}"
        classes[key] = {
            "key": key,
            "taxonomy": taxonomy,
            "common": v["common"],
            "ecocrop": eco_index.get(b or ""),
            "verdant": v["id"],
        }

    ordered = sorted(classes.values(), key=lambda c: c["key"])
    for c in ordered:
        taxon = " ".join(t for t in c["taxonomy"] if t)
        c["text"] = (
            f"a photo of {taxon} with common name {c['common']}."
            if c["common"]
            else f"a photo of {taxon}."
        )
        c["scientific"] = " ".join(t for t in c["taxonomy"][5:7] if t) or c["key"]
        c["family"] = c["taxonomy"][4] if len(c["taxonomy"]) > 4 else ""

    out.mkdir(parents=True, exist_ok=True)
    stats = {
        "classes": len(ordered),
        "with_ecocrop": sum(c["ecocrop"] is not None for c in ordered),
        "with_verdant": sum(c["verdant"] is not None for c in ordered),
    }
    print(stats)

    import open_clip
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model, _, _ = open_clip.create_model_and_transforms(f"local-dir:{models / 'bioclip-2'}")
    tokenizer = open_clip.get_tokenizer(f"local-dir:{models / 'bioclip-2'}")
    model = model.to(device).eval()
    embs = []
    with torch.no_grad(), torch.autocast(device, enabled=device == "cuda"):
        for i in range(0, len(ordered), 256):
            tokens = tokenizer([c["text"] for c in ordered[i : i + 256]]).to(device)
            e = model.encode_text(tokens)
            embs.append(
                torch.nn.functional.normalize(e.float(), dim=-1).cpu().numpy().astype(np.float16)
            )
            print(f"  embedded {min(i + 256, len(ordered))}/{len(ordered)}", end="\r")
    np.save(out / "text_emb.npy", np.concatenate(embs))
    (out / "classes.json").write_text(
        json.dumps({"stats": stats, "classes": ordered}, ensure_ascii=False), encoding="utf-8"
    )
    print("\nCatalogue written to", out)


def download(small: bool) -> None:
    from huggingface_hub import hf_hub_download, snapshot_download

    models = models_dir()
    print("1/5 verdant plant model (Apache-2.0)")
    snapshot_download("m3r1al/verdant-plant-model", local_dir=models / "verdant-plant-model")
    print("2/5 verdant care database (CC BY-SA 4.0)")
    snapshot_download(
        "m3r1al/verdant-care-db", repo_type="dataset", local_dir=models / "verdant-care-db"
    )
    print("3/5 FAO EcoCrop (via OpenCLIM)")
    (models / "ecocrop").mkdir(parents=True, exist_ok=True)
    for name in ("EcoCrop_DB.csv", "Ecocrop_variable_lookup.csv"):
        url = f"https://raw.githubusercontent.com/openclim/ecocrop/main/{name}"
        urllib.request.urlretrieve(url, models / "ecocrop" / name)  # noqa: S310 - fixed https URL

    if not small:
        print("4/5 BioCLIP 2 (MIT, ~1.7 GB) + TreeOfLife species list (CC0)")
        snapshot_download(
            "imageomics/bioclip-2",
            local_dir=models / "bioclip-2",
            allow_patterns=["*.json", "*.txt", "*.safetensors", "README.md"],
        )
        hf_hub_download(
            "imageomics/TreeOfLife-200M",
            "embeddings/txt_emb_species.json",
            repo_type="dataset",
            local_dir=models / "treeoflife",
        )
        print("5/5 building the BioCLIP catalogue (GPU recommended)")
        build_catalog()

    print("Models ready in", models)


if __name__ == "__main__":
    if "--build" in sys.argv:
        build_catalog()
    else:
        download(small="--small" in sys.argv)

# Ported unchanged from RaziSnihaa/is9ini backend/download_models.py at commit 2aaac4ad73eee1aae11c890086b92f322611da45
# (team-owned code, reuse confirmed 2026-11-21, research.md OQ-6). Paths inside still refer to
# the reference layout (backend/...); later FARMLINK tasks adapt them.
"""Download every model and dataset the plant scanner needs into backend/models (~2 GB), then build the catalogue.

    python download_models.py            # everything (BioCLIP 2 needs ~1.7 GB)
    python download_models.py --small    # only the small offline model + care databases (~35 MB)

Sources and licences: see docs/RAPPORT_IA.md
"""
import sys
import urllib.request
from pathlib import Path

from huggingface_hub import hf_hub_download, snapshot_download

MODELS = Path(__file__).resolve().parent / "models"
small = "--small" in sys.argv

print("1/5 verdant plant model (Apache-2.0)")
snapshot_download("m3r1al/verdant-plant-model", local_dir=MODELS / "verdant-plant-model")
print("2/5 verdant care database (CC BY-SA 4.0)")
snapshot_download("m3r1al/verdant-care-db", repo_type="dataset", local_dir=MODELS / "verdant-care-db")
print("3/5 FAO EcoCrop (via OpenCLIM)")
(MODELS / "ecocrop").mkdir(parents=True, exist_ok=True)
for name in ("EcoCrop_DB.csv", "Ecocrop_variable_lookup.csv"):
    urllib.request.urlretrieve(f"https://raw.githubusercontent.com/openclim/ecocrop/main/{name}", MODELS / "ecocrop" / name)

if not small:
    print("4/5 BioCLIP 2 (MIT, ~1.7 GB) + TreeOfLife species list (CC0)")
    snapshot_download("imageomics/bioclip-2", local_dir=MODELS / "bioclip-2",
                      allow_patterns=["*.json", "*.txt", "*.safetensors", "README.md"])
    hf_hub_download("imageomics/TreeOfLife-200M", "embeddings/txt_emb_species.json", repo_type="dataset",
                    local_dir=MODELS / "treeoflife")
    print("5/5 building the BioCLIP catalogue (GPU recommended)")
    import build_catalog

    build_catalog.main()

print("Models ready in", MODELS)

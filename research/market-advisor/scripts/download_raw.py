"""Download selected national datasets from catalog.data.gov.tn into data/raw (unchanged) + manifest.

Usage: python download_raw.py <catalog.json> <raw_dir> [ca_bundle]
"""
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

DATASETS = [
    "evolution-de-la-production-des-cultures-maraicheres-mille-tonnes",
    "evolution_cultures_maraichere",
    "evolution-de-la-productivite-des-cultures-maraicheres-tonnes-ha",
    "evolution-de-la-superficie-des-cultures-maraichere",
    "evolution-des-prix-a-la-production-des-cultures-maraicheres-d-t",
    "evolution-de-la-production-de-l-arboriculture-fruitiere-en-tonne",
    "evolution-de-la-production-arboricole-en-tonne",
    "evolution-de-la-production-des-autres-arboricultures-fruitiere",
    "evolution-de-la-production-des-agrumes-par-type-de-produit",
    "evolution-de-la-superficie-des-agrumes",
    "production-agrumes",
    "production-et-superficie-des-fruits-pour-la-campagne-2021-2022",
    "production-des-dattes-1000-t",
    "suivi-de-la-filiere-palmier-et-production-de-dattes",
    "2000-2016",
    "evolution-des-superficies-de-la-culture-de-pomme-de-terre-d-arriere-saison-en-ha",
    "evolution-de-la-production-de-tomate-de-saison-en-tonnes",
    "evolution-des-superficies-du-tomates-de-saison-en-hectare-entre-2000-et-2016",
    "prix-des-principaux-intrants-des-produits-agricoles",
    "prix-des-engrais-chimiques-aupres-des-societes-qui-s-approvisionnent-directement-du-groupe-chimique",
    "prix-moyens-a-la-production-des-olives",
    "suivi-des-prix",
    "evolution-du-tarif-de-vente-du-m3-d-eau-en-millime_secadenord",
]
cat = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
raw = Path(sys.argv[2]); raw.mkdir(parents=True, exist_ok=True)
s = requests.Session(); s.verify = sys.argv[3] if len(sys.argv) > 3 else True
s.headers["User-Agent"] = "FARMLINK-research/0.1"
manifest = []
for name in DATASETS:
    meta = cat.get(name)
    if not meta:
        manifest.append({"dataset": name, "status": "not_in_catalog_search"}); continue
    for i, res in enumerate(meta["resources"]):
        url = res["url"]; fmt = (res["format"] or "").lower()
        if fmt not in ("xlsx", "xls", "csv", "json") and not re.search(r"\.(xlsx?|csv|json)$", url, re.I):
            continue
        ext = (fmt or url.rsplit(".", 1)[-1]).lower()
        fname = f"{name[:80]}__{i}.{ext}"
        entry = {"dataset": name, "title": meta["title"], "publisher": meta["org"],
                 "landing_page": f"https://catalog.data.gov.tn/fr/dataset/{name}",
                 "resource_name": res["name"], "url": url, "format": ext,
                 "resource_modified": res["modified"], "dataset_modified": meta["modified"],
                 "notes": meta["notes"], "file": fname}
        try:
            for a in range(3):
                try:
                    r = s.get(url, timeout=90); break
                except requests.RequestException:
                    if a == 2: raise
                    time.sleep(3)
            r.raise_for_status()
            (raw / fname).write_bytes(r.content)
            entry.update(status="ok", bytes=len(r.content), sha256=hashlib.sha256(r.content).hexdigest(),
                         retrieved_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
        except Exception as e:
            entry.update(status="error", error=str(e)[:200])
        manifest.append(entry); print(entry["status"], fname)
(raw / "_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")

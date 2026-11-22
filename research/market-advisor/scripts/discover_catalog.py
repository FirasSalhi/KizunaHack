"""Search catalog.data.gov.tn (CKAN API) and save dataset metadata for review."""
import json
import sys
import time
from pathlib import Path

import requests

OUT = Path(sys.argv[1])
CA = sys.argv[2] if len(sys.argv) > 2 else True
QUERIES = ["maraicheres", "maraîchères", "agrumes", "prix", "marche de gros", "marché", "fruits",
           "legumes", "productivite", "arboriculture", "pomme de terre", "tomate", "dattes", "olive",
           "apports", "prix a la production", "superficie production", "pasteque", "piment", "oignon",
           "cout de production", "intrants", "engrais", "prix de detail"]
seen = {}
s = requests.Session(); s.verify = CA
for q in QUERIES:
    for start in range(0, 200, 100):
        for attempt in range(3):
            try:
                r = s.get("https://catalog.data.gov.tn/api/3/action/package_search",
                          params={"q": q, "rows": 100, "start": start}, timeout=60)
                d = r.json()["result"]; break
            except Exception as e:
                print("retry", q, e); time.sleep(3)
        else:
            continue
        for p in d["results"]:
            seen[p["name"]] = {
                "name": p["name"], "title": p["title"], "org": (p.get("organization") or {}).get("title"),
                "notes": (p.get("notes") or "")[:300], "modified": p.get("metadata_modified"),
                "resources": [{"name": r.get("name"), "format": r.get("format"), "url": r.get("url"),
                               "modified": r.get("last_modified") or r.get("created")} for r in p["resources"]]}
        if start + 100 >= d["count"]:
            break
    print(q, len(seen))
OUT.write_text(json.dumps(seen, ensure_ascii=False, indent=1), encoding="utf-8")

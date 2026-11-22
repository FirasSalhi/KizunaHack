"""Download INS 'Bulletin Mensuel de la Statistique' PDFs (tables 9.1 retail prices Tunis, 9.5 Tunis wholesale arrivals).

Usage: python download_ins_bulletins.py <out_dir> slug [slug ...]
slug example: juillet-2026
"""
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
s = requests.Session(); s.headers["User-Agent"] = "FARMLINK-research/0.1"
man_path = out / "_manifest.json"
manifest = json.loads(man_path.read_text(encoding="utf-8")) if man_path.exists() else []
done = {m["slug"] for m in manifest if m.get("status") == "ok"}
for slug in sys.argv[2:]:
    if slug in done:
        continue
    page = f"https://www.ins.tn/publication/bulletin-mensuel-de-la-statistique-{slug}"
    entry = {"slug": slug, "landing_page": page, "publisher": "Institut National de la Statistique (INS)",
             "title": f"Bulletin Mensuel de la Statistique, {slug}"}
    try:
        html = s.get(page, timeout=60).text
        m = re.search(r'href="([^"]+\.pdf)"', html)
        if not m:
            raise RuntimeError("no pdf link on page")
        url = m.group(1) if m.group(1).startswith("http") else "https://www.ins.tn" + m.group(1)
        for a in range(3):
            try:
                r = s.get(url, timeout=180); r.raise_for_status(); break
            except requests.RequestException:
                if a == 2: raise
                time.sleep(5)
        fname = f"bms_{slug}.pdf"
        (out / fname).write_bytes(r.content)
        entry.update(status="ok", url=url, file=fname, bytes=len(r.content),
                     sha256=hashlib.sha256(r.content).hexdigest(),
                     retrieved_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    except Exception as e:
        entry.update(status="error", error=str(e)[:200])
    manifest = [m for m in manifest if m["slug"] != slug] + [entry]
    print(entry["status"], slug)
man_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")

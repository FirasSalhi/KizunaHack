"""Re-download every raw source and rebuild the processed tables.

Usage (from research/market-advisor):   python scripts/refresh_data.py [--skip-download]

Steps: data.gov.tn catalogue search + selected datasets, INS bulletins, INS SMAG page, FAOSTAT bulk
files, World Bank CPI, NASA POWER climatology, then `python -m farmlink_market.pipeline`.
catalog.data.gov.tn does not send its intermediate TLS certificate: the script downloads it from
the URL published in the server certificate (AIA) and adds it to certifi's roots, so HTTPS stays verified.
"""
from __future__ import annotations

import hashlib
import json
import ssl
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PY = sys.executable
SCRIPTS = ROOT / "scripts"
# Bulletins whose tables cover Feb 2021 -> Jul 2026 (each table holds 13 months)
BULLETINS = ["juillet-2022", "decembre-2022", "juillet-2023", "decembre-2023", "fevrier-2024", "mars-2024",
             "avril-2024", "juillet-2024", "decembre-2024", "mars-2025", "avril-2025", "mai-2025", "juin-2025",
             "juillet-2025", "aout-2025", "septembre-2025", "octobre-2025", "novembre-2025", "decembre-2025",
             "janvier-2026", "fevrier-2026", "mars-2026", "avril-2026", "mai-2026", "juin-2026", "juillet-2026"]
AIA_FALLBACK = "http://crt.sectigo.com/SectigoPublicServerAuthenticationCADVR36.crt"


def ca_bundle() -> Path:
    import certifi
    url = AIA_FALLBACK
    try:
        from cryptography import x509
        from cryptography.x509.oid import AuthorityInformationAccessOID, ExtensionOID
        leaf = x509.load_pem_x509_certificate(ssl.get_server_certificate(("catalog.data.gov.tn", 443), timeout=15).encode())
        for d in leaf.extensions.get_extension_for_oid(ExtensionOID.AUTHORITY_INFORMATION_ACCESS).value:
            if d.access_method == AuthorityInformationAccessOID.CA_ISSUERS:
                url = d.access_location.value
    except Exception as e:  # cryptography missing or AIA unreadable: use the known issuer URL
        print(f"AIA lookup skipped ({type(e).__name__}), using {url}")
    der = requests.get(url, timeout=30).content
    pem = ssl.DER_cert_to_PEM_cert(der) if not der.lstrip().startswith(b"-----") else der.decode()
    out = ROOT / "data" / "metadata" / "ca_bundle_data_gov_tn.pem"
    out.write_text(Path(certifi.where()).read_text() + "\n" + pem)
    return out


def get(url: str, dest: Path) -> dict:
    r = requests.get(url, timeout=300, headers={"User-Agent": "FARMLINK-research/0.1"})
    r.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(r.content)
    return {"url": url, "file": dest.name, "sha256": hashlib.sha256(r.content).hexdigest(),
            "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}


def run(*args: str) -> None:
    print(">", " ".join(args))
    subprocess.run([PY, *args], check=True, cwd=ROOT)


def main() -> None:
    if "--skip-download" not in sys.argv:
        ca = ca_bundle()
        catalog = ROOT / "data" / "metadata" / "catalog_search_data_gov_tn.json"
        run(str(SCRIPTS / "discover_catalog.py"), str(catalog), str(ca))
        run(str(SCRIPTS / "download_raw.py"), str(catalog), str(RAW / "data_gov_tn"), str(ca))
        run(str(SCRIPTS / "download_ins_bulletins.py"), str(RAW / "ins"), *BULLETINS)
        get("https://www.ins.tn/statistiques/98", RAW / "ins" / "ins_smag_statistiques_98.html")
        files = []
        for f in ("Prices_E_Africa.zip", "Production_Crops_Livestock_E_Africa.zip"):
            files.append(get(f"https://bulks-faostat.fao.org/production/{f}", RAW / "faostat" / f))
        (RAW / "faostat" / "_manifest.json").write_text(json.dumps(
            {"files": [x["file"] for x in files], "urls": [x["url"] for x in files],
             "retrieved_at": files[0]["retrieved_at"], "sha256": {x["file"]: x["sha256"] for x in files}}, indent=1))
        get("https://api.worldbank.org/v2/country/TUN/indicator/FP.CPI.TOTL?format=json&per_page=100",
            RAW / "world_bank" / "TUN_FP.CPI.TOTL.json")
        run(str(SCRIPTS / "download_climate.py"), str(RAW / "nasa_power"))
    run("-m", "farmlink_market.pipeline")


if __name__ == "__main__":
    main()

"""Build an HTML verification page from an executed notebook.
Usage: python -I make_report.py executed.ipynb report.html [reference_executed.ipynb]
Works with any executed version (local or downloaded from Kaggle)."""
import base64, html, json, re, sys
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")
nb_path, out_path = sys.argv[1], sys.argv[2]
ref_path = sys.argv[3] if len(sys.argv) > 3 else None


def load(p):
    nb = json.load(open(p, encoding="utf-8"))
    cells = []
    for i, c in enumerate(nb["cells"]):
        if c["cell_type"] != "code":
            continue
        src = "".join(c["source"])
        text, err, imgs = [], None, []
        for o in c.get("outputs", []):
            t = o.get("output_type")
            if t == "stream":
                text.append("".join(o.get("text", "")))
            elif t == "error":
                err = (o.get("ename", ""), o.get("evalue", ""))
            elif t in ("display_data", "execute_result"):
                d = o.get("data", {})
                if "image/png" in d:
                    imgs.append(d["image/png"] if isinstance(d["image/png"], str) else "".join(d["image/png"]))
                elif "text/plain" in d and "widget" not in "".join(d.keys()):
                    text.append("".join(d["text/plain"]))
        first = next((l.strip("# =—-").strip() for l in src.splitlines() if l.strip() and not l.strip().startswith(("import", "from"))), "")
        cells.append({"idx": i, "src": src, "out": "".join(text), "err": err, "imgs": imgs, "ran": c.get("execution_count") is not None,
                      "title": first[:90]})
    return cells


def all_out(cells):
    return "\n".join(c["out"] for c in cells)


def find(cells, pattern):
    for c in cells:
        if re.search(pattern, c["src"]):
            return c
    return None


def checks(cells):
    O = all_out(cells)
    R = []

    def add(group, name, status, detail):
        R.append({"group": group, "name": name, "status": status, "detail": detail})

    # execution
    n_err = sum(1 for c in cells if c["err"])
    n_run = sum(1 for c in cells if c["ran"])
    add("Exécution", "Toutes les cellules exécutées", "ok" if n_run == len(cells) else "fail", f"{n_run}/{len(cells)} cellules de code exécutées")
    add("Exécution", "Aucune erreur Python", "ok" if n_err == 0 else "fail",
        "0 erreur" if n_err == 0 else "; ".join(f"cellule {c['idx']}: {c['err'][0]}" for c in cells if c["err"]))

    # security / data
    if "TLS verification ON" in O:
        add("Données & sécurité", "Vérification TLS (HTTPS) active", "ok", "certificat de catalog.data.gov.tn vérifié (intermédiaire ajouté)")
    elif "verify=False" in "".join(c["src"] for c in cells):
        add("Données & sécurité", "Vérification TLS (HTTPS) active", "fail", "le code utilise verify=False (vérification désactivée)")
    else:
        add("Données & sécurité", "Vérification TLS (HTTPS) active", "warn", "chaîne TLS non vérifiée dans cette exécution")
    m = re.search(r"DATA_PROVENANCE = (\S+)", O)
    prov = m.group(1) if m else "inconnu"
    add("Données & sécurité", "Provenance des données capteurs", "ok" if prov == "REAL_DGACTA" else ("warn" if prov.startswith("REAL") else "fail"), prov)
    c10 = find(cells, r"ACQ_ROWS, NEW_MANIFEST")
    if c10:
        failed = c10["out"].count("PACKAGE_FAILED")
        add("Données & sécurité", "Téléchargement DGACTA vérifié (5 stations)", "ok" if failed == 0 else "fail",
            "toutes les stations lues" if failed == 0 else "PACKAGE_FAILED présent dans le rapport d'acquisition")
    m = re.search(r"Total Records Extracted & Classified: ([\d,]+)", O)
    dup = re.search(r"Removed ([\d,]+) exact duplicate", O)
    ign = re.search(r"(\d+) CSV file\(s\) in DATA_DIR are not in the manifest", O)
    detail = f"{m.group(1) if m else '?'} mesures classées"
    if dup: detail += f"; {dup.group(1)} doublons supprimés"
    if ign: detail += f"; {ign.group(1)} fichiers en double ignorés"
    has_fix = "drop_duplicates(subset=[c for c in ['station'" in "".join(c["src"] for c in cells)
    add("Données & sécurité", "Pas de double comptage des fichiers", "ok" if has_fix else "warn", detail + ("" if has_fix else " (aucune déduplication dans le code)"))
    m = re.search(r"Dimensions: (\d+) timestamps", O)
    r = re.search(r"Observed Time Range: (.+)", O)
    add("Données & sécurité", "Série horaire Chott Meriam", "ok" if m else "fail", f"{m.group(1)} heures | {r.group(1).strip()}" if m and r else "absente")

    # weather
    m = re.search(r"Weather source used: (\S+) \| fallback used: (\S+)", O)
    add("Météo", "Source météo du moteur", "ok" if m else "fail", f"{m.group(1)} (secours utilisé : {m.group(2)})" if m else "aucune source")
    c46 = find(cells, r"ELEVATION_M = ")
    if c46:
        lm = re.search(r"Last valid ETo: ([\d.]+) mm/day on (\S+)\s+\| source: (\S+)", c46["out"])
        hs = re.search(r"Hargreaves_Samani\(fallback\)\s+(\d+)", c46["out"])
        lag = re.search(r"weather is (\d+) day\(s\) older", O)
        st = "ok"
        det = f"ET₀ = {lm.group(1)} mm/j le {lm.group(2)} ({lm.group(3)})" if lm else "ET₀ indisponible"
        if lag and int(lag.group(1)) > 1:
            st = "warn"; det += f" — météo en retard de {lag.group(1)} jour(s) sur le capteur"
        elif lag:
            det += f" — retard {lag.group(1)} j"
        add("Météo", "ET₀ récente pour la recommandation", st if lm else "fail", det)
        pm = re.search(r"FAO56_Penman_Monteith\s+(\d+)", c46["out"])
        add("Météo", "Méthode ET₀ (Penman-Monteith)", "ok" if (pm and not hs) else "warn",
            f"Penman-Monteith : {pm.group(1) if pm else 0} j, Hargreaves (secours) : {hs.group(1) if hs else 0} j")

    # models
    m = re.search(r"Winning Forecasting Model: (.+?) \(MAE = ([\d.]+) %, R² = ([\-\d.]+)\)", O)
    add("Modèles", "Sélection honnête du modèle (1 h)", "ok" if m else "fail", f"{m.group(1)} — MAE {m.group(2)} %, R² {m.group(3)}" if m else "absent")
    add("Modèles", "Rechargement du modèle (processus neuf)", "ok" if "Subprocess load test SUCCESS" in O else "fail", "best_model.pkl rechargé" if "Subprocess load test SUCCESS" in O else "échec")
    if "INSUFFICIENT_DATA" in O:
        add("Modèles", "Prédicteur ridge (12L)", "info", "INSUFFICIENT_DATA : moins de 200 heures continues ; la persistance reste la réponse")

    # tests
    m = re.search(r"Ran (\d+) tests in [\d.]+s\s*\n\s*\n?OK", O)
    add("Tests", "Tests unitaires du module irrigation", "ok" if m else "fail", f"{m.group(1)} tests OK" if m else "échec ou absents")
    m2 = re.search(r"FRESH-PROCESS TESTS \(package dir\): (\w+)\s+\['Ran (\d+) tests", O)
    add("Tests", "Tests du paquet FARMLINK (processus neuf)", "ok" if m2 and m2.group(1) == "PASS" else "fail", f"{m2.group(2)} tests — {m2.group(1)}" if m2 else "absent")
    m3 = re.search(r"TESTS INSIDE UNZIPPED ZIP.*?: (\w+)", O)
    add("Tests", "Tests depuis le ZIP décompressé", "ok" if m3 and m3.group(1) == "PASS" else "fail", m3.group(1) if m3 else "absent")
    m4 = re.search(r"FRESH-PROCESS END-TO-END: (\S+)", O)
    add("Tests", "Exemple ferme de bout en bout", "ok" if m4 and m4.group(1) == "E2E_OK" else "fail", m4.group(0).split(": ", 1)[1] if m4 else "absent")
    add("Tests", "Export vérifié", "ok" if "EXPORT VERIFIED" in O else "fail", "ZIP + manifeste OK" if "EXPORT VERIFIED" in O else "absent")

    # decisions
    conf = re.search(r"Readiness: (\S+) \| confidence: (\S+)", O)
    conflict = "physically inconsistent with the declared soil" in O
    if conf:
        st = "warn" if conflict and conf.group(2) == "LOW" else ("info")
        det = f"readiness {conf.group(1)}, confiance {conf.group(2)}"
        if conflict: det += " — capteur sous le point de flétrissement déclaré"
        add("Décisions", "Démo irrigation (tomate)", st, det)
    a = re.search(r"Available ([\d.]+) m3 \| allocated ([\d.]+) m3", O)
    cov = re.search(r"available water covers (\d+) %", O)
    if a:
        st = "ok" if cov and int(cov.group(1)) >= 10 else "warn"
        add("Décisions", "Exemple d'eau limitée", st, f"{a.group(1)} m³ disponibles, {a.group(2)} m³ alloués" + (f" ({cov.group(1)} % du besoin)" if cov else " (part du besoin non affichée)"))
    nd = re.search(r"NEEDS_DATA:\s*\n\s*- (.+)", O)
    if nd:
        add("Décisions", "Zones sans données refusées", "ok", nd.group(1).strip())
    return R


cells = load(nb_path)
R = checks(cells)
REF = {(r["group"], r["name"]): r for r in checks(load(ref_path))} if ref_path else {}
counts = {k: sum(1 for r in R if r["status"] == k) for k in ("ok", "warn", "fail", "info")}
verdict = "fail" if counts["fail"] else ("warn" if counts["warn"] else "ok")
VERDICT_TXT = {"ok": "Tout est bon", "warn": "Fonctionne, avec des points à surveiller", "fail": "Des contrôles échouent"}[verdict]
LABEL = {"ok": "OK", "warn": "Attention", "fail": "Échec", "info": "Info"}
ICON = {"ok": "✓", "warn": "!", "fail": "✕", "info": "i"}
E = html.escape

rows, group = [], None
for r in R:
    if r["group"] != group:
        group = r["group"]; rows.append(f'<tr class="grp"><th colspan="{4 if REF else 3}">{E(group)}</th></tr>')
    ref = REF.get((r["group"], r["name"]))
    refcell = (f'<td><span class="pill {ref["status"]}" title="{E(ref["detail"])}">{ICON[ref["status"]]} {LABEL[ref["status"]]}</span></td>' if ref else '<td><span class="muted">—</span></td>') if REF else ""
    rows.append(f'<tr><td>{E(r["name"])}</td>{refcell}<td><span class="pill {r["status"]}">{ICON[r["status"]]} {LABEL[r["status"]]}</span></td><td class="det">{E(r["detail"])}</td></tr>')

cell_rows = []
for c in cells:
    st = "fail" if c["err"] else ("ok" if c["ran"] else "warn")
    out = c["out"].strip()
    body = E(out[-6000:]) if out else '<span class="muted">(pas de sortie texte)</span>'
    if c["err"]:
        body = f'<div class="errbox">{E(c["err"][0])}: {E(c["err"][1][:600])}</div>' + body
    imgs = "".join(f'<img loading="lazy" alt="figure cellule {c["idx"]}" src="data:image/png;base64,{im}">' for im in c["imgs"])
    cell_rows.append(f'<details class="cell {st}"><summary><span class="pill {st}">{ICON[st]}</span> <b>Cellule {c["idx"]}</b> <span class="muted">{E(c["title"])}</span>'
                     f'{" · " + str(len(c["imgs"])) + " figure(s)" if c["imgs"] else ""}</summary><pre>{body}</pre>{imgs}</details>')

page = f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Vérification FARMLINK</title>
<style>
:root{{--bg:#f7f7f5;--card:#fff;--ink:#1b1b1a;--muted:#6b6a66;--line:#e4e3df;
--ok:#1a7f4b;--ok-bg:#e6f4ec;--warn:#9a5b00;--warn-bg:#fdf1dc;--fail:#b3261e;--fail-bg:#fbe7e5;--info:#2a5db0;--info-bg:#e7eefb}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#151514;--card:#1f1f1d;--ink:#ecebe8;--muted:#a3a29d;--line:#33322f;
--ok:#5fd394;--ok-bg:#183626;--warn:#f0b65a;--warn-bg:#3a2b12;--fail:#ff8a80;--fail-bg:#3d1a18;--info:#8fb4ff;--info-bg:#1a2742}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}}
main{{max-width:1080px;margin:0 auto;padding:28px 16px 60px}}h1{{font-size:24px;margin:0 0 4px}}h2{{font-size:18px;margin:32px 0 12px}}
.muted{{color:var(--muted)}}.hero{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px;margin-top:16px;display:flex;gap:18px;align-items:center;flex-wrap:wrap}}
.big{{font-size:20px;font-weight:700}}.badge{{width:54px;height:54px;border-radius:50%;display:grid;place-items:center;font-size:26px;font-weight:700}}
.badge.ok{{background:var(--ok-bg);color:var(--ok)}}.badge.warn{{background:var(--warn-bg);color:var(--warn)}}.badge.fail{{background:var(--fail-bg);color:var(--fail)}}
.stats{{display:flex;gap:10px;flex-wrap:wrap;margin-left:auto}}.stat{{border:1px solid var(--line);border-radius:10px;padding:6px 12px;text-align:center;min-width:76px}}.stat b{{display:block;font-size:20px}}
.wrap{{overflow-x:auto;background:var(--card);border:1px solid var(--line);border-radius:14px}}
table{{width:100%;border-collapse:collapse}}td,th{{padding:9px 12px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}}
tr.grp th{{background:var(--bg);font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}}
thead th{{font-size:13px;color:var(--muted)}}.det{{color:var(--muted);font-size:14px}}
.pill{{display:inline-block;padding:1px 9px;border-radius:99px;font-size:12px;font-weight:600;white-space:nowrap}}
.pill.ok{{background:var(--ok-bg);color:var(--ok)}}.pill.warn{{background:var(--warn-bg);color:var(--warn)}}.pill.fail{{background:var(--fail-bg);color:var(--fail)}}.pill.info{{background:var(--info-bg);color:var(--info)}}
details.cell{{background:var(--card);border:1px solid var(--line);border-radius:10px;margin:8px 0;padding:8px 12px}}details.cell.fail{{border-color:var(--fail)}}
summary{{cursor:pointer}}pre{{white-space:pre-wrap;word-break:break-word;font:12.5px/1.45 ui-monospace,Consolas,monospace;background:var(--bg);padding:10px;border-radius:8px;max-height:420px;overflow:auto}}
img{{max-width:100%;border-radius:8px;margin-top:8px;background:#fff}}.errbox{{color:var(--fail);font-weight:600;margin-bottom:6px}}
.filters{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px}}button{{font:inherit;border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:8px;padding:4px 10px;cursor:pointer}}button.on{{border-color:var(--ink)}}
</style></head><body><main>
<h1>Vérification du notebook FARMLINK</h1>
<div class="muted">Fichier analysé : {E(nb_path.replace(chr(92), '/').split('/')[-1])} · rapport généré le {datetime.now():%d/%m/%Y %H:%M}{(" · comparé à : " + E(ref_path.replace(chr(92), '/').split('/')[-1])) if ref_path else ""}</div>
<div class="hero"><div class="badge {verdict}">{ICON[verdict]}</div><div><div class="big">{VERDICT_TXT}</div>
<div class="muted">{len(R)} contrôles automatiques sur les sorties réelles du notebook</div></div>
<div class="stats"><div class="stat"><b style="color:var(--ok)">{counts['ok']}</b>OK</div><div class="stat"><b style="color:var(--warn)">{counts['warn']}</b>Attention</div>
<div class="stat"><b style="color:var(--fail)">{counts['fail']}</b>Échec</div><div class="stat"><b style="color:var(--info)">{counts['info']}</b>Info</div></div></div>
<h2>Contrôles</h2>
<div class="wrap"><table><thead><tr><th>Contrôle</th>{"<th>Avant</th><th>Après</th>" if REF else "<th>Résultat</th>"}<th>Détail</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<h2>Détail des cellules ({len(cells)} cellules de code)</h2>
<div class="filters"><button class="on" data-f="all">Toutes</button><button data-f="fail">Erreurs</button><button data-f="img">Avec figures</button></div>
<div id="cells">{''.join(cell_rows)}</div>
<p class="muted" style="margin-top:28px">Rappel : les volumes d'irrigation restent illustratifs (capteurs non calibrés, sol de Chott Meriam non documenté). Ces contrôles vérifient que le code tourne et que ses sorties sont cohérentes, pas la validité agronomique sur le terrain.</p>
</main><script>
document.querySelectorAll('.filters button').forEach(b=>b.onclick=()=>{{document.querySelectorAll('.filters button').forEach(x=>x.classList.remove('on'));b.classList.add('on');
const f=b.dataset.f;document.querySelectorAll('details.cell').forEach(d=>{{d.style.display=(f==='all'||(f==='fail'&&d.classList.contains('fail'))||(f==='img'&&d.querySelector('img')))?'':'none'}})}});
</script></body></html>"""
open(out_path, "w", encoding="utf-8").write(page)
print(f"verdict={verdict} {counts} -> {out_path}")
for r in R:
    print(f"  [{r['status']:4}] {r['group']} | {r['name']}: {r['detail']}")

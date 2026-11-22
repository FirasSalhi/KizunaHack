"""Compatibilité entre cultures.

Règles, dans l'ordre :
1. Relation connue et sourcée (guides de vulgarisation, littérature d'association, systèmes oasiens).
   Une incompatibilité connue l'emporte toujours.
2. Même famille botanique → déconseillé (ravageurs et maladies partagés).
3. Règles physiques : besoins en eau proches, racines à profondeurs différentes,
   hauteur/lumière, chevauchement des cycles.
"""
import csv
from pathlib import Path

from .i18n import crop_name, family, mechanism, t

CONF = {"high": 1.0, "medium": 0.7, "low": 0.4}
DATA = Path(__file__).resolve().parent.parent / "data" / "companions.csv"


def load_known():
    with open(DATA, encoding="utf-8") as f:
        return {(r["crop_a"], r["crop_b"]): r for r in csv.DictReader(f)}


KNOWN = load_known()


def _months(sow, n):
    return {((sow - 1 + d // 30) % 12) + 1 for d in range(0, max(n, 1), 15)}


def pair(a, b, sow_a=None, sow_b=None):
    """a, b : fiches cultures (crops.json). sow_* : mois de semis retenus."""
    rel = KNOWN.get((a["id"], b["id"])) or KNOWN.get((b["id"], a["id"]))
    s, why = 0.0, []
    if rel:
        w = CONF[rel["confidence"]]
        s += {"beneficial": 0.55 * w, "antagonist": -0.7 * w}.get(rel["relation"], 0.0)
        why.append(mechanism(rel["mechanism"]))
    same_family = a["family"] == b["family"]
    if same_family and not (rel and rel["relation"] == "beneficial"):
        s -= 0.35
        why.append(t("co.same_family", fam=family(a["family"])))
    sim = max(0.0, 1 - abs(a["kc_mid"] - b["kc_mid"]) / 0.5)
    s += 0.15 * sim
    if sim < 0.4:
        why.append(t("co.water_diff"))
    if abs(a["root_depth_m"] - b["root_depth_m"]) >= 0.4:
        s += 0.1
        why.append(t("co.roots"))
    tall, low = (a, b) if a["height_m"] >= b["height_m"] else (b, a)
    if tall["height_m"] >= 2.5 * low["height_m"]:
        if low["light_need"] == "medium" or tall["type"] == "perennial":
            s += 0.1
            why.append(t("co.shade_ok", low=crop_name(low), tall=crop_name(tall)))
        else:
            s -= 0.1
            why.append(t("co.shade_bad", tall=crop_name(tall), low=crop_name(low)))
    overlap = None
    if sow_a and sow_b:
        ma = _months(sow_a, 365 if a["type"] == "perennial" else a["l_ini"] + a["l_dev"] + a["l_mid"] + a["l_late"])
        mb = _months(sow_b, 365 if b["type"] == "perennial" else b["l_ini"] + b["l_dev"] + b["l_mid"] + b["l_late"])
        overlap = len(ma & mb) / max(1, min(len(ma), len(mb)))
        if overlap < 0.3:
            s *= 0.3
            why.append(t("co.no_overlap"))
    s = max(-1.0, min(1.0, s))
    if rel and rel["relation"] == "antagonist":
        s = min(s, -0.2)
    rel_code = "with" if s >= 0.35 else "avoid" if s < -0.1 else "neutral"
    if rel and rel["relation"] == "antagonist":
        rel_code = "avoid"  # une incompatibilité connue l'emporte toujours
    return {"score": round(s * 100), "relation": rel_code, "reasons": why,
            "known": bool(rel) and rel["relation"] == "beneficial",
            "source": rel["source"] if rel else t("co.generic_src"),
            "confidence": t("conf." + (rel["confidence"] if rel else "low")),
            "season_overlap_pct": None if overlap is None else round(overlap * 100)}


def best_pair(a, b, months_a, months_b):
    """Évalue la paire pour toutes les combinaisons de mois de semis et garde la meilleure."""
    best = None
    for ma in months_a or [None]:
        for mb in months_b or [None]:
            r = pair(a, b, ma, mb)
            if best is None or r["score"] > best["score"]:
                best = r
    return best


def companions_for(cid, crops, candidates, sow=None, country=None):
    a = crops[cid]
    out = []
    for other in candidates:
        if other == cid:
            continue
        if country:
            r = best_pair(a, crops[other], a["sowing_months"].get(country), crops[other]["sowing_months"].get(country))
        else:
            r = pair(a, crops[other], (sow or {}).get(cid), (sow or {}).get(other))
        out.append({"crop": other, "name": crop_name(crops[other]), **r})
    out.sort(key=lambda x: -x["score"])
    return {"crop": cid, "name": crop_name(a),
            "with": [x for x in out if x["relation"] == "with"],
            "avoid": [x for x in out if x["relation"] == "avoid"]}

"""Combinaisons sur le même hectare : faisabilité sur la parcelle + causes (3 langues)."""
import json
from pathlib import Path

from .i18n import crop_name, lang, t


def _num(x):
    return str(x).replace(".", ",") if lang() in ("fr", "tn") else str(x)

DATA = Path(__file__).resolve().parent.parent / "data" / "combos.json"
COMBOS = json.loads(DATA.read_text(encoding="utf-8"))
CONF_W = {"high": 1.0, "medium": 0.9, "low": 0.75}


def _tx(d):
    return d.get(lang()) or d["fr"]


SHARE = {"top": 1.0, "middle": 0.5, "low": 0.5, "first": 1.0, "then": 1.0}


def _agronomic(r):
    """Adéquation sans le facteur eau : climat × sol × sel × (1 − risque). L'eau est jugée à part,
    car en association la culture basse n'occupe qu'une partie de l'hectare."""
    f = r["factors"]
    return round(f["climat"] * f["sol"] * f["sel"] / 1e4 * (1 - 0.8 * f["risque"] / 100))


def evaluate(country, crops, ranking_irrigated, ranking_rainfed, water_source, water_m3=None, area_ha=None):
    by_irr = {r["crop"]: r for r in (ranking_irrigated or [])}
    by_dry = {r["crop"]: r for r in (ranking_rainfed or [])}
    rainfed_mode = water_source == "pluie"
    out = []
    for c in COMBOS:
        if country not in c["countries"]:
            continue
        feasible, why_not = True, None
        if rainfed_mode and c["water"] == "irrigated":
            feasible, why_not = False, t("cb.needs_irrig")
        members, scores, need = [], [], 0.0
        lows = sum(1 for m in c["members"] if m["role"] == "low")
        for m in c["members"]:
            r = (by_dry if rainfed_mode else by_irr).get(m["crop"]) or by_dry.get(m["crop"])
            sc = 0 if not r else (r["score"] if rainfed_mode else _agronomic(r))
            scores.append(sc)
            share = SHARE[m["role"]] / (lows if m["role"] == "low" and lows > 1 else 1)
            w = None if (not r or rainfed_mode) else r["water_m3_ha_typical"]
            if w and by_dry.get(m["crop"]):
                # une plante qui tient en partie en sec n'a besoin que du complément d'irrigation
                w = round(w * (1 - by_dry[m["crop"]]["factors"]["eau"] / 100), -1)
            if w:
                need += w * share
            members.append({"crop": m["crop"], "name": crop_name(crops[m["crop"]]), "role": m["role"],
                            "role_label": t("cb.role." + m["role"]), "score": sc, "share_pct": round(share * 100),
                            "water_m3_ha": w})
        weakest = min(members, key=lambda m: m["score"])
        if feasible and weakest["score"] < 30:
            feasible, why_not = False, t("cb.weak_member", crop=weakest["name"], s=weakest["score"])
        base = 0.6 * max(scores) + 0.4 * (sum(scores) / len(scores))
        water_note, ha_possible = None, None
        if not rainfed_mode and need > 0:
            if water_m3:
                ha_possible = round(min(area_ha or 1e9, water_m3 / need), 1)
                water_note = t("cb.water_ok", need=f"{round(need, -1):,.0f}".replace(",", " ")) if ha_possible >= (area_ha or 0) \
                    else t("cb.water_part", need=f"{round(need, -1):,.0f}".replace(",", " "), ha=_num(ha_possible))
            else:
                water_note = t("cb.water_need", need=f"{round(need, -1):,.0f}".replace(",", " "))
        fit = round(base * CONF_W[c["confidence"]] * (1 if feasible else 0.4))
        out.append({
            "id": c["id"], "members": members, "fit": fit, "feasible": feasible, "why_not": why_not,
            "water": c["water"], "water_label": t("cb.water." + c["water"]),
            "water_need_m3_ha": None if rainfed_mode else round(need, -1), "water_note": water_note, "ha_possible": ha_possible,
            "causes": [{"type": x["type"], "type_label": t("cb.cause." + x["type"]), "text": _tx(x)} for x in c["causes"]],
            "cautions": [_tx(x) for x in c["cautions"]], "layout": _tx(c["layout"]),
            "confidence": c["confidence"], "confidence_label": t("conf." + c["confidence"]),
            "sources": c["sources"], "title": " + ".join(m["name"] for m in members),
        })
    out.sort(key=lambda x: (not x["feasible"], -x["fit"]))
    return out


def catalogue(country, crops):
    return [{"id": c["id"], "title": " + ".join(crop_name(crops[m["crop"]]) for m in c["members"]),
             "members": [m["crop"] for m in c["members"]], "water": c["water"],
             "causes": [{"type": x["type"], "type_label": t("cb.cause." + x["type"]), "text": _tx(x)} for x in c["causes"]],
             "cautions": [_tx(x) for x in c["cautions"]], "layout": _tx(c["layout"]),
             "confidence": c["confidence"], "confidence_label": t("conf." + c["confidence"]), "sources": c["sources"]}
            for c in COMBOS if country in c["countries"]]

"""Mesure de la précision du modèle par gouvernorat (Tunisie).

Principe : si le modèle est juste, les cultures qu'il juge les mieux adaptées dans un gouvernorat
doivent être celles que les agriculteurs y produisent réellement.

1. Remplissez validation/verite_terrain_tunisie.csv à partir des statistiques officielles
   (catalog.agridata.tn : « Production végétale » / « Exploitation des terres » par gouvernorat).
   Colonnes : gouvernorat, culture (identifiant MIZU, ex. olive, tomato, durum_wheat), surface_ha
2. Lancez :  python validate.py          (avec internet : vraie météo NASA POWER et sol SoilGrids)
3. Résultat : validation/rapport_validation.csv + indicateurs affichés.

Indicateurs :
- précision top-5 : part des 5 cultures les mieux notées qui figurent parmi les 10 plus cultivées du gouvernorat ;
- corrélation de Spearman entre le score du modèle et la surface réellement cultivée.
Aucun chiffre n'est fourni ici : la vérité terrain doit venir des statistiques officielles.
"""
import csv
import math
import sys
from collections import defaultdict
from pathlib import Path

from scipy.stats import spearmanr

from engine.climate import load_history
from engine.core import CROPS
from engine.soil import get_soil
from engine.suitability import rank

GOUVERNORATS = {  # centre approximatif des zones agricoles
    "Tunis": (36.80, 10.10), "Ariana": (36.95, 10.15), "Ben Arous": (36.65, 10.25), "Manouba": (36.80, 9.95),
    "Nabeul": (36.60, 10.65), "Zaghouan": (36.35, 10.10), "Bizerte": (37.10, 9.70), "Béja": (36.70, 9.20),
    "Jendouba": (36.55, 8.70), "Le Kef": (36.10, 8.75), "Siliana": (36.05, 9.35), "Sousse": (35.80, 10.50),
    "Monastir": (35.65, 10.75), "Mahdia": (35.35, 10.80), "Sfax": (34.75, 10.55), "Kairouan": (35.60, 9.95),
    "Kasserine": (35.25, 8.80), "Sidi Bouzid": (34.95, 9.45), "Gabès": (33.85, 9.95), "Médenine": (33.40, 10.70),
    "Tataouine": (32.95, 10.30), "Gafsa": (34.40, 8.75), "Tozeur": (33.90, 8.15), "Kébili": (33.65, 8.95),
}
VAL = Path(__file__).resolve().parent / "validation"
TRUTH = VAL / "verite_terrain_tunisie.csv"


def main(online=True):
    if not TRUTH.exists():
        sys.exit(f"Fichier manquant : {TRUTH}")
    truth = defaultdict(dict)
    with open(TRUTH, encoding="utf-8") as f:
        for r in csv.DictReader(r for r in f if not r.startswith("#")):
            if r["culture"] in CROPS and r.get("surface_ha"):
                truth[r["gouvernorat"]][r["culture"]] = float(r["surface_ha"])
    if not truth:
        sys.exit("La vérité terrain est vide : remplissez-la depuis Agridata.tn avant de lancer la validation.")
    rows, precs, rhos = [], [], []
    for gov, crops_real in truth.items():
        if gov not in GOUVERNORATS:
            print(f"! gouvernorat inconnu ignoré : {gov}")
            continue
        lat, lon = GOUVERNORATS[gov]
        h = load_history(lat, lon, online)
        soil = get_soil(lat, lon, None, online, "tunisie")
        ranking = rank(h, CROPS, "tunisie", soil, None, "non", 0.85)
        scores = {r["crop"]: r["score"] for r in ranking}
        top_model = [r["crop"] for r in ranking[:5]]
        top_real = sorted(crops_real, key=lambda c: -crops_real[c])[:10]
        prec = sum(c in top_real for c in top_model) / 5
        common = [c for c in crops_real if c in scores]
        rho = spearmanr([scores[c] for c in common], [math.log1p(crops_real[c]) for c in common]).statistic if len(common) >= 4 else float("nan")
        precs.append(prec)
        if not math.isnan(rho):
            rhos.append(rho)
        rows.append({"gouvernorat": gov, "precision_top5": round(prec, 2), "spearman": None if math.isnan(rho) else round(rho, 2),
                     "top5_modele": " | ".join(CROPS[c]["name_fr"] for c in top_model),
                     "top5_reel": " | ".join(CROPS[c]["name_fr"] for c in top_real[:5]),
                     "meteo": "démo" if h["demo"] else "NASA POWER", "sol": soil["source"][:30]})
        print(f"{gov:12} précision top-5 {prec:.0%}  Spearman {rho:+.2f}")
    with open(VAL / "rapport_validation.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    print(f"\nPrécision top-5 moyenne : {sum(precs)/len(precs):.0%} sur {len(precs)} gouvernorats")
    if rhos:
        print(f"Corrélation de Spearman moyenne : {sum(rhos)/len(rhos):+.2f}")
    if any(r["meteo"] == "démo" for r in rows):
        print("ATTENTION : météo de démonstration utilisée (pas d'internet) → ces chiffres ne valent rien.")


if __name__ == "__main__":
    main(online="--offline" not in sys.argv)

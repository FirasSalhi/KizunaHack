# Irrigation FARMLINK : guide rapide

Ce dossier dit à un agriculteur **quelles parcelles arroser, quand, et combien d'eau donner**.
Il s'appuie sur de vraies mesures de capteurs de sol (ministère de l'Agriculture, DGACTA), la météo
et la méthode de la FAO (FAO-56).

Il est indépendant du reste du projet : `apps/web` et `services/api` ne l'utilisent pas, et la CI ne le lit pas.

## Pour voir le résultat en 2 minutes

Ouvrez ces fichiers dans un navigateur (double-clic). Il faut une connexion Internet pour la 3D et les polices.

| Fichier | Ce que c'est |
|---|---|
| `html/ferme_3d.html` | **La ferme en 3D pour l'agriculteur.** On ajoute ou supprime ses parcelles, on choisit ses plantes, et chaque champ montre s'il faut arroser (drapeau rouge, orange ou vert). Mode « Promenade » pour marcher dans la ferme. |
| `html/banc_essai.html` | **Le banc d'essai** : un onglet par module (capteurs, météo, prévision, calcul d'irrigation, ferme, tests). |
| `html/rapport_verification.html` | Les contrôles automatiques du notebook, avant et après corrections. |

Dans la ferme 3D, les modifications ne sont pas enregistrées : un rechargement revient à la ferme d'exemple.

## Ce qu'il y a dans le dossier

| Dossier | Contenu |
|---|---|
| `notebooks/` | `farmlink_irrigation_kaggle.ipynb` = **le notebook à lancer**. `..._executed` = déjà exécuté avec ses résultats. `..._original_v3` = l'ancienne version. |
| `package/FARMLINK_Module5_Deliverables/` | **Le moteur réutilisable** (Python) : décision d'irrigation, 39 cultures, priorités, partage de l'eau. C'est la partie à brancher dans l'API. |
| `models/` | Le modèle de prévision sauvegardé (`best_model.pkl`, c'est la « persistance »). |
| `results/`, `data/` | Résultats CSV et figures de l'exécution du 21/11/2026, et les données téléchargées. |
| `scripts/` | Scripts qui fabriquent les corrections et les pages HTML (à utiliser seulement pour les modifier). |

## Lancer le notebook

1. Sur Kaggle : importer `notebooks/farmlink_irrigation_kaggle.ipynb`.
2. Dans *Session options*, mettre **Internet sur ON**.
3. *Run all*. Compter quelques minutes : téléchargement des données, puis tests.

## Utiliser le moteur dans un autre code

Il faut seulement `numpy`, `pandas` et `requests`.

```python
import sys
sys.path.insert(0, "research/irrigation-notebook/package/FARMLINK_Module5_Deliverables")
from engine.data_sources import fetch_weather
from engine.farm_runner import run_farm

meteo, prov = fetch_weather(35.918, 10.558, "2026-10-20", "2026-11-21")   # Open-Meteo, sinon NASA POWER
ferme = {
  "farm_id": "ma_ferme",
  "location": {"lat": 35.918, "lon": 10.558, "elevation_m": 10},
  "zones": [{
    "zone_id": "A", "crop": "tomate", "area_ha": 1.5, "planting_date": "2026-10-01",
    "soil": {"fc": 0.25, "wp": 0.11},          # capacité au champ / point de flétrissement
    "irrigation": {"method": "drip"},           # drip, sprinkler ou surface
    "current_depletion_mm": 45                  # eau déjà consommée depuis le dernier arrosage
  }]
}
resultat = run_farm(ferme, meteo, "2026-11-18", weather_source=prov["source_used"], available_water_m3=500)
print(resultat["zones"][0]["timing"], resultat["zones"][0]["volumes"])   # ex. irrigate_now, 750 m³
```

`resultat` est un dictionnaire prêt à être renvoyé en JSON : décision par parcelle, volumes,
classement des priorités et partage de l'eau disponible. Le format complet est dans
`package/FARMLINK_Module5_Deliverables/api/api_schema.json`.

## Les règles à connaître

- **Pas de type de sol = pas de volume.** Le moteur n'invente jamais une donnée manquante : la parcelle est marquée « données manquantes ».
- **Les volumes sont des estimations.** Les capteurs de Chott Meriam ne sont pas calibrés et rien n'a encore été validé sur une vraie ferme.
- **La prévision d'humidité est la persistance** (« demain comme aujourd'hui ») : avec 8 jours de données, elle bat Random Forest et Gradient Boosting.
- **La météo vient d'Open-Meteo.** Si ce service ne répond pas, NASA POWER prend le relais, avec 2 à 3 jours de retard.

## Ce qui a été corrigé dans le notebook (v3.1)

1. HTTPS vérifié vers data.gov.tn : il n'y a plus de `verify=False`.
2. Les fichiers comptés en double sont supprimés : 2 368 mesures réelles au lieu de 4 648.
3. L'ET₀ est calculée avec la météo la plus récente.
4. La confiance baisse quand un capteur contredit le sol.
5. L'exemple d'eau limitée est réaliste : 1 500 m³.
6. Les textes et la provenance des données sont honnêtes.
7. Le notebook ne reste plus bloqué quand Open-Meteo dépasse son quota (erreur 429).

## Modifier les pages HTML

```bash
# ferme 3D : éditer scripts/ferme_3d/template.html, puis
cd scripts/ferme_3d && python build.py        # écrit farmlink_ferme_3d.html et preview.html
cp preview.html ../../html/ferme_3d.html

# rapport de vérification d'un notebook exécuté
python scripts/make_report.py notebooks/farmlink_irrigation_executed.ipynb rapport.html
```

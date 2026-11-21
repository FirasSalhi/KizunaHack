# Notebook d'irrigation FARMLINK (Module 5)

Notebook « Tunisian Smart Crop Monitoring & Irrigation Intelligence », version corrigée (v3.1),
avec les résultats d'une exécution complète du 21/11/2026, le modèle sauvegardé et deux pages HTML
pour vérifier et tester chaque module.

Ce dossier est indépendant du reste du monorepo : il n'est pas utilisé par `apps/web` ni par
`services/api`, et la CI ne le lit pas.

## Contenu

| Dossier | Contenu |
|---|---|
| `notebooks/farmlink_irrigation_kaggle.ipynb` | **Notebook à lancer sur Kaggle** (corrigé, sorties vidées). Activer *Internet* dans *Session options*. |
| `notebooks/farmlink_irrigation_executed.ipynb` | Le même notebook exécuté en entier le 21/11/2026 (sorties et figures incluses). |
| `notebooks/farmlink_irrigation_original_v3.ipynb` | Version d'origine (v3), avant corrections, avec ses sorties Kaggle. |
| `results/` | Résultats CSV/JSON de l'exécution et `figures/` (7 tableaux de bord PNG). |
| `data/` | Données téléchargées : capteurs DGACTA des 5 stations (`tunisia/`), série horaire de Chott Meriam, météo NASA POWER, manifeste des sources. |
| `models/` | `best_model.pkl` (modèle retenu : persistance) et `persistence_predictor.py` (classe nécessaire pour le recharger). |
| `package/` | Paquet FARMLINK (`engine/`, base de 39 cultures, API JSON, 82 tests) et son ZIP, plus le module `irrigation/` du notebook et ses 51 tests. |
| `html/banc_essai.html` | **Interface de test** : capteurs, météo et ET₀, prévision, calcul d'irrigation, ferme, tests. S'ouvre directement dans un navigateur. |
| `html/rapport_verification.html` | Rapport automatique avant / après corrections (21 contrôles). |
| `scripts/` | Scripts qui ont produit les corrections, le rapport et l'interface (voir plus bas). |

## Corrections de la v3.1

1. **HTTPS** : `verify=False` supprimé. Le serveur `catalog.data.gov.tn` n'envoie pas son certificat
   intermédiaire ; le notebook le récupère et l'ajoute aux certificats de confiance.
2. **Doublons** : le parseur ne lit que les fichiers du manifeste et supprime les mesures identiques
   (4 648 mesures comptées avant, 2 368 réelles).
3. **Météo** : l'ET₀ utilise la météo la plus récente du moteur (Open-Meteo, NASA POWER en secours).
4. **Conflit capteur / sol** : un capteur sous le point de flétrissement fait passer la confiance à `VERY_LOW`.
5. **Eau limitée** : exemple à 1 500 m³ (≈ 58 % du besoin) au lieu de 20 m³.
6. **Provenance et textes** : `DATA_PROVENANCE` honnête, explication de `INSUFFICIENT_DATA`, chiffres périmés retirés.
7. **Blocage météo** : une erreur 429 d'Open-Meteo (quota) ne bloque plus le notebook pendant des heures.

## Résultats de l'exécution du 21/11/2026

- 40 cellules exécutées, 0 erreur ; 51 + 82 tests réussis, aussi depuis le ZIP.
- Chott Meriam : 176 heures de mesures à 10, 30 et 60 cm.
- Prévision à 1 h : la persistance gagne (MAE 0,023 %, R² 0,99) ; Random Forest et Gradient Boosting ont un R² négatif.
- Météo : Open-Meteo était saturé (quota) lors de cette exécution, donc NASA POWER a été utilisé,
  avec 3 jours de retard. Sur Kaggle, Open-Meteo répond normalement.
- Les volumes d'irrigation restent **illustratifs** : capteurs non calibrés, sol de Chott Meriam non documenté.

## Refaire les pages

```bash
# rapport de vérification d'un notebook exécuté (par exemple téléchargé depuis Kaggle)
python scripts/make_report.py notebooks/farmlink_irrigation_executed.ipynb rapport.html notebooks/farmlink_irrigation_original_v3.ipynb

# interface de test : données (dossier d'une exécution) puis assemblage
python scripts/build_data.py <dossier_execution> scripts/data.json
python scripts/ref_cases.py <dossier_execution> scripts/ref_cases.json
cd scripts && python build.py      # écrit farmlink_banc_essai.html à côté du template
```

`scripts/patch.py` applique les corrections au notebook d'origine :
`python scripts/patch.py original.ipynb corrige.ipynb`.

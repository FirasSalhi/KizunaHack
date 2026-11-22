# FARMLINK : intelligence de marché et conseil d'investissement

*Agricultural Market Intelligence & Investment Advisor* pour les agriculteurs tunisiens.

Ce module répond à deux questions :

1. Quels fruits et légumes ont compté le plus sur le marché tunisien pendant la dernière campagne ?
2. Quelles cultures envisager pour la prochaine saison, compte tenu des prix, du rendement, de l'eau et des coûts ?

Toutes les valeurs viennent de **sources officielles téléchargées** : INS, ministère de l'Agriculture (data.gov.tn), FAOSTAT, NASA POWER et Banque mondiale. Aucune valeur n'est inventée. Quand une donnée manque, l'application l'écrit.

## La partie à mettre dans le tableau de bord FARMLINK

C'est la version **simple, pour les agriculteurs** : quelques indicateurs, en français et en arabe, avec des fruits et légumes en 3D.

| Fichier | Rôle |
|---|---|
| `html/marche_simple.html` | La page complète, qui fonctionne seule : double-clic, ou `<iframe src="marche_simple.html">` dans le tableau de bord. |
| `data/processed/dashboard_kpis.json` | Les mêmes chiffres en JSON, pour refaire les écrans dans `apps/web` si vous le souhaitez. |

La page tient en 3 étapes :

1. **Ce qui arrive au marché** : un étal 3D avec le top 5 des légumes et des fruits arrivés au marché de gros de Tunis. La hauteur des caisses correspond aux tonnes, et une flèche montre l'évolution sur un an.
2. **Quand vendre** : un calendrier de 12 mois du prix de détail à Tunis, avec le mois le plus cher et le moins cher (12 produits). Juste après, le prix payé au producteur et son évolution, inflation déduite.
3. **Que planter** : on choisit son gouvernorat et son eau (peu, moyenne ou beaucoup). L'écran montre 6 cultures classées, avec des étoiles, des gouttes d'eau et la fourchette de revenu par hectare.

Pour la mettre à jour après un `refresh_data.py` :

```bash
.venv/Scripts/python scripts/build_simple_dashboard.py
```

La mise en page vient de `scripts/simple_dashboard_template.html`, et les données sont insérées à la place de `__DATA__`.

## Version complète pour analystes (Streamlit, 2 commandes)

```bash
cd research/market-advisor
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt     # Linux/Mac : .venv/bin/pip
.venv/Scripts/streamlit run app/streamlit_app.py                           # ouvre http://localhost:8501
```

Les données déjà traitées sont dans le dépôt : il n'y a rien à télécharger pour lancer l'application.

> Sous Windows, si un dossier a un chemin très long, `pyarrow` peut échouer avec « DLL load failed ». Il suffit de cloner le dépôt dans un dossier court, par exemple `C:\dev\KizunaHack`.

## Les 4 pages

| Page | Contenu |
|---|---|
| **Vue du marché** | Top 5 des légumes et des fruits arrivés au marché de gros de Tunis, plus fortes hausses et baisses, apports mensuels, prix de détail, production et prix à la production nationaux. Filtres par campagne, années et produits. |
| **Fiche culture** | Pour une culture : production, superficie, rendement, prix courants et constants, apports et saisonnalité à Tunis, prix de gros et de détail (Tunis, Sidi Bouzid), besoin en eau dans les 24 gouvernorats. |
| **Conseiller d'investissement** | Formulaire de l'agriculteur (gouvernorat, surface, budget, eau, irrigation, coûts), classement des cultures, 3 scénarios financiers, explications, risques et données manquantes. |
| **Sources et fiabilité** | Liens vers les sources, couverture des données, mois manquants, 101 contrôles de qualité, méthode de calcul. |

## Ce qu'il faut savoir avant de présenter les résultats

- Les **apports** sont des tonnes entrées au **marché de gros de Tunis**. Ce n'est ni la production nationale ni la consommation.
- Le conseiller ne classe que les cultures qui ont **au moins 5 ans de rendement et de prix officiels sur les 10 dernières années**. Ce sont aujourd'hui la tomate, la pomme de terre, l'oignon, le piment, la pastèque et le melon (publiés ensemble), et l'artichaut. Les autres cultures reçoivent « Preuves insuffisantes », avec la raison.
- **Aucune source officielle ne publie les coûts de production des légumes.** Le bénéfice n'est calculé que si l'agriculteur saisit ses coûts. Sinon, l'application affiche le revenu brut.
- Les scénarios sont des fourchettes du passé (2016-2025, en dinars constants), pas des prévisions.

## Organisation du dossier

```
data/raw/          fichiers originaux, non modifiés (+ _manifest.json : URL, date, sha256)
data/processed/    tables nettoyées (CSV), avec la source de chaque ligne
data/metadata/     sources.json, data_quality_report.json, recherche du catalogue data.gov.tn
farmlink_market/   le code : lecture des PDF INS, pipeline, indicateurs, conseiller
app/               le tableau de bord Streamlit
scripts/           téléchargement des sources (refresh_data.py fait tout)
tests/             22 tests automatiques
reports/           rapport final et méthode
```

## Mettre les données à jour

```bash
.venv/Scripts/python scripts/refresh_data.py                  # tout retélécharger puis reconstruire (~5 min)
.venv/Scripts/python scripts/refresh_data.py --skip-download  # reconstruire seulement
.venv/Scripts/python -m pytest                                # vérifier
```

Quand l'INS publie un nouveau bulletin mensuel, ajoutez son nom (par exemple `aout-2026`) à la liste `BULLETINS` de `scripts/refresh_data.py`.

## Utiliser le moteur dans un autre code (par exemple l'API)

```python
from farmlink_market import kpis, advisor
data = kpis.load()
table, details = advisor.recommend(data, advisor.FarmerInput(governorate="Nabeul", area_ha=2, water="limited",
                                   costs_per_ha={"tomato": {"seeds": 3000, "fertilisers": 2500}}))
```

Le rapport complet se trouve dans [reports/final_report.md](reports/final_report.md).

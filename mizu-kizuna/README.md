# MIZU KIZUNA — Que planter sur ma terre ?

Site web + API pour l'agriculteur : il trouve sa ferme sur une **vraie carte satellite**, **dessine sa parcelle**,
répond à **2 questions sur son eau**, et obtient :

- **quelles cultures planter** (classées et expliquées), avec le meilleur mois de semis ;
- **quelles cultures planter ensemble** et lesquelles éviter ;
- **un plan de sa parcelle** (où mettre quoi, surfaces, eau nécessaire en année normale et sèche) ;
- **ce que disent le sol et le satellite** sur sa terre, le climat sur 30+ ans et les prévisions à 16 jours.

Pays couverts : **Tunisie** et **Japon** (35 cultures).
Langues : **français**, **tunisien (derja, écrit de droite à gauche)** et **japonais** — bouton en haut à droite.
L'API accepte `"lang": "fr" | "tn" | "ja"` : tous les textes (raisons, alertes, compatibilités, noms de cultures) sont traduits.

## Lancer (Windows)

Double-cliquez sur **`lancer.bat`**. La première fois, il installe tout (quelques minutes), puis ouvre
http://localhost:8000. Internet est nécessaire pour la carte et les données.

Autre système :
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```
Sur téléphone (même Wi-Fi) : `http://<IP-du-PC>:8000`. Mode sans internet (démo) : `MIZU_OFFLINE=1`.

## Données utilisées (toutes gratuites, sans compte)

| Donnée | Source | Usage |
|---|---|---|
| Carte satellite | Esri World Imagery | Trouver et dessiner la ferme |
| Recherche de lieux | OpenStreetMap / Nominatim | Barre de recherche |
| Météo journalière 1991 → année dernière | NASA POWER (communauté AG) | Températures, pluie, rayonnement, humidité, vent |
| Évapotranspiration | FAO-56 Penman-Monteith (calculée) | Besoins en eau |
| Exigences des cultures | FAO EcoCrop (2 568 espèces) | Températures, pluie, pH, texture |
| Coefficients culturaux, stades, racines | FAO-56 (tableaux 11, 12, 22) | Besoins en eau |
| Tolérance au sel | FAO-29 (Ayers & Westcot) | Eau/sol salés |
| Sol : argile, sable, limon, pH, carbone, CEC | SoilGrids 2.0 (ISRIC), 250 m | Adéquation du sol |
| Images de la parcelle (24 mois) | Sentinel-2 L2A via Microsoft Planetary Computer | NDVI, zones de vigueur, sol nu |
| Prévisions 16 jours | Open-Meteo | Conseils de semis |

## Comment le modèle décide

Pour chaque culture et chaque mois de semis possible, **sur chaque année de l'historique** :

`score = climat × sol × sel × eau × (1 − risque)` — facteur limitant, comme FAO EcoCrop / GAEZ.

- **Climat** : fonction trapèze EcoCrop sur la température moyenne mensuelle, pondérée par le stade (Kc).
- **Risque** : part des années avec un gel destructeur ou 3 jours de canicule pendant la saison.
- **Eau** : besoin d'irrigation FAO-56 d'une **année sèche** (80e centile) vs l'eau disponible ;
  la pluie compte (une culture qui tient en sec n'est pas pénalisée). En « pluie seulement » :
  pluviométrie annuelle vs exigences EcoCrop.
- **Sol** : pH et texture (SoilGrids). **Sel** : seuil FAO-29.
- **Plan** : assortiment de 2 à 4 cultures compatibles, surfaces optimisées (programmation linéaire)
  sous la contrainte d'eau ; si l'eau manque, le reste de la ferme reçoit des cultures pluviales ;
  les cultures exigeantes vont sur les zones de forte vigueur Sentinel-2.
- **Compatibilité** : relations sourcées (guides de vulgarisation, littérature d'association céréale-légumineuse,
  systèmes oasiens) + même famille botanique + règles eau / racines / lumière / calendrier.

## Ajustements à la réalité tunisienne (v2.1)

Les seuils FAO EcoCrop sont mondiaux. Les tests ont montré trois écarts, corrigés dans `tools/build_crops.py` :
- **Cultures d'hiver** (blé, orge, fève, pois chiche, pois, ail, oignon) : EcoCrop donne des optimums de cycles de
  printemps (blé dur 17-25 °C) ; remplacés par des optimums d'hiver méditerranéens (blé dur 9-22 °C).
  Avant : blé dur à Béja = 43/100 ; après : 83/100.
- **Culture en sec** : seuils de pluie annuelle calibrés sur la pratique tunisienne (orge 150-300 mm,
  olivier 150-300 mm, blé dur 300-450 mm…) ; les cultures qui ne se font pas en sec en Tunisie
  (maraîchage d'été, agrumes, palmier, luzerne…) sont exclues dans ce mode.
- **Gel** : températures létales agronomiques pour les cultures endurcies (EcoCrop met souvent 0 °C).
Ce sont des ajustements d'expert : la validation sur Agridata doit les confirmer.

Le plan propose aussi des **cultures intercalaires sous les arbres** (olivier + orge/fève/pois chiche,
amandier + orge/fève, palmier + luzerne…) et alerte si le satellite voit une parcelle verte en été alors
que l'agriculteur a répondu « pluie seulement ».

## Combinaisons sur le même hectare (v2.2)

Section « Combinaisons sur le même hectare » : 14 associations sourcées (olivier + orge, fève, pois chiche,
**menthe**, romarin et thym, piment et tomate, amandier ; oasis à 3 étages ; céréale + légumineuse ; oignon + carotte ;
tomate + basilic ; blé puis soja au Japon). Pour chacune, le site affiche :
- **pourquoi ça marche** (étages, racines, azote, insectes, eau, sol, revenu, calendrier, microclimat) ;
- **les précautions** et **la disposition au champ** ;
- **la faisabilité sur la parcelle** : adéquation de chaque plante (climat, sol, sel, risque) et
  **eau estimée** de la combinaison, avec la surface possible selon l'eau disponible ;
- **le niveau de confiance et les sources**. « Faible » = pas d'essai publié pour cette combinaison exacte
  (cas de l'olivier + menthe : conseil fondé sur les mécanismes, à tester sur une petite surface).

Le catalogue est dans `tools/build_combos.py` (textes fr / tn / ja) ; API : `GET /api/combinations?country=tunisie&lang=fr`.
Nouvelles plantes : menthe (Kc FAO-56), romarin, thym, basilic (Kc estimés).

## Mesurer la précision

`python validate.py` compare, gouvernorat par gouvernorat, les cultures recommandées aux cultures
réellement produites (à saisir depuis **catalog.agridata.tn** dans `validation/verite_terrain_tunisie.csv`).
Indicateurs : précision top-5 et corrélation de Spearman. Le fichier est livré **vide** : aucun chiffre de
précision n'est annoncé tant qu'il n'a pas été mesuré sur les données officielles.

## Limites connues (à dire au jury)

- Les seuils EcoCrop sont mondiaux ; certains ont été ajustés (pH sur sols calcaires, gel des cultures
  d'hiver endurcies — voir `tools/build_crops.py`). Les fenêtres de semis sont des pratiques courantes à faire valider.
- Les oliveraies pluviales à faible densité (Sfax) sont sous-estimées : le modèle raisonne à l'hectare couvert.
- Sentinel-2 ne mesure pas directement la composition du sol : il donne la vigueur et des indicateurs relatifs
  de sol nu ; la composition vient de SoilGrids.
- Aide à la décision : à confirmer avec un technicien agricole (CRDA, JA au Japon).

## API (pour Next.js / Flutter)

Documentation interactive : http://localhost:8000/docs

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/api/health` | État |
| GET | `/api/geocode?q=Kairouan` | Recherche de lieux (Tunisie, Japon) |
| POST | `/api/analyze` | **Appel principal** |
| GET | `/api/crops?country=tunisie` | Liste des cultures |
| GET | `/api/crops/{id}/companions?country=tunisie` | Compatibilités d'une culture |

```json
POST /api/analyze
{
  "farm": {"type": "Polygon", "coordinates": [[[10.650,36.530],[10.654,36.530],[10.654,36.533],[10.650,36.533],[10.650,36.530]]]},
  "water": {"source": "puits", "method": "goutte_a_goutte", "volume_m3": 30000},
  "salinity": "non",
  "soil_type": null,
  "kinds": "all"
}
```
`water.source` : `puits` | `reseau` | `pluie` · `salinity` : `non` | `un_peu` | `oui` · `soil_type` : `null` (SoilGrids) ou `sableux` | `limoneux` | `argileux` | `acide`.

Réponse : `ranking[]` (score, label, facteurs, pour/contre, eau m³/ha), `plan.allocation[]`, `plan.map`
(GeoJSON coloré prêt à afficher), `companions{}`, `land.soil`, `land.satellite` (série NDVI, zones de vigueur GeoJSON),
`climate.normals`, `forecast.advice[]`, `calendar[]`, `warnings[]`.

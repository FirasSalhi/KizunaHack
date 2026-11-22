# FARMLINK : intelligence de marché et conseil d'investissement, rapport final

Ce rapport a été produit le 22/11/2026. Tous les chiffres ci-dessous sont recalculés à chaque exécution de `python -m farmlink_market.pipeline` à partir des fichiers de `data/raw`.

## 1. Ce qui fonctionne

- **Tableau de bord Streamlit** (4 pages) : marché, fiche culture, conseiller d'investissement, sources et fiabilité.
- **Pipeline reproductible** : 32 fichiers data.gov.tn, 26 bulletins mensuels INS, FAOSTAT, NASA POWER et Banque mondiale sont transformés en 11 tables nettoyées. Il produit aussi un fichier des sources et un rapport de qualité de 101 contrôles.
- **Lecture automatique des PDF de l'INS** : tableaux 9.5 (apports au marché de gros de Tunis) et 9.1 (prix de détail à Tunis). Les mois et les années sont lus dans l'en-tête de chaque tableau.
- **Indicateurs** de marché, de production et de prix.
- **Conseiller d'investissement** :
  - un formulaire pour l'agriculteur ;
  - le calcul du besoin en eau (FAO-56) dans les 24 gouvernorats ;
  - trois scénarios financiers ;
  - un score sur plusieurs critères, avec des pondérations modifiables ;
  - des explications, des risques et la liste des données manquantes ;
  - la réponse « Preuves insuffisantes » quand les données ne suffisent pas.
- **22 tests automatiques**, qui passent tous. Ils couvrent :
  - la lecture des PDF ;
  - les unités ;
  - les indicateurs ;
  - les filtres de dates ;
  - les valeurs manquantes ;
  - le bénéfice, les scénarios et les scores ;
  - la comparaison d'un échantillon de valeurs traitées avec les fichiers d'origine.

## 2. Jeux de données récupérés

| Source | Contenu | Couverture | Période |
|---|---|---|---|
| [INS – Bulletin mensuel de la statistique](https://www.ins.tn/publication), tableau 9.5 | Apports mensuels au marché de gros de Tunis : 20 légumes, 19 fruits (tonnes) | Marché de gros de Tunis | févr. 2021 → juil. 2026 |
| INS, tableau 9.1 | Prix moyens de détail à Tunis (millimes/kg, convertis en DT/kg) | Tunis | juil. 2021 → juil. 2026 |
| [Ministère de l'Agriculture – production maraîchère](https://catalog.data.gov.tn/fr/dataset/evolution-de-la-production-des-cultures-maraicheres-mille-tonnes) | Production (milliers de tonnes) | National | 2004 → 2025 |
| [Ministère – productivité](https://catalog.data.gov.tn/fr/dataset/evolution-de-la-productivite-des-cultures-maraicheres-tonnes-ha) | Rendement (t/ha) | National | 2004 → 2025 |
| [Ministère – superficie](https://catalog.data.gov.tn/fr/dataset/evolution-de-la-superficie-des-cultures-maraichere) | Superficie (milliers d'ha) | National | 2004 → 2025 |
| [Ministère – prix à la production](https://catalog.data.gov.tn/fr/dataset/evolution-des-prix-a-la-production-des-cultures-maraicheres-d-t) | Prix à la production (DT/t) | National | 2004 → 2025 |
| [Ministère – agrumes](https://catalog.data.gov.tn/fr/dataset/production-agrumes) et [agrumes par type](https://catalog.data.gov.tn/fr/dataset/evolution-de-la-production-des-agrumes-par-type-de-produit) | Production | National | 1993 → 2026, et 2018 → 2025 par type |
| [Ministère – arboriculture fruitière](https://catalog.data.gov.tn/fr/dataset/evolution-de-la-production-de-l-arboriculture-fruitiere-en-tonne) et [autres fruits](https://catalog.data.gov.tn/fr/dataset/evolution-de-la-production-des-autres-arboricultures-fruitiere) | Production par fruit | National | 2009 → 2018 et 2009 → 2020 |
| [CRDA Sidi Bouzid – suivi des prix](https://catalog.data.gov.tn/fr/dataset/suivi-des-prix) | Prix de gros et de détail (min/max) et quantités, quotidiens | Sidi Bouzid | janv. 2018 → oct. 2022 |
| [SECADENORD – tarif de l'eau](https://catalog.data.gov.tn/fr/dataset/evolution-du-tarif-de-vente-du-m3-d-eau-en-millime_secadenord) | Prix de l'eau brute (millimes/m³) | Nord | 2014 → 2025 |
| [Ministère – prix des engrais](https://catalog.data.gov.tn/fr/dataset/prix-des-engrais-chimiques-aupres-des-societes-qui-s-approvisionnent-directement-du-groupe-chimique) | Super 45 %, ammonitre, DAP (DT/t) | National | 2010/11 → 2019/20 |
| [INS – SMAG](https://www.ins.tn/statistiques/98) | Salaire minimum agricole (DT/jour) | National | 2018 → 2026 |
| [FAOSTAT](https://bulks-faostat.fao.org/production/) (QCL et PP) | Production, superficie, rendement, prix à la production, avec le statut de chaque valeur | Tunisie | 1961 → 2024 |
| [NASA POWER](https://power.larc.nasa.gov/) | Climat mensuel moyen (température, pluie) | 24 chefs-lieux | climatologie |
| [Banque mondiale FP.CPI.TOTL](https://api.worldbank.org/v2/country/TUN/indicator/FP.CPI.TOTL) | Indice des prix à la consommation | Tunisie | 1983 → 2025 |
| Base FAO-56 du module irrigation (`data/raw/reference`) | Coefficients culturaux et durées de cycle | — | FAO-56 |

**Sources non retenues :**
- **ONAGRI** : le site répond, mais il n'a pas été exploré en détail pour ce prototype. C'est la prochaine source à étudier pour les prix de gros et les coûts.
- **INS, page « Production végétale »** : elle présente des tableaux sur les céréales, non utilisés ici.
- **Coûts de production** : sur data.gov.tn, ils n'existent que pour l'aviculture (GIPAC).

Chaque fichier brut est conservé sans modification. Un fichier `_manifest.json` par source donne l'URL, la date de téléchargement et l'empreinte sha256.

## 3. Résultats : la dernière campagne complète

La campagne 2024/25 (septembre 2024 → août 2025) est la dernière dont les 12 mois sont publiés.

**Apports au marché de gros de Tunis**
- Légumes : 251 830 t (+1,2 % par rapport à 2023/24, sur les mêmes mois).
- Fruits : 132 987 t (−8,4 %).

| Top 5 des légumes | Tonnes | Mois de pointe | Évolution sur un an |
|---|---|---|---|
| Tomate | 42 194 | août 2025 | +8,3 % |
| Oignon | 32 887 | mars 2025 | +5,1 % |
| Pomme de terre | 27 051 | oct. 2024 | −11,2 % |
| Piment piquant | 23 296 | août 2025 | −0,1 % |
| Carotte | 18 435 | nov. 2024 | −0,8 % |

| Top 5 des fruits | Tonnes | Mois de pointe | Évolution sur un an |
|---|---|---|---|
| Pêche | 13 571 | juin 2025 | +6,8 % |
| Pomme | 11 483 | août 2025 | −42,3 % |
| Raisin de table | 10 313 | sept. 2024 | +7,0 % |
| Melon | 10 233 | juil. 2025 | +6,1 % |
| Citron | 8 414 | avr. 2025 | −13,0 % |

**Plus fortes évolutions** (produits d'au moins 2 000 t) :
- en hausse : grenade (+36 %), poivron doux (+19 %), chou (+10 %) ;
- en baisse : pomme (−42 %), fenouil (−23 %), datte (−23 %).

**Prix à la production nationaux, 2016-2025**
- En dinars courants, ils montent pour toutes les cultures (+3 à +10 %/an).
- Une fois l'inflation retirée, la tomate (−1,1 %/an), le piment (−3,3 %/an), l'artichaut et l'oignon **baissent**.
- La pomme de terre (+1,1 %/an) et la pastèque-melon (+2,7 %/an) **montent**.

**Conseiller** (exemple : Nabeul, 1 ha, eau moyenne, goutte-à-goutte, coûts non saisis) :

| Rang | Culture | Score |
|---|---|---|
| 1 | Pastèque et melon | 73 |
| 2 | Pomme de terre | 66 |
| 3 | Piment | 50 |
| 4 | Artichaut | 39 |
| 5 | Tomate | 29 |
| 6 | Oignon | 24 |

- La tomate a le 2e revenu par ha, mais le plus fort besoin en eau après l'oignon (≈ 10 300 m³/ha pour un semis en avril) et un prix réel en baisse.
- Ce classement dépend des pondérations et des coûts saisis.

## 4. Cultures avec assez de preuves

- **Classées par le conseiller** : tomate, pomme de terre, oignon, piment/poivron, pastèque et melon (publiés ensemble), artichaut. Ce sont les séries officielles nationales 2016-2025.
- **Indicateurs de marché seulement** (apports et prix à Tunis, sans rendement ni prix officiels récents) : carotte, chou, chou-fleur, concombre, courge, courgette, épinard, fenouil, fève, navet, persil, petit pois, salade, blette, ail, et les 19 fruits.
- **Fruits et autres cultures pérennes** : « Preuves insuffisantes » pour l'investissement. Le coût d'installation et le délai avant la première récolte manquent dans les sources.

## 5. Indicateurs disponibles

- **A. Marché** : total et moyenne mensuelle des apports, mois de pointe et de creux, évolution sur un an (mêmes mois), évolution mensuelle, saisonnalité, top 5, hausses et baisses.
- **B. Production** : production, superficie, rendement, croissance, tendance et stabilité du rendement (national).
- **C. Prix** : prix à la production (courant et réel), tendance, instabilité ; prix de détail à Tunis (moyenne, min, max, variation mensuelle, sur un an) ; prix de gros et de détail à Sidi Bouzid ; écart entre le prix de détail à Tunis et le prix à la production national, présenté comme un écart, pas comme une marge.

Tous ces indicateurs sont fonctionnels. Un indicateur n'est pas affiché quand ses données manquent.

## 6. Méthode d'investissement

Le détail est dans [methodology_fr.md](methodology_fr.md). En résumé :
- revenu = rendement × prix ;
- coûts = coûts saisis + eau calculée (FAO-56 × tarif) ;
- main-d'œuvre = jours saisis × SMAG officiel ;
- scénarios = 20e, 50e et 80e percentiles du revenu réel 2016-2025 ;
- scores normalisés de 0 à 100 entre les cultures comparées, pondérés 30/25/25/20 (modifiable), avec un poids de l'eau ajusté selon la disponibilité.

## 7. Problèmes de qualité constatés (extrait des 101 contrôles)

- **Superficie** : la colonne « Superficie_ha » du ministère est en milliers d'hectares. Le contrôle production ≈ superficie × rendement ne tient que pour 95 % des années. Six années sont incohérentes, par exemple la pastèque-melon en 2004-2006.
- **Deux fichiers du ministère contredisent la même série de production** sur 23 des 60 cultures-années, en particulier l'oignon de 2010 à 2018 (jusqu'à 136 kt d'écart). On garde la série la plus longue.
- **Bulletins INS** : 28 mois de produit ont des valeurs différentes d'un bulletin à l'autre. Par exemple, le concombre en juillet 2025 vaut 214 t dans un bulletin et 2 314 t dans un autre. On garde le bulletin le plus récent.
- **Mois non publiés à Tunis** : 03/2021, 09/2021, 09/2022, 12/2022, 11/2023, 04/2026. Les campagnes 2021/22, 2022/23 et 2023/24 sont donc incomplètes.
- **Unités non indiquées dans la source** :
  - fruits « en tonne » : ce sont en réalité des milliers de tonnes ;
  - prix de Sidi Bouzid : millimes/kg, déduit des valeurs ;
  - jours où le prix vaut 0 : traités comme « pas en vente ».
- **FAOSTAT** : seuls 55 % des valeurs pour la Tunisie sont officielles. Après 2012-2015, beaucoup de rendements sont estimés ou imputés par la FAO. Elles ne sont pas utilisées pour le conseil.

## 8. Limites

- Les rendements et les prix sont des **moyennes nationales**. Aucune donnée officielle de rendement par gouvernorat et par culture n'a été intégrée : les fichiers régionaux sont partiels et hétérogènes.
- **Aucune donnée officielle de coûts de production des légumes** : le bénéfice dépend des coûts saisis.
- Les **apports** ne concernent que le marché de Tunis. Il n'existe pas de série de prix de gros à Tunis dans les sources trouvées.
- Le **besoin en eau** est une estimation : climat moyen d'un seul point par gouvernorat, méthode de Hargreaves, durées de cycle FAO-56 et non tunisiennes.
- Les **groupes de cultures** du ministère (« Piment », « Pastèque et melon ») ne sont pas découpés.
- Le **tarif de l'eau** par défaut (SECADENORD) concerne l'eau brute vendue aux CRDA du Nord, pas le prix payé par l'agriculteur au GDA.

## 9. Améliorations possibles

1. Ajouter les rendements et superficies par gouvernorat (fichiers CRDA de data.gov.tn) pour rendre le conseil régional.
2. Demander à l'ONAGRI ou à l'APIA les fiches technico-économiques (coûts par culture), puis les afficher comme « référence officielle » à côté des saisies.
3. Recharger automatiquement chaque nouveau bulletin INS et ajouter les prix de gros de Bir El Kassâa si l'INS ou l'ONAGRI les publient.
4. Brancher le moteur sur l'API FastAPI du projet, comme pour l'irrigation, et sur le moteur FAO-56 complet du module irrigation (ET₀ Penman-Monteith quotidienne).

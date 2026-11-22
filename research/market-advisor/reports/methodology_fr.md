**Principe :** toutes les valeurs affichées viennent des fichiers officiels téléchargés (dossier `data/raw`, non modifiés). Une valeur absente reste absente. Les seules saisies sont celles de l'agriculteur (coûts, eau, mois de semis), et elles sont signalées comme telles.

**Apports au marché de gros de Tunis.**
- Tonnes entrées chaque mois au marché de gros de Tunis, d'après le tableau 9.5 du bulletin mensuel de l'INS. Ce ne sont ni la production nationale ni des achats des consommateurs.
- Chaque bulletin couvre 13 mois. Pour chaque mois, on garde le bulletin le plus récent qui publie un chiffre ; les écarts entre bulletins sont listés dans les contrôles de qualité.
- « /// » (aucun apport) compte pour 0 t ; « … » (non publié) reste manquant.

**Campagne agricole :** de septembre à août. La « dernière campagne complète » est la plus récente dont les 12 mois sont publiés.

**Évolution sur un an :** on compare la campagne choisie à la précédente, sur les seuls mois publiés dans les deux (au moins 9 mois).

**Plus fortes hausses ou baisses :** seulement les produits d'au moins 2 000 t, pour éviter les pourcentages trompeurs sur de petits volumes.

**Prix.**
- Trois niveaux de prix ne sont jamais mélangés :
  - production : national, ministère de l'Agriculture, DT/t ;
  - gros : Sidi Bouzid, CRDA ;
  - détail : Tunis, INS.
- L'écart détail-production est affiché comme un simple écart de prix, pas comme une marge ou un bénéfice.

**Prix réels :** les prix courants sont convertis en dinars constants de la dernière année disponible, avec l'indice des prix à la consommation (Banque mondiale, série FP.CPI.TOTL).

**Tendance :** pente d'une régression log-linéaire sur les 10 dernières années, exprimée en % par an.

**Instabilité :** écart type des variations annuelles du prix, en %.

**Besoin en eau (estimation).**
- Méthode FAO-56 : coefficient cultural (Kc) multiplié par l'ET₀.
- L'ET₀ est calculée par la méthode de Hargreaves avec le climat moyen NASA POWER du chef-lieu du gouvernorat.
- La pluie efficace suit la méthode USDA-SCS.
- Besoin brut (m³/ha) = besoin net (mm) × 10 ÷ efficience d'irrigation. Efficience : 90 % en goutte-à-goutte, 75 % en aspersion, 60 % en gravitaire.
- Les durées de cycle et le mois de semis par défaut sont ceux de la FAO-56 : l'agriculteur doit les adapter.

**Conseiller d'investissement.**
- Une culture n'est classée que si l'on dispose d'**au moins 5 ans, sur les 10 dernières années**, de rendement et de prix à la production officiels.
- Sinon, le résultat est « Preuves insuffisantes », avec la raison.
- Les cultures pérennes sont exclues : le coût d'installation et le délai avant récolte manquent dans les sources.
- Calcul :
  - revenu = rendement × prix × surface ;
  - coût = coûts saisis + eau calculée ;
  - bénéfice = revenu − coût.
- Scénarios : 20e (pessimiste), 50e (attendu) et 80e (optimiste) percentiles du revenu historique par hectare, en dinars constants. Ce sont des fourchettes passées, pas une prévision.

**Scores de 0 à 100, relatifs aux cultures comparées.**

| Critère | Calcul |
|---|---|
| Marché | tendance du prix réel et stabilité du prix |
| Productivité | tendance et stabilité du rendement national |
| Rentabilité | bénéfice par ha si les coûts sont saisis, sinon revenu brut moins l'eau |
| Eau | besoin en m³/ha le plus faible = 100 ; 50 si le besoin n'est pas calculable |

- Pondérations par défaut : 30 / 25 / 25 / 20. Ce sont des hypothèses de conception, modifiables.
- Le poids de l'eau est multiplié par 1,5 si l'eau est limitée et par 0,5 si elle est abondante.

**Limites principales.**
- Aucune source officielle ne publie les coûts de production des légumes. Ils doivent être saisis.
- Les rendements et les prix sont des moyennes nationales, pas ceux de votre parcelle.
- Les apports concernent un seul marché : Tunis.
- Les prix de Sidi Bouzid s'arrêtent en octobre 2022.
- Les données de FAOSTAT postérieures à 2012-2015 sont souvent estimées ou imputées par la FAO, et sont donc affichées avec leur statut.

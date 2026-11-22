# Pompe solaire et coupure STEG : simulation 3D

Ce dossier contient une page de démonstration pour le jury. Elle montre une journée à la ferme : quand le réseau STEG est coupé, les panneaux solaires, la batterie et un onduleur automatique continuent à faire tourner la pompe de l'irrigation souterraine ROOTLOOP.

- **Ouvrir :** `html/solaire_3d.html` (double-clic), ou dans le tableau de bord, section **Énergie solaire** (`/dashboard/solar`).
- **Bouton « Scénario pour le jury » :** la même journée est jouée deux fois, avec une coupure de 10 h à 15 h.
  1. Sans solaire : la pompe s'arrête et les plantes souffrent.
  2. Avec FARMLINK : l'onduleur bascule sur les panneaux, puis sur la batterie, et l'eau continue d'arriver aux racines.
- **Commandes :**
  - couper ou rétablir la STEG ;
  - avec ou sans solaire ;
  - taille des panneaux et de la batterie ;
  - gouvernorat, mois, culture, surface, débit et hauteur de pompage ;
  - ciel ;
  - 4 vues de caméra (dont « Sous le sol ») ;
  - l'heure, et la vitesse ×1, ×4 ou ×12.

## Les calculs (simples et vérifiables)

| Grandeur | Formule | Source |
|---|---|---|
| Soleil | Rayonnement global moyen du mois, réparti sur la journée entre lever et coucher du soleil | NASA POWER, chef-lieu de chaque gouvernorat (`data/`) |
| Production des panneaux | kWc × rayonnement (kW/m²) × 0,80, moins 0,4 % par °C au-dessus de 25 °C | Valeurs classiques de dimensionnement PV |
| Puissance de la pompe | 9,81 × débit (m³/s) × hauteur (m) ÷ rendement | Formule hydraulique |
| Eau du jour | (ET₀ × Kc − pluie efficace) × 10 × surface ÷ 0,95 | FAO-56 (ET₀ Hargreaves, Kc mi-saison) |
| Gestion de l'énergie | D'abord le soleil, puis la batterie (au-dessus de sa réserve), puis la STEG. Le surplus solaire recharge la batterie. La pompe à vitesse variable s'arrête sous 30 % de sa puissance. | Choix de conception |

**Hypothèses à confirmer avec le vrai matériel** (modifiables dans la page) :
- tarif STEG : 0,25 DT/kWh ;
- rendement de la pompe et du moteur : 45 % ;
- batterie : 15 kWh, réserve de 20 %, rendement de 95 % ;
- émissions de CO₂ : 0,46 kg par kWh STEG ;
- goutte-à-goutte enterré : efficacité de 95 %.

C'est une simulation pour expliquer le principe, pas un dimensionnement certifié.

## Mettre à jour

```bash
cd research/solar-pump
python scripts/build.py            # reconstruit html/solaire_3d.html à partir de scripts/template.html
python scripts/build.py --refresh  # retélécharge le climat NASA POWER
```

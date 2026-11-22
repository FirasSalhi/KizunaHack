"""Construit data/crops.json : exigences FAO EcoCrop + paramètres FAO-56 + tolérance au sel FAO-29.

Sources :
- FAO EcoCrop (copie OpenCLIM : github.com/OpenCLIM/ecocrop, EcoCrop_DB.csv)
- FAO-56 (Allen et al. 1998) : Kc (tableau 12), durées des stades (tableau 11), profondeur racinaire (tableau 22)
- FAO-29 (Ayers & Westcot 1985) : seuil de salinité ECe (dS/m) sans perte de rendement
Les fenêtres de semis sont des pratiques courantes par pays (à valider avec un agronome local).
"""
import json
import math

import pandas as pd

ECO = pd.read_csv("tools/EcoCrop_DB.csv", encoding="latin1")
ECO["ScientificName"] = ECO["ScientificName"].str.strip()

# id: (nom_fr, nom scientifique EcoCrop, famille, type, (kc_ini,kc_mid,kc_end), (l_ini,l_dev,l_mid,l_late),
#      racines_m, hauteur_m, lumière, fixe_N, seuil_sel_ECe, {pays: mois de semis possibles})
C = {
 "tomato":      ("Tomate", "Lycopersicon esculentum", "Solanacées", "annual", (0.6,1.15,0.8), (30,40,40,25), 1.0, 0.8, "high", 0, 2.5, {"tunisie":[2,3,4,8], "japon":[4,5]}),
 "pepper":      ("Poivron / piment", "Capsicum annuum", "Solanacées", "annual", (0.6,1.05,0.9), (30,35,40,20), 0.8, 0.7, "high", 0, 1.5, {"tunisie":[3,4], "japon":[5]}),
 "eggplant":    ("Aubergine", "Solanum melongena", "Solanacées", "annual", (0.6,1.05,0.9), (30,40,40,20), 0.9, 0.8, "high", 0, 1.1, {"tunisie":[3,4], "japon":[5]}),
 "potato":      ("Pomme de terre", "Solanum tuberosum", "Solanacées", "annual", (0.5,1.15,0.75), (25,30,45,30), 0.5, 0.6, "high", 0, 1.7, {"tunisie":[1,2,9], "japon":[3,8]}),
 "onion":       ("Oignon", "Allium cepa", "Alliacées", "annual", (0.7,1.05,0.75), (15,25,70,40), 0.4, 0.4, "high", 0, 1.2, {"tunisie":[10,11,12], "japon":[9,10]}),
 "garlic":      ("Ail", "Allium sativum", "Alliacées", "annual", (0.7,1.0,0.7), (20,30,70,30), 0.4, 0.4, "high", 0, 1.7, {"tunisie":[10,11], "japon":[9,10]}),
 "melon":       ("Melon", "Cucumis melo", "Cucurbitacées", "annual", (0.5,1.05,0.75), (25,35,40,20), 1.0, 0.3, "high", 0, 2.2, {"tunisie":[3,4], "japon":[4,5]}),
 "watermelon":  ("Pastèque", "Citrullus lanatus", "Cucurbitacées", "annual", (0.4,1.0,0.75), (20,30,30,30), 1.0, 0.4, "high", 0, 2.0, {"tunisie":[3,4], "japon":[5]}),
 "cucumber":    ("Concombre", "Cucumis sativus", "Cucurbitacées", "annual", (0.6,1.0,0.75), (20,30,40,15), 0.8, 0.3, "high", 0, 2.5, {"tunisie":[3,4,9], "japon":[4,5]}),
 "carrot":      ("Carotte", "Daucus carota", "Apiacées", "annual", (0.7,1.05,0.95), (20,30,50,20), 0.7, 0.3, "medium", 0, 1.0, {"tunisie":[9,10,11,2], "japon":[3,7,8]}),
 "lettuce":     ("Laitue", "Lactuca sativa var. capitata", "Astéracées", "annual", (0.7,1.0,0.95), (20,30,15,10), 0.4, 0.3, "medium", 0, 1.3, {"tunisie":[9,10,11,2], "japon":[3,9]}),
 "cabbage":     ("Chou", "Brassica oleracea var. capitata", "Brassicacées", "annual", (0.7,1.05,0.95), (40,60,50,15), 0.6, 0.4, "medium", 0, 1.8, {"tunisie":[8,9,10], "japon":[3,8]}),
 "daikon":      ("Radis / daikon", "Raphanus sativus", "Brassicacées", "annual", (0.7,0.9,0.85), (10,15,30,10), 0.4, 0.4, "medium", 0, 1.2, {"tunisie":[9,10,2], "japon":[8,9,3]}),
 "durum_wheat": ("Blé dur", "Triticum durum", "Poacées", "annual", (0.4,1.15,0.3), (20,60,60,40), 1.2, 0.9, "high", 0, 5.9, {"tunisie":[11,12]}),
 "wheat":       ("Blé tendre", "Triticum aestivum", "Poacées", "annual", (0.4,1.15,0.3), (20,60,60,40), 1.2, 0.9, "high", 0, 6.0, {"tunisie":[11,12], "japon":[10,11]}),
 "barley":      ("Orge", "Hordeum vulgare", "Poacées", "annual", (0.3,1.15,0.25), (20,50,50,30), 1.2, 0.8, "high", 0, 8.0, {"tunisie":[10,11,12], "japon":[10,11]}),
 "rice":        ("Riz", "Oryza sativa", "Poacées", "annual", (1.05,1.2,0.9), (30,30,60,30), 0.7, 1.0, "high", 0, 3.0, {"japon":[5,6]}),
 "faba_bean":   ("Fève", "Vicia faba", "Fabacées", "annual", (0.5,1.15,0.3), (20,30,40,25), 0.6, 0.9, "high", 1, 1.6, {"tunisie":[10,11]}),
 "chickpea":    ("Pois chiche", "Cicer arietinum", "Fabacées", "annual", (0.4,1.0,0.35), (20,30,40,20), 0.8, 0.5, "high", 1, 2.0, {"tunisie":[1,2,11]}),
 "pea":         ("Petit pois", "Pisum sativum", "Fabacées", "annual", (0.5,1.15,1.1), (15,25,35,15), 0.7, 0.6, "high", 1, 1.6, {"tunisie":[10,11], "japon":[10,3]}),
 "soybean":     ("Soja", "Glycine max", "Fabacées", "annual", (0.4,1.15,0.5), (15,15,40,15), 0.9, 0.8, "high", 1, 5.0, {"japon":[6,7]}),
 "alfalfa":     ("Luzerne", "Medicago sativa", "Fabacées", "perennial", (0.4,0.95,0.9), (0,0,365,0), 1.5, 0.6, "high", 1, 2.0, {"tunisie":[10,3], "japon":[9]}),
 "sweet_potato":("Patate douce", "Ipomoea batatas", "Convolvulacées", "annual", (0.5,1.15,0.65), (20,30,60,40), 1.2, 0.4, "high", 0, 1.5, {"japon":[5,6], "tunisie":[4,5]}),
 "strawberry":  ("Fraise", "Fragaria x ananassa", "Rosacées", "annual", (0.4,0.85,0.75), (40,60,90,30), 0.3, 0.2, "medium", 0, 1.0, {"tunisie":[9,10], "japon":[9]}),
 "olive":       ("Olivier", "Olea europaea", "Oléacées", "perennial", (0.65,0.7,0.7), (0,0,365,0), 1.5, 5.0, "high", 0, 4.0, {"tunisie":[1,2,11]}),
 "date_palm":   ("Palmier dattier", "Phoenix dactylifera", "Arécacées", "perennial", (0.95,0.95,0.95), (0,0,365,0), 2.0, 15.0, "high", 0, 4.0, {"tunisie":[3,4]}),
 "orange":      ("Oranger", "Citrus sinensis", "Rutacées", "perennial", (0.7,0.65,0.7), (0,0,365,0), 1.2, 3.5, "high", 0, 1.7, {"tunisie":[2,3]}),
 "mandarin_jp": ("Mandarinier (unshiu)", "Citrus unshiu", "Rutacées", "perennial", (0.7,0.65,0.7), (0,0,365,0), 1.2, 3.0, "high", 0, 1.7, {"japon":[3,4]}),
 "almond":      ("Amandier", "Prunus amygdalus", "Rosacées", "perennial", (0.4,0.9,0.65), (0,0,365,0), 1.5, 5.0, "high", 0, 1.5, {"tunisie":[12,1,2]}),
 "apricot":     ("Abricotier", "Prunus armeniaca", "Rosacées", "perennial", (0.55,0.9,0.65), (0,0,365,0), 1.5, 4.0, "high", 0, 1.6, {"tunisie":[12,1,2]}),
 "grape":       ("Vigne", "Vitis vinifera", "Vitacées", "perennial", (0.3,0.7,0.45), (0,0,365,0), 1.5, 1.8, "high", 0, 1.5, {"tunisie":[1,2], "japon":[3]}),
 "fig":         ("Figuier", "Ficus carica", "Moracées", "perennial", (0.5,0.8,0.6), (0,0,365,0), 1.5, 4.0, "high", 0, 2.5, {"tunisie":[1,2,3]}),
 "pomegranate": ("Grenadier", "Punica granatum", "Lythracées", "perennial", (0.5,0.8,0.6), (0,0,365,0), 1.2, 3.0, "high", 0, 4.0, {"tunisie":[1,2,3]}),
 "pistachio":   ("Pistachier", "Pistacia vera", "Anacardiacées", "perennial", (0.4,1.1,0.45), (0,0,365,0), 1.5, 5.0, "high", 0, 6.0, {"tunisie":[1,2]}),
 "tea":         ("Thé", "Camellia sinensis", "Théacées", "perennial", (0.95,1.0,1.0), (0,0,365,0), 1.2, 1.0, "medium", 0, 1.0, {"japon":[3,4]}),
 # Aromatiques. Menthe : Kc FAO-56 tableau 12. Romarin, thym, basilic : absents de FAO-56, Kc estimés (à affiner).
 # Seuils de sel des aromatiques : estimations (FAO-29 ne les couvre pas).
 "mint":        ("Menthe", "Mentha spicata var. crispa", "Lamiacées", "perennial", (0.6,1.15,1.1), (0,0,365,0), 0.5, 0.5, "medium", 0, 1.5, {"tunisie":[2,3,10], "japon":[4,5]}),
 "rosemary":    ("Romarin", "Rosmarinus officinalis", "Lamiacées", "perennial", (0.4,0.55,0.55), (0,0,365,0), 0.8, 1.0, "medium", 0, 3.0, {"tunisie":[10,11,2,3], "japon":[4]}),
 "thyme":       ("Thym", "Thymus vulgaris", "Lamiacées", "perennial", (0.4,0.55,0.55), (0,0,365,0), 0.4, 0.3, "medium", 0, 2.0, {"tunisie":[10,11,2,3], "japon":[4]}),
 "basil":       ("Basilic", "Ocimum basilicum", "Lamiacées", "annual", (0.6,1.0,0.9), (20,30,40,20), 0.4, 0.5, "medium", 0, 1.5, {"tunisie":[3,4], "japon":[5]}),
}
# Température létale (°C, air) pour cultures endurcies : la valeur KTMP d'EcoCrop (souvent 0 °C)
# est trop prudente pour les cultures d'hiver. Valeurs agronomiques usuelles (à affiner).
KILL_OVERRIDE = {"durum_wheat": -8, "wheat": -10, "barley": -10, "faba_bean": -6, "pea": -6, "chickpea": -6,
                 "onion": -6, "garlic": -8, "cabbage": -6, "carrot": -4, "lettuce": -3, "daikon": -4,
                 "potato": -1, "alfalfa": -10, "olive": -8, "date_palm": -6, "orange": -3, "mandarin_jp": -6,
                 "almond": -10, "apricot": -12, "grape": -15, "fig": -9, "pomegranate": -10, "pistachio": -12,
                 "strawberry": -6, "tea": -12, "rice": 2, "soybean": 0, "sweet_potato": 2,
                 "tomato": 0, "pepper": 0, "eggplant": 0, "melon": 0, "watermelon": 1, "cucumber": 0,
                 "mint": -10, "rosemary": -10, "thyme": -15, "basil": 2}

# Culture en sec : seuils de pluie ANNUELLE calibrés sur la pratique tunisienne (mm/an).
# EcoCrop (mondial) place p. ex. l'optimum de l'orge à 500 mm alors que l'orge pluviale se cultive
# couramment entre 250 et 350 mm en Tunisie centrale. Ajustement d'expert, à confirmer par la validation.
RAIN_OVERRIDE = {
    "barley": (150, 300), "rosemary": (200, 350), "thyme": (250, 400), "durum_wheat": (300, 450), "wheat": (330, 500), "faba_bean": (300, 450),
    "chickpea": (280, 400), "pea": (300, 450), "olive": (150, 300), "almond": (180, 320),
    "pistachio": (150, 280), "fig": (250, 450), "grape": (300, 500),
}
# Cultures qui ne se font pas en sec en Tunisie (oasis, agrumes, maraîchage d'été irrigué…)
NOT_RAINFED_TN = {"date_palm", "orange", "apricot", "pomegranate", "alfalfa", "tomato", "pepper", "eggplant",
                  "melon", "watermelon", "cucumber", "potato", "strawberry", "lettuce", "carrot", "daikon",
                  "cabbage", "sweet_potato"}

# Cultures d'hiver méditerranéennes : EcoCrop donne des optimums de cycles de printemps (ex. blé dur
# 17-25 °C) alors qu'en Tunisie ces cultures poussent de novembre à mai (moyennes 10-20 °C).
# (TMIN, TOPMN, TOPMX, TMAX) en température moyenne — valeurs usuelles des cultures d'hiver.
THERMAL_WINTER = {"durum_wheat": (0, 9, 22, 30), "wheat": (0, 8, 22, 28), "barley": (0, 7, 22, 32),
                  "faba_bean": (2, 9, 22, 30), "chickpea": (3, 10, 25, 33), "pea": (2, 8, 20, 28),
                  "garlic": (2, 10, 24, 32), "onion": (3, 10, 25, 32),
                  # aromatiques méditerranéennes (romarin et thym poussent à l'état sauvage en Tunisie) :
                  # EcoCrop décrit des populations européennes, plus sensibles à la chaleur
                  "rosemary": (3, 12, 30, 40), "thyme": (3, 12, 30, 40)}
NOT_RAINFED_TN.update({"onion", "mint", "basil"})

# Valeur relative indicative de la production par hectare (ordre de grandeur, 1 = céréales/fourrage,
# 3 = cultures à très forte valeur). Sert seulement à départager les cultures dans le plan, quand l'eau
# est limitée. À remplacer par les prix ONAGRI / rendements Agridata.
VALUE = {"date_palm": 3, "pistachio": 2.5, "strawberry": 2,
         "olive": 2, "almond": 2, "grape": 2, "fig": 2, "pomegranate": 2, "orange": 2, "mandarin_jp": 2, "apricot": 2,
         "tomato": 2, "pepper": 2, "eggplant": 2, "melon": 2, "watermelon": 2, "potato": 2, "onion": 2, "garlic": 2,
         "cucumber": 2, "carrot": 2, "cabbage": 2, "lettuce": 2, "sweet_potato": 2, "tea": 2, "rice": 2,
         "mint": 2, "rosemary": 2, "thyme": 2, "basil": 2,
         "chickpea": 1.5, "faba_bean": 1.5, "pea": 1.5, "daikon": 1.5, "soybean": 1.5,
         "barley": 1, "durum_wheat": 1, "wheat": 1, "alfalfa": 1}
# Palmier dattier : la maturation des dattes dépend de la chaleur cumulée (somme des températures
# moyennes journalières au-dessus de 18 °C pendant la fructification). Deglet Nour : ≈ 1 937 °C·j
# (Rekis et al. 2024, Acta Univ. Sapientiae, Biskra). EcoCrop ne le prend pas en compte.
HEAT_UNITS = {"date_palm": {"base": 18, "months": [5, 6, 7, 8, 9, 10], "required": 1940,
                            "source": "Rekis et al. 2024 (Deglet Nour, base 18 °C)"}}

NAMES = {  # (tunisien, japonais)
 "tomato": ("طماطم", "トマト"), "pepper": ("فلفل", "ピーマン・トウガラシ"), "eggplant": ("بادنجان", "ナス"),
 "potato": ("بطاطا", "ジャガイモ"), "onion": ("بصل", "タマネギ"), "garlic": ("ثوم", "ニンニク"),
 "melon": ("بطّيخ", "メロン"), "watermelon": ("دلاّع", "スイカ"), "cucumber": ("خيار", "キュウリ"),
 "carrot": ("سفنارية", "ニンジン"), "lettuce": ("خسّ", "レタス"), "cabbage": ("كرنب", "キャベツ"),
 "daikon": ("فجل", "ダイコン"), "durum_wheat": ("قمح صلب", "デュラム小麦"), "wheat": ("قمح لين", "小麦"),
 "barley": ("شعير", "大麦"), "rice": ("روز", "稲（米）"), "faba_bean": ("فول", "ソラマメ"),
 "chickpea": ("حمّص", "ヒヨコマメ"), "pea": ("جلبانة", "エンドウ"), "soybean": ("صوجا", "大豆"),
 "alfalfa": ("فصّة", "アルファルファ"), "sweet_potato": ("بطاطا حلوة", "サツマイモ"), "strawberry": ("فراولو", "イチゴ"),
 "olive": ("زيتون", "オリーブ"), "date_palm": ("نخلة (دقلة)", "ナツメヤシ"), "orange": ("بردقان", "オレンジ"),
 "mandarin_jp": ("مندرين ياباني", "温州みかん"), "almond": ("لوز", "アーモンド"), "apricot": ("مشمش", "アンズ"),
 "grape": ("دالية (عنب)", "ブドウ"), "fig": ("كرموس", "イチジク"), "pomegranate": ("رمّان", "ザクロ"),
 "pistachio": ("فستق", "ピスタチオ"), "tea": ("تاي", "茶"),
 "mint": ("نعناع", "ミント"), "rosemary": ("إكليل الجبل (روزماري)", "ローズマリー"), "thyme": ("زعتر", "タイム"), "basil": ("حبق", "バジル"),
}

ECO_COLS = ["TOPMN","TOPMX","TMIN","TMAX","KTMP","ROPMN","ROPMX","RMIN","RMAX",
            "PHOPMN","PHOPMX","PHMIN","PHMAX","TEXT","SAL","DEP","DRA","GMIN","GMAX","LIFO"]


def clean(v):
    if isinstance(v, float) and math.isnan(v):
        return None
    return v


out = {}
for cid, (fr, sci, fam, typ, kc, ls, root, h, light, nfix, ece, sow) in C.items():
    row = ECO[ECO.ScientificName == sci]
    if row.empty:
        raise SystemExit(f"EcoCrop introuvable : {sci}")
    eco = {k.lower(): clean(row.iloc[0][k]) for k in ECO_COLS}
    if cid in THERMAL_WINTER:
        eco["tmin"], eco["topmn"], eco["topmx"], eco["tmax"] = THERMAL_WINTER[cid]
        eco["_thermal_source"] = "ajusté : culture d'hiver méditerranéenne"
    out[cid] = {"id": cid, "name_fr": fr, "scientific_name": sci, "family": fam, "type": typ,
                "kc_ini": kc[0], "kc_mid": kc[1], "kc_end": kc[2],
                "l_ini": ls[0], "l_dev": ls[1], "l_mid": ls[2], "l_late": ls[3],
                "root_depth_m": root, "height_m": h, "light_need": light, "n_fixer": nfix,
                "salt_threshold_ece": ece, "sowing_months": sow, "ecocrop": eco,
                "kill_temp": KILL_OVERRIDE.get(cid, eco["ktmp"] if eco["ktmp"] is not None else (eco["tmin"] - 4 if eco["tmin"] is not None else None)),
                "kill_temp_source": "valeur agronomique (culture endurcie)" if cid in KILL_OVERRIDE else "FAO EcoCrop",
                "names": {"fr": fr, "tn": NAMES[cid][0], "ja": NAMES[cid][1]},
                "rainfed_override_tn": RAIN_OVERRIDE.get(cid), "rainfed_possible_tn": cid not in NOT_RAINFED_TN,
                "value_class": VALUE.get(cid, 1.5), "heat_units": HEAT_UNITS.get(cid)}
json.dump(out, open("data/crops.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(out), "cultures")
for k, v in out.items():
    e = v["ecocrop"]
    print(f"{k:13} opt {e['topmn']}-{e['topmx']} abs {e['tmin']}-{e['tmax']} kill {e['ktmp']} rain {e['rmin']}-{e['rmax']} pH {e['phmin']}-{e['phmax']} text={e['text']} sal={e['sal']}")

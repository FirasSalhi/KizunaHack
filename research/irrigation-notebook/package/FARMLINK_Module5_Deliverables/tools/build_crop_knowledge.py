"""Build crop_knowledge/{crop_database.json, crop_parameters.csv, crop_sources.json}.

Numerical agronomic values below were transcribed from FAO-56 (Allen et al., 1998) Tables 11, 12 and 22 as returned by
a text-extraction service on 2026-11-21. Limits of that extraction (stated, not hidden):
  * Table 12: individual Kc_ini values are printed in an image column that the extraction did not expose. Where a crop's own
    Kc_ini was unavailable, the FAO-56 *group default* row is used and labelled FAO56_TABLE12_GROUP_DEFAULT.
  * All values should be re-checked against the FAO-56 PDF before operational use (confidence != locally_validated).
Nothing here is Tunisia-validated. ECOCROP / CROPWAT / WaPOR tables could NOT be retrieved from the build environment
(no outbound access); the corresponding fields are null and listed under `missing`.
"""
import csv, json, pathlib, datetime

OUT = pathlib.Path(__file__).resolve().parent.parent / "crop_knowledge"
OUT.mkdir(exist_ok=True)

SRC = {
    "FAO56_T12": {"title": "FAO Irrigation & Drainage Paper 56, Table 12 - single crop coefficients Kc and mean max plant height", "url": "https://www.fao.org/4/x0490e/x0490e0b.htm"},
    "FAO56_T11": {"title": "FAO-56, Table 11 - lengths of crop development stages", "url": "https://www.fao.org/4/x0490e/x0490e0b.htm"},
    "FAO56_T22": {"title": "FAO-56, Table 22 - maximum effective rooting depth Zr and depletion fraction p (ETc ~5 mm/day)", "url": "https://www.fao.org/4/x0490e/x0490e0e.htm"},
    "FAO56_EX38": {"title": "FAO-56, Example 38 - only documented starting root depth (0.3 m on day 1, one example)", "url": "https://www.fao.org/4/x0490e/x0490e0e.htm"},
    "CURATED_NAMES": {"title": "Scientific/French/Arabic names curated by the FARMLINK developers (not taken from FAO tables; unverified against ECOCROP)", "url": None},
}
RETRIEVAL_NOTE = ("Values transcribed from FAO-56 via a text-extraction service on 2026-11-21; Kc_ini per crop often unavailable "
                  "(image column) -> group default used where flagged; re-verify against the PDF before operational use.")

DOC, GRP, GEN = "directly_documented", "derived_from_published_reference", "generic_crop_approximation"

# id, en, sci, fr, ar, synonyms, family, category, perennial,
#   kc(ini, ini_src, mid, end, end_low, end_high, mid_alt_note), h, zr(min,max), p, stage(default or None), notes, approx
def C(id, en, sci, fr, ar, syn, fam, cat, per, kc, h, zr, p, stage=None, variants=None, notes=(), approx=(), conf_overrides=None, kc_variants=None):
    return dict(id=id, en=en, sci=sci, fr=fr, ar=ar, syn=syn, fam=fam, cat=cat, per=per, kc=kc, h=h, zr=zr, p=p,
                stage=stage, variants=variants or [], notes=list(notes), approx=list(approx), conf=conf_overrides or {}, kcv=kc_variants or [])

T = "FAO56_TABLE12"; G = "FAO56_TABLE12_GROUP_DEFAULT"
def kc(ini, ini_src, mid, end, lo=None, hi=None):
    return dict(ini=ini, ini_source=ini_src, mid=mid, end=end, end_low=lo if lo is not None else end, end_high=hi if hi is not None else end)
def st(i, d, m, l, region, plant, total_note=""):
    return dict(ini=i, dev=d, mid=m, late=l, total=i + d + m + l, region=region, plant_date=plant, note=total_note)

CROPS = [
 C("tomato","Tomato","Solanum lycopersicum","Tomate","طماطم",["tomatoes","tomate","tamatem","طماطم","banadoura"],"Solanaceae","vegetable",False,
   kc(0.60,G,1.15,0.80,0.70,0.90),0.6,(0.7,1.5),0.40,st(30,40,45,30,"Mediterranean","April/May"),
   [st(35,45,70,30,"Arid region","Oct/Nov"),st(30,40,40,25,"Arid region","January")],
   ["Table 12 footnote 2: tomatoes on stakes (1.5-2 m) may need Kc mid ~1.20 and higher h.","Greenhouse tomatoes need indoor ETo; outdoor weather does not apply directly."],
   ["Kc end is the midpoint of the published range 0.70-0.90."]),
 C("sweet_pepper","Sweet pepper","Capsicum annuum","Poivron","فلفل",["pepper","bell pepper","peppers","piment doux","poivron","فلفل حلو","felfel"],"Solanaceae","vegetable",False,
   kc(0.60,G,1.05,0.90),0.7,(0.5,1.0),0.30,st(30,35,40,20,"Europe and Mediterranean","April/June","printed Linit '25/30'; 30 used (sum matches printed 125)"),
   [st(30,40,110,30,"Arid region","October")],["Table 12 footnote 2: crops grown on stalks may need higher Kc."],[]),
 C("eggplant","Eggplant","Solanum melongena","Aubergine","باذنجان",["aubergine","brinjal","aubergines","badhinjan"],"Solanaceae","vegetable",False,
   kc(0.60,G,1.05,0.90),0.8,(0.7,1.2),0.45,st(30,45,40,25,"Mediterranean","May/June","source prints total '40*' but stages sum to 140; stages used"),
   [st(30,40,40,20,"Arid region","October")],[],["Stage-length row has a printed inconsistency (see note)."]),
 C("potato","Potato","Solanum tuberosum","Pomme de terre","بطاطا",["potatoes","patate","pomme de terre","batata","بطاطس"],"Solanaceae","vegetable",False,
   kc(0.50,G,1.15,0.75),0.6,(0.4,0.6),0.35,st(25,30,45,30,"(Semi) arid climate","Jan/Nov","printed mid '30/45' and total '115/130'; the 45 / 130 variant is used"),
   [st(30,35,50,30,"Europe","April"),st(25,30,45,30,"Continental","May")],
   ["Table 12 footnote 4: Kc end ~0.40 for long-season potatoes with vine kill."],["Shallow Zr (0.4-0.6 m) makes TAW small: irrigation is frequent."]),
 C("onion_dry","Onion (dry)","Allium cepa","Oignon sec","بصل",["onion","onions","oignon","basal"],"Amaryllidaceae","vegetable",False,
   kc(0.70,G,1.05,0.75),0.4,(0.3,0.6),0.30,st(15,25,70,40,"Mediterranean","April"),[st(20,35,110,45,"Arid region / California","Oct; Jan")],[],[]),
 C("garlic","Garlic","Allium sativum","Ail","ثوم",["ail","thoum"],"Amaryllidaceae","vegetable",False,kc(0.70,G,1.00,0.70),0.3,(0.3,0.5),0.30,None,[],[],[]),
 C("carrot","Carrot","Daucus carota","Carotte","جزر",["carrots","carotte","jazar"],"Apiaceae","vegetable",False,kc(0.70,G,1.05,0.95),0.3,(0.5,1.0),0.35,None,[],[],[]),
 C("cabbage","Cabbage","Brassica oleracea var. capitata","Chou","ملفوف",["chou","kronb","كرنب"],"Brassicaceae","vegetable",False,kc(0.70,G,1.05,0.95),0.4,(0.5,0.8),0.45,None,[],[],[]),
 C("cauliflower","Cauliflower","Brassica oleracea var. botrytis","Chou-fleur","قرنبيط",["chou-fleur","karnabit"],"Brassicaceae","vegetable",False,kc(0.70,G,1.05,0.95),0.4,(0.4,0.7),0.45,None,[],[],[]),
 C("lettuce","Lettuce","Lactuca sativa","Laitue","خس",["laitue","khass"],"Asteraceae","vegetable",False,kc(0.70,G,1.00,0.95),0.3,(0.3,0.5),0.30,None,[],[],[]),
 C("spinach","Spinach","Spinacia oleracea","Épinard","سبانخ",["epinard","spinaches","sabanekh"],"Amaranthaceae","vegetable",False,kc(0.70,G,1.00,0.95),0.3,(0.3,0.5),0.20,None,[],[],[]),
 C("cucumber","Cucumber","Cucumis sativus","Concombre","خيار",["cucumbers","concombre","khyar"],"Cucurbitaceae","vegetable",False,
   kc(0.60,T,1.00,0.75),0.3,(0.7,1.2),0.50,st(25,35,50,20,"Arid region","Nov; Feb"),[st(20,30,40,15,"Arid region","June/Aug")],["Fresh-market values; machine-harvest: Kc ini 0.5, end 0.90."],[]),
 C("melon","Melon (sweet)","Cucumis melo","Melon","شمام",["melons","cantaloupe","sweet melon","bettikh asfar","بطيخ أصفر"],"Cucurbitaceae","vegetable",False,
   kc(0.50,G,1.05,0.75),0.4,(0.8,1.5),0.40,st(25,35,40,20,"Mediterranean","May"),[st(30,45,65,20,"Arid region","Dec/Jan")],["Cantaloupe has different values (Kc mid 0.85)."],[]),
 C("watermelon","Watermelon","Citrullus lanatus","Pastèque","دلاع",["watermelons","pasteque","dellaa","بطيخ"],"Cucurbitaceae","vegetable",False,
   kc(0.40,T,1.00,0.75),0.4,(0.8,1.5),0.40,st(20,30,30,30,"Italy","April"),[st(10,20,20,30,"Near East (desert)","Mar/Aug")],[],[]),
 C("zucchini","Zucchini","Cucurbita pepo","Courgette","كوسة",["squash","courgette","kousa"],"Cucurbitaceae","vegetable",False,kc(0.50,G,0.95,0.75),0.3,(0.6,1.0),0.50,None,[],[],[]),
 C("artichoke","Artichoke","Cynara cardunculus var. scolymus","Artichaut","قنارية",["artichaut","guenarya"],"Asteraceae","vegetable",True,kc(0.50,T,1.00,0.95),0.7,(0.6,0.9),0.45,None,[],[],[]),
 C("green_bean","Green bean","Phaseolus vulgaris","Haricot vert","لوبيا خضراء",["beans","haricot","string bean","loubia"],"Fabaceae","legume",False,
   kc(0.50,T,1.05,0.90),0.4,(0.5,0.7),0.45,st(20,30,30,10,"California / Mediterranean","Feb/Mar"),[st(15,25,25,10,"California / Egypt / Lebanon","Aug/Sep")],[],[]),
 C("faba_bean","Faba (broad) bean, dry","Vicia faba","Fève (sèche)","فول",["broad bean","fava","feve","foul","fèves"],"Fabaceae","legume",False,
   kc(0.50,T,1.15,0.30),0.8,(0.5,0.7),0.45,st(90,45,40,60,"Europe (autumn sowing)","November","region = Europe, not Tunisia; autumn sowing assumed typical -> regionally_estimated"),
   [st(20,30,35,15,"Mediterranean","Mar/Apr")],["Fresh-harvest variant: Kc end 1.10."],["Stage lengths come from a European row."],
   conf_overrides={"stage_lengths":"regionally_estimated"}),
 C("chickpea","Chickpea","Cicer arietinum","Pois chiche","حمص",["pois chiche","hummus","chick pea"],"Fabaceae","legume",False,kc(0.40,G,1.00,0.35),0.4,(0.6,1.0),0.50,None,[],[],[]),
 C("lentil","Lentil","Lens culinaris","Lentille","عدس",["lentilles","adas"],"Fabaceae","legume",False,kc(0.40,G,1.10,0.30),0.5,(0.6,0.8),0.50,None,[],[],[]),
 C("durum_wheat","Durum wheat","Triticum turgidum subsp. durum","Blé dur","قمح صلب",["wheat","durum","ble dur","blé","قمح","qamh"],"Poaceae","cereal",False,
   kc(0.70,T,1.15,0.325,0.25,0.40),1.0,(1.5,1.8),0.55,st(30,140,40,30,"Mediterranean","November"),[st(20,60,70,30,"California","December")],
   ["FAO-56 has NO durum-specific row: generic WINTER WHEAT (non-frozen soils) values are used.","Kc ini 0.7 is wetting-frequency dependent (Table 12 note); likely high for dry, infrequently wetted soil.","In Tunisia durum wheat is mostly rainfed with supplementary irrigation."],
   ["Generic winter-wheat parameters, not durum-specific.","Zr 1.5-1.8 m is the winter-wheat range; spring wheat 1.0-1.5 m."],conf_overrides={"kc":GEN,"zr":GEN,"p":GEN,"stage_lengths":GEN}),
 C("barley","Barley","Hordeum vulgare","Orge","شعير",["orge","chaair"],"Poaceae","cereal",False,kc(0.30,G,1.15,0.25),1.0,(1.0,1.5),0.55,st(40,60,60,40,"(region unspecified in table)","November"),[],[],["Stage lengths from the grouped 'Barley/Oats/Wheat' row, region unspecified."],conf_overrides={"stage_lengths":GRP}),
 C("maize_grain","Maize (grain)","Zea mays","Maïs grain","ذرة",["corn","maize","mais","dhoura"],"Poaceae","cereal",False,kc(0.30,G,1.20,0.475,0.35,0.60),2.0,(1.0,1.7),0.55,st(30,40,50,30,"Spain / California","April"),[st(25,40,45,30,"Arid climate","Dec/Jan")],["Kc end: 0.60 (high grain moisture) to 0.35 (field-dried)."],[]),
 C("sunflower","Sunflower","Helianthus annuus","Tournesol","دوار الشمس",["tournesol","ain echams"],"Asteraceae","oilseed",False,kc(0.35,G,1.075,0.35,None,None),2.0,(0.8,1.5),0.45,st(25,35,45,25,"Mediterranean / California","April/May"),[],["Kc mid printed as 1.0-1.15; midpoint used (kc_mid_range stored)."],["Kc mid is a range midpoint."]),
 C("alfalfa","Alfalfa (hay)","Medicago sativa","Luzerne","برسيم حجازي",["lucerne","luzerne","fessa"],"Fabaceae","forage",True,kc(0.40,T,0.95,0.90),0.7,(1.0,2.0),0.55,None,[],["Stage lengths are per cutting cycle (not a planting-date calendar)."],[]),
 C("sugar_beet","Sugar beet","Beta vulgaris","Betterave sucrière","شمندر سكري",["betterave","sugarbeet","chamandar"],"Amaranthaceae","industrial",False,kc(0.35,T,1.20,0.70),0.5,(0.7,1.2),0.55,None,[],["Footnote 5: Kc end can rise to 1.0 with irrigation/rain in the last month."],[]),
 C("strawberry","Strawberry","Fragaria x ananassa","Fraise","فراولة",["fraise","fraises","farawla"],"Rosaceae","fruit",False,kc(0.40,T,0.85,0.75),0.2,(0.2,0.3),0.20,None,[],[],[]),
 C("olive","Olive","Olea europaea","Olivier (olive)","زيتون",["olives","olivier","olea","zitoun","zitouna"],"Oleaceae","tree",True,kc(0.65,T,0.70,0.70),4.0,(1.2,1.7),0.65,st(30,90,60,90,"Mediterranean","March","stage lengths describe a first-year planting example; mature orchards are phenological"),[],
   ["Table 12 footnote 24: values represent 40-60 % ground cover; a Spanish monthly set also exists.","Evergreen: 'stages' are phenological phases with weak Kc contrast; deficit irrigation is common."],["Canopy-cover dependent: sparse groves need a cover-based reduction not applied here."],conf_overrides={"kc":DOC}),
 C("almond","Almond","Prunus dulcis","Amandier","لوز",["almonds","amande","amandier","louz"],"Rosaceae","tree",True,kc(0.40,T,0.90,0.65),5.0,(1.0,2.0),0.40,None,[],["Footnote 18: Kc end applies before leaf drop; no ground cover assumed."],[]),
 C("pistachio","Pistachio","Pistacia vera","Pistachier","فستق",["pistachios","pistache","fostok"],"Anacardiaceae","tree",True,kc(0.40,T,1.10,0.45),4.0,(1.0,1.5),0.40,None,[],[],[]),
 C("walnut","Walnut","Juglans regia","Noyer","جوز",["noix","noyer","walnuts"],"Juglandaceae","tree",True,kc(0.50,T,1.10,0.65),4.5,(1.7,2.4),0.50,None,[],[],[]),
 C("apple","Apple / Pear / Cherry","Malus domestica","Pommier (pommes/poires/cerises)","تفاح",["apples","pomme","pommier","pear","cherry","tofah"],"Rosaceae","tree",True,kc(0.60,T,0.95,0.75),4.0,(1.0,2.0),0.50,None,[],["Variant 'no killing frost' used; 'killing frost' variant: 0.45/0.95/0.70."],["Frost regime of the orchard decides the variant."],kc_variants=[dict(label="killing frost",ini=0.45,mid=0.95,end=0.70)]),
 C("stone_fruit","Stone fruit (peach, apricot, plum)","Prunus persica","Arbres à noyau (pêcher, abricotier, prunier)","فواكه ذات نواة",["peach","apricot","plum","peche","abricot","prunier","khokh","مشمش","خوخ"],"Rosaceae","tree",True,kc(0.55,T,0.90,0.65),3.0,(1.0,2.0),0.50,None,[],["Variant 'no killing frost' used; frost variant 0.45/0.90/0.65."],["Table 22 lists peaches/apricots; plums are not listed separately."],kc_variants=[dict(label="killing frost",ini=0.45,mid=0.90,end=0.65)]),
 C("citrus","Citrus (orange, lemon, mandarin)","Citrus x sinensis","Agrumes (oranger, citronnier, mandarinier)","حمضيات",["orange","lemon","mandarin","clementine","agrumes","orange tree","citron","limoun","bortokal","برتقال","ليمون"],"Rutaceae","tree",True,
   kc(0.65,T,0.60,0.65),3.0,(1.1,1.5),0.50,st(60,90,120,95,"Mediterranean","January","365-day annual cycle example"),[],
   ["Table 12 lists citrus by canopy cover (70 %: 0.70/0.65/0.70; 50 %: 0.65/0.60/0.65; 20 %: 0.50/0.45/0.55), not by species. 50 % canopy is the default here.","With active ground cover Kc is higher (footnote 22)."],["Canopy fraction of the grove is unknown -> 50 % variant assumed."],
   kc_variants=[dict(label="70% canopy",ini=0.70,mid=0.65,end=0.70),dict(label="20% canopy",ini=0.50,mid=0.45,end=0.55)]),
 C("grape_wine","Grape (wine)","Vitis vinifera","Vigne (raisin de cuve)","عنب",["grapes","vigne","raisin","vine","dalia"],"Vitaceae","fruit",True,kc(0.30,T,0.70,0.45),1.75,(1.0,2.0),0.45,st(30,60,40,80,"Mid latitudes (wine)","April"),[],[],[]),
 C("grape_table","Grape (table/raisin)","Vitis vinifera","Raisin de table","عنب مائدة",["table grapes","raisin de table"],"Vitaceae","fruit",True,kc(0.30,T,0.85,0.45),2.0,(1.0,2.0),0.35,st(20,50,75,60,"California (proxy)","March","California row used as proxy"),[],[],["Stage lengths borrowed from a California row."],conf_overrides={"stage_lengths":GRP}),
 C("date_palm","Date palm","Phoenix dactylifera","Palmier dattier","نخيل التمر",["dates","datte","palmier","nakhl","deglet nour"],"Arecaceae","tree",True,kc(0.90,T,0.95,0.95),8.0,(1.5,2.5),0.50,None,[],[],[]),
 C("fig","Fig","Ficus carica","Figuier","تين",["figs","figue","karmous"],"Moraceae","tree",True,None,None,None,None,None,[],["Not listed in FAO-56 Tables 12/22: all irrigation parameters unavailable from this source."],[]),
 C("pomegranate","Pomegranate","Punica granatum","Grenadier","رمان",["grenade","rommane","grenadier"],"Lythraceae","tree",True,None,None,None,None,None,[],["Not listed in FAO-56 Tables 12/22 (appears only in the salinity table)."],[]),
]

def build():
    db, rows = [], []
    for c in CROPS:
        k = c["kc"]
        missing = []
        if k is None: missing += ["kc","zr","p"]
        if c["stage"] is None: missing.append("stage_lengths")
        missing += ["water_sensitivity_ky","ecocrop_environmental_requirements","planting_calendar_tunisia","harvest_calendar_tunisia","arabic_name_verification"]
        conf = {"kc": DOC if k and k["ini_source"] == T else (GRP if k else "missing"),
                "zr": DOC if k else "missing", "p": DOC if k else "missing",
                "stage_lengths": GRP if c["stage"] else "missing", "names": "curated_unverified"}
        conf.update(c["conf"])
        if k and k["ini_source"] == G and "kc" not in c["conf"]: conf["kc"] = GRP
        rec = {
            "id": c["id"], "names": {"en": c["en"], "scientific": c["sci"], "fr": c["fr"], "ar": c["ar"], "synonyms": c["syn"], "names_source": "CURATED_NAMES"},
            "family": c["fam"], "category": c["cat"], "perennial": c["per"], "variety": None,
            "kc": None if not k else {"ini": k["ini"], "ini_source": k["ini_source"], "mid": k["mid"], "end": k["end"], "end_low": k["end_low"], "end_high": k["end_high"],
                                       "variants": c["kcv"], "source": "FAO56_T12"},
            "max_plant_height_m": c["h"],
            "root_depth": None if not k else {"zr_min_m": c["zr"][0], "zr_max_m": c["zr"][1], "default_for_scheduling_m": c["zr"][0], "source": "FAO56_T22",
                                               "development": {"model": "linear_from_initial_to_zr_max_over_initial_plus_development_stages", "initial_zr_m_assumption": 0.3,
                                                               "initial_zr_source": "FAO56_EX38 (single worked example; ASSUMPTION for all crops, capped at zr_min)", "perennial_constant": c["per"]}},
            "depletion_fraction_p": None if not k else {"value": c["p"], "reference_etc_mm_day": 5.0, "adjustment": "p = p + 0.04 (5 - ETc), clamp 0.1-0.8", "source": "FAO56_T22"},
            "growth_stages": ["initial", "development", "mid_season", "late_season"],
            "stage_lengths_days": None if not c["stage"] else {**c["stage"], "source": "FAO56_T11"},
            "stage_length_variants": c["variants"],
            "typical_duration_days": None if not c["stage"] else c["stage"]["total"],
            "planting_calendar": None if not c["stage"] else {"as_published": c["stage"]["plant_date"], "region": c["stage"]["region"], "note": "Plant date of the FAO-56 example row, not a Tunisian calendar."},
            "harvest_calendar": None,
            "climate_requirements": None, "temperature_requirements": None, "soil_requirements": None, "water_sensitivity": None,
            "ecocrop": {"retrieved": False, "reason": "build environment had no outbound network access"},
            "irrigation_notes": c["notes"], "approximations": c["approx"], "missing": missing,
            "confidence": conf, "sources": ["FAO56_T12", "FAO56_T11", "FAO56_T22", "FAO56_EX38", "CURATED_NAMES"] if k else ["CURATED_NAMES"],
            "irrigation_ready": bool(k),
        }
        db.append(rec)
        rows.append({"id": c["id"], "name_en": c["en"], "name_fr": c["fr"], "name_ar": c["ar"], "scientific_name": c["sci"], "family": c["fam"], "category": c["cat"], "perennial": c["per"],
                     "kc_ini": k and k["ini"], "kc_ini_source": k and k["ini_source"], "kc_mid": k and k["mid"], "kc_end": k and k["end"],
                     "zr_min_m": k and c["zr"][0], "zr_max_m": k and c["zr"][1], "p": k and c["p"],
                     "stage_ini_d": c["stage"] and c["stage"]["ini"], "stage_dev_d": c["stage"] and c["stage"]["dev"], "stage_mid_d": c["stage"] and c["stage"]["mid"], "stage_late_d": c["stage"] and c["stage"]["late"],
                     "stage_region": c["stage"] and c["stage"]["region"], "irrigation_ready": bool(k), "confidence_kc": conf["kc"], "confidence_stage_lengths": conf["stage_lengths"],
                     "missing": "|".join(missing)})
    meta = {"schema_version": "1.0", "generated_utc": datetime.datetime.utcnow().isoformat() + "Z", "n_crops": len(db),
            "n_irrigation_ready": sum(r["irrigation_ready"] for r in db), "retrieval_note": RETRIEVAL_NOTE}
    (OUT / "crop_database.json").write_text(json.dumps({"meta": meta, "crops": db}, ensure_ascii=False, indent=1), encoding="utf-8")
    with open(OUT / "crop_parameters.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    (OUT / "crop_sources.json").write_text(json.dumps({"sources": SRC, "retrieval_note": RETRIEVAL_NOTE,
        "not_retrieved": ["FAO ECOCROP (environmental requirements)", "FAO CROPWAT tables", "FAO WaPOR", "FAO-33 yield response factors (water sensitivity)", "FAO-56 Table 19 (soil water characteristics)"],
        "confidence_labels": {DOC: "value printed in the cited FAO-56 table row", GRP: "group default / interpolation / adjacent-row proxy", GEN: "generic parameters of a related crop (e.g. winter wheat for durum)",
                              "regionally_estimated": "published value from another region used as estimate", "locally_validated": "NOT USED - no local validation exists", "curated_unverified": "names curated by developers"}}, ensure_ascii=False, indent=1), encoding="utf-8")
    return meta

if __name__ == "__main__":
    print(build())

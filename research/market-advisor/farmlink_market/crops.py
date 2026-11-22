"""Crop registry: one id per crop, with its names in each source.

Every mapping below is a naming correspondence between sources (not data). When a source groups
crops (e.g. the Ministry series "Pastèque _Melon" or "Piment"), the group is kept as its own id
and never split with an invented ratio.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Crop:
    id: str
    fr: str
    ar: str
    en: str
    category: str  # vegetable | fruit
    scientific: str = ""
    perennial: bool = False
    # Ministry of Agriculture national series on data.gov.tn (vegetables 2004-2025)
    moa_veg: str | None = None
    # INS bulletin table 9.5 (Tunis wholesale market arrivals)
    tunis_arrivals: tuple[str, ...] = ()
    # INS bulletin table 9.1 (retail prices in Tunis), only items sold per kg
    tunis_retail: tuple[str, ...] = ()
    # FAOSTAT item names (Tunisia)
    faostat: tuple[str, ...] = ()
    # Sidi Bouzid regional price monitoring (data.gov.tn)
    sidi_bouzid: tuple[str, ...] = ()
    # FAO-56 crop knowledge base id (water requirements), from the irrigation module
    fao56: str | None = None
    group: str | None = None  # parent id when a source only reports the group
    notes: tuple[str, ...] = field(default_factory=tuple)


CROPS: list[Crop] = [
    # ---- vegetables with official national series (Ministry of Agriculture) ----
    Crop("tomato", "Tomate", "طماطم", "Tomato", "vegetable", "Solanum lycopersicum",
         moa_veg="Tomate", tunis_arrivals=("Tomate",), tunis_retail=("Tomates",),
         faostat=("Tomatoes",), fao56="tomato"),
    Crop("potato", "Pomme de terre", "بطاطا", "Potato", "vegetable", "Solanum tuberosum",
         moa_veg="Pomme_de_terre", tunis_arrivals=("Pomme de terre",), tunis_retail=("Pommes de terre",),
         faostat=("Potatoes",), sidi_bouzid=("pomme de terre",), fao56="potato"),
    Crop("onion", "Oignon", "بصل", "Onion (dry)", "vegetable", "Allium cepa",
         moa_veg="Oignon", tunis_arrivals=("Oignons",), tunis_retail=("Oignons secs",),
         faostat=("Onions and shallots, dry (excluding dehydrated)",), sidi_bouzid=("oignon",), fao56="onion_dry"),
    Crop("pepper", "Piment / poivron", "فلفل", "Chilli & pepper", "vegetable", "Capsicum annuum",
         moa_veg="Piment", faostat=("Chillies and peppers, green (Capsicum spp. and Pimenta spp.)",),
         fao56="sweet_pepper",
         notes=("La série du ministère « Piment » couvre tous les piments et poivrons ; le marché de Tunis distingue doux et piquant.",)),
    Crop("sweet_pepper", "Poivron doux", "فلفل حلو", "Sweet pepper", "vegetable", "Capsicum annuum",
         tunis_arrivals=("Poivron doux",), tunis_retail=("Poivrons doux frais",), sidi_bouzid=("piment doux",),
         fao56="sweet_pepper", group="pepper"),
    Crop("hot_pepper", "Piment piquant", "فلفل حار", "Hot pepper", "vegetable", "Capsicum annuum",
         tunis_arrivals=("Poivron piquant",), tunis_retail=("Poivrons piquants frais",),
         sidi_bouzid=("piment piquant",), fao56="sweet_pepper", group="pepper"),
    Crop("watermelon_melon", "Pastèque et melon", "دلاع و بطيخ", "Watermelon & melon", "vegetable",
         "Citrullus lanatus / Cucumis melo", moa_veg="Pastèque _Melon", fao56="watermelon",
         notes=("Le ministère publie la pastèque et le melon ensemble.",)),
    Crop("watermelon", "Pastèque", "دلاع", "Watermelon", "fruit", "Citrullus lanatus",
         tunis_arrivals=("Pastèques",), tunis_retail=("Pastèques",), faostat=("Watermelons",),
         fao56="watermelon", group="watermelon_melon"),
    Crop("melon", "Melon", "بطيخ", "Melon", "fruit", "Cucumis melo",
         tunis_arrivals=("Melons",), tunis_retail=("Melons",), faostat=("Cantaloupes and other melons",),
         fao56="melon", group="watermelon_melon"),
    Crop("artichoke", "Artichaut", "قنارية", "Artichoke", "vegetable", "Cynara cardunculus var. scolymus",
         moa_veg="Artichaut", faostat=("Artichokes",), fao56="artichoke",
         notes=("Le prix de détail à Tunis est donné pour 3 pièces, pas au kg : non converti.",)),
    # ---- other vegetables: Tunis market + FAOSTAT only ----
    Crop("carrot", "Carotte", "سفنارية", "Carrot", "vegetable", "Daucus carota",
         tunis_arrivals=("Carotte",), tunis_retail=("Carottes",), faostat=("Carrots and turnips",), fao56="carrot",
         notes=("FAOSTAT regroupe carottes et navets.",)),
    Crop("cabbage", "Chou", "كرنب", "Cabbage", "vegetable", "Brassica oleracea",
         tunis_arrivals=("Choux",), tunis_retail=("Choux",), faostat=("Cabbages",), fao56="cabbage"),
    Crop("cauliflower", "Chou-fleur", "بروكلو", "Cauliflower", "vegetable", "Brassica oleracea var. botrytis",
         tunis_arrivals=("Choux- fleur",), faostat=("Cauliflowers and broccoli",), fao56="cauliflower"),
    Crop("cucumber", "Concombre", "فقوس", "Cucumber", "vegetable", "Cucumis sativus",
         tunis_arrivals=("Concombre",), faostat=("Cucumbers and gherkins",), fao56="cucumber"),
    Crop("squash", "Courge", "قرع أحمر", "Squash", "vegetable", "Cucurbita maxima",
         tunis_arrivals=("Courge",), tunis_retail=("Courges",), faostat=("Pumpkins, squash and gourds",)),
    Crop("zucchini", "Courgette", "قرع بوطزينة", "Zucchini", "vegetable", "Cucurbita pepo",
         tunis_arrivals=("Courgette",), fao56="zucchini"),
    Crop("spinach", "Épinard", "سبناخ", "Spinach", "vegetable", "Spinacia oleracea",
         tunis_arrivals=("Epinard",), faostat=("Spinach",), fao56="spinach"),
    Crop("fennel", "Fenouil", "بسباس", "Fennel", "vegetable", "Foeniculum vulgare",
         tunis_arrivals=("Fenouil",), tunis_retail=("Fenouils",)),
    Crop("faba_bean", "Fève verte", "فول", "Broad bean (green)", "vegetable", "Vicia faba",
         tunis_arrivals=("Fève",), tunis_retail=("Fèves vertes",),
         faostat=("Broad beans and horse beans, green",), fao56="faba_bean"),
    Crop("turnip", "Navet", "لفت", "Turnip", "vegetable", "Brassica rapa",
         tunis_arrivals=("Navet",), tunis_retail=("Navets",)),
    Crop("parsley", "Persil", "معدنوس", "Parsley", "vegetable", "Petroselinum crispum",
         tunis_arrivals=("Persil",)),
    Crop("pea", "Petit pois", "جلبانة", "Green pea", "vegetable", "Pisum sativum",
         tunis_arrivals=("Petit- pois",), tunis_retail=("Petits pois frais",), faostat=("Peas, green",)),
    Crop("lettuce", "Salade", "سلاطة", "Lettuce", "vegetable", "Lactuca sativa",
         tunis_arrivals=("Salade",), faostat=("Lettuce and chicory",), fao56="lettuce"),
    Crop("chard", "Blette", "سلق", "Chard", "vegetable", "Beta vulgaris subsp. vulgaris",
         tunis_arrivals=("Blette",)),
    Crop("garlic", "Ail", "ثوم", "Garlic", "vegetable", "Allium sativum",
         tunis_retail=("Ails secs",), faostat=("Green garlic",), fao56="garlic"),
    # ---- fruits ----
    Crop("apricot", "Abricot", "مشمش", "Apricot", "fruit", "Prunus armeniaca", perennial=True,
         tunis_arrivals=("Abricots",), faostat=("Apricots",), fao56="stone_fruit"),
    Crop("green_almond", "Amande verte", "لوز أخضر", "Green almond", "fruit", "Prunus dulcis", perennial=True,
         tunis_arrivals=("Amandes vertes",), fao56="almond"),
    Crop("lemon", "Citron", "ليمون", "Lemon", "fruit", "Citrus limon", perennial=True,
         tunis_arrivals=("Citrons",), tunis_retail=("Citrons",), faostat=("Lemons and limes",), fao56="citrus"),
    Crop("clementine", "Clémentine", "كليمنتين", "Clementine", "fruit", "Citrus clementina", perennial=True,
         tunis_arrivals=("Clémentines",), sidi_bouzid=("clémentine",),
         faostat=("Tangerines, mandarins, clementines",), fao56="citrus"),
    Crop("orange_maltese", "Orange maltaise", "برتقال مالطي", "Maltese orange", "fruit", "Citrus sinensis",
         perennial=True, tunis_arrivals=("Oranges maltaises",), tunis_retail=("Oranges maltaises",),
         sidi_bouzid=("maltaise",), fao56="citrus", group="orange"),
    Crop("orange_sweet", "Orange douce", "برتقال حلو", "Sweet orange", "fruit", "Citrus sinensis",
         perennial=True, tunis_arrivals=("Oranges douces",), tunis_retail=("Oranges douces",),
         sidi_bouzid=("thomson",), fao56="citrus", group="orange"),
    Crop("orange", "Orange", "برتقال", "Orange", "fruit", "Citrus sinensis", perennial=True,
         faostat=("Oranges",), fao56="citrus"),
    Crop("date", "Datte", "تمور", "Date", "fruit", "Phoenix dactylifera", perennial=True,
         tunis_arrivals=("Dattes",), tunis_retail=("Dégela",), faostat=("Dates",), fao56="date_palm",
         notes=("Le prix de détail « Dégela » à Tunis correspond aux dattes Deglet Nour.",)),
    Crop("fig", "Figue", "تين", "Fig", "fruit", "Ficus carica", perennial=True,
         tunis_arrivals=("Figues",), faostat=("Figs",), fao56="fig"),
    Crop("strawberry", "Fraise", "فراولة", "Strawberry", "fruit", "Fragaria × ananassa",
         tunis_arrivals=("Fraises",), faostat=("Strawberries",), fao56="strawberry"),
    Crop("pomegranate", "Grenade", "رمان", "Pomegranate", "fruit", "Punica granatum", perennial=True,
         tunis_arrivals=("Grenades",), fao56="pomegranate"),
    Crop("loquat", "Nèfle", "بوصاع", "Loquat", "fruit", "Eriobotrya japonica", perennial=True,
         tunis_arrivals=("Nefles",)),
    Crop("peach", "Pêche", "خوخ", "Peach", "fruit", "Prunus persica", perennial=True,
         tunis_arrivals=("Pêches",), faostat=("Peaches and nectarines",), fao56="stone_fruit"),
    Crop("pear", "Poire", "إجاص", "Pear", "fruit", "Pyrus communis", perennial=True,
         tunis_arrivals=("Poires",), faostat=("Pears",)),
    Crop("apple", "Pomme", "تفاح", "Apple", "fruit", "Malus domestica", perennial=True,
         tunis_arrivals=("Pommes",), sidi_bouzid=("pommes",), faostat=("Apples",), fao56="apple"),
    Crop("plum", "Prune", "عوينة", "Plum", "fruit", "Prunus domestica", perennial=True,
         tunis_arrivals=("Prunes",), faostat=("Plums and sloes",), fao56="stone_fruit"),
    Crop("grape", "Raisin de table", "عنب", "Table grape", "fruit", "Vitis vinifera", perennial=True,
         tunis_arrivals=("Raisins",), tunis_retail=("Raisins ordinaires",), faostat=("Grapes",),
         fao56="grape_table", notes=("FAOSTAT « Grapes » inclut le raisin de cuve.",)),
    Crop("olive", "Olive", "زيتون", "Olive", "fruit", "Olea europaea", perennial=True,
         faostat=("Olives",), fao56="olive"),
]

BY_ID = {c.id: c for c in CROPS}


def _index(attr: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for c in CROPS:
        for name in getattr(c, attr) if isinstance(getattr(c, attr), tuple) else (
                [getattr(c, attr)] if getattr(c, attr) else []):
            out[_norm(name)] = c.id
    return out


def _norm(s: str) -> str:
    return " ".join(s.lower().replace("_", " ").replace("é", "e").replace("è", "e").split())


def lookup(source: str, name: str) -> str | None:
    """Crop id for a raw name in a source (moa_veg, tunis_arrivals, tunis_retail, faostat, sidi_bouzid)."""
    return _INDEX[source].get(_norm(name))


_INDEX = {a: _index(a) for a in ("moa_veg", "tunis_arrivals", "tunis_retail", "faostat", "sidi_bouzid")}
# National series spell the group differently across files
_INDEX["moa_veg"][_norm("Pasteque _Melon")] = "watermelon_melon"

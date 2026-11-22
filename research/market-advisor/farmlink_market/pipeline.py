"""Build the processed FARMLINK datasets from the unchanged raw files.

Run:  python -m farmlink_market.pipeline      (from research/market-advisor)

Every processed table keeps a `source_id` column pointing to data/metadata/sources.json.
Nothing here invents a value: unknown stays NaN, and every inference about units is recorded
in the quality report.
"""
from __future__ import annotations

import json
import math
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import crops as C
from .ins_bulletin import extract as extract_bulletin

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
META = ROOT / "data" / "metadata"

SOURCES: dict[str, dict] = {}
ISSUES: list[dict] = []


def source(sid: str, **meta) -> str:
    SOURCES[sid] = meta
    return sid


def issue(dataset: str, severity: str, message: str) -> None:
    ISSUES.append({"dataset": dataset, "severity": severity, "message": message})


def _dgt_manifest() -> dict[str, dict]:
    m = json.loads((RAW / "data_gov_tn" / "_manifest.json").read_text(encoding="utf-8"))
    return {e["file"]: e for e in m if e.get("status") == "ok"}


def _dgt_source(fname: str, sid: str, unit_note: str, coverage: str) -> str:
    e = _dgt_manifest()[fname]
    return source(sid, title=e["title"], publisher=e["publisher"], url=e["url"], landing_page=e["landing_page"],
                  file=f"data/raw/data_gov_tn/{fname}", retrieved_at=e["retrieved_at"],
                  resource_modified=e["resource_modified"], units=unit_note, geography=coverage,
                  level="official national statistic" if coverage == "Tunisia (national)" else "official regional statistic")


# --------------------------------------------------------------------------------------------
# 1. Ministry of Agriculture national vegetable series (2004-2025)
# --------------------------------------------------------------------------------------------
def national_vegetables() -> pd.DataFrame:
    files = {
        "production_kt": ("evolution-de-la-production-des-cultures-maraicheres-mille-tonnes__0.xlsx", "Production"),
        "yield_t_ha": ("evolution-de-la-productivite-des-cultures-maraicheres-tonnes-ha__0.xlsx", "Productivite_T_Ha"),
        "area_kha": ("evolution-de-la-superficie-des-cultures-maraichere__0.xlsx", "Superficie_ha"),
        "producer_price_dt_t": ("evolution-des-prix-a-la-production-des-cultures-maraicheres-d-t__0.xlsx",
                                "Prix_a_la_production_D/T"),
    }
    units = {"production_kt": "1000 tonnes", "yield_t_ha": "t/ha", "area_kha": "1000 ha (column label says ha)",
             "producer_price_dt_t": "dinars per tonne (nominal), producer price"}
    frames = []
    for col, (fname, raw_col) in files.items():
        sid = _dgt_source(fname, f"moa_veg_{col}", units[col], "Tunisia (national)")
        d = pd.read_excel(RAW / "data_gov_tn" / fname)
        d = d.rename(columns={"Annee": "year", "Culture": "culture_raw", raw_col: col})
        d["crop_id"] = d["culture_raw"].map(lambda s: C.lookup("moa_veg", s) or (
            "other_vegetables" if "autres" in s.lower() else None))
        unknown = d[d.crop_id.isna()].culture_raw.unique()
        if len(unknown):
            issue(sid, "warning", f"unmapped crop names: {list(unknown)}")
        d[f"{col}_source"] = sid
        frames.append(d[["year", "crop_id", col, f"{col}_source"]].dropna(subset=["crop_id"]))
    df = frames[0]
    for f in frames[1:]:
        df = df.merge(f, on=["year", "crop_id"], how="outer")
    df = df.sort_values(["crop_id", "year"]).reset_index(drop=True)
    dup = df.duplicated(["crop_id", "year"]).sum()
    if dup:
        issue("moa_veg", "error", f"{dup} duplicated crop-year rows")
    # Unit check: production (kt) should equal area (kha) x yield (t/ha)
    chk = df.dropna(subset=["production_kt", "area_kha", "yield_t_ha"])
    ratio = chk.production_kt / (chk.area_kha * chk.yield_t_ha)
    ok = ratio.between(0.85, 1.15).mean()
    issue("moa_veg_area_kha", "info",
          f"Area column is labelled 'Superficie_ha' but production(kt) ≈ area × yield holds for {ok:.0%} of "
          f"{len(chk)} crop-years only if area is in 1000 ha; treated as 1000 ha.")
    bad = chk[~ratio.between(0.85, 1.15)]
    for _, r in bad.iterrows():
        issue("moa_veg", "warning", f"{r.crop_id} {int(r.year)}: production {r.production_kt} kt ≠ area "
                                     f"{r.area_kha} kha × yield {r.yield_t_ha} t/ha (ratio "
                                     f"{r.production_kt / (r.area_kha * r.yield_t_ha):.2f})")
    df["production_t"] = df.production_kt * 1000
    df["area_ha"] = df.area_kha * 1000
    # Cross-check with the Arabic copy of the production series (2010-2021)
    ar = pd.read_excel(RAW / "data_gov_tn" / "evolution_cultures_maraichere__0.xlsx")
    ar_map = {"البطاطا": "potato", "الطماطم": "tomato", "القنارية": "artichoke", "الفلفل": "pepper", "البصل": "onion"}
    ar = ar.rename(columns={ar.columns[0]: "year"}).melt("year", var_name="ar", value_name="kt")
    ar["crop_id"] = ar.ar.map(ar_map)
    m = ar.dropna(subset=["crop_id"]).merge(df[["year", "crop_id", "production_kt"]], on=["year", "crop_id"])
    diff = m[(m.kt - m.production_kt).abs() > 0.5]
    issue("moa_veg_production_kt", "info",
          f"Cross-check with the Arabic file 'evolution_cultures_maraichere' (2010-2021): "
          f"{len(m) - len(diff)}/{len(m)} crop-years identical.")
    for _, r in diff.iterrows():
        issue("moa_veg_production_kt", "warning",
              f"{r.crop_id} {int(r.year)}: {r.production_kt} kt vs {r.kt} kt in the Arabic copy")
    return df


# --------------------------------------------------------------------------------------------
# 2. INS bulletins: Tunis wholesale arrivals + Tunis retail prices
# --------------------------------------------------------------------------------------------
def ins_bulletins() -> tuple[pd.DataFrame, pd.DataFrame]:
    man = {e["file"]: e for e in json.loads((RAW / "ins" / "_manifest.json").read_text(encoding="utf-8"))
           if e.get("status") == "ok"}
    arrivals, retail = [], []
    for fname, e in sorted(man.items()):
        a, r = extract_bulletin(RAW / "ins" / fname)
        end = (a.year * 100 + a.month).max()
        a["bulletin_end"] = end
        r["bulletin_end"] = end
        arrivals.append(a)
        retail.append(r)
    source("ins_tunis_arrivals", title="Apports au marché de gros de Tunis (table 9.5, Bulletin Mensuel de la Statistique)",
           publisher="INS; primary source: Marché de Gros de Tunis (Bir El Kassâa)",
           url="https://www.ins.tn/publication (Bulletin Mensuel de la Statistique)",
           files=[f"data/raw/ins/{f}" for f in sorted(man)], retrieved_at=min(e["retrieved_at"] for e in man.values()),
           units="tonnes per month", geography="Tunis wholesale market only (not national, not consumption)",
           level="official market statistic")
    source("ins_tunis_retail", title="Prix moyen de détail à Tunis (table 9.1, Bulletin Mensuel de la Statistique)",
           publisher="INS", url="https://www.ins.tn/publication (Bulletin Mensuel de la Statistique)",
           files=[f"data/raw/ins/{f}" for f in sorted(man)], retrieved_at=min(e["retrieved_at"] for e in man.values()),
           units="millimes per kg in the source, converted to DT/kg", geography="Tunis (retail)",
           level="official price statistic")
    A, R = pd.concat(arrivals), pd.concat(retail)
    arr = _reconcile(A, ["item_raw", "section"], "ins_tunis_arrivals")
    arr["crop_id"] = arr.item_raw.map(lambda s: C.lookup("tunis_arrivals", s))
    arr.loc[arr.item_raw.str.startswith("Autres"), "crop_id"] = arr.section.map(
        {"vegetable": "other_vegetables", "fruit": "other_fruits", "fish": None})
    arr.loc[arr.item_raw == "Total", "crop_id"] = arr.section.map(
        {"vegetable": "total_vegetables", "fruit": "total_fruits", "fish": None})
    arr = arr[arr.section.isin(["vegetable", "fruit"])].copy()
    arr = arr.rename(columns={"value": "arrivals_t"})
    arr["source_id"] = "ins_tunis_arrivals"
    ret = _reconcile(R, ["item_raw", "unit"], "ins_tunis_retail")
    ret["crop_id"] = ret.item_raw.map(lambda s: C.lookup("tunis_retail", s))
    ret = ret.dropna(subset=["crop_id"]).copy()
    per_kg = ret.unit.str.lower() == "kg"
    for item in ret[~per_kg].item_raw.unique():
        issue("ins_tunis_retail", "info", f"'{item}' is priced per '{ret[ret.item_raw == item].unit.iloc[0]}', "
                                          f"not per kg: excluded from DT/kg comparisons.")
    ret = ret[per_kg].copy()
    ret["retail_price_dt_kg"] = ret.value / 1000.0
    ret["source_id"] = "ins_tunis_retail"
    return (arr.drop(columns=["value"], errors="ignore"), ret.drop(columns=["value"]))


def _reconcile(df: pd.DataFrame, keys: list[str], dataset: str) -> pd.DataFrame:
    """One value per item-month: the most recent bulletin that reports a figure for that month."""
    df = df.copy()
    df["has_value"] = df.status == "ok"
    df = df.sort_values(["has_value", "bulletin_end"], ascending=[False, False])
    vals = df[df.has_value]
    conflicts = vals.groupby(keys + ["year", "month"]).value.agg(["nunique", "min", "max", "count"])
    conflicts = conflicts[conflicts["nunique"] > 1]
    for idx, r in conflicts.iterrows():
        issue(dataset, "warning", f"{idx[0]} {idx[-2]}-{idx[-1]:02d}: bulletins disagree ({r['min']:g} to "
                                  f"{r['max']:g}); the most recent bulletin is kept.")
    issue(dataset, "info", f"{len(conflicts)} item-months reported with different values in two bulletins.")
    best = df.groupby(keys + ["year", "month"], as_index=False).first()
    nb = df.groupby(keys + ["year", "month"]).bulletin.nunique().rename("n_bulletins").reset_index()
    best = best.merge(nb, on=keys + ["year", "month"])
    best["date"] = pd.to_datetime(dict(year=best.year, month=best.month, day=1))
    return best.drop(columns=["has_value"])


# --------------------------------------------------------------------------------------------
# 3. FAOSTAT Tunisia (production, area, yield, producer prices) with flags
# --------------------------------------------------------------------------------------------
def faostat() -> pd.DataFrame:
    def load(zname: str, csv: str, elements: dict[str, str]) -> pd.DataFrame:
        z = zipfile.ZipFile(RAW / "faostat" / zname)
        d = pd.read_csv(z.open(csv), encoding="latin1")
        d = d[(d.Area == "Tunisia") & d.Element.isin(elements)]
        if "Months" in d.columns:
            d = d[d.Months == "Annual value"]
        ycols = [c for c in d.columns if re.fullmatch(r"Y\d{4}", c)]
        v = d.melt(["Item", "Element"], ycols, var_name="y", value_name="value")
        f = d.melt(["Item", "Element"], [c + "F" for c in ycols], var_name="y", value_name="flag")
        f["y"] = f.y.str[:-1]
        out = v.merge(f, on=["Item", "Element", "y"])
        out["year"] = out.y.str[1:].astype(int)
        out["element"] = out.Element.map(elements)
        return out.dropna(subset=["value"])[["Item", "element", "year", "value", "flag"]]

    prod = load("Production_Crops_Livestock_E_Africa.zip", "Production_Crops_Livestock_E_Africa.csv",
                {"Production": "production_t", "Area harvested": "area_ha", "Yield": "yield_kg_ha"})
    price = load("Prices_E_Africa.zip", "Prices_E_Africa.csv", {"Producer Price (LCU/tonne)": "producer_price_dt_t"})
    df = pd.concat([prod, price])
    df.loc[df.element == "yield_kg_ha", "value"] /= 1000.0
    df.loc[df.element == "yield_kg_ha", "element"] = "yield_t_ha"
    df["crop_id"] = df.Item.map(lambda s: C.lookup("faostat", s))
    df = df.dropna(subset=["crop_id"]).rename(columns={"Item": "faostat_item"})
    flags = {"A": "official", "E": "estimated", "I": "imputed", "X": "external", "M": "missing"}
    df["flag_meaning"] = df.flag.map(flags)
    df["source_id"] = "faostat"
    now = json.loads((RAW / "faostat" / "_manifest.json").read_text(encoding="utf-8"))
    source("faostat", title="FAOSTAT Production (QCL) and Producer Prices (PP), Africa bulk files", publisher="FAO",
           url="https://bulks-faostat.fao.org/production/", files=[f"data/raw/faostat/{n}" for n in now["files"]],
           retrieved_at=now["retrieved_at"], units="t, ha, t/ha, DT/t (LCU)", geography="Tunisia (national)",
           level="international compilation; each value carries its FAO flag (official / estimated / imputed)")
    share = (df.flag == "A").mean()
    issue("faostat", "info", f"{share:.0%} of FAOSTAT Tunisia values used are official (flag A); the rest are "
                             f"FAO estimates or imputations and are labelled as such.")
    return df


# --------------------------------------------------------------------------------------------
# 4. Sidi Bouzid daily wholesale/retail monitoring (regional)
# --------------------------------------------------------------------------------------------
def sidi_bouzid() -> pd.DataFrame:
    sid = _dgt_source("suivi-des-prix__0.csv", "sidi_bouzid_prices",
                      "qte: tonnes; prices: millimes/kg (unit not stated, inferred from magnitudes)",
                      "Sidi Bouzid (regional market)")
    SOURCES[sid]["files"] = ["data/raw/data_gov_tn/suivi-des-prix__0.csv", "data/raw/data_gov_tn/suivi-des-prix__1.csv"]
    frames = []
    for f in ("suivi-des-prix__0.csv", "suivi-des-prix__1.csv"):
        d = pd.read_csv(RAW / "data_gov_tn" / f)
        frames.append(d)
    d = pd.concat(frames)
    d["date"] = pd.to_datetime(d.date, errors="coerce")
    d["crop_id"] = d["type"].map(lambda s: C.lookup("sidi_bouzid", str(s)))
    d = d.dropna(subset=["crop_id", "date"])
    zero = (d[["pgmin", "pgmax", "pdmin", "pdmax"]] == 0).all(axis=1)
    issue(sid, "info", f"{int(zero.sum())} rows with all prices = 0 treated as 'not on sale' (NaN).")
    for c in ("pgmin", "pgmax", "pdmin", "pdmax"):
        d.loc[d[c] == 0, c] = np.nan
        d[c] = d[c] / 1000.0
    d = d.rename(columns={"qte": "arrivals_t", "pgmin": "wholesale_min_dt_kg", "pgmax": "wholesale_max_dt_kg",
                          "pdmin": "retail_min_dt_kg", "pdmax": "retail_max_dt_kg", "type": "item_raw"})
    d = d.drop_duplicates(["crop_id", "date"])
    d["source_id"] = sid
    return d


# --------------------------------------------------------------------------------------------
# 5. National fruit series (Ministry, data.gov.tn)
# --------------------------------------------------------------------------------------------
AR_FRUITS = {"زيتون الزيت": "olive_oil_olive", "القوارص": "citrus_total", "عنب النبيذ": "grape_wine",
             "عنب المائدة": "grape", "لوز جاف": "almond_dry", "مشمش": "apricot", "التمور": "date",
             "غلال اخرى": "other_fruits", "تفاح": "apple", "اجاص": "pear", "سفرجل": "quince",
             "بوصاع+حب ملوك": "loquat_cherry", "خوخ": "peach", "العوينة": "plum", "التين": "fig",
             "الرمان": "pomegranate", "زيتون المائدة": "table_olive", "الفستق": "pistachio"}


def national_fruits() -> pd.DataFrame:
    rows = []
    for fname, sid in (("evolution-de-la-production-de-l-arboriculture-fruitiere-en-tonne__0.xlsx", "moa_fruit_main"),
                       ("evolution-de-la-production-des-autres-arboricultures-fruitiere__0.xlsx", "moa_fruit_other")):
        _dgt_source(fname, sid, "1000 tonnes (title says 'en tonne'; magnitudes and FAOSTAT match 1000 t)",
                    "Tunisia (national)")
        d = pd.read_excel(RAW / "data_gov_tn" / fname)
        d = d.rename(columns={d.columns[0]: "name_ar"}).melt("name_ar", var_name="year", value_name="kt")
        d["crop_id"] = d.name_ar.str.strip().map(AR_FRUITS)
        d["year"] = d.year.astype(float).astype(int)
        d["source_id"] = sid
        rows.append(d)
    sid = _dgt_source("production-agrumes__0.xlsx", "moa_citrus_total", "1000 tonnes", "Tunisia (national)")
    d = pd.read_excel(RAW / "data_gov_tn" / "production-agrumes__0.xlsx")
    d.columns = ["year", "kt"]
    d["crop_id"], d["source_id"], d["name_ar"] = "citrus_total", sid, None
    rows.append(d)
    sid = _dgt_source("evolution-de-la-production-des-agrumes-par-type-de-produit__0.xlsx", "moa_citrus_type",
                      "1000 tonnes", "Tunisia (national)")
    d = pd.read_excel(RAW / "data_gov_tn" / "evolution-de-la-production-des-agrumes-par-type-de-produit__0.xlsx")
    d.columns = ["year", "type", "kt"]
    d["crop_id"] = d["type"].map({"Maltaise": "orange_maltese", "Clémentine": "clementine", "Mandarine": "mandarin",
                                  "Navel": "orange_navel", "Citron": "lemon"})
    d["source_id"], d["name_ar"] = sid, d["type"]
    rows.append(d.drop(columns=["type"]))
    out = pd.concat(rows, ignore_index=True)
    unmapped = out[out.crop_id.isna()].name_ar.unique()
    if len(unmapped):
        issue("moa_fruit", "warning", f"unmapped fruit names: {list(unmapped)}")
    out = out.dropna(subset=["crop_id", "kt"])
    # citrus total appears in two files: keep the long series, check agreement
    dup = out[out.crop_id == "citrus_total"].groupby("year").kt.agg(["nunique", "min", "max"])
    for y, r in dup[dup["nunique"] > 1].iterrows():
        issue("moa_citrus_total", "warning", f"citrus {y}: {r['min']} kt vs {r['max']} kt in two Ministry files")
    out = out.sort_values("source_id").drop_duplicates(["crop_id", "year"], keep="last")
    out["production_t"] = out.kt * 1000
    sid = "moa_dates_gov"
    _dgt_source("production-des-dattes-1000-t__0.xlsx", sid, "1000 tonnes", "4 oasis governorates")
    issue("moa_fruit", "info", "Regional fruit files (Kasserine 2022-2023, 'production arboricole' of an unnamed "
                               "governorate, dates by governorate) are kept in raw data but not used as national data.")
    return out[["crop_id", "year", "production_t", "source_id"]]


# --------------------------------------------------------------------------------------------
# 6. Climate (NASA POWER) -> monthly ETo (Hargreaves) and effective rain
# --------------------------------------------------------------------------------------------
MONTH_KEYS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
DAYS = [31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def ra_mm_day(lat_deg: float, doy: int) -> float:
    """Extraterrestrial radiation (FAO-56 eq. 21), expressed as mm/day of evaporation."""
    phi = math.radians(lat_deg)
    dr = 1 + 0.033 * math.cos(2 * math.pi * doy / 365)
    d = 0.409 * math.sin(2 * math.pi * doy / 365 - 1.39)
    ws = math.acos(-math.tan(phi) * math.tan(d))
    ra = 24 * 60 / math.pi * 0.0820 * dr * (ws * math.sin(phi) * math.sin(d) + math.cos(phi) * math.cos(d) * math.sin(ws))
    return 0.408 * ra


def effective_rain(p_mm_month: float) -> float:
    """USDA-SCS method as used in FAO CROPWAT (monthly)."""
    return p_mm_month * (125 - 0.2 * p_mm_month) / 125 if p_mm_month <= 250 else 125 + 0.1 * p_mm_month


def climate() -> pd.DataFrame:
    j = json.loads((RAW / "nasa_power" / "nasa_power_climatology_governorates.json").read_text(encoding="utf-8"))
    source("nasa_power", title="NASA POWER monthly climatology (T2M_MAX, T2M_MIN, T2M, PRECTOTCORR)",
           publisher="NASA Langley Research Center", url=j["url"],
           files=["data/raw/nasa_power/nasa_power_climatology_governorates.json"], retrieved_at=j["retrieved_at"],
           units="°C, mm/day", geography="24 governorate seats (point values)", level="satellite/reanalysis model")
    rows = []
    for gov, g in j["governorates"].items():
        p = g["parameter"]
        for i, mk in enumerate(MONTH_KEYS):
            tmax, tmin, tmean, pr = p["T2M_MAX"][mk], p["T2M_MIN"][mk], p["T2M"][mk], p["PRECTOTCORR"][mk]
            doy = int(15 + 30.4 * i)
            eto_day = 0.0023 * ra_mm_day(g["lat"], doy) * (tmean + 17.8) * math.sqrt(max(tmax - tmin, 0))
            rain = pr * DAYS[i]
            rows.append({"governorate": gov, "lat": g["lat"], "lon": g["lon"], "month": i + 1, "tmax": tmax,
                         "tmin": tmin, "tmean": tmean, "rain_mm": rain, "eff_rain_mm": effective_rain(rain),
                         "eto_mm": eto_day * DAYS[i], "source_id": "nasa_power"})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------------
# 7. Small reference tables: CPI, SMAG, water tariff, fertiliser prices
# --------------------------------------------------------------------------------------------
def cpi() -> pd.DataFrame:
    j = json.loads((RAW / "world_bank" / "TUN_FP.CPI.TOTL.json").read_text(encoding="utf-8"))
    source("world_bank_cpi", title="Consumer price index (2010 = 100), Tunisia, FP.CPI.TOTL", publisher="World Bank (from IMF/INS)",
           url="https://api.worldbank.org/v2/country/TUN/indicator/FP.CPI.TOTL", files=["data/raw/world_bank/TUN_FP.CPI.TOTL.json"],
           retrieved_at=j[0].get("lastupdated"), units="index 2010 = 100", geography="Tunisia", level="official (via World Bank)")
    d = pd.DataFrame([{"year": int(x["date"]), "cpi": x["value"]} for x in j[1] if x["value"] is not None])
    d["source_id"] = "world_bank_cpi"
    return d.sort_values("year")


def smag() -> pd.DataFrame:
    html = (RAW / "ins" / "ins_smag_statistiques_98.html").read_text(encoding="utf-8")
    source("ins_smag", title="Salaire Minimum Agricole Garanti (SMAG)", publisher="INS", url="https://www.ins.tn/statistiques/98",
           files=["data/raw/ins/ins_smag_statistiques_98.html"], units="DT per working day", geography="Tunisia",
           level="official", retrieved_at="2026-11-22")
    m = re.search(r"Evolution Annuelle du SMAG.*?<thead.*?</thead>.*?<tbody>(.*?)</tbody>", html, re.S)
    head = re.findall(r"<th scope=\"col\">\s*(\d{4})\s*</th>", html[m.start(): m.end()]) if m else []
    vals = re.findall(r"<td>\s*([\d.]+)\s*</td>", m.group(1)) if m else []
    monthly = re.search(r"Evolution Mensuelle du SMAG.*?<tbody>(.*?)</tbody>", html, re.S)
    rows = [{"year": int(y), "smag_dt_day": float(v)} for y, v in zip(head, vals)]
    latest = re.findall(r"<td>\s*([\d.]+)\s*</td>", monthly.group(1)) if monthly else []
    if latest:
        rows.append({"year": 2026, "smag_dt_day": float(latest[-1]), "note": "latest monthly value"})
    d = pd.DataFrame(rows).drop_duplicates("year", keep="last")
    d["source_id"] = "ins_smag"
    if d.empty:
        issue("ins_smag", "error", "SMAG table not parsed")
    return d


def water_tariff() -> pd.DataFrame:
    fname = "evolution-du-tarif-de-vente-du-m3-d-eau-en-millime_secadenord__0.xlsx"
    sid = _dgt_source(fname, "secadenord_tariff", "millimes per m3", "Northern Tunisia (SECADENORD customers)")
    d = pd.read_excel(RAW / "data_gov_tn" / fname)
    d.columns = ["year", "client", "zone", "tariff_millime_m3"]
    d["tariff_millime_m3"] = pd.to_numeric(d.tariff_millime_m3, errors="coerce")
    d["tariff_dt_m3"] = d.tariff_millime_m3 / 1000
    d["agricultural_client"] = d.client.astype(str).str.startswith("CRDA")
    d["source_id"] = sid
    issue(sid, "info", "SECADENORD sells bulk water to CRDAs (agricultural) and SONEDE in the north; farm-gate "
                       "irrigation prices in public irrigated areas (GDA) are different and not in this dataset.")
    return d.dropna(subset=["tariff_dt_m3"])


def fertiliser() -> pd.DataFrame:
    fname = "prix-des-engrais-chimiques-aupres-des-societes-qui-s-approvisionnent-directement__0.xlsx"
    sid = _dgt_source(fname, "moa_fertiliser", "DT per tonne", "Tunisia (national)")
    d = pd.read_excel(RAW / "data_gov_tn" / fname)
    d = d.melt("campagne", var_name="product", value_name="price_dt_t")
    d["product"] = d["product"].str.replace("_dinar_tonne", "").str.replace("_", " ")
    d["source_id"] = sid
    return d


# --------------------------------------------------------------------------------------------
def quality_report(tables: dict[str, pd.DataFrame]) -> dict:
    rep = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "tables": {}, "issues": ISSUES}
    for name, df in tables.items():
        info = {"records": int(len(df)), "columns": list(df.columns)}
        if "year" in df.columns:
            info["years"] = [int(df.year.min()), int(df.year.max())]
        if "date" in df.columns:
            info["dates"] = [str(df.date.min())[:10], str(df.date.max())[:10]]
        if "crop_id" in df.columns:
            info["crops"] = sorted(map(str, df.crop_id.dropna().unique()))
        info["missing_pct"] = {c: round(float(df[c].isna().mean() * 100), 1) for c in df.columns if df[c].isna().any()}
        info["duplicates"] = int(df.duplicated().sum())
        rep["tables"][name] = info
    return rep


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    META.mkdir(parents=True, exist_ok=True)
    arrivals, retail = ins_bulletins()
    tables = {
        "national_vegetables": national_vegetables(),
        "tunis_wholesale_arrivals": arrivals,
        "tunis_retail_prices": retail,
        "faostat_tunisia": faostat(),
        "sidi_bouzid_market": sidi_bouzid(),
        "national_fruits": national_fruits(),
        "climate_governorates": climate(),
        "cpi": cpi(),
        "smag": smag(),
        "water_tariff_secadenord": water_tariff(),
        "fertiliser_prices": fertiliser(),
    }
    for name, df in tables.items():
        df.to_csv(OUT / f"{name}.csv", index=False, encoding="utf-8")
    crops = pd.DataFrame([{k: (list(v) if isinstance(v, tuple) else v) for k, v in c.__dict__.items()} for c in C.CROPS])
    crops.to_csv(OUT / "crops.csv", index=False, encoding="utf-8")
    (META / "sources.json").write_text(json.dumps(SOURCES, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    rep = quality_report(tables)
    (META / "data_quality_report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1, default=str),
                                                   encoding="utf-8")
    for name, df in tables.items():
        print(f"{name:28} {len(df):6} rows")
    print(f"{len(ISSUES)} quality notes")


if __name__ == "__main__":
    main()

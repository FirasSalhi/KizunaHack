"""Parsing, unit conversion and validation of processed records against the original files."""
from pathlib import Path

import pandas as pd
import pytest

from farmlink_market import crops as C
from farmlink_market.ins_bulletin import extract, parse_arrivals_pages, parse_header
from farmlink_market.pipeline import effective_rain, ra_mm_day

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"

SAMPLE = """9.5 Apports au marché de gros de tunis
Unité: La Tonne
2026 2025
Juill. Juin Mai Avril Mars Fév Jan Déc Nov Oct Sept Août Juill.
LEGUMES الخضر
Tomate 4384 4184 2386 … 1263 2521 2432 2589 2923 4533 4248 4502 4382 طماطم
Fève /// 161 1433 … 416 … … /// /// /// /// /// /// فول
FRUITS الغلال
Abricots 49 1723 3786 … /// /// /// /// /// /// /// /// 196 مشماش
"""


def test_header_reads_months_and_wraps_year():
    h = parse_header(SAMPLE)
    assert h.columns[0] == (2026, 7)
    assert h.columns[6] == (2026, 1)
    assert h.columns[7] == (2025, 12)
    assert h.columns[-1] == (2025, 7)


def test_header_skips_annual_average_column():
    text = "2026 2025\nJuill. Juin Mai Avril Mars Fév Jan Moy. Mens Déc Nov Oct Sept Août Juill.\n"
    h = parse_header(text)
    assert len(h.columns) == 14 and h.columns[7] is None and h.columns[8] == (2025, 12)


def test_arrival_rows_keep_missing_and_out_of_season_apart():
    df = parse_arrivals_pages([SAMPLE])
    tom = df[df.item_raw == "Tomate"].set_index(["year", "month"])
    assert tom.loc[(2025, 7), "value"] == 4382
    assert tom.loc[(2026, 4), "status"] == "not_available"
    feve = df[df.item_raw == "Fève"].set_index(["year", "month"])
    assert feve.loc[(2025, 9), "status"] == "no_arrivals"
    assert set(df.section) == {"vegetable", "fruit"}


def test_crop_lookup_handles_source_spellings():
    assert C.lookup("moa_veg", "Pastéque _Melon") == "watermelon_melon"
    assert C.lookup("moa_veg", "Pasteque _Melon") == "watermelon_melon"
    assert C.lookup("tunis_arrivals", "Pomme de terre") == "potato"
    assert C.lookup("tunis_retail", "Oignons secs") == "onion"
    assert C.lookup("faostat", "Tomatoes") == "tomato"
    assert C.lookup("tunis_arrivals", "Kiwi") is None


def test_effective_rain_and_radiation():
    assert effective_rain(0) == 0
    assert effective_rain(100) == pytest.approx(100 * (125 - 20) / 125)
    assert effective_rain(300) == pytest.approx(155)
    # Tunis (36.8 N): more radiation in June than in December
    assert ra_mm_day(36.8, 172) > 2.5 * ra_mm_day(36.8, 355)


# ---------------------------------------------------------------- validation against raw files
@pytest.fixture(scope="module")
def veg():
    return pd.read_csv(P / "national_vegetables.csv")


def test_national_series_units_converted(veg):
    raw = pd.read_excel(ROOT / "data/raw/data_gov_tn/evolution-de-la-production-des-cultures-maraicheres-mille-tonnes__0.xlsx")
    r = raw[(raw.Annee == 2004) & (raw.Culture == "Tomate")].Production.iloc[0]
    row = veg[(veg.crop_id == "tomato") & (veg.year == 2004)].iloc[0]
    assert row.production_t == r * 1000 == 970_000
    assert row.producer_price_dt_t == 145
    assert row.area_ha == 26_000  # published as 26.0 (thousand ha)
    assert not veg.duplicated(["crop_id", "year"]).any()


def test_processed_arrivals_match_bulletin_pdf():
    a, _ = extract(ROOT / "data/raw/ins/bms_juillet-2026.pdf")
    pdf = a[(a.item_raw == "Tomate") & (a.year == 2025) & (a.month == 7)].value.iloc[0]
    proc = pd.read_csv(P / "tunis_wholesale_arrivals.csv")
    v = proc[(proc.crop_id == "tomato") & (proc.year == 2025) & (proc.month == 7)].arrivals_t.iloc[0]
    assert pdf == v == 4382
    assert not proc.duplicated(["item_raw", "section", "year", "month"]).any()


def test_retail_prices_converted_from_millimes():
    r = pd.read_csv(P / "tunis_retail_prices.csv")
    v = r[(r.crop_id == "tomato") & (r.year == 2026) & (r.month == 7)].retail_price_dt_kg.iloc[0]
    assert v == pytest.approx(1.288)  # 1288 millimes in table 9.1 of the July 2026 bulletin
    assert set(r.unit.str.lower()) == {"kg"}


def test_sidi_bouzid_zero_means_not_on_sale():
    sb = pd.read_csv(P / "sidi_bouzid_market.csv", parse_dates=["date"])
    row = sb[(sb.crop_id == "potato") & (sb.date == "2022-10-21")].iloc[0]
    assert row.wholesale_min_dt_kg == pytest.approx(0.7)
    assert row.retail_max_dt_kg == pytest.approx(2.2)
    raw = pd.read_csv(ROOT / "data/raw/data_gov_tn/suivi-des-prix__1.csv")
    assert ((raw.type == "maltaise") & (raw.pgmin == 0)).any()
    m = sb[sb.crop_id == "orange_maltese"]
    assert (m.wholesale_min_dt_kg.dropna() > 0).all()


def test_faostat_values_keep_their_flag():
    f = pd.read_csv(P / "faostat_tunisia.csv")
    assert f.flag.notna().all()
    assert set(f.flag_meaning.dropna()) <= {"official", "estimated", "imputed", "external", "missing"}

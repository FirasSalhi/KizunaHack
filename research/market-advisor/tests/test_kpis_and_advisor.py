"""KPI, date filtering, profit, scenario and scoring calculations."""
import numpy as np
import pandas as pd
import pytest

from farmlink_market import advisor as A
from farmlink_market import kpis as K


def arrivals_frame(rows):
    df = pd.DataFrame(rows, columns=["crop_id", "section", "date", "arrivals_t", "status"])
    df["date"] = pd.to_datetime(df.date)
    df["item_raw"] = df.crop_id
    return df


def full_season(crop, start_year, values, section="vegetable"):
    months = pd.date_range(f"{start_year}-09-01", periods=12, freq="MS")
    out = []
    for d, v in zip(months, values):
        if v == "///":
            out.append((crop, section, d, np.nan, "no_arrivals"))
        elif v is None:
            out.append((crop, section, d, np.nan, "not_available"))
        else:
            out.append((crop, section, d, float(v), "ok"))
    return out


def test_season_boundaries():
    assert K.season_of(pd.Timestamp("2024-09-01")) == "2024/25"
    assert K.season_of(pd.Timestamp("2025-08-31")) == "2024/25"
    assert K.season_of(pd.Timestamp("2025-01-15")) == "2024/25"
    assert K.season_months("2024/25")[0] == pd.Timestamp("2024-09-01")
    assert len(K.season_months("2024/25")) == 12


def test_arrival_kpis_totals_peaks_and_yoy_on_common_months():
    rows = (full_season("tomato", 2023, [10] * 12)
            + full_season("tomato", 2024, [20] * 11 + [None])          # August not published
            + full_season("melon", 2024, ["///"] * 9 + [5, 30, 10], "fruit")
            + full_season("total_vegetables", 2024, [100] * 12))
    k = K.arrivals_kpis(arrivals_frame(rows), "2024/25").set_index("crop_id")
    assert k.loc["tomato", "total_t"] == 220
    assert k.loc["tomato", "months_reported"] == 11
    assert k.loc["tomato", "yoy_pct"] == pytest.approx(100.0)  # 11 common months, 220 vs 110
    assert k.loc["melon", "total_t"] == 45                      # '///' counts as 0
    assert k.loc["melon", "months_with_arrivals"] == 3
    assert k.loc["melon", "peak_month"] == pd.Timestamp("2025-07-01")
    assert k.loc["melon", "low_month"] == pd.Timestamp("2025-06-01")
    assert np.isnan(k.loc["melon", "yoy_pct"])                  # no previous season


def test_rankings_exclude_aggregates_and_small_volumes():
    k = pd.DataFrame({"crop_id": ["total_vegetables", "tomato", "potato", "chard"], "category": ["vegetable"] * 4,
                      "total_t": [999, 50, 40, 10], "yoy_pct": [5, 10, -20, 300.0]})
    top = K.top_by_arrivals(k, "vegetable")
    assert top.crop_id.tolist() == ["tomato", "potato", "chard"]
    up, down = K.arrival_movers(k, min_tonnes=20)
    assert up.crop_id.tolist()[0] == "tomato" and "chard" not in up.crop_id.tolist()
    assert down.crop_id.tolist() == ["potato"]


def test_latest_complete_season_needs_twelve_published_months():
    rows = full_season("total_vegetables", 2023, [1] * 12) + full_season("total_vegetables", 2024, [1] * 11 + [None])
    assert K.latest_complete_season(arrivals_frame(rows)) == "2023/24"


def test_deflate_and_trend():
    cpi = pd.DataFrame({"year": [2020, 2025], "cpi": [100.0, 150.0]})
    assert K.deflate(pd.Series([10.0]), pd.Series([2020]), cpi).iloc[0] == pytest.approx(15.0)
    years = pd.Series(range(2015, 2025))
    assert K._slope_pct(years, 100 * 1.05 ** (years - 2015)) == pytest.approx(5.0)


def test_seasonality_filters_by_calendar_month():
    rows = full_season("tomato", 2023, list(range(1, 13))) + full_season("tomato", 2024, list(range(11, 23)))
    s = K.seasonality(arrivals_frame(rows), "tomato").set_index("month")
    assert s.loc[9, "avg_t"] == pytest.approx(6.0)   # Sept: 1 and 11
    assert s.loc[9, "n_years"] == 2


# ---------------------------------------------------------------- advisor (real processed data)
@pytest.fixture(scope="module")
def data():
    return K.load()


def test_water_need_is_physical(data):
    nab = data.climate[data.climate.governorate == "Nabeul"]
    drip = A.water_need("tomato", nab, 4, 0.9)
    surface = A.water_need("tomato", nab, 4, 0.6)
    assert 300 < drip.net_irrigation_mm < 1500
    assert drip.gross_m3_ha == pytest.approx(drip.net_irrigation_mm * 10 / 0.9)
    assert surface.gross_m3_ha > drip.gross_m3_ha
    south = A.water_need("tomato", data.climate[data.climate.governorate == "Tozeur"], 4, 0.9)
    assert south.net_irrigation_mm > drip.net_irrigation_mm
    assert A.water_need("carrot", nab, 4, 0.9) is None   # no FAO-56 stage lengths -> no invented value


def test_perennial_and_sparse_crops_are_insufficient_evidence(data):
    assert A.evidence(data, "olive").level == "insufficient"
    assert A.evidence(data, "cucumber").level == "insufficient"
    assert A.evidence(data, "tomato").level == "A"


def test_profit_and_scenarios(data):
    fi = A.FarmerInput(governorate="Nabeul", area_ha=2, candidates=["tomato"], water_tariff_dt_m3=0.1,
                       costs_per_ha={"tomato": {"seeds": 3000, "fertilisers": 2000, "labour": 5000}})
    r = A.analyse_crop(data, fi, "tomato")
    ev = A.evidence(data, "tomato").history.real_revenue_dt_ha
    assert r["revenue_ha"]["expected"] == pytest.approx(np.median(ev))
    assert r["revenue_ha"]["pessimistic"] <= r["revenue_ha"]["expected"] <= r["revenue_ha"]["optimistic"]
    water_cost = r["water"]["gross_m3_ha"] * 0.1
    assert r["cost_ha"] == pytest.approx(10_000 + water_cost)
    exp = r["scenarios"]["expected"]
    assert exp["revenue"] == pytest.approx(r["revenue_ha"]["expected"] * 2)
    assert exp["profit"] == pytest.approx(exp["revenue"] - exp["cost"])
    assert exp["profit_ha"] == pytest.approx(exp["profit"] / 2)


def test_no_costs_means_no_profit_claim(data):
    r = A.analyse_crop(data, A.FarmerInput(governorate="Sfax", area_ha=1), "potato")
    assert r["scenarios"]["expected"]["profit"] is None
    assert any("Coûts de production" in m for m in r["missing"])


def test_scores_are_bounded_and_weights_matter(data):
    base = A.FarmerInput(governorate="Kairouan", area_ha=1, water="moderate")
    t1, _ = A.recommend(data, base)
    assert t1.Score.between(0, 100).all() and len(t1) >= 5
    for col in ["Marché", "Productivité", "Rentabilité", "Eau"]:
        assert t1[col].between(0, 100).all()
    water_only = A.FarmerInput(governorate="Kairouan", area_ha=1,
                               weights={"market": 0, "productivity": 0, "profitability": 0, "water": 1})
    t2, res = A.recommend(data, water_only)
    top = next(r for r in res if r["crop_id"] == t2.crop_id.iloc[0])
    lowest = min((r["water"]["gross_m3_ha"] for r in res if r["status"] == "OK" and r["water"]))
    assert top["water"]["gross_m3_ha"] == pytest.approx(lowest)


def test_all_insufficient_returns_empty_ranking(data):
    t, res = A.recommend(data, A.FarmerInput(governorate="Tunis", area_ha=1, candidates=["olive", "date"]))
    assert t.empty and all(r["status"] == "Insufficient evidence" for r in res)

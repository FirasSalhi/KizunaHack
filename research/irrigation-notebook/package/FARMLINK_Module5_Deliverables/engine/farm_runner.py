"""End-to-end entry point for the web app: farm definition + weather -> JSON-serialisable response."""
from __future__ import annotations

import json
from typing import Dict, Optional

import pandas as pd

from .crop_retrieval import CropIndex
from .eto import compute_eto
from .farm_registry import load_farm
from .irrigation_engine import recommend_zone
from .prioritization import allocate_limited_water, rank_farm


def prepare_weather(df: pd.DataFrame, lat: float, elevation_m: float) -> pd.DataFrame:
    """Compute ETo (Penman-Monteith when complete, else Hargreaves; method recorded per day)."""
    return compute_eto(df, lat, elevation_m)


def run_farm(farm, weather: pd.DataFrame, today: str, forecast: Optional[pd.DataFrame] = None, weather_source: str = "unspecified",
             available_water_m3: Optional[float] = None, horizon_days: int = 5) -> Dict:
    farm = load_farm(farm)
    loc = farm["location"]; ix = CropIndex()
    w = prepare_weather(weather, loc["lat"], loc.get("elevation_m", 0.0))
    f = prepare_weather(forecast, loc["lat"], loc.get("elevation_m", 0.0)) if forecast is not None else None
    recs = [recommend_zone(z, w, today, f, horizon_days, ix, weather_source=weather_source) for z in farm["zones"]]
    ranking = rank_farm(recs)
    resp = {"farm_id": farm.get("farm_id"), "date": today, "weather_source": weather_source, "eto_methods_in_window": sorted(w["eto_method"].unique().tolist()),
            "zones": recs, "ranking": [{"rank": z["rank"], "zone_id": z["zone_id"], "level": z["priority"]["level"], "score": z["priority"]["score"],
                                        "explanation": z["priority"]["explanation"]} for z in ranking["ranked"]],
            "needs_data": ranking["needs_data"], "ranking_weights": ranking["weights"]}
    if available_water_m3 is not None:
        resp["allocation"] = allocate_limited_water(ranking["ranked"], available_water_m3)
    return json.loads(json.dumps(resp, default=lambda o: o.item() if hasattr(o, "item") else str(o)))

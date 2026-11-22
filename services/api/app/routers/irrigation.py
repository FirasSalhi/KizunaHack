"""Irrigation endpoints: which zone to irrigate, when and how much, with today's weather."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator

from app.irrigation import service

router = APIRouter(prefix="/api/v1/irrigation", tags=["irrigation"])

Stage = Literal["initial", "development", "mid_season", "late_season"]


class Soil(BaseModel):
    fc: float = Field(gt=0, lt=0.7, description="Field capacity (m3/m3)")
    wp: float = Field(gt=0, lt=0.7, description="Wilting point (m3/m3)")
    texture: str | None = Field(default=None, max_length=60)
    source: Literal["measured", "user_declared", "illustrative_preset"] = "user_declared"

    @model_validator(mode="after")
    def _wp_below_fc(self) -> Soil:
        if self.wp >= self.fc:
            raise ValueError("wp must be lower than fc")
        return self


class Irrigation(BaseModel):
    method: Literal["drip", "sprinkler", "surface"] | None = None
    ea: float | None = Field(default=None, gt=0, le=1, description="Measured efficiency, if known")


class Zone(BaseModel):
    zone_id: str = Field(min_length=1, max_length=40)
    name: str | None = Field(default=None, max_length=120)
    crop: str = Field(min_length=1, max_length=80, description="Crop id or name (FR, AR, EN)")
    area_ha: float = Field(gt=0, le=1000)
    planting_date: date | None = None
    stage_override: Stage | None = None
    soil: Soil | None = None
    irrigation: Irrigation | None = None
    current_depletion_mm: float | None = Field(default=None, ge=0, le=1000)
    last_refill_date: date | None = Field(
        default=None, description="Last day the soil was refilled to field capacity"
    )


class Location(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    elevation_m: float = Field(default=0.0, ge=-500, le=9000)


class FarmRequest(BaseModel):
    farm_id: str = Field(default="farm", min_length=1, max_length=60)
    location: Location
    zones: list[Zone] = Field(min_length=1, max_length=50)
    available_water_m3: float | None = Field(default=None, ge=0)
    on_date: date | None = Field(default=None, description="Decision day (default: today, UTC)")

    @model_validator(mode="after")
    def _unique_zone_ids(self) -> FarmRequest:
        ids = [z.zone_id for z in self.zones]
        if len(ids) != len(set(ids)):
            raise ValueError("zone_id values must be unique")
        return self


class Crop(BaseModel):
    id: str
    name_fr: str
    name_ar: str | None
    name_en: str | None
    category: str | None
    perennial: bool
    irrigation_ready: bool


def get_weather_provider() -> service.WeatherProvider:
    return service.fetch_live_weather


@router.get("/crops")
def crops() -> list[Crop]:
    return [Crop(**c) for c in service.list_crops()]


@router.post("/farm")
def recommend_farm(
    request: FarmRequest,
    weather_provider: Annotated[service.WeatherProvider, Depends(get_weather_provider)],
) -> dict[str, Any]:
    """Recommendation per zone (what, when, how much), farm-wide ranking and water sharing."""
    today = request.on_date or datetime.now(UTC).date()
    loc = request.location
    try:
        weather = weather_provider(loc.lat, loc.lon, today)
    except service.WeatherUnavailableError as exc:
        raise HTTPException(
            status_code=503, detail="No weather source is reachable right now. Try again later."
        ) from exc
    farm = {
        "farm_id": request.farm_id,
        "location": loc.model_dump(),
        "zones": [z.model_dump(mode="json", exclude_none=True) for z in request.zones],
    }
    try:
        result = service.recommend_farm(farm, weather, today, request.available_water_m3)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    result["weather"] = {
        "source": weather.source,
        "fallback_used": weather.fallback_used,
        "forecast_days": 0 if weather.forecast is None else len(weather.forecast),
    }
    return result

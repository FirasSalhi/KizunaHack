"""MIZU KIZUNA — site + API.

Lancer :  python -m uvicorn main:app --host 0.0.0.0 --port 8000
Site   :  http://localhost:8000      Docs API : http://localhost:8000/docs
"""
import os
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from engine.core import FarmError, analyze, combo_catalogue, crop_companions, crop_list
from engine.sources import SourceUnavailable, geocode

ONLINE = os.getenv("MIZU_OFFLINE", "0") != "1"
STATIC = Path(__file__).resolve().parent / "static"

app = FastAPI(title="MIZU KIZUNA API", version="2.0",
              description="Planification des cultures et compatibilités à partir de la météo historique, du sol et du satellite.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class Water(BaseModel):
    source: Literal["puits", "reseau", "pluie"] = "puits"
    method: Literal["goutte_a_goutte", "aspersion", "gravitaire"] = "goutte_a_goutte"
    volume_m3: Optional[float] = Field(None, ge=0, description="Eau disponible par an (m³). Vide = inconnu")


class AnalyzeRequest(BaseModel):
    farm: dict = Field(..., description="Contour GeoJSON Polygon (ou Feature) en [longitude, latitude]")
    water: Water = Water()
    salinity: Literal["non", "un_peu", "oui"] = "non"
    soil_type: Optional[Literal["sableux", "limoneux", "argileux", "acide"]] = Field(None, description="Vide = SoilGrids")
    kinds: Literal["all", "annual", "perennial"] = "all"
    max_crops: int = Field(4, ge=1, le=6)
    use_satellite: bool = True
    lang: Literal["fr", "tn", "ja"] = Field("fr", description="Langue des textes : fr, tn (tunisien), ja (japonais)")


@app.get("/api/health")
def health():
    return {"status": "ok", "online_data": ONLINE, "version": "2.4"}


@app.get("/api/geocode")
def api_geocode(q: str, lang: Literal["fr", "tn", "ja"] = "fr"):
    if len(q.strip()) < 2:
        return []
    try:
        return geocode(q.strip(), lang={"fr": "fr", "tn": "ar,fr", "ja": "ja"}[lang])
    except SourceUnavailable as e:
        raise HTTPException(503, f"Recherche indisponible : {e}")


@app.post("/api/analyze")
def api_analyze(req: AnalyzeRequest):
    try:
        return analyze(req.model_dump(), online=ONLINE)
    except FarmError as e:
        raise HTTPException(422, str(e))


@app.get("/api/crops")
def api_crops(country: Literal["tunisie", "japon"] = "tunisie", lang: Literal["fr", "tn", "ja"] = "fr"):
    return crop_list(country, lang)


@app.get("/api/crops/{crop}/companions")
def api_companions(crop: str, country: Literal["tunisie", "japon"] = "tunisie", lang: Literal["fr", "tn", "ja"] = "fr"):
    try:
        return crop_companions(crop, country, lang)
    except FarmError as e:
        raise HTTPException(404, str(e))


@app.get("/api/combinations")
def api_combinations(country: Literal["tunisie", "japon"] = "tunisie", lang: Literal["fr", "tn", "ja"] = "fr"):
    """Catalogue des combinaisons sur le même hectare, avec causes, précautions et sources."""
    return combo_catalogue(country, lang)


app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")

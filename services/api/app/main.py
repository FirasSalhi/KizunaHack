from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.database import engine
from app.core.logging import logger, setup_logging
from app.models.base import Base
from app.plants import engine as plant_engine
from app.routers import assistant, irrigation, plants, sensors, weather
from app.sensors.feed import feed as sensor_feed


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Configure logging
    setup_logging(debug=settings.DEBUG)

    # Load the plant scanner models in the background so the first scan is fast
    plant_engine.warm_up()

    # Listen to the field unit's readings (MQTT, background thread)
    sensor_feed.start()

    # Initialize tables if connected to database
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:
        # Gracefully handle offline database during local builds or tests
        logger.debug("Database table auto-creation skipped: %s", exc)

    yield

    sensor_feed.stop()

    # Clean up engine resources on shutdown
    try:
        await engine.dispose()
    except Exception as exc:
        logger.debug("Database engine disposal skipped: %s", exc)


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# CORS for the Next.js frontend, local dev proxies and the static irrigation demo pages (:8080)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
app.include_router(irrigation.router)
app.include_router(plants.router)
app.include_router(sensors.router)
app.include_router(weather.router)
app.include_router(assistant.router)


# Backward-compatible root health check
@app.get("/health", include_in_schema=False)
@app.get("/api/v1/health", include_in_schema=False)
async def root_health() -> dict[str, bool]:
    return {"ok": True}

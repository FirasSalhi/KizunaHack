"""Latest field-unit readings for the dashboard (app/sensors/feed.py)."""

from typing import Any

from fastapi import APIRouter

from app.sensors.feed import feed

router = APIRouter(prefix="/api/v1/sensors", tags=["sensors"])


@router.get("/latest")
def latest() -> dict[str, Any]:
    """Latest reading of each field unit, its age in seconds, the gateway state and 1-minute trends.

    Readable without an account, like the public broker it comes from (demo session included).
    """
    return feed.snapshot()

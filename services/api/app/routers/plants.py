"""Plant scanner: photo -> plant name, health, care sheet; scan history for signed-in users.

Ported from is9ini (github.com/RaziSnihaa/is9ini). Anyone can scan, including the dashboard's demo
session; only signed-in users' scans are saved to their history.
"""

from __future__ import annotations

import asyncio
import io
import uuid
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session, get_optional_user
from app.core.config import settings
from app.models.plant_scan import PlantScan
from app.models.user import User
from app.plants import engine

router = APIRouter(prefix="/api/v1/plants", tags=["plant scanner"])

MAX_PHOTO_BYTES = 10 * 1024 * 1024


def _error(code: int, err: str, message: str) -> HTTPException:
    return HTTPException(status_code=code, detail={"error": {"code": err, "message": message}})


def _not_installed() -> HTTPException:
    return _error(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "SCANNER_NOT_INSTALLED",
        "The plant scanner models are not installed. Run: python -m app.plants.catalog",
    )


def _photo_path(scan_id: uuid.UUID, size: Literal["thumb", "full"]) -> Path:
    suffix = "_thumb" if size == "thumb" else ""
    return Path(settings.PLANT_SCANS_DIR) / f"{scan_id}{suffix}.jpg"


def _save_photo(scan_id: uuid.UUID, data: bytes) -> None:
    """Keep a 1280 px copy and a 360 px thumbnail of each saved scan."""
    from PIL import Image, ImageOps

    Path(settings.PLANT_SCANS_DIR).mkdir(parents=True, exist_ok=True)
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    img.thumbnail((1280, 1280))
    img.save(_photo_path(scan_id, "full"), "JPEG", quality=85)
    img.thumbnail((360, 360))
    img.save(_photo_path(scan_id, "thumb"), "JPEG", quality=80)


def _summary(scan: PlantScan) -> dict[str, Any]:
    return {
        "id": str(scan.id),
        "created_at": scan.created_at.isoformat(),
        "common_name": scan.common_name,
        "scientific_name": scan.scientific_name,
        "confidence": scan.confidence,
        "sure": scan.sure,
        "engine": scan.engine,
        "health_status": scan.health_status,
    }


async def _own_scan(db: AsyncSession, scan_id: uuid.UUID, user: User) -> PlantScan:
    scan = await db.get(PlantScan, scan_id)
    if scan is None or scan.user_id != user.id:  # other users' scans are not visible
        raise _error(status.HTTP_404_NOT_FOUND, "SCAN_NOT_FOUND", "Scan not found.")
    return scan


@router.get("/status")
def scanner_status() -> dict[str, Any]:
    """Which engines are installed and configured."""
    return {"installed": engine.available(), "engines": engine.engines()}


@router.post("/identify")
async def identify(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    user: User | None = Depends(get_optional_user),
) -> dict[str, Any]:
    """Body = the photo as raw bytes (JPEG/PNG). Returns plant, health, care and alternatives."""
    if not engine.available():
        raise _not_installed()
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_PHOTO_BYTES:
        raise _error(413, "PHOTO_TOO_LARGE", "Photo too large (max 10 MB).")
    data = await request.body()
    if not data:
        raise _error(422, "NO_PHOTO", "Send the photo as the request body.")
    if len(data) > MAX_PHOTO_BYTES:
        raise _error(413, "PHOTO_TOO_LARGE", "Photo too large (max 10 MB).")
    try:
        result = await asyncio.to_thread(engine.identify, data)
    except engine.ScannerUnavailable as exc:
        raise _not_installed() from exc
    except Exception as exc:  # unreadable image
        raise _error(422, "BAD_PHOTO", "Could not read this image.") from exc

    result["saved"] = False
    if user is not None:
        species = result["species"]
        scan = PlantScan(
            user_id=user.id,
            common_name=str(species["common_name"])[:200],
            scientific_name=str(species["scientific_name"])[:200],
            confidence=float(result["confidence"]),
            sure=bool(result["sure"]),
            engine=str(result["engine"])[:100],
            health_status=(result.get("health") or {}).get("status"),
            result=result,
        )
        db.add(scan)
        await db.commit()
        await asyncio.to_thread(_save_photo, scan.id, data)
        result["scan_id"] = str(scan.id)
        result["saved"] = True
    return result


@router.get("/search")
def search(q: str) -> list[dict[str, Any]]:
    """Find a plant by common or scientific name, to correct a scan by hand."""
    if len(q.strip()) < 2:
        return []
    if not engine.available():
        raise _not_installed()
    return engine.search(q[:80])


@router.get("/care/{species_id}")
def care(species_id: str) -> dict[str, Any]:
    """Care sheet of one plant (used when correcting an unsaved scan)."""
    if not engine.available():
        raise _not_installed()
    return engine.care_sheet(species_id[:80].lower())


@router.get("/scans")
async def list_scans(
    limit: int = 50,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    rows = await db.scalars(
        select(PlantScan)
        .where(PlantScan.user_id == user.id)
        .order_by(PlantScan.created_at.desc())
        .limit(min(max(limit, 1), 200))
    )
    return [_summary(s) for s in rows]


@router.get("/scans/{scan_id}")
async def get_scan(
    scan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    scan = await _own_scan(db, scan_id, user)
    return _summary(scan) | {"result": scan.result}


@router.get("/scans/{scan_id}/image")
async def scan_image(
    scan_id: uuid.UUID,
    size: Literal["thumb", "full"] = "thumb",
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> FileResponse:
    await _own_scan(db, scan_id, user)
    path = _photo_path(scan_id, size)
    if not path.exists():
        raise _error(status.HTTP_404_NOT_FOUND, "NO_PHOTO", "No photo for this scan.")
    return FileResponse(path, media_type="image/jpeg")


class ScanFix(BaseModel):
    species_id: str = Field(min_length=2, max_length=80)


@router.patch("/scans/{scan_id}")
async def fix_scan(
    scan_id: uuid.UUID,
    body: ScanFix,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Correct a scan by hand: the user picked the right plant."""
    scan = await _own_scan(db, scan_id, user)
    if not engine.available():
        raise _not_installed()
    species = await asyncio.to_thread(engine.care_sheet, body.species_id.lower())
    result = scan.result | {"species": species, "sure": True, "chosen": True}
    scan.result = result
    scan.common_name = str(species["common_name"])[:200]
    scan.scientific_name = str(species["scientific_name"])[:200]
    scan.sure = True
    await db.commit()
    return _summary(scan) | {"result": result}


@router.delete("/scans/{scan_id}")
async def delete_scan(
    scan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    scan = await _own_scan(db, scan_id, user)
    await db.delete(scan)
    await db.commit()
    for size in ("thumb", "full"):
        _photo_path(scan_id, size).unlink(missing_ok=True)
    return {"deleted": str(scan_id)}

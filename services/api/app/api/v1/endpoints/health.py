from fastapi import APIRouter

router = APIRouter()


@router.get("/health", summary="Health check endpoint")
async def health() -> dict[str, bool]:
    return {"ok": True}

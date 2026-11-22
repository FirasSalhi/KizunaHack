import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import irrigation

app = FastAPI(
    title="FARMLINK API",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
)

# Browsers may call the API from these origins (comma-separated). The defaults cover local
# development: the Next.js app on :3000 and static demo pages served on :8080.
_DEFAULT_ORIGINS = (
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8080,http://127.0.0.1:8080"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        o.strip() for o in os.environ.get("CORS_ALLOW_ORIGINS", _DEFAULT_ORIGINS).split(",") if o
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(irrigation.router)


@app.get("/api/v1/health")
async def health() -> dict[str, bool]:
    return {"ok": True}

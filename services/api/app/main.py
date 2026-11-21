from fastapi import FastAPI

app = FastAPI(
    title="FARMLINK API",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
)


@app.get("/api/v1/health")
async def health() -> dict[str, bool]:
    return {"ok": True}

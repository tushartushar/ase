from fastapi import FastAPI

from app.order_router import router
from app.bulk_cancel import router as bulk_router

app = FastAPI(title="OrderMaster", version="0.1.0")

app.include_router(router)
app.include_router(bulk_router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    """Liveness check — returns 200 {"status": "ok"} when the service is up."""
    return {"status": "ok"}

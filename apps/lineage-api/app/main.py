
from fastapi import FastAPI, HTTPException, status

from app.api.v1.lineage import router as lineage_router
from app.db.neo4j import get_session


app = FastAPI(title="Lineage API", version="0.3.0")
app.include_router(lineage_router, prefix="/api/v1/lineage", tags=["Lineage"])


@app.get("/health", tags=["Operations"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/live", tags=["Operations"])
def liveness() -> dict[str, str]:
    return {"status": "live"}


@app.get("/health/ready", tags=["Operations"])
def readiness() -> dict[str, str]:
    try:
        with get_session() as session:
            session.run("RETURN 1 AS ready").single()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "not_ready", "message": "The lineage graph store is unavailable."},
        ) from exc
    return {"status": "ready"}

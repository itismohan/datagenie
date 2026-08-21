from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status

from app.api.v1.quality import router
from app.db.session import create_schema, database_ready


@asynccontextmanager
async def lifespan(_app: FastAPI):
    create_schema()
    yield


app = FastAPI(title="DataGenie Quality API", version="1.0.0", lifespan=lifespan)
app.include_router(router, prefix="/api/v1/quality", tags=["quality"])


@app.get("/health/live")
def liveness() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def readiness() -> dict[str, str]:
    if not database_ready():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Quality database is not ready.")
    return {"status": "ready"}


from fastapi import FastAPI
from app.api.v1.quality import router

app = FastAPI(title="Quality API - Phase 2")
app.include_router(router, prefix="/api/v1/quality")

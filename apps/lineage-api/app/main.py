
from fastapi import FastAPI
from app.api.v1.lineage import router

app = FastAPI(title="Lineage API")
app.include_router(router, prefix="/api/v1/lineage")

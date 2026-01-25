
from fastapi import FastAPI
from app.api.v1.search import router

app = FastAPI(title="Search API")
app.include_router(router, prefix="/api/v1/search")

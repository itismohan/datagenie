
from fastapi import FastAPI
from app.api.v1 import assets, glossary

app = FastAPI(title="DataGinie Catalog API")

app.include_router(assets.router, prefix="/api/v1/assets", tags=["Assets"])
app.include_router(glossary.router, prefix="/api/v1/glossary", tags=["Glossary"])

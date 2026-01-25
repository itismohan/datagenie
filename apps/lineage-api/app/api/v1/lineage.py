
from fastapi import APIRouter
from app.services.lineage_service import create_lineage, get_lineage

router = APIRouter()

@router.post("/")
def add_lineage(source: str, target: str):
    create_lineage(source, target)
    return {"status": "created"}

@router.get("/{asset_id}")
def fetch_lineage(asset_id: str):
    return get_lineage(asset_id)

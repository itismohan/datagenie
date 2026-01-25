
from fastapi import APIRouter
from app.schemas.asset import AssetCreate, Asset
import uuid

router = APIRouter()
ASSETS = {}

@router.post("/", response_model=Asset)
def create_asset(asset: AssetCreate):
    aid = str(uuid.uuid4())
    data = asset.dict()
    data["id"] = aid
    ASSETS[aid] = data
    return data

@router.get("/", response_model=list[Asset])
def list_assets():
    return list(ASSETS.values())

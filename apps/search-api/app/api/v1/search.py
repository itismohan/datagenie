
from fastapi import APIRouter
from app.services.search_service import search_assets

router = APIRouter()

@router.get("/")
def search(q: str):
    return search_assets(q)


from fastapi import APIRouter
import random

router = APIRouter()

@router.post("/run")
def run_quality(asset_id: str):
    return {
        "asset_id": asset_id,
        "completeness": random.randint(80,100),
        "uniqueness": random.randint(70,100),
        "score": random.randint(80,95)
    }

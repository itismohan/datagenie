
from pydantic import BaseModel

class AssetCreate(BaseModel):
    name: str
    type: str
    description: str | None = None

class Asset(AssetCreate):
    id: str

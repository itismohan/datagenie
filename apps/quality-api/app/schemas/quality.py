
from pydantic import BaseModel

class QualityResult(BaseModel):
    asset_id: str
    completeness: int
    uniqueness: int
    score: int

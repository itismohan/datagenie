
from pydantic import BaseModel

class GlossaryCreate(BaseModel):
    name: str
    definition: str

class GlossaryTerm(GlossaryCreate):
    id: str

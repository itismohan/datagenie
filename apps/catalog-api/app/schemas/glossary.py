
from pydantic import BaseModel, ConfigDict, Field


class GlossaryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    definition: str = Field(min_length=2, max_length=10000)
    owner: str | None = Field(default=None, max_length=255)


class GlossaryTerm(GlossaryCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str

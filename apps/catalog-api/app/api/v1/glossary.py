
from fastapi import APIRouter
from app.schemas.glossary import GlossaryTerm, GlossaryCreate
import uuid

router = APIRouter()
TERMS = {}

@router.post("/", response_model=GlossaryTerm)
def create_term(term: GlossaryCreate):
    tid = str(uuid.uuid4())
    data = term.dict()
    data["id"] = tid
    TERMS[tid] = data
    return data

@router.get("/", response_model=list[GlossaryTerm])
def list_terms():
    return list(TERMS.values())

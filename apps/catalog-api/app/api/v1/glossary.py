
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import (
    ROLE_ANALYST,
    ROLE_DATA_OWNER,
    ROLE_DATA_STEWARD,
    ROLE_PLATFORM_ADMIN,
    ROLE_READ_ONLY,
    Principal,
    require_roles,
)
from app.db.session import get_db
from app.models.catalog import BusinessGlossaryTerm
from app.schemas.glossary import GlossaryCreate, GlossaryTerm
from app.services.audit_service import record_audit_event
from app.services.idempotency_service import IdempotencyContext, get_idempotency_context, replay_response, store_response

router = APIRouter()
glossary_reader = require_roles(ROLE_PLATFORM_ADMIN, ROLE_DATA_STEWARD, ROLE_DATA_OWNER, ROLE_ANALYST, ROLE_READ_ONLY)
glossary_editor = require_roles(ROLE_PLATFORM_ADMIN, ROLE_DATA_STEWARD)


@router.post("/", response_model=GlossaryTerm, status_code=status.HTTP_201_CREATED)
def create_term(
    term: GlossaryCreate,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(glossary_editor),
    idempotency: IdempotencyContext | None = Depends(get_idempotency_context),
) -> BusinessGlossaryTerm | Response:
    replay = replay_response(db, idempotency)
    if replay:
        return replay
    existing = db.scalar(select(BusinessGlossaryTerm).where(BusinessGlossaryTerm.name == term.name))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"code": "conflict", "message": "A glossary term with this name already exists."})
    created = BusinessGlossaryTerm(**term.model_dump())
    db.add(created)
    db.commit()
    db.refresh(created)
    record_audit_event(
        db,
        principal=principal,
        action="glossary.create",
        resource_type="glossary_term",
        resource_id=created.id,
        outcome="success",
        request_id=getattr(request.state, "request_id", "unknown"),
        metadata={"name": created.name},
    )
    body = GlossaryTerm.model_validate(created).model_dump(mode="json")
    store_response(db, idempotency, body, status.HTTP_201_CREATED)
    return created


@router.get("/", response_model=list[GlossaryTerm])
def list_terms(
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(glossary_reader),
) -> list[BusinessGlossaryTerm]:
    terms = list(db.scalars(select(BusinessGlossaryTerm).order_by(BusinessGlossaryTerm.name.asc())))
    record_audit_event(
        db,
        principal=principal,
        action="glossary.list",
        resource_type="glossary_term",
        resource_id=None,
        outcome="success",
        request_id=getattr(request.state, "request_id", "unknown"),
        metadata={"result_count": len(terms)},
    )
    db.commit()
    return terms

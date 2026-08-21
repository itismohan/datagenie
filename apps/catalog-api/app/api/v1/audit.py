from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import ROLE_PLATFORM_ADMIN, Principal, require_roles
from app.db.session import get_db
from app.models.catalog import AuditEvent
from app.schemas.catalog import AuditEventSearchResponse
from app.services.audit_service import record_audit_event

router = APIRouter()
audit_reader = require_roles(ROLE_PLATFORM_ADMIN)


@router.get("/", response_model=AuditEventSearchResponse)
def list_audit_events(
    request: Request,
    actor_subject: str | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    request_id: str | None = None,
    outcome: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    principal: Principal = Depends(audit_reader),
) -> AuditEventSearchResponse:
    filters = []
    for column, value in (
        (AuditEvent.actor_subject, actor_subject),
        (AuditEvent.action, action),
        (AuditEvent.resource_type, resource_type),
        (AuditEvent.resource_id, resource_id),
        (AuditEvent.request_id, request_id),
        (AuditEvent.outcome, outcome),
    ):
        if value is not None:
            filters.append(column == value)
    statement = select(AuditEvent).where(*filters)
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    items = list(db.scalars(statement.order_by(AuditEvent.created_at.desc()).offset(offset).limit(limit)))
    record_audit_event(
        db,
        principal=principal,
        action="audit_event.list",
        resource_type="audit_event",
        resource_id=None,
        outcome="success",
        request_id=getattr(request.state, "request_id", "unknown"),
        metadata={"result_count": len(items), "filters_present": any([actor_subject, action, resource_type, resource_id, request_id, outcome])},
    )
    db.commit()
    return AuditEventSearchResponse(items=items, total=total)

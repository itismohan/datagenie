from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.security import Principal, get_current_principal
from app.db.session import get_db
from app.schemas.policy import PolicyDecisionRead, PolicyDecisionRequest
from app.services.policy_service import evaluate_access

router = APIRouter()


def request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


@router.post("/decisions", response_model=PolicyDecisionRead)
def evaluate_policy_decision(
    payload: PolicyDecisionRequest,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> PolicyDecisionRead:
    """Return a deterministic, auditable policy decision without executing an action."""
    context = payload.context.model_copy(update={"request_id": request_id(request)})
    decision = evaluate_access(
        db,
        subject=principal,
        tenant=principal.tenant_id,
        action=payload.action,
        resource=payload.resource,
        purpose=payload.purpose,
        context=context,
    )
    db.commit()
    return decision.to_read()

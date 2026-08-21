from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.security import Principal
from app.services.audit_service import record_audit_event
from app.services.policy_service import PolicyEvaluationError, evaluate_rest_policy


def request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def enforce_policy(
    db: Session,
    principal: Principal,
    request: Request,
    *,
    action: str,
    resource_type: str,
    resource_id: str,
    purpose: str | None = None,
) -> None:
    """Evaluate and durably record policy before a REST route returns protected data or mutates it."""
    try:
        decision = evaluate_rest_policy(
            db,
            principal=principal,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            purpose=purpose,
            request_id=request_id(request),
        )
        db.commit()
    except PolicyEvaluationError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "policy_unavailable", "message": "A safe policy decision could not be recorded."},
        ) from exc
    if decision.outcome.value == "allow":
        return
    record_audit_event(
        db,
        principal=principal,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id if decision.resource_visible else None,
        outcome="denied",
        request_id=request_id(request),
        metadata={"policy_outcome": decision.outcome.value, "rule_ids": list(decision.rule_ids)},
    )
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "policy_unavailable", "message": "A safe policy denial could not be recorded."},
        ) from exc
    status_code = status.HTTP_409_CONFLICT if decision.outcome.value == "requires_human_approval" else status.HTTP_403_FORBIDDEN
    code = "policy_requires_human_approval" if decision.outcome.value == "requires_human_approval" else "policy_denied"
    raise HTTPException(
        status_code=status_code,
        detail={
            "code": code,
            "message": "The policy decision does not permit this request to proceed.",
            "details": {
                "outcome": decision.outcome.value,
                "rule_ids": list(decision.rule_ids),
                "obligations": list(decision.obligations),
            },
        },
    )

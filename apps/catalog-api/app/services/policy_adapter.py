from sqlalchemy.orm import Session

from app.core.security import Principal
from app.schemas.policy import PolicyContext, PolicyResource
from app.services.policy_service import PolicyDecision, evaluate_access


def evaluate_transport_policy(
    db: Session,
    *,
    principal: Principal,
    action: str,
    resource_type: str,
    resource_id: str,
    purpose: str | None,
    request_id: str,
    workflow_id: str | None = None,
) -> PolicyDecision:
    """Transport-neutral adapter for REST, UI, and future MCP callers.

    This adapter deliberately supplies only identity derived from the same trusted
    principal/session boundary used by REST. Transport metadata cannot supply a
    different tenant, role set, decision, rule, evidence, or obligation.
    """
    return evaluate_access(
        db,
        subject=principal,
        tenant=principal.tenant_id,
        action=action,
        resource=PolicyResource(resource_type=resource_type, resource_id=resource_id),
        purpose=purpose,
        context=PolicyContext(request_id=request_id, workflow_id=workflow_id),
    )

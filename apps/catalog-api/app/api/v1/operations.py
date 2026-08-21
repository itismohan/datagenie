from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.security import ROLE_DATA_STEWARD, ROLE_PLATFORM_ADMIN, Principal, require_roles
from app.db.session import get_db
from app.models.catalog import Asset, AuditEvent, RetentionPolicy, WebhookDelivery, WebhookSubscription
from app.schemas.catalog import AssetRead, AuditEventRead
from app.schemas.operations import (
    RetentionPolicyRead,
    RetentionPolicyUpsert,
    WebhookDeliveryRead,
    WebhookSubscriptionCreate,
    WebhookSubscriptionRead,
)
from app.services.audit_service import record_audit_event
from app.services.operations_service import (
    apply_retention_policy,
    create_webhook_subscription,
    upsert_retention_policy,
)


router = APIRouter()
operator = require_roles(ROLE_PLATFORM_ADMIN, ROLE_DATA_STEWARD)


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


@router.get("/exports/catalog")
def export_catalog(
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(operator),
) -> dict[str, object]:
    assets = list(db.scalars(select(Asset).options(selectinload(Asset.columns), selectinload(Asset.metadata_versions))))
    record_audit_event(
        db,
        principal=principal,
        action="export.catalog",
        resource_type="asset",
        resource_id=None,
        outcome="success",
        request_id=_request_id(request),
        metadata={"asset_count": len(assets)},
    )
    db.commit()
    return {"assets": [AssetRead.model_validate(asset).model_dump(mode="json") for asset in assets]}


@router.get("/exports/audit")
def export_audit(
    request: Request,
    limit: int = Query(default=10_000, ge=1, le=10_000),
    db: Session = Depends(get_db),
    principal: Principal = Depends(operator),
) -> dict[str, object]:
    events = list(db.scalars(select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit)))
    record_audit_event(
        db,
        principal=principal,
        action="export.audit",
        resource_type="audit_event",
        resource_id=None,
        outcome="success",
        request_id=_request_id(request),
        metadata={"event_count": len(events)},
    )
    db.commit()
    return {"events": [AuditEventRead.model_validate(event).model_dump(mode="json") for event in events]}


@router.get("/retention", response_model=list[RetentionPolicyRead])
def list_retention_policies(
    db: Session = Depends(get_db),
    principal: Principal = Depends(operator),
) -> list[RetentionPolicy]:
    return list(db.scalars(select(RetentionPolicy).order_by(RetentionPolicy.resource_type)))


@router.put("/retention", response_model=RetentionPolicyRead)
def set_retention_policy(
    payload: RetentionPolicyUpsert,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(operator),
) -> RetentionPolicy:
    policy = upsert_retention_policy(db, payload)
    record_audit_event(
        db,
        principal=principal,
        action="retention_policy.upsert",
        resource_type="retention_policy",
        resource_id=policy.id,
        outcome="success",
        request_id=_request_id(request),
        metadata={"resource_type": policy.resource_type.value, "retention_days": policy.retention_days, "active": policy.active},
    )
    db.commit()
    db.refresh(policy)
    return policy


@router.post("/retention/{policy_id}/apply")
def apply_retention(
    policy_id: str,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(operator),
) -> dict[str, int]:
    policy = db.get(RetentionPolicy, policy_id)
    if policy is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Retention policy not found.")
    deleted_count = apply_retention_policy(db, policy)
    record_audit_event(
        db,
        principal=principal,
        action="retention_policy.apply",
        resource_type="retention_policy",
        resource_id=policy.id,
        outcome="success",
        request_id=_request_id(request),
        metadata={"deleted_count": deleted_count, "resource_type": policy.resource_type.value},
    )
    db.commit()
    return {"deleted_count": deleted_count}


@router.post("/webhooks", response_model=WebhookSubscriptionRead, status_code=status.HTTP_201_CREATED)
def create_webhook(
    payload: WebhookSubscriptionCreate,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(operator),
) -> WebhookSubscription:
    subscription = create_webhook_subscription(db, payload)
    record_audit_event(
        db,
        principal=principal,
        action="webhook_subscription.create",
        resource_type="webhook_subscription",
        resource_id=subscription.id,
        outcome="success",
        request_id=_request_id(request),
        metadata={"event_type": subscription.event_type.value, "target_host": subscription.target_url.split("/")[2]},
    )
    db.commit()
    db.refresh(subscription)
    return subscription


@router.get("/webhooks", response_model=list[WebhookSubscriptionRead])
def list_webhooks(
    db: Session = Depends(get_db),
    principal: Principal = Depends(operator),
) -> list[WebhookSubscription]:
    return list(db.scalars(select(WebhookSubscription).order_by(WebhookSubscription.created_at.desc())))


@router.get("/webhook-deliveries", response_model=list[WebhookDeliveryRead])
def list_webhook_deliveries(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    principal: Principal = Depends(operator),
) -> list[WebhookDelivery]:
    return list(db.scalars(select(WebhookDelivery).order_by(WebhookDelivery.created_at.desc()).limit(limit)))

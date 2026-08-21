from datetime import timedelta
from urllib.parse import urlparse

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.catalog import (
    AuditEvent,
    DiscoveryEvent,
    IngestionJob,
    RetentionPolicy,
    RetentionResourceType,
    WebhookDelivery,
    WebhookDeliveryStatus,
    WebhookEventType,
    WebhookSubscription,
    utc_now,
)
from app.schemas.operations import RetentionPolicyUpsert, WebhookSubscriptionCreate


RETENTION_MODELS = {
    RetentionResourceType.AUDIT_EVENT: AuditEvent,
    RetentionResourceType.DISCOVERY_EVENT: DiscoveryEvent,
    RetentionResourceType.INGESTION_JOB: IngestionJob,
}


def upsert_retention_policy(db: Session, payload: RetentionPolicyUpsert) -> RetentionPolicy:
    policy = db.scalar(select(RetentionPolicy).where(RetentionPolicy.resource_type == payload.resource_type))
    if policy is None:
        policy = RetentionPolicy(**payload.model_dump())
        db.add(policy)
    else:
        policy.retention_days = payload.retention_days
        policy.active = payload.active
    db.flush()
    return policy


def apply_retention_policy(db: Session, policy: RetentionPolicy) -> int:
    """Delete only records selected through the active tenant-scoped ORM query."""
    if not policy.active:
        return 0
    model = RETENTION_MODELS[policy.resource_type]
    cutoff = utc_now() - timedelta(days=policy.retention_days)
    expired = list(db.scalars(select(model).where(model.created_at < cutoff)))
    for record in expired:
        db.delete(record)
    policy.last_applied_at = utc_now()
    db.flush()
    return len(expired)


def create_webhook_subscription(db: Session, payload: WebhookSubscriptionCreate) -> WebhookSubscription:
    allowed_hosts = {host.strip().lower() for host in get_settings().webhook_allowed_hosts.split(",") if host.strip()}
    target_host = (urlparse(payload.target_url).hostname or "").lower()
    if not allowed_hosts or target_host not in allowed_hosts:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "webhook_target_not_allowlisted", "message": "The webhook target host is not on the tenant-approved outbound allowlist."},
        )
    subscription = WebhookSubscription(**payload.model_dump())
    db.add(subscription)
    db.flush()
    return subscription


def queue_webhook_deliveries(
    db: Session, event_type: WebhookEventType, payload: dict[str, object]
) -> list[WebhookDelivery]:
    subscriptions = list(
        db.scalars(
            select(WebhookSubscription).where(
                WebhookSubscription.event_type == event_type,
                WebhookSubscription.enabled.is_(True),
            )
        )
    )
    deliveries = [
        WebhookDelivery(
            subscription_id=subscription.id,
            event_type=event_type,
            payload=payload,
            status=WebhookDeliveryStatus.PENDING,
        )
        for subscription in subscriptions
    ]
    db.add_all(deliveries)
    db.flush()
    return deliveries

from typing import Any

from sqlalchemy.orm import Session

from app.core.security import Principal
from app.models.catalog import AuditEvent

SENSITIVE_METADATA_KEY_FRAGMENTS = {
    "secret",
    "password",
    "token",
    "authorization",
    "credential",
    "connection_string",
    "private_key",
}


def sanitize_audit_metadata(value: Any, key: str | None = None) -> Any:
    """Remove secrets recursively before an audit event can reach durable storage."""
    if key and any(fragment in key.lower() for fragment in SENSITIVE_METADATA_KEY_FRAGMENTS):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(item_key): sanitize_audit_metadata(item_value, str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [sanitize_audit_metadata(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_audit_metadata(item) for item in value]
    return value


def record_audit_event(
    db: Session,
    *,
    principal: Principal | None,
    action: str,
    resource_type: str,
    resource_id: str | None,
    outcome: str,
    request_id: str,
    metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    """Persist an auditable, credential-safe summary of a protected action."""
    event = AuditEvent(
        actor_subject=principal.subject if principal else None,
        actor_roles=sorted(principal.roles) if principal else [],
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        outcome=outcome,
        request_id=request_id,
        metadata_json=sanitize_audit_metadata(metadata or {}),
    )
    db.add(event)
    return event

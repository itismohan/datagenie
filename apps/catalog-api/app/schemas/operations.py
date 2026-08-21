import ipaddress
from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.catalog import RetentionResourceType, WebhookDeliveryStatus, WebhookEventType


class RetentionPolicyUpsert(BaseModel):
    resource_type: RetentionResourceType
    retention_days: int = Field(ge=1, le=3650)
    active: bool = True


class RetentionPolicyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    resource_type: RetentionResourceType
    retention_days: int
    active: bool
    last_applied_at: datetime | None
    created_at: datetime
    updated_at: datetime


class WebhookSubscriptionCreate(BaseModel):
    event_type: WebhookEventType
    target_url: str = Field(min_length=8, max_length=2048)
    secret_ref: str = Field(min_length=8, max_length=1024)

    @field_validator("target_url")
    @classmethod
    def require_public_https_target(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("Webhook targets must use HTTPS and include a hostname.")
        try:
            address = ipaddress.ip_address(parsed.hostname)
        except ValueError:
            address = None
        if address and (address.is_private or address.is_loopback or address.is_link_local or address.is_reserved):
            raise ValueError("Webhook targets must not resolve to a private or loopback IP address.")
        return value

    @field_validator("secret_ref")
    @classmethod
    def require_secret_reference(cls, value: str) -> str:
        normalized = value.strip()
        if not (normalized.startswith("env://") or normalized.startswith("vault://") or normalized.startswith("aws-secretsmanager://")):
            raise ValueError("Webhook signing secrets must be supplied as an external secret reference.")
        return normalized


class WebhookSubscriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_type: WebhookEventType
    target_url: str
    enabled: bool
    failure_count: int
    created_at: datetime
    updated_at: datetime


class WebhookDeliveryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    subscription_id: str
    event_type: WebhookEventType
    status: WebhookDeliveryStatus
    attempt_count: int
    next_attempt_at: datetime | None
    last_error: str | None
    delivered_at: datetime | None
    created_at: datetime

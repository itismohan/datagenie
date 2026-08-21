import hashlib
import hmac
import json
import os
from datetime import timedelta

import httpx
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.catalog import WebhookDelivery, WebhookDeliveryStatus, WebhookSubscription, utc_now


def _resolve_signing_secret(secret_ref: str) -> str:
    if not secret_ref.startswith("env://"):
        raise ValueError("Only env:// webhook signing secret references are supported by the current delivery worker.")
    secret_name = secret_ref.removeprefix("env://")
    secret = os.getenv(secret_name)
    if not secret:
        raise ValueError("Webhook signing secret reference could not be resolved.")
    return secret


def deliver_webhook(db: Session, delivery_id: str, settings: Settings) -> WebhookDelivery:
    delivery = db.get(WebhookDelivery, delivery_id)
    if delivery is None:
        raise ValueError("Webhook delivery not found.")
    if delivery.status in {WebhookDeliveryStatus.DELIVERED, WebhookDeliveryStatus.DEAD_LETTER}:
        return delivery
    subscription = db.get(WebhookSubscription, delivery.subscription_id)
    if subscription is None or not subscription.enabled:
        raise ValueError("Webhook subscription is unavailable.")

    payload_bytes = json.dumps(delivery.payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    signature = hmac.new(_resolve_signing_secret(subscription.secret_ref).encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    delivery.attempt_count += 1
    try:
        response = httpx.post(
            subscription.target_url,
            content=payload_bytes,
            headers={
                "Content-Type": "application/json",
                "X-DataGenie-Event": delivery.event_type.value,
                "X-DataGenie-Delivery": delivery.id,
                "X-DataGenie-Signature-256": f"sha256={signature}",
            },
            timeout=settings.webhook_delivery_timeout_seconds,
            follow_redirects=False,
        )
        response.raise_for_status()
    except Exception as exc:
        subscription.failure_count += 1
        delivery.status = WebhookDeliveryStatus.FAILED
        delivery.last_error = f"{type(exc).__name__}: {str(exc)[:500]}"
        delivery.next_attempt_at = utc_now() + timedelta(seconds=settings.connector_retry_backoff_seconds)
        db.commit()
        raise

    delivery.status = WebhookDeliveryStatus.DELIVERED
    delivery.delivered_at = utc_now()
    delivery.next_attempt_at = None
    delivery.last_error = None
    subscription.failure_count = 0
    db.commit()
    return delivery

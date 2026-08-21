from datetime import timedelta

import sentry_sdk

from app.core.config import get_settings
from app.core.error_tracking import configure_error_tracking
from app.core.tenant import tenant_context
from app.db.session import SessionLocal
from app.models.catalog import IngestionJob, JobStatus, WebhookDelivery, WebhookDeliveryStatus, utc_now
from app.services.ingestion_service import run_ingestion_job
from app.services.webhook_delivery_service import deliver_webhook
from app.workers.celery_app import celery


@celery.task(bind=True, name="app.workers.tasks.run_connector_job")
def run_connector_job(self, job_id: str, tenant_id: str) -> dict[str, object]:
    """Run a pre-persisted job; only workers execute connector network calls."""
    settings = get_settings()
    configure_error_tracking(settings)
    with tenant_context(tenant_id):
        db = SessionLocal()
        db.info["tenant_id"] = tenant_id
        try:
            job = run_ingestion_job(db, job_id, lease_seconds=settings.connector_lease_seconds)
            if job.status == JobStatus.FAILED:
                retry_number = self.request.retries + 1
                if retry_number > settings.connector_max_retries:
                    job.status = JobStatus.DEAD_LETTER
                    job.dead_lettered_at = utc_now()
                    job.next_retry_at = None
                    db.commit()
                    sentry_sdk.capture_message(
                        "Connector ingestion exhausted its retry budget and was moved to the dead-letter queue.",
                        level="error",
                    )
                    return {"job_id": job.id, "status": job.status.value, "attempt_count": job.attempt_count}

                countdown = settings.connector_retry_backoff_seconds * (2 ** self.request.retries)
                job.next_retry_at = utc_now() + timedelta(seconds=countdown)
                db.commit()
                raise self.retry(exc=RuntimeError(job.error_message or "Connector ingestion failed."), countdown=countdown)

            return {"job_id": job.id, "status": job.status.value, "attempt_count": job.attempt_count}
        finally:
            db.close()



@celery.task(bind=True, name="app.workers.tasks.deliver_webhook_event")
def deliver_webhook_event(self, delivery_id: str, tenant_id: str) -> dict[str, object]:
    """Deliver one outbox record without exposing signing secrets through API processes."""
    settings = get_settings()
    configure_error_tracking(settings)
    with tenant_context(tenant_id):
        db = SessionLocal()
        db.info["tenant_id"] = tenant_id
        try:
            try:
                delivery = deliver_webhook(db, delivery_id, settings)
            except Exception as exc:
                delivery = db.get(WebhookDelivery, delivery_id)
                retry_number = self.request.retries + 1
                if delivery is not None and retry_number > settings.webhook_max_retries:
                    delivery.status = WebhookDeliveryStatus.DEAD_LETTER
                    delivery.next_attempt_at = None
                    db.commit()
                    sentry_sdk.capture_exception(exc)
                    return {"delivery_id": delivery_id, "status": "dead_letter"}
                raise self.retry(exc=exc, countdown=settings.connector_retry_backoff_seconds * (2 ** self.request.retries))
            return {"delivery_id": delivery.id, "status": delivery.status.value}
        finally:
            db.close()


def enqueue_webhook_delivery(delivery_id: str, tenant_id: str) -> str:
    result = deliver_webhook_event.apply_async(args=[delivery_id, tenant_id])
    return result.id


def enqueue_connector_job(job_id: str, tenant_id: str) -> str:
    """Submit a durable job without executing connector work in the caller process."""
    result = run_connector_job.apply_async(args=[job_id, tenant_id])
    return result.id


def replay_dead_letter_job(job_id: str, tenant_id: str) -> str:
    """Resubmit a reviewed dead-letter job through the same worker path."""
    return enqueue_connector_job(job_id, tenant_id)

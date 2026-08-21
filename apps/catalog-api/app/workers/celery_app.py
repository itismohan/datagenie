from celery import Celery

from app.core.config import get_settings


settings = get_settings()
redis_url = settings.connector_redis_url or "redis://redis:6379/2"
celery = Celery("catalog_connector_worker", broker=redis_url, backend=redis_url, include=["app.workers.tasks"])
celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_always_eager=settings.connector_task_always_eager,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_time_limit=settings.connector_task_time_limit_seconds,
    task_soft_time_limit=settings.connector_task_soft_time_limit_seconds,
    broker_transport_options={"visibility_timeout": settings.connector_lease_seconds},
    task_routes={"app.workers.tasks.*": {"queue": "connectors"}},
)

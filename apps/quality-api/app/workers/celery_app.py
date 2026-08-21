from celery import Celery

from app.core.config import get_settings

settings = get_settings()
celery = Celery(
    "quality_worker", broker=settings.redis_url, backend=settings.redis_url, include=["app.workers.tasks"]
)
celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_always_eager=settings.quality_task_always_eager,
    task_routes={"app.workers.tasks.*": {"queue": "quality"}},
    beat_schedule={
        "dispatch-due-quality-schedules": {
            "task": "app.workers.tasks.dispatch_scheduled_runs",
            "schedule": 60.0,
        }
    },
)

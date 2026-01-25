
from celery import Celery

celery = Celery(
    "quality_worker",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0"
)

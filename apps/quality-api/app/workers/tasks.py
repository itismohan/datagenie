from app.db.session import SessionLocal
from app.services.execution_service import dispatch_due_schedules, execute_quality_run
from app.workers.celery_app import celery


@celery.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, retry_kwargs={"max_retries": 3})
def run_quality_job(self, run_id: str) -> dict[str, object]:
    """Execute one pre-persisted run. All customer-visible state lives in the quality database."""
    db = SessionLocal()
    try:
        run = execute_quality_run(db, run_id)
        return {
            "run_id": run.id,
            "status": run.status.value,
            "technical_score": run.technical_score,
            "explainable": run.explainable,
        }
    finally:
        db.close()


@celery.task
def dispatch_scheduled_runs() -> dict[str, object]:
    """Create due scheduled runs and enqueue them through the same durable execution path."""
    db = SessionLocal()
    try:
        runs = dispatch_due_schedules(db)
        for run in runs:
            run_quality_job.delay(run.id)
        return {"dispatched_run_ids": [run.id for run in runs], "count": len(runs)}
    finally:
        db.close()

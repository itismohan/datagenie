from types import SimpleNamespace

from app.models.catalog import JobStatus
from app.workers import tasks


class FakeSession:
    def __init__(self):
        self.info = {}
        self.commits = 0
        self.closed = False

    def commit(self):
        self.commits += 1

    def close(self):
        self.closed = True


def test_worker_moves_a_failed_job_to_dead_letter_after_retry_budget_is_exhausted(monkeypatch):
    session = FakeSession()
    job = SimpleNamespace(
        id="job-1",
        status=JobStatus.FAILED,
        attempt_count=4,
        error_message="connector timeout",
        dead_lettered_at=None,
        next_retry_at=None,
    )
    settings = SimpleNamespace(
        connector_lease_seconds=1_860,
        connector_max_retries=0,
        connector_retry_backoff_seconds=30,
        error_tracking_dsn=None,
        environment="development",
        error_tracking_traces_sample_rate=0.1,
    )
    monkeypatch.setattr(tasks, "SessionLocal", lambda: session)
    monkeypatch.setattr(tasks, "get_settings", lambda: settings)
    monkeypatch.setattr(tasks, "run_ingestion_job", lambda _db, _job_id, lease_seconds: job)

    result = tasks.run_connector_job.apply(args=[job.id, "tenant-finance"]).get()

    assert result == {"job_id": "job-1", "status": "dead_letter", "attempt_count": 4}
    assert job.status == JobStatus.DEAD_LETTER
    assert job.dead_lettered_at is not None
    assert session.info["tenant_id"] == "tenant-finance"
    assert session.commits == 1
    assert session.closed is True


def test_enqueue_connector_job_submits_a_task_without_invoking_ingestion_synchronously(monkeypatch):
    submitted = []
    monkeypatch.setattr(
        tasks.run_connector_job,
        "apply_async",
        lambda args: submitted.append(args) or SimpleNamespace(id="celery-task-456"),
    )

    task_id = tasks.enqueue_connector_job("job-2", "tenant-sales")

    assert task_id == "celery-task-456"
    assert submitted == [["job-2", "tenant-sales"]]

import importlib
import sys
from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient


def build_client(monkeypatch, tmp_path) -> tuple[TestClient, str, object]:
    secret = "test-jwt-secret-that-is-longer-than-thirty-two-characters"
    monkeypatch.setenv("DATAGENIE_ENVIRONMENT", "development")
    monkeypatch.setenv("DATAGENIE_DATABASE_URL", f"sqlite:///{tmp_path / 'connector-queue.db'}")
    monkeypatch.setenv("DATAGENIE_AUTH_ENABLED", "true")
    monkeypatch.setenv("DATAGENIE_AUTH_JWT_SECRET", secret)
    monkeypatch.setenv("DATAGENIE_CONNECTOR_REDIS_URL", "redis://test-connectors/2")

    from app.core.config import get_settings

    get_settings.cache_clear()
    for module_name in [
        "app.db.session",
        "app.api.v1.assets",
        "app.api.v1.sources",
        "app.api.v1.glossary",
        "app.api.v1.ingestion_jobs",
        "app.api.v1.governance",
        "app.main",
    ]:
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])
    import app.api.v1.sources as sources_module
    import app.main as main_module

    return TestClient(main_module.app), secret, sources_module


def headers(secret: str) -> dict[str, str]:
    access_token = jwt.encode(
        {
            "sub": "steward@example.com",
            "tenant_id": "tenant-finance",
            "roles": ["data_steward"],
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        secret,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {access_token}", "Idempotency-Key": "queue-ingestion-001"}


def source_payload() -> dict:
    return {
        "name": "finance-warehouse",
        "source_type": "postgresql",
        "host": "warehouse.internal",
        "database_name": "analytics",
        "username": "catalog_reader",
        "secret_ref": "env://WAREHOUSE_PASSWORD",
    }


def test_source_ingestion_persists_a_queued_job_before_worker_execution(monkeypatch, tmp_path):
    client, secret, sources_module = build_client(monkeypatch, tmp_path)
    queued: list[tuple[str, str]] = []
    monkeypatch.setattr(
        sources_module,
        "enqueue_connector_job",
        lambda job_id, tenant_id: queued.append((job_id, tenant_id)) or "celery-task-123",
    )

    with client:
        source = client.post("/api/v1/sources/", json=source_payload(), headers=headers(secret))
        job = client.post(f"/api/v1/sources/{source.json()['id']}/ingestion-jobs", json={"sync_mode": "incremental"}, headers=headers(secret))

    assert source.status_code == 201
    assert job.status_code == 201
    assert job.json()["status"] == "queued"
    assert job.json()["task_id"] == "celery-task-123"
    assert queued == [(job.json()["id"], "tenant-finance")]

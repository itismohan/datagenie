import importlib
import sys
from datetime import datetime, timezone

from fastapi.testclient import TestClient


def build_client(monkeypatch, tmp_path) -> TestClient:
    monkeypatch.setenv("DATAGENIE_QUALITY_DATABASE_URL", f"sqlite:///{tmp_path / 'quality-api.db'}")
    monkeypatch.setenv("DATAGENIE_QUALITY_TASK_ALWAYS_EAGER", "false")

    from app.core.config import get_settings

    get_settings.cache_clear()
    for module_name in [
        "app.db.session",
        "app.workers.celery_app",
        "app.workers.tasks",
        "app.api.v1.quality",
        "app.main",
    ]:
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])
    import app.main as main_module

    return TestClient(main_module.app)


def test_quality_api_persists_rules_profiles_queued_runs_and_explainable_results(monkeypatch, tmp_path) -> None:
    client = build_client(monkeypatch, tmp_path)
    from app.services.execution_service import execute_quality_run
    from app.db.session import SessionLocal

    with client:
        rule = client.post(
            "/api/v1/quality/rules",
            json={
                "asset_id": "asset-payments",
                "column_name": "payment_id",
                "name": "Payment identifier uniqueness",
                "rule_type": "uniqueness",
                "severity": "high",
                "owner": "payments-owner@example.com",
                "parameters": {"minimum_ratio": 0.99},
            },
            headers={"X-Quality-Actor": "steward@example.com"},
        )
        assert rule.status_code == 201
        assert rule.json()["version"] == 1

        profile = client.put(
            "/api/v1/quality/assets/asset-payments/profile",
            json={
                "snapshot": {
                    "columns": {
                        "payment_id": {
                            "row_count": 100,
                            "distinct_count": 100,
                            "sample_rows": [{"payment_id": "p-001"}],
                        }
                    }
                },
                "observed_at": datetime.now(timezone.utc).isoformat(),
                "profiled_by": "postgresql-profiler",
            },
        )
        assert profile.status_code == 200

        queued = client.post("/api/v1/quality/assets/asset-payments/runs", json={})
        assert queued.status_code == 202
        assert queued.json()["status"] == "queued"
        run_id = queued.json()["id"]

        db = SessionLocal()
        execute_quality_run(db, run_id)
        db.close()

        completed = client.get(f"/api/v1/quality/runs/{run_id}")
        assert completed.status_code == 200
        payload = completed.json()
        assert payload["status"] == "succeeded"
        assert payload["technical_score"] == 100
        assert payload["explainable"] is True
        assert payload["results"][0]["observed_value"]["ratio"] == 1.0
        assert payload["results"][0]["evidence"]["sample_rows"] == [{"payment_id": "p-001"}]

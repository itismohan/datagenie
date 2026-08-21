import importlib
import sys
from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient


def build_client(monkeypatch, tmp_path) -> tuple[TestClient, str]:
    secret = "test-jwt-secret-that-is-longer-than-thirty-two-characters"
    monkeypatch.setenv("DATAGENIE_ENVIRONMENT", "development")
    monkeypatch.setenv("DATAGENIE_DATABASE_URL", f"sqlite:///{tmp_path / 'tenant-api.db'}")
    monkeypatch.setenv("DATAGENIE_AUTH_ENABLED", "true")
    monkeypatch.setenv("DATAGENIE_AUTH_JWT_SECRET", secret)

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
    import app.main as main_module

    return TestClient(main_module.app), secret


def tenant_headers(secret: str, tenant_id: str) -> dict[str, str]:
    access_token = jwt.encode(
        {
            "sub": "platform-admin@example.com",
            "tenant_id": tenant_id,
            "roles": ["platform_admin"],
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        secret,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {access_token}"}


def source_payload(name: str) -> dict:
    return {
        "name": name,
        "source_type": "postgresql",
        "host": "warehouse.internal",
        "database_name": "analytics",
        "username": "catalog_reader",
        "secret_ref": "env://WAREHOUSE_PASSWORD",
    }


def test_authenticated_tenant_boundaries_filter_source_lists_and_direct_resource_reads(monkeypatch, tmp_path):
    client, secret = build_client(monkeypatch, tmp_path)
    finance_headers = tenant_headers(secret, "tenant-finance")
    sales_headers = tenant_headers(secret, "tenant-sales")

    with client:
        finance = client.post("/api/v1/sources/", json=source_payload("finance-warehouse"), headers=finance_headers)
        sales = client.post("/api/v1/sources/", json=source_payload("sales-warehouse"), headers=sales_headers)
        finance_list = client.get("/api/v1/sources/", headers=finance_headers)
        sales_list = client.get("/api/v1/sources/", headers=sales_headers)
        finance_audit = client.get("/api/v1/audit-events/", headers=finance_headers)
        sales_audit = client.get("/api/v1/audit-events/", headers=sales_headers)
        cross_tenant_read = client.get(f"/api/v1/sources/{finance.json()['id']}", headers=sales_headers)

    assert finance.status_code == 201
    assert sales.status_code == 201
    assert [item["name"] for item in finance_list.json()] == ["finance-warehouse"]
    assert [item["name"] for item in sales_list.json()] == ["sales-warehouse"]
    assert finance.json()["id"] in {item["resource_id"] for item in finance_audit.json()["items"]}
    assert sales.json()["id"] not in {item["resource_id"] for item in finance_audit.json()["items"]}
    assert sales.json()["id"] in {item["resource_id"] for item in sales_audit.json()["items"]}
    assert finance.json()["id"] not in {item["resource_id"] for item in sales_audit.json()["items"]}
    assert cross_tenant_read.status_code == 404

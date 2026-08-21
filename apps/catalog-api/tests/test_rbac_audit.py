import importlib
import json
import sys
from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient

from app.services.audit_service import sanitize_audit_metadata


def build_client(monkeypatch, tmp_path) -> tuple[TestClient, str]:
    secret = "rbac-test-secret-that-is-longer-than-thirty-two-characters"
    monkeypatch.setenv("DATAGENIE_ENVIRONMENT", "development")
    monkeypatch.setenv("DATAGENIE_DATABASE_URL", f"sqlite:///{tmp_path / 'rbac.db'}")
    monkeypatch.setenv("DATAGENIE_AUTH_ENABLED", "true")
    monkeypatch.setenv("DATAGENIE_AUTH_JWT_SECRET", secret)

    from app.core.config import get_settings

    get_settings.cache_clear()
    for module_name in ["app.db.session", "app.api.v1.assets", "app.api.v1.sources", "app.api.v1.glossary", "app.api.v1.ingestion_jobs", "app.api.v1.audit", "app.main"]:
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])
    import app.main as main_module

    return TestClient(main_module.app), secret


def token(secret: str, subject: str, roles: list[str]) -> str:
    return jwt.encode(
        {"sub": subject, "roles": roles, "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        secret,
        algorithm="HS256",
    )


def headers(secret: str, subject: str, role: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token(secret, subject, [role])}"}


def test_connector_management_permissions_and_audit_history(monkeypatch, tmp_path) -> None:
    client, secret = build_client(monkeypatch, tmp_path)
    steward_headers = headers(secret, "steward@example.com", "data_steward")
    analyst_headers = headers(secret, "analyst@example.com", "analyst")
    admin_headers = headers(secret, "admin@example.com", "platform_admin")
    source_payload = {
        "name": "protected-finance-source",
        "source_type": "postgresql",
        "host": "finance.internal",
        "database_name": "finance",
        "username": "catalog_reader",
        "secret_ref": "env://DATAGENIE_FINANCE_PASSWORD",
    }

    with client:
        created = client.post("/api/v1/sources/", json=source_payload, headers=steward_headers)
        assert created.status_code == 201
        source_id = created.json()["id"]

        denied = client.get("/api/v1/sources/", headers=analyst_headers)
        assert denied.status_code == 403
        assert denied.json()["error"]["code"] == "forbidden"

        inspected = client.get(f"/api/v1/sources/{source_id}/capabilities", headers=steward_headers)
        assert inspected.status_code == 200

        state = client.get(f"/api/v1/sources/{source_id}/sync-state", headers=steward_headers)
        assert state.status_code == 200
        assert state.json()["cursor"] == {}

        unauthorized_audit = client.get("/api/v1/audit-events/", headers=steward_headers)
        assert unauthorized_audit.status_code == 403

        audit_response = client.get("/api/v1/audit-events/", headers=admin_headers)
        assert audit_response.status_code == 200
        events = audit_response.json()["items"]

    actions = {event["action"] for event in events}
    assert {"source.create", "source.capabilities", "source.sync_state", "authorization.denied"}.issubset(actions)
    source_create = next(event for event in events if event["action"] == "source.create")
    assert source_create["actor_subject"] == "steward@example.com"
    assert source_create["resource_id"] == source_id
    assert "secret_ref" not in json.dumps(source_create["metadata_json"])
    assert "DATAGENIE_FINANCE_PASSWORD" not in json.dumps(events)


def test_audit_metadata_redacts_nested_secrets() -> None:
    sanitized = sanitize_audit_metadata(
        {
            "secret_ref": "env://DATAGENIE_SOURCE_PASSWORD",
            "nested": {"access_token": "token-value", "safe": "visible"},
            "items": [{"private_key": "private-key-value"}],
        }
    )
    assert sanitized == {
        "secret_ref": "[REDACTED]",
        "nested": {"access_token": "[REDACTED]", "safe": "visible"},
        "items": [{"private_key": "[REDACTED]"}],
    }


def test_data_owner_can_curate_only_assigned_assets(monkeypatch, tmp_path) -> None:
    client, secret = build_client(monkeypatch, tmp_path)
    from app.db.session import SessionLocal
    from app.models.catalog import Asset, AssetType, DataSource, SourceType

    with client:
        db = SessionLocal()
        source = DataSource(
            name="rbac-owner-source",
            source_type=SourceType.POSTGRESQL,
            host="warehouse.internal",
            port=5432,
            database_name="analytics",
            username="catalog_reader",
            secret_ref="env://DATAGENIE_OWNER_PASSWORD",
        )
        db.add(source)
        db.flush()
        owned_asset = Asset(
            source_id=source.id,
            asset_type=AssetType.TABLE,
            qualified_name="analytics.public.orders",
            name="orders",
            database_name="analytics",
            schema_name="public",
            technical_metadata={"engine": "postgresql"},
            owner="owner@example.com",
        )
        db.add(owned_asset)
        db.commit()
        asset_id = owned_asset.id
        db.close()

        owner_headers = headers(secret, "owner@example.com", "data_owner")
        permitted = client.patch(
            f"/api/v1/assets/{asset_id}",
            json={"description": "Owner-curated description"},
            headers=owner_headers,
        )
        assert permitted.status_code == 200
        assert permitted.json()["description"] == "Owner-curated description"

        other_owner_headers = headers(secret, "other-owner@example.com", "data_owner")
        denied = client.patch(
            f"/api/v1/assets/{asset_id}",
            json={"description": "Unexpected update"},
            headers=other_owner_headers,
        )
        assert denied.status_code == 403

        admin_headers = headers(secret, "admin@example.com", "platform_admin")
        events = client.get("/api/v1/audit-events/", headers=admin_headers).json()["items"]

    denied_event = next(
        event
        for event in events
        if event["action"] == "asset.curate" and event["outcome"] == "denied" and event["actor_subject"] == "other-owner@example.com"
    )
    assert denied_event["resource_id"] == asset_id

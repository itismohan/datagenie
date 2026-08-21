import importlib
import json
import sys
from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient


def build_client(monkeypatch, tmp_path) -> tuple[TestClient, str]:
    secret = "policy-test-secret-that-is-longer-than-thirty-two-characters"
    monkeypatch.setenv("DATAGENIE_ENVIRONMENT", "development")
    monkeypatch.setenv("DATAGENIE_DATABASE_URL", f"sqlite:///{tmp_path / 'policy.db'}")
    monkeypatch.setenv("DATAGENIE_AUTH_ENABLED", "true")
    monkeypatch.setenv("DATAGENIE_AUTH_JWT_SECRET", secret)

    from app.core.config import get_settings

    get_settings.cache_clear()
    for module_name in [
        "app.db.session",
        "app.core.policy",
        "app.api.v1.assets",
        "app.api.v1.governance",
        "app.api.v1.policy",
        "app.main",
    ]:
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])
    import app.main as main_module

    return TestClient(main_module.app), secret


def headers(secret: str, subject: str, roles: list[str], tenant_id: str) -> dict[str, str]:
    token = jwt.encode(
        {
            "sub": subject,
            "roles": roles,
            "tenant_id": tenant_id,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        secret,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def create_asset(tenant_id: str) -> str:
    from app.db.session import SessionLocal
    from app.models.catalog import Asset, AssetType, DataSource, SourceType

    db = SessionLocal()
    db.info["tenant_id"] = tenant_id
    source = DataSource(
        name=f"policy-source-{tenant_id}",
        source_type=SourceType.POSTGRESQL,
        host="warehouse.internal",
        database_name="analytics",
        username="catalog_reader",
        secret_ref="env://DATAGENIE_POLICY_TEST",
    )
    db.add(source)
    db.flush()
    asset = Asset(
        source_id=source.id,
        asset_type=AssetType.TABLE,
        qualified_name=f"analytics.public.policy_orders_{tenant_id}",
        name=f"policy_orders_{tenant_id}",
        technical_metadata={"engine": "postgresql"},
        owner="owner@example.com",
    )
    db.add(asset)
    db.commit()
    asset_id = asset.id
    db.close()
    return asset_id


def test_policy_endpoint_returns_explainable_allow_and_minimized_audit(monkeypatch, tmp_path) -> None:
    client, secret = build_client(monkeypatch, tmp_path)
    with client:
        asset_id = create_asset("tenant-a")
        response = client.post(
            "/api/v1/policy/decisions",
            json={
                "action": "asset.read",
                "resource": {"resource_type": "asset", "resource_id": asset_id},
                "purpose": "catalog analysis",
                "context": {},
            },
            headers={**headers(secret, "analyst@example.com", ["analyst"], "tenant-a"), "X-Request-ID": "policy-request-1"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["outcome"] == "allow"
        assert body["decision_version"] == "1.0.0"
        assert body["request_id"] == "policy-request-1"
        assert body["resource_visible"] is True
        assert "DG-POLICY-RBAC-ALLOW" in body["rule_ids"]
        assert body["evidence"]
        assert body["expires_at"] > body["evaluated_at"]

        events = client.get(
            "/api/v1/audit-events/",
            headers=headers(secret, "admin@example.com", ["platform_admin"], "tenant-a"),
        ).json()["items"]

    event = next(event for event in events if event["action"] == "policy.decision")
    assert event["outcome"] == "allow"
    assert event["request_id"] == "policy-request-1"
    serialized = json.dumps(event["metadata_json"])
    assert "catalog analysis" not in serialized
    assert event["metadata_json"]["purpose_digest"]
    assert event["metadata_json"]["resource_visible"] is True


def test_sensitive_asset_returns_obligations_and_asset_route_does_not_bypass_them(monkeypatch, tmp_path) -> None:
    client, secret = build_client(monkeypatch, tmp_path)
    with client:
        asset_id = create_asset("tenant-a")
        from app.db.session import SessionLocal
        from app.models.catalog import Asset

        db = SessionLocal()
        db.info["tenant_id"] = "tenant-a"
        asset = db.get(Asset, asset_id)
        assert asset is not None
        asset.classification = "payment_data"
        db.commit()
        db.close()

        analyst = headers(secret, "analyst@example.com", ["analyst"], "tenant-a")
        decision = client.post(
            "/api/v1/policy/decisions",
            json={
                "action": "asset.read",
                "resource": {"resource_type": "asset", "resource_id": asset_id},
                "purpose": "financial reporting analysis",
                "context": {},
            },
            headers=analyst,
        )
        assert decision.status_code == 200
        assert decision.json()["outcome"] == "allow_with_obligations"
        assert "handle_sensitive_data" in decision.json()["obligations"]

        protected_read = client.get(
            f"/api/v1/assets/{asset_id}?purpose=financial%20reporting%20analysis",
            headers=analyst,
        )

    assert protected_read.status_code == 403
    assert protected_read.json()["error"]["code"] == "policy_denied"
    assert protected_read.json()["error"]["details"]["outcome"] == "allow_with_obligations"


def test_foreign_tenant_policy_request_is_non_visible_and_audited(monkeypatch, tmp_path) -> None:
    client, secret = build_client(monkeypatch, tmp_path)
    with client:
        asset_id = create_asset("tenant-a")
        foreign = headers(secret, "foreign@example.com", ["analyst"], "tenant-b")
        response = client.post(
            "/api/v1/policy/decisions",
            json={
                "action": "asset.read",
                "resource": {"resource_type": "asset", "resource_id": asset_id},
                "purpose": "catalog analysis",
                "context": {},
            },
            headers=foreign,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["outcome"] == "deny"
        assert body["resource_visible"] is False
        assert body["evidence"] == [{"type": "resource", "reference": "not-visible"}]

        events = client.get(
            "/api/v1/audit-events/",
            headers=headers(secret, "foreign-admin@example.com", ["platform_admin"], "tenant-b"),
        ).json()["items"]

    event = next(event for event in events if event["action"] == "policy.decision")
    assert event["outcome"] == "deny"
    assert event["resource_id"] is None
    assert event["metadata_json"]["resource_visible"] is False


def test_stale_quality_certification_requires_human_approval(monkeypatch, tmp_path) -> None:
    client, secret = build_client(monkeypatch, tmp_path)
    with client:
        asset_id = create_asset("tenant-a")
        from app.db.session import SessionLocal
        from app.models.catalog import CertificationRequest

        db = SessionLocal()
        db.info["tenant_id"] = "tenant-a"
        request = CertificationRequest(asset_id=asset_id, requested_by="analyst@example.com")
        db.add(request)
        db.commit()
        request_id = request.id
        db.close()

        response = client.post(
            "/api/v1/policy/decisions",
            json={
                "action": "certification.decide",
                "resource": {"resource_type": "certification_request", "resource_id": request_id},
                "context": {},
            },
            headers=headers(secret, "steward@example.com", ["data_steward"], "tenant-a"),
        )

    assert response.status_code == 200
    assert response.json()["outcome"] == "requires_human_approval"
    assert "DG-POLICY-QUALITY-FRESHNESS-APPROVAL" in response.json()["rule_ids"]
    assert "obtain_current_explainable_quality_evidence" in response.json()["obligations"]


def test_policy_context_cannot_add_authority_or_tenant_override(monkeypatch, tmp_path) -> None:
    client, secret = build_client(monkeypatch, tmp_path)
    with client:
        asset_id = create_asset("tenant-a")
        response = client.post(
            "/api/v1/policy/decisions",
            json={
                "action": "asset.read",
                "resource": {"resource_type": "asset", "resource_id": asset_id},
                "purpose": "catalog analysis",
                "context": {"tenant_id": "tenant-b", "roles": ["platform_admin"], "outcome": "allow"},
            },
            headers=headers(secret, "analyst@example.com", ["analyst"], "tenant-a"),
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"

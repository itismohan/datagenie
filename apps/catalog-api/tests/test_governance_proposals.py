import base64
import hashlib
import hmac
import importlib
import json
import sys
import time
from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient


def build_client(monkeypatch, tmp_path) -> tuple[TestClient, str]:
    secret = "proposal-test-secret-that-is-longer-than-thirty-two-characters"
    monkeypatch.setenv("DATAGENIE_ENVIRONMENT", "development")
    monkeypatch.setenv("DATAGENIE_DATABASE_URL", f"sqlite:///{tmp_path / 'proposals.db'}")
    monkeypatch.setenv("DATAGENIE_AUTH_ENABLED", "true")
    monkeypatch.setenv("DATAGENIE_AUTH_JWT_SECRET", secret)
    monkeypatch.setenv("DATAGENIE_MCP_GATEWAY_SERVICE_ID", "mcp-gateway")
    monkeypatch.setenv("DATAGENIE_MCP_GATEWAY_SERVICE_SHARED_SECRET", "gateway-service-secret")
    monkeypatch.setenv("DATAGENIE_MCP_GATEWAY_SERVICE_IDENTITY_ENABLED", "true")
    from app.core.config import get_settings

    get_settings.cache_clear()
    for module_name in [
        "app.db.session",
        "app.core.policy",
        "app.services.policy_service",
        "app.services.proposal_service",
        "app.api.v1.proposals",
        "app.main",
    ]:
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])
    import app.main as main_module

    return TestClient(main_module.app), secret


def headers(secret: str, subject: str, roles: list[str], tenant_id: str, *, expiry_seconds: int = 300) -> dict[str, str]:
    token = jwt.encode(
        {
            "sub": subject,
            "roles": roles,
            "tenant_id": tenant_id,
            "exp": datetime.now(timezone.utc) + timedelta(seconds=expiry_seconds),
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
        name=f"proposal-source-{tenant_id}",
        source_type=SourceType.POSTGRESQL,
        host="warehouse.internal",
        database_name="analytics",
        username="catalog_reader",
        secret_ref="env://DATAGENIE_PROPOSAL_TEST",
    )
    db.add(source)
    db.flush()
    asset = Asset(
        source_id=source.id,
        asset_type=AssetType.TABLE,
        qualified_name=f"analytics.public.proposal_orders_{tenant_id}",
        name=f"proposal_orders_{tenant_id}",
        technical_metadata={"engine": "postgresql"},
        owner="owner@example.com",
    )
    db.add(asset)
    db.commit()
    asset_id = asset.id
    db.close()
    return asset_id


def proposal_payload(asset_id: str, *, title: str = "Curate payments description", technical_version: int = 1) -> dict:
    return {
        "proposal_type": "asset_curation",
        "title": title,
        "proposal_text": "Update the business description using approved glossary evidence.",
        "resource": {"resource_type": "asset", "resource_id": asset_id},
        "purpose": "metadata stewardship",
        "diff": {"description": "Daily payment settlement facts", "tags": ["finance", "payments"]},
        "evidence": [{"type": "glossary_term", "reference": "term:payments-settlement"}],
        "impact": {"summary": "Metadata-only change", "risk_level": "low"},
        "version_preconditions": {"technical_version": technical_version},
        "source": {"channel": "api", "agent_id": "agent-1", "model_id": "approved-model"},
    }


def signed_mcp_headers(*, subject: str = "analyst@example.com", tenant_id: str = "tenant-a", host_id: str = "approved-host") -> dict[str, str]:
    timestamp = str(int(time.time()))
    actor = {"subject": subject, "tenant_id": tenant_id, "roles": ["analyst"], "host_id": host_id}
    actor_b64 = base64.urlsafe_b64encode(json.dumps(actor, separators=(",", ":"), sort_keys=True).encode()).decode().rstrip("=")
    signing_input = "\n".join([timestamp, "POST", "/api/v1/internal/mcp/proposals", actor_b64]).encode()
    signature = hmac.new(b"gateway-service-secret", signing_input, hashlib.sha256).hexdigest()
    return {
        "X-DataGenie-Service-Id": "mcp-gateway",
        "X-DataGenie-Service-Timestamp": timestamp,
        "X-DataGenie-Service-Actor": actor_b64,
        "X-DataGenie-Service-Signature": signature,
    }


def create_proposal(client: TestClient, secret: str, asset_id: str, *, key: str = "proposal-key", technical_version: int = 1) -> dict:
    response = client.post(
        "/api/v1/governance/proposals",
        json=proposal_payload(asset_id, technical_version=technical_version),
        headers={**headers(secret, "analyst@example.com", ["analyst"], "tenant-a"), "Idempotency-Key": key},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_steward_inbox_approves_and_executes_a_proposal_once(monkeypatch, tmp_path) -> None:
    client, secret = build_client(monkeypatch, tmp_path)
    with client:
        asset_id = create_asset("tenant-a")
        created = create_proposal(client, secret, asset_id)
        assert created["status"] == "pending_review"
        assert created["initiating_model_id"] == "approved-model"
        assert created["initiating_host_id"] is None
        assert created["policy_snapshot"]["outcome"] == "allow"
        assert created["audit_event_id"]

        inbox = client.get("/api/v1/governance/inbox", headers=headers(secret, "steward@example.com", ["data_steward"], "tenant-a"))
        assert inbox.status_code == 200
        assert "Structured diff" in inbox.text
        assert "approved-model" in inbox.text

        approval = client.post(
            f"/api/v1/governance/proposals/{created['id']}/approve",
            json={"review_note": "Evidence and impact reviewed."},
            headers=headers(secret, "steward@example.com", ["data_steward"], "tenant-a"),
        )
        assert approval.status_code == 200, approval.text
        approved = approval.json()
        assert approved["status"] == "approved"
        assert approved["confirmation_nonce"]

        execute = client.post(
            f"/api/v1/governance/proposals/{created['id']}/execute",
            json={"proposal_hash": approved["proposal_hash"], "confirmation_nonce": approved["confirmation_nonce"]},
            headers=headers(secret, "steward@example.com", ["data_steward"], "tenant-a"),
        )
        assert execute.status_code == 200, execute.text
        assert execute.json()["status"] == "executed"
        assert execute.json()["execution_result"]["changed_fields"] == ["description", "tags"]

        replay = client.post(
            f"/api/v1/governance/proposals/{created['id']}/execute",
            json={"proposal_hash": approved["proposal_hash"], "confirmation_nonce": approved["confirmation_nonce"]},
            headers=headers(secret, "steward@example.com", ["data_steward"], "tenant-a"),
        )
        assert replay.status_code == 409
        assert replay.json()["error"]["code"] == "proposal_not_approved"


def test_bounded_certification_and_quality_schedule_handlers_require_steward_confirmation(monkeypatch, tmp_path) -> None:
    client, secret = build_client(monkeypatch, tmp_path)
    with client:
        asset_id = create_asset("tenant-a")
        typed_payloads = [
            {
                **proposal_payload(asset_id, title="Request certification review"),
                "proposal_type": "certification_review_request",
                "proposal_text": "Request a human certification review; no certification decision is applied directly.",
                "diff": {"note": "Evidence reviewed by the initiating agent."},
            },
            {
                **proposal_payload(asset_id, title="Schedule explainable quality checks"),
                "proposal_type": "quality_check_schedule",
                "proposal_text": "Request a steward-approved quality schedule; no job is dispatched before confirmation.",
                "diff": {"schedule": {"frequency": "daily", "rule_types": ["completeness"]}},
            },
        ]
        expected_resource_types = ["certification_request", "quality_check_schedule_request"]
        for index, (payload, expected_type) in enumerate(zip(typed_payloads, expected_resource_types), start=1):
            created = client.post(
                "/api/v1/governance/proposals",
                json=payload,
                headers={**headers(secret, "analyst@example.com", ["analyst"], "tenant-a"), "Idempotency-Key": f"typed-proposal-{index}"},
            )
            assert created.status_code == 201, created.text
            proposal = created.json()
            approval = client.post(
                f"/api/v1/governance/proposals/{proposal['id']}/approve",
                json={"review_note": "Steward reviewed the request."},
                headers=headers(secret, "steward@example.com", ["data_steward"], "tenant-a"),
            )
            assert approval.status_code == 200, approval.text
            executed = client.post(
                f"/api/v1/governance/proposals/{proposal['id']}/execute",
                json={"proposal_hash": approval.json()["proposal_hash"], "confirmation_nonce": approval.json()["confirmation_nonce"]},
                headers=headers(secret, "steward@example.com", ["data_steward"], "tenant-a"),
            )
            assert executed.status_code == 200, executed.text
            assert executed.json()["execution_result"]["resource_type"] == expected_type


def test_signed_mcp_delegation_binds_verified_host_identity(monkeypatch, tmp_path) -> None:
    client, _ = build_client(monkeypatch, tmp_path)
    with client:
        asset_id = create_asset("tenant-a")
        payload = proposal_payload(asset_id)
        payload["source"]["channel"] = "mcp"
        created = client.post("/api/v1/internal/mcp/proposals", json=payload, headers=signed_mcp_headers())
        assert created.status_code == 201, created.text
        assert created.json()["initiating_host_id"] == "approved-host"
        assert created.json()["source_channel"] == "mcp"
        assert created.json()["inbox_uri"].endswith(created.json()["id"])


def test_public_api_rejects_spoofed_mcp_provenance(monkeypatch, tmp_path) -> None:
    client, secret = build_client(monkeypatch, tmp_path)
    with client:
        asset_id = create_asset("tenant-a")
        payload = proposal_payload(asset_id)
        payload["source"]["channel"] = "mcp"
        rejected = client.post(
            "/api/v1/governance/proposals",
            json=payload,
            headers={**headers(secret, "analyst@example.com", ["analyst"], "tenant-a"), "Idempotency-Key": "spoofed-mcp", "X-DataGenie-MCP-Host": "untrusted-host"},
        )
        assert rejected.status_code == 422
        assert rejected.json()["error"]["code"] == "mcp_delegation_required"


def test_expired_credentials_cannot_create_governance_proposals(monkeypatch, tmp_path) -> None:
    client, secret = build_client(monkeypatch, tmp_path)
    with client:
        asset_id = create_asset("tenant-a")
        expired = client.post(
            "/api/v1/governance/proposals",
            json=proposal_payload(asset_id),
            headers={**headers(secret, "analyst@example.com", ["analyst"], "tenant-a", expiry_seconds=-1), "Idempotency-Key": "expired-credential"},
        )
        assert expired.status_code == 401


def test_creation_is_idempotent_and_body_conflicts_are_rejected(monkeypatch, tmp_path) -> None:
    client, secret = build_client(monkeypatch, tmp_path)
    with client:
        asset_id = create_asset("tenant-a")
        first = create_proposal(client, secret, asset_id, key="same-key")
        second = client.post(
            "/api/v1/governance/proposals",
            json=proposal_payload(asset_id),
            headers={**headers(secret, "analyst@example.com", ["analyst"], "tenant-a"), "Idempotency-Key": "same-key"},
        )
        assert second.status_code == 201
        assert second.headers["Idempotent-Replayed"] == "true"
        assert second.json()["id"] == first["id"]
        conflict = client.post(
            "/api/v1/governance/proposals",
            json=proposal_payload(asset_id, title="Changed request body"),
            headers={**headers(secret, "analyst@example.com", ["analyst"], "tenant-a"), "Idempotency-Key": "same-key"},
        )
        assert conflict.status_code == 409
        assert conflict.json()["error"]["code"] == "idempotency_conflict"


def test_stale_resource_cancelled_and_revoked_approvals_cannot_mutate(monkeypatch, tmp_path) -> None:
    client, secret = build_client(monkeypatch, tmp_path)
    with client:
        asset_id = create_asset("tenant-a")
        created = create_proposal(client, secret, asset_id, key="stale-key")
        approved = client.post(
            f"/api/v1/governance/proposals/{created['id']}/approve",
            json={"review_note": "Approved."},
            headers=headers(secret, "steward@example.com", ["data_steward"], "tenant-a"),
        ).json()
        from app.db.session import SessionLocal
        from app.models.catalog import Asset

        db = SessionLocal()
        db.info["tenant_id"] = "tenant-a"
        asset = db.get(Asset, asset_id)
        assert asset is not None
        asset.technical_version = 2
        db.commit()
        db.close()
        stale = client.post(
            f"/api/v1/governance/proposals/{created['id']}/execute",
            json={"proposal_hash": approved["proposal_hash"], "confirmation_nonce": approved["confirmation_nonce"]},
            headers=headers(secret, "steward@example.com", ["data_steward"], "tenant-a"),
        )
        assert stale.status_code == 409
        assert stale.json()["error"]["code"] == "proposal_precondition_failed"

        second = create_proposal(client, secret, asset_id, key="cancel-key", technical_version=2)
        cancelled = client.post(
            f"/api/v1/governance/proposals/{second['id']}/cancel",
            headers=headers(secret, "analyst@example.com", ["analyst"], "tenant-a"),
        )
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "cancelled"
        blocked = client.post(
            f"/api/v1/governance/proposals/{second['id']}/execute",
            json={"proposal_hash": second["proposal_hash"], "confirmation_nonce": "x" * 43},
            headers=headers(secret, "steward@example.com", ["data_steward"], "tenant-a"),
        )
        assert blocked.status_code == 409

        third = create_proposal(client, secret, asset_id, key="revoked-key", technical_version=2)
        approved_third = client.post(
            f"/api/v1/governance/proposals/{third['id']}/approve",
            json={"review_note": "Approved."},
            headers=headers(secret, "steward@example.com", ["data_steward"], "tenant-a"),
        ).json()
        revoked = client.post(
            f"/api/v1/governance/proposals/{third['id']}/execute",
            json={"proposal_hash": approved_third["proposal_hash"], "confirmation_nonce": approved_third["confirmation_nonce"]},
            headers=headers(secret, "steward@example.com", ["analyst"], "tenant-a"),
        )
        assert revoked.status_code == 403


def test_foreign_tenant_cannot_read_or_approve_a_proposal(monkeypatch, tmp_path) -> None:
    client, secret = build_client(monkeypatch, tmp_path)
    with client:
        asset_id = create_asset("tenant-a")
        created = create_proposal(client, secret, asset_id, key="tenant-key")
        foreign = client.get(f"/api/v1/governance/proposals/{created['id']}", headers=headers(secret, "foreign@example.com", ["data_steward"], "tenant-b"))
        assert foreign.status_code == 404
        approval = client.post(
            f"/api/v1/governance/proposals/{created['id']}/approve",
            json={"review_note": "Attempt cross tenant approval."},
            headers=headers(secret, "foreign@example.com", ["data_steward"], "tenant-b"),
        )
        assert approval.status_code == 404

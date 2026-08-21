from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.schemas import PolicyEvidence, PolicyPacket
from app.server import McpApplication, create_app
from app.services.execution_ledger import ExecutionLedger


class FakeClient:
    def __init__(self, outcome: str = "allow_with_obligations") -> None:
        self.outcome = outcome

    async def close(self) -> None:
        return None

    async def evaluate_policy(self, _principal, _request_id, _asset_id, _purpose):
        return PolicyPacket(
            outcome=self.outcome,
            rule_ids=["DG-POLICY-RBAC-ALLOW"],
            evidence=[PolicyEvidence(type="asset", reference="asset:asset-1")],
            obligations=["handle_sensitive_data"] if self.outcome == "allow_with_obligations" else [],
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            decision_version="1.0.0",
        )

    async def search_assets(self, _principal, _request_id, _params):
        return {"items": [{"asset": {"id": "asset-1", "name": "payments"}, "policy": {"outcome": "allow"}}], "total": 1, "visible_total": 1, "facets": {}, "index_fresh_at": "2026-08-22T00:00:00Z"}

    async def asset_context(self, _principal, _request_id, _asset_id, _purpose):
        return {"asset": {"id": "asset-1", "name": "payments", "technical_metadata": {"secret_like": "redacted"}, "columns": []}}

    async def quality_evidence(self, _principal, _request_id, asset_id, _purpose, _history_limit):
        return {"asset_id": asset_id, "state": "current", "technical_score": 93, "explainable_at": "2026-08-22T00:00:00Z", "runs": [], "incidents": [], "evidence": [{"type": "catalog_quality_summary", "reference": f"catalog:asset:{asset_id}"}], "source": "catalog-api"}

    async def lineage_impact(self, _principal, _request_id, asset_id, direction, depth, _purpose):
        return {"focal_asset_id": asset_id, "direction": direction, "depth": depth, "nodes": [{"id": asset_id}], "edges": []}


def make_client(tmp_path, outcome: str = "allow_with_obligations") -> tuple[TestClient, str]:
    secret = "mcp-test-secret-that-is-longer-than-thirty-two-characters"
    settings = Settings(
        auth_jwt_secret=secret,
        downstream_service_shared_secret="gateway-service-secret",
        mcp_internal_beta_enabled=True,
        mcp_allowed_tenants="internal-beta",
        mcp_allowed_hosts="approved-host",
        mcp_allowed_origins="https://host.internal",
        ledger_database_url=f"sqlite:///{tmp_path / 'ledger.db'}",
    )
    ledger = ExecutionLedger(settings.ledger_database_url)
    runtime = McpApplication(settings=settings, client=FakeClient(outcome), ledger=ledger)
    return TestClient(create_app(runtime)), secret


def headers(secret: str) -> dict[str, str]:
    token = jwt.encode(
        {"sub": "analyst@example.com", "tenant_id": "internal-beta", "roles": ["analyst"], "scope": "catalog:read quality:read lineage:read", "aud": "datagenie-mcp", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        secret,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}", "Mcp-Client-Id": "approved-host", "MCP-Protocol-Version": "2026-07-28", "Content-Type": "application/json"}


def call(name: str, arguments: dict) -> dict:
    return {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": arguments}}


def test_tool_call_returns_structured_evidence_policy_obligations_and_redactions(tmp_path) -> None:
    client, secret = make_client(tmp_path)
    with client:
        response = client.post("/mcp", json=call("get_asset_context", {"asset_id": "asset-1", "purpose": "financial reporting analysis"}), headers=headers(secret))

    assert response.status_code == 200
    body = response.json()["result"]["structuredContent"]
    assert body["tenant_bound"] is True
    assert body["policy"]["outcome"] == "allow_with_obligations"
    assert body["obligations"] == ["handle_sensitive_data"]
    assert body["provenance"] and body["evidence"] and body["timestamp"]
    assert "technical_metadata" not in body["data"]["asset"]
    assert body["confidence"] > 0


def test_all_remaining_read_tools_return_structured_evidence_packets(tmp_path) -> None:
    client, secret = make_client(tmp_path)
    cases = [
        ("search_governed_assets", {"query": "payments", "purpose": "catalog analysis"}),
        ("get_quality_evidence", {"asset_id": "asset-1", "purpose": "quality review"}),
        ("analyze_lineage_impact", {"asset_id": "asset-1", "purpose": "impact analysis", "depth": 2}),
    ]
    with client:
        for tool_name, arguments in cases:
            response = client.post("/mcp", json=call(tool_name, arguments), headers=headers(secret))
            assert response.status_code == 200
            body = response.json()["result"]["structuredContent"]
            assert body["provenance"] and body["evidence"] and body["timestamp"]
            assert body["confidence"] >= 0
            assert "data" in body


def test_tool_call_denial_is_safe_jsonrpc_error_without_context_payload(tmp_path) -> None:
    client, secret = make_client(tmp_path, outcome="deny")
    with client:
        response = client.post("/mcp", json=call("get_asset_context", {"asset_id": "asset-1", "purpose": "financial reporting analysis"}), headers=headers(secret))

    assert response.status_code == 403
    body = response.json()
    assert body["error"]["data"]["code"] == "mcp_forbidden"
    assert "asset" not in str(body)


def test_policy_resource_and_all_prompts_are_structured_and_non_mutating(tmp_path) -> None:
    client, secret = make_client(tmp_path)
    with client:
        resource = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 10, "method": "resources/read", "params": {"uri": "datagenie://policy/assets/asset-1?purpose=financial%20reporting"}},
            headers=headers(secret),
        )
        assert resource.status_code == 200
        structured = resource.json()["result"]["structuredContent"]
        assert structured["policy"]["outcome"] == "allow_with_obligations"
        assert structured["evidence"] and structured["timestamp"]

        for prompt in ["assess_data_for_use", "explain_lineage_impact", "summarize_governed_asset"]:
            response = client.post(
                "/mcp",
                json={"jsonrpc": "2.0", "id": 11, "method": "prompts/get", "params": {"name": prompt, "arguments": {"asset_id": "asset-1"}}},
                headers=headers(secret),
            )
            assert response.status_code == 200
            prompt_packet = response.json()["result"]["structuredContent"]
            assert prompt_packet["prompt"] == prompt
            assert prompt_packet["may_mutate"] is False
            assert prompt_packet["requires_evidence_bearing_result"] is True


def test_global_kill_switch_disables_mcp_before_auth_or_dispatch(tmp_path) -> None:
    secret = "mcp-test-secret-that-is-longer-than-thirty-two-characters"
    settings = Settings(
        auth_jwt_secret=secret,
        downstream_service_shared_secret="gateway-service-secret",
        mcp_internal_beta_enabled=True,
        mcp_kill_switch_enabled=True,
        mcp_allowed_tenants="internal-beta",
        mcp_allowed_hosts="approved-host",
        ledger_database_url=f"sqlite:///{tmp_path / 'ledger.db'}",
    )
    runtime = McpApplication(settings=settings, client=FakeClient(), ledger=ExecutionLedger(settings.ledger_database_url))
    with TestClient(create_app(runtime)) as client:
        response = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}, headers=headers(secret))

    assert response.status_code == 503
    assert response.json()["error"]["data"]["code"] == "tool_disabled"

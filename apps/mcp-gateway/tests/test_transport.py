from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient


def build_client(monkeypatch, tmp_path):
    secret = "mcp-test-secret-that-is-longer-than-thirty-two-characters"
    monkeypatch.setenv("DATAGENIE_AUTH_ENABLED", "true")
    monkeypatch.setenv("DATAGENIE_AUTH_MODE", "hs256")
    monkeypatch.setenv("DATAGENIE_AUTH_JWT_SECRET", secret)
    monkeypatch.setenv("DATAGENIE_MCP_INTERNAL_BETA_ENABLED", "true")
    monkeypatch.setenv("DATAGENIE_MCP_ALLOWED_TENANTS", "internal-beta")
    monkeypatch.setenv("DATAGENIE_MCP_ALLOWED_HOSTS", "approved-host")
    monkeypatch.setenv("DATAGENIE_MCP_ALLOWED_ORIGINS", "https://host.internal")
    monkeypatch.setenv("DATAGENIE_DOWNSTREAM_SERVICE_SHARED_SECRET", "gateway-service-secret")
    monkeypatch.setenv("DATAGENIE_LEDGER_DATABASE_URL", f"sqlite:///{tmp_path / 'ledger.db'}")

    from app.core.config import get_settings
    from app.server import create_app

    get_settings.cache_clear()
    return TestClient(create_app()), secret


def headers(secret: str, *, version: str = "2026-07-28", host: str = "approved-host") -> dict[str, str]:
    token = jwt.encode(
        {
            "sub": "analyst@example.com",
            "tenant_id": "internal-beta",
            "roles": ["analyst"],
            "scope": "catalog:read quality:read lineage:read",
            "aud": "datagenie-mcp",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        secret,
        algorithm="HS256",
    )
    return {
        "Authorization": f"Bearer {token}",
        "Mcp-Client-Id": host,
        "MCP-Protocol-Version": version,
        "Content-Type": "application/json",
    }


def rpc(method: str, params: dict | None = None, request_id: int = 1) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}


def test_metadata_capability_negotiation_and_proposal_only_tool_surface(monkeypatch, tmp_path) -> None:
    client, secret = build_client(monkeypatch, tmp_path)
    with client:
        metadata = client.get("/.well-known/oauth-protected-resource/mcp")
        assert metadata.status_code == 200
        assert metadata.json()["resource"].endswith("/mcp")
        assert metadata.json()["authorization_servers"]

        initialized = client.post("/mcp", json=rpc("initialize"), headers=headers(secret))
        assert initialized.status_code == 200
        assert initialized.json()["result"]["protocolVersion"] == "2026-07-28"
        instructions = initialized.json()["result"]["instructions"]
        assert "proposal-intent creation" in instructions
        assert "never approve, execute, or directly mutate" in instructions

        tools = client.post("/mcp", json=rpc("tools/list", request_id=2), headers=headers(secret))
        advertised = {tool["name"] for tool in tools.json()["result"]["tools"]}
        assert advertised == {
            "search_governed_assets",
            "get_asset_context",
            "get_quality_evidence",
            "analyze_lineage_impact",
            "create_governance_proposal",
            "request_certification_review",
            "schedule_quality_check",
        }
        assert not {"approve_governance_proposal", "execute_governance_proposal", "update_asset", "certify_asset", "run_quality_check", "check_data_use_policy"}.intersection(advertised)

        resources = client.post("/mcp", json=rpc("resources/list", request_id=3), headers=headers(secret))
        assert len(resources.json()["result"]["resources"]) == 5
        prompts = client.post("/mcp", json=rpc("prompts/list", request_id=4), headers=headers(secret))
        assert len(prompts.json()["result"]["prompts"]) == 3


def test_rejects_unapproved_host_origin_and_protocol(monkeypatch, tmp_path) -> None:
    client, secret = build_client(monkeypatch, tmp_path)
    with client:
        host_rejected = client.post("/mcp", json=rpc("initialize"), headers=headers(secret, host="unknown-host"))
        assert host_rejected.status_code == 401
        assert "governance:propose" in host_rejected.headers["WWW-Authenticate"]

        origin_rejected = client.post("/mcp", json=rpc("initialize"), headers={**headers(secret), "Origin": "https://evil.example"})
        assert origin_rejected.status_code == 403
        assert origin_rejected.json()["error"]["data"]["code"] == "mcp_origin_forbidden"

        protocol_rejected = client.post("/mcp", json=rpc("initialize"), headers=headers(secret, version="1999-01-01"))
        assert protocol_rejected.status_code == 400
        assert protocol_rejected.json()["error"]["data"]["code"] == "mcp_protocol_unsupported"


def test_adversarial_identity_and_input_attempts_do_not_leak_results(monkeypatch, tmp_path) -> None:
    client, secret = build_client(monkeypatch, tmp_path)
    foreign_token = jwt.encode(
        {
            "sub": "analyst@example.com",
            "tenant_id": "tenant-b",
            "roles": ["analyst"],
            "scope": "catalog:read quality:read lineage:read",
            "aud": "datagenie-mcp",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        secret,
        algorithm="HS256",
    )
    wrong_audience = jwt.encode(
        {
            "sub": "analyst@example.com",
            "tenant_id": "internal-beta",
            "roles": ["analyst"],
            "scope": "catalog:read",
            "aud": "some-other-resource",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        secret,
        algorithm="HS256",
    )
    with client:
        foreign = client.post("/mcp", json=rpc("initialize"), headers={**headers(secret), "Authorization": f"Bearer {foreign_token}"})
        assert foreign.status_code == 401
        assert "tenant-b" not in str(foreign.json())

        audience = client.post("/mcp", json=rpc("initialize"), headers={**headers(secret), "Authorization": f"Bearer {wrong_audience}"})
        assert audience.status_code == 401

        injected_tenant = client.post(
            "/mcp",
            json=rpc("tools/call", {"name": "get_asset_context", "arguments": {"asset_id": "asset-a", "purpose": "catalog analysis", "tenant_id": "tenant-b"}}),
            headers=headers(secret),
        )
        assert injected_tenant.status_code == 422
        assert injected_tenant.json()["error"]["data"]["code"] == "mcp_invalid_arguments"
        assert "asset-a" not in str(injected_tenant.json())

        mutation = client.post("/mcp", json=rpc("tools/call", {"name": "certify_asset", "arguments": {"asset_id": "asset-a"}}), headers=headers(secret))
        assert mutation.status_code == 404
        assert mutation.json()["error"]["data"]["code"] == "mcp_method_not_found"

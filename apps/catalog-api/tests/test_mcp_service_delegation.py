import base64
import hashlib
import hmac
import importlib
import json
import sys
import time

from fastapi.testclient import TestClient


def build_client(monkeypatch, tmp_path) -> tuple[TestClient, str]:
    secret = "catalog-mcp-service-secret-that-is-longer-than-thirty-two-characters"
    monkeypatch.setenv("DATAGENIE_ENVIRONMENT", "development")
    monkeypatch.setenv("DATAGENIE_DATABASE_URL", f"sqlite:///{tmp_path / 'mcp-delegation.db'}")
    monkeypatch.setenv("DATAGENIE_AUTH_ENABLED", "true")
    monkeypatch.setenv("DATAGENIE_AUTH_JWT_SECRET", "catalog-auth-secret-that-is-longer-than-thirty-two-characters")
    monkeypatch.setenv("DATAGENIE_MCP_GATEWAY_SERVICE_IDENTITY_ENABLED", "true")
    monkeypatch.setenv("DATAGENIE_MCP_GATEWAY_SERVICE_ID", "mcp-gateway")
    monkeypatch.setenv("DATAGENIE_MCP_GATEWAY_SERVICE_SHARED_SECRET", secret)

    from app.core.config import get_settings

    get_settings.cache_clear()
    for module_name in ["app.db.session", "app.core.security", "app.api.v1.policy", "app.api.v1.mcp_internal", "app.main"]:
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])
    import app.main as main_module

    return TestClient(main_module.app), secret


def signed_headers(secret: str, method: str, path: str, *, tenant: str = "tenant-a") -> dict[str, str]:
    actor = {"subject": "analyst@example.com", "tenant_id": tenant, "roles": ["analyst"], "scopes": ["catalog:read"], "host_id": "approved-host", "request_id": "delegated-request-1"}
    actor_b64 = base64.urlsafe_b64encode(json.dumps(actor, separators=(",", ":"), sort_keys=True).encode()).decode().rstrip("=")
    timestamp = str(int(time.time()))
    signature = hmac.new(secret.encode(), f"{timestamp}\n{method}\n{path}\n{actor_b64}".encode(), hashlib.sha256).hexdigest()
    return {
        "X-DataGenie-Service-Id": "mcp-gateway",
        "X-DataGenie-Service-Timestamp": timestamp,
        "X-DataGenie-Service-Actor": actor_b64,
        "X-DataGenie-Service-Signature": signature,
    }


def test_private_mcp_policy_delegation_requires_valid_signed_actor(monkeypatch, tmp_path) -> None:
    client, secret = build_client(monkeypatch, tmp_path)
    path = "/api/v1/policy/internal/mcp/decisions"
    payload = {"action": "asset.read", "resource": {"resource_type": "asset", "resource_id": "unknown-asset"}, "purpose": "catalog analysis", "context": {}}
    with client:
        invalid = client.post(path, json=payload, headers={**signed_headers(secret, "POST", path), "X-DataGenie-Service-Signature": "invalid"})
        assert invalid.status_code == 401
        assert invalid.json()["error"]["code"] == "unauthorized"

        valid = client.post(path, json=payload, headers=signed_headers(secret, "POST", path))
        assert valid.status_code == 200
        assert valid.json()["outcome"] == "deny"
        assert valid.json()["resource_visible"] is False

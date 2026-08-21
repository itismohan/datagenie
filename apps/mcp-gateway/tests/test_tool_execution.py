from datetime import datetime, timedelta, timezone

import pytest

from app.core.config import Settings
from app.schemas import PolicyEvidence, PolicyPacket, Principal
from app.services.execution_ledger import AgentExecution, ExecutionLedger
from app.services.tool_execution import McpToolError, ToolExecutor


class FakeClient:
    def __init__(self, outcome: str = "allow_with_obligations") -> None:
        self.outcome = outcome
        self.asset_context_called = False

    async def evaluate_policy(self, _principal, _request_id, _asset_id, _purpose):
        return PolicyPacket(
            outcome=self.outcome,
            rule_ids=["DG-POLICY-RBAC-ALLOW"],
            evidence=[PolicyEvidence(type="asset", reference="asset:asset-1")],
            obligations=["handle_sensitive_data"] if self.outcome == "allow_with_obligations" else [],
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            decision_version="1.0.0",
        )

    async def asset_context(self, _principal, _request_id, _asset_id, _purpose):
        self.asset_context_called = True
        return {
            "asset": {
                "id": "asset-1",
                "name": "payments",
                "technical_metadata": {"internal": "not for MCP"},
                "columns": [{"name": "email", "data_type": "text"}],
                "quality_score": 90,
                "quality_explainable_at": "2026-08-22T00:00:00Z",
            }
        }


def settings() -> Settings:
    return Settings(
        auth_jwt_secret="mcp-test-secret-that-is-longer-than-thirty-two-characters",
        downstream_service_shared_secret="gateway-service-secret",
        mcp_allowed_tenants="internal-beta",
        mcp_allowed_hosts="approved-host",
    )


def principal() -> Principal:
    return Principal(
        subject="analyst@example.com",
        tenant_id="internal-beta",
        roles=frozenset({"analyst"}),
        scopes=frozenset({"catalog:read", "quality:read", "lineage:read"}),
        host_id="approved-host",
    )


@pytest.mark.asyncio
async def test_asset_context_is_structured_policy_bound_redacted_and_ledgered(tmp_path) -> None:
    ledger = ExecutionLedger(f"sqlite:///{tmp_path / 'ledger.db'}")
    ledger.create_schema()
    client = FakeClient()
    executor = ToolExecutor(client=client, ledger=ledger, settings=settings())

    result = await executor.execute(
        principal(),
        "mcp-request-1",
        "get_asset_context",
        {"asset_id": "asset-1", "purpose": "financial reporting analysis", "include": ["columns"]},
    )

    assert result.policy is not None
    assert result.policy.outcome == "allow_with_obligations"
    assert result.obligations == ["handle_sensitive_data"]
    assert result.provenance and result.evidence and result.timestamp
    assert result.confidence > 0
    assert "technical_metadata" not in result.data["asset"]
    assert "technical_metadata:bounded" in result.redactions
    assert client.asset_context_called is True
    with ledger.sessions() as session:
        entry = session.query(AgentExecution).one()
        assert entry.tenant_id == "internal-beta"
        assert entry.outcome == "allowed"
        assert "financial reporting analysis" not in entry.input_digest


@pytest.mark.asyncio
async def test_denied_policy_fails_closed_before_asset_retrieval_and_records_ledger(tmp_path) -> None:
    ledger = ExecutionLedger(f"sqlite:///{tmp_path / 'ledger.db'}")
    ledger.create_schema()
    client = FakeClient(outcome="deny")
    executor = ToolExecutor(client=client, ledger=ledger, settings=settings())

    with pytest.raises(McpToolError) as exc:
        await executor.execute(
            principal(),
            "mcp-request-2",
            "get_asset_context",
            {"asset_id": "asset-1", "purpose": "financial reporting analysis"},
        )

    assert exc.value.code == "mcp_forbidden"
    assert client.asset_context_called is False
    with ledger.sessions() as session:
        entry = session.query(AgentExecution).one()
        assert entry.outcome == "denied"
        assert entry.policy_outcome == "deny"

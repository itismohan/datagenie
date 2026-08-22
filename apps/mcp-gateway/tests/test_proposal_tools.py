import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from app.core.config import Settings
from app.schemas import Principal
from app.services.execution_ledger import ExecutionLedger
from app.services.tool_execution import McpToolError, TOOL_SCOPES, ToolExecutor


class ProposalOnlyClient:
    def __init__(self) -> None:
        self.payloads: list[dict] = []

    async def create_governance_proposal(self, principal, _request_id, payload):
        self.payloads.append(payload)
        now = datetime.now(timezone.utc)
        return {
            "id": f"proposal-{len(self.payloads)}",
            "proposal_hash": "b" * 64,
            "status": "pending_review",
            "expires_at": (now + timedelta(hours=1)).isoformat(),
            "inbox_uri": "/api/v1/governance/inbox?proposal_id=proposal-1",
            "proposal_type": payload["proposal_type"],
            "impact": payload["impact"],
            "initiating_subject": principal.subject,
            "initiating_agent_id": payload["source"].get("agent_id"),
            "initiating_model_id": payload["source"].get("model_id"),
            "initiating_host_id": principal.host_id,
            "source_evidence": payload["evidence"],
            "policy_snapshot": {
                "outcome": "allow",
                "rule_ids": ["DG-POLICY-RBAC-ALLOW"],
                "evidence": [{"type": "asset", "reference": "asset:asset-1"}],
                "obligations": [],
                "expires_at": (now + timedelta(minutes=5)).isoformat(),
                "decision_version": "1.0.0",
            },
        }


def _executor(tmp_path) -> tuple[ToolExecutor, ProposalOnlyClient]:
    client = ProposalOnlyClient()
    settings = Settings(
        auth_jwt_secret="mcp-test-secret-that-is-longer-than-thirty-two-characters",
        downstream_service_shared_secret="gateway-service-secret",
        mcp_internal_beta_enabled=True,
        mcp_allowed_tenants="internal-beta",
        mcp_allowed_hosts="approved-host",
        ledger_database_url=f"sqlite:///{tmp_path / 'proposal-ledger.db'}",
    )
    ledger = ExecutionLedger(settings.ledger_database_url)
    ledger.create_schema()
    return ToolExecutor(client=client, ledger=ledger, settings=settings), client


def _principal() -> Principal:
    return Principal(
        subject="agent-user@example.com",
        tenant_id="internal-beta",
        roles=frozenset({"analyst"}),
        scopes=frozenset({"governance:propose"}),
        host_id="approved-host",
    )


def test_mcp_exposes_only_proposal_tools_and_never_executes_them(tmp_path) -> None:
    executor, client = _executor(tmp_path)
    cases = [
        (
            "create_governance_proposal",
            {
                "proposal_type": "asset_curation",
                "asset_id": "asset-1",
                "title": "Curate payments description",
                "proposal_text": "Create a steward-reviewable metadata change.",
                "purpose": "metadata stewardship",
                "diff": {"description": "Payments facts"},
                "technical_version": 3,
                "agent_id": "agent-1",
                "model_id": "approved-model",
            },
        ),
        (
            "request_certification_review",
            {
                "asset_id": "asset-1",
                "purpose": "certification stewardship",
                "technical_version": 3,
                "agent_id": "agent-1",
            },
        ),
        (
            "schedule_quality_check",
            {
                "asset_id": "asset-1",
                "purpose": "quality stewardship",
                "frequency": "daily",
                "rule_types": ["completeness"],
                "technical_version": 3,
                "model_id": "approved-model",
            },
        ),
    ]

    for request_number, (tool_name, arguments) in enumerate(cases, start=1):
        result = asyncio.run(executor.execute(_principal(), f"request-{request_number}", tool_name, arguments))
        assert result.data["status"] == "pending_review"
        assert result.data["proposal_hash"] == "b" * 64
        assert result.data["inbox_uri"].startswith("/api/v1/governance/inbox")
        assert "confirmation_nonce" not in result.data
        assert result.redactions == ["confirmation_nonce:never_returned", "direct_mutation:never_performed"]

    assert len(client.payloads) == 3
    assert {payload["source"]["channel"] for payload in client.payloads} == {"mcp"}
    assert {payload["version_preconditions"]["technical_version"] for payload in client.payloads} == {3}
    assert {"create_governance_proposal", "request_certification_review", "schedule_quality_check"}.issubset(TOOL_SCOPES)
    assert not {"approve_proposal", "execute_proposal", "certify_asset", "update_asset", "run_quality_check"}.intersection(TOOL_SCOPES)


@pytest.mark.parametrize("tool_name", ["approve_proposal", "execute_proposal", "certify_asset", "update_asset", "run_quality_check"])
def test_mcp_rejects_direct_governance_mutation_tool_names(tmp_path, tool_name: str) -> None:
    executor, client = _executor(tmp_path)

    with pytest.raises(McpToolError) as exc_info:
        asyncio.run(executor.execute(_principal(), "request-2", tool_name, {"asset_id": "asset-1"}))

    assert exc_info.value.code == "mcp_method_not_found"
    assert client.payloads == []

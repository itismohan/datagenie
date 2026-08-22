from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PYTHON_HELPER = ROOT / "clients" / "python"
sys.path.insert(0, str(PYTHON_HELPER))

from datagenie_mcp import DataGenieMcpClient, UnsupportedToolError


def test_published_productization_docs_cover_required_admin_controls() -> None:
    onboarding = (ROOT / "docs" / "mcp-tenant-admin-onboarding.md").read_text(encoding="utf-8")
    lifecycle = (ROOT / "docs" / "mcp-versioning-and-deprecation-policy.md").read_text(encoding="utf-8")
    certification = (ROOT / "docs" / "mcp-partner-certification.md").read_text(encoding="utf-8")
    for phrase in ("OAuth application registration", "Scope matrix", "Test-tenant walkthrough", "Data-handling expectations", "Support investigation", "X-Request-ID"):
        assert phrase in onboarding
    for phrase in ("Additive compatible", "Deprecation lifecycle", "Breaking", "90 days", "retirement date"):
        assert phrase in lifecycle
    for phrase in ("generic-streamable-http", "enterprise-governed-host", "synthetic_preflight", "request ID"):
        assert phrase in certification


def test_python_helper_uses_standard_jsonrpc_and_rejects_unapproved_tools() -> None:
    calls: list[tuple[str, dict[str, str], dict]] = []

    def recording_transport(endpoint: str, headers: dict[str, str], payload: dict) -> dict:
        calls.append((endpoint, headers, payload))
        return {"jsonrpc": "2.0", "id": payload["id"], "result": {"structuredContent": {"tenant_bound": True}}}

    client = DataGenieMcpClient(
        endpoint="https://mcp.example.test/mcp",
        bearer_token="caller-owned-token",
        host_id="approved-host",
        transport=recording_transport,
    )
    response = client.call_tool("get_asset_context", {"asset_id": "asset-1", "purpose": "financial reporting analysis"}, "host-request-1")
    assert response["result"]["structuredContent"]["tenant_bound"] is True
    assert calls == [
        (
            "https://mcp.example.test/mcp",
            {
                "Authorization": "Bearer caller-owned-token",
                "Mcp-Client-Id": "approved-host",
                "MCP-Protocol-Version": "2026-07-28",
                "X-Request-ID": "host-request-1",
                "User-Agent": "datagenie-mcp-python-helper/0.1.0",
            },
            {
                "jsonrpc": "2.0",
                "id": "host-request-1",
                "method": "tools/call",
                "params": {"name": "get_asset_context", "arguments": {"asset_id": "asset-1", "purpose": "financial reporting analysis"}},
            },
        )
    ]
    with pytest.raises(UnsupportedToolError):
        client.call_tool("execute_proposal", {"asset_id": "asset-1"}, "host-request-2")
    assert len(calls) == 1


def test_typescript_helper_declares_the_same_constrained_surface() -> None:
    source = (ROOT / "clients" / "typescript" / "src" / "index.ts").read_text(encoding="utf-8")
    for allowed in ("search_governed_assets", "get_asset_context", "get_quality_evidence", "analyze_lineage_impact", "create_governance_proposal", "request_certification_review", "schedule_quality_check"):
        assert allowed in source
    for prohibited in ("approve_proposal", "execute_proposal", "certify_asset", "run_quality_check"):
        assert prohibited not in source
    assert 'method: "POST"' in source
    assert '"MCP-Protocol-Version"' in source
    assert '"X-Request-ID"' in source


def test_partner_certification_harness_emits_sanitized_two_profile_evidence() -> None:
    result = subprocess.run([sys.executable, str(ROOT / "tools" / "run_mcp_partner_certification.py")], cwd=ROOT, check=True, capture_output=True, text=True)
    assert "mcp-partner-certification-synthetic.json" in result.stdout
    artifact = json.loads((ROOT / "docs" / "evidence" / "mcp-partner-certification-synthetic.json").read_text(encoding="utf-8"))
    assert artifact["certification_level"] == "synthetic_preflight"
    assert artifact["pass"] is True
    assert artifact["assertions"]["two_distinct_host_profiles"] is True
    assert artifact["assertions"]["proposal_tools_return_pending_intent_only"] is True
    assert artifact["assertions"]["request_to_ledger_correlation"] is True
    serialized = json.dumps(artifact).lower()
    for prohibited in ("bearer partner", "client_secret", "\"password\"", "partner-certification-secret", "synthetic-certification-downstream-secret"):
        assert prohibited not in serialized


def test_domain_pack_governance_requires_approved_feedback_and_sdd() -> None:
    policy = (ROOT / "docs" / "mcp-domain-pack-governance.md").read_text(encoding="utf-8")
    for phrase in ("approved its use", "Security review", "SDD change", "must not introduce arbitrary SQL", "proposal with immutable diff/evidence"):
        assert phrase in policy
    assert "Feedback does not alter policy rules" in policy

#!/usr/bin/env python3
"""Run sanitized synthetic preflight checks for DataGenie MCP host interoperability.

This validates representative host profiles against an in-process gateway only. It
never certifies an external host, connects to a customer tenant, or emits tokens,
source credentials, prompts, or raw governed result data.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GATEWAY = ROOT / "apps" / "mcp-gateway"
sys.path.insert(0, str(GATEWAY))

import jwt
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.schemas import PolicyEvidence, PolicyPacket
from app.server import McpApplication, create_app
from app.services.execution_ledger import AgentExecution, ExecutionLedger

CERTIFICATION_LEVEL = "synthetic_preflight"
TEST_TENANT = "internal-certification"
SECRET = "partner-certification-secret-that-is-longer-than-thirty-two-characters"
EXPECTED_TOOLS = {
    "search_governed_assets",
    "get_asset_context",
    "get_quality_evidence",
    "analyze_lineage_impact",
    "create_governance_proposal",
    "request_certification_review",
    "schedule_quality_check",
}
HOST_PROFILES = {
    "generic-streamable-http": {"host_id": "certification-generic-host", "scope": "catalog:read quality:read lineage:read"},
    "enterprise-governed-host": {"host_id": "certification-enterprise-host", "scope": "catalog:read quality:read lineage:read governance:propose"},
}


class SyntheticDownstream:
    async def close(self) -> None:
        return None

    async def evaluate_policy(self, _principal, _request_id, _asset_id, _purpose):
        return PolicyPacket(
            outcome="allow_with_obligations",
            rule_ids=["DG-POLICY-RBAC-ALLOW"],
            evidence=[PolicyEvidence(type="asset", reference="asset:certification-synthetic")],
            obligations=["cite_governance_evidence"],
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            decision_version="1.0.0",
        )

    async def search_assets(self, _principal, _request_id, _params):
        return {"items": [{"asset": {"id": "certification-asset", "name": "synthetic_asset"}, "policy": {"outcome": "allow"}}], "total": 1, "visible_total": 1, "facets": {}, "index_fresh_at": "synthetic"}

    async def asset_context(self, _principal, _request_id, _asset_id, _purpose):
        return {"asset": {"id": "certification-asset", "name": "synthetic_asset", "technical_metadata": {"internal": True}, "columns": []}}

    async def quality_evidence(self, _principal, _request_id, asset_id, _purpose, _history_limit):
        return {"asset_id": asset_id, "state": "current", "technical_score": 100, "explainable_at": "synthetic", "runs": [], "incidents": [], "evidence": [{"type": "quality_run", "reference": f"quality:{asset_id}"}], "source": "synthetic"}

    async def lineage_impact(self, _principal, _request_id, asset_id, direction, depth, _purpose):
        return {"focal_asset_id": asset_id, "direction": direction, "depth": depth, "nodes": [{"id": asset_id}], "edges": []}

    async def create_governance_proposal(self, principal, _request_id, payload):
        now = datetime.now(timezone.utc)
        return {
            "id": "synthetic-proposal",
            "proposal_hash": "c" * 64,
            "status": "pending_review",
            "expires_at": (now + timedelta(hours=1)).isoformat(),
            "inbox_uri": "/api/v1/governance/inbox?proposal_id=synthetic-proposal",
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
                "evidence": [{"type": "asset", "reference": "asset:certification-synthetic"}],
                "obligations": [],
                "expires_at": (now + timedelta(minutes=5)).isoformat(),
                "decision_version": "1.0.0",
            },
        }


def token(scope: str) -> str:
    return jwt.encode(
        {
            "sub": "certification-agent@internal",
            "tenant_id": TEST_TENANT,
            "roles": ["analyst"],
            "scope": scope,
            "aud": "datagenie-mcp",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        SECRET,
        algorithm="HS256",
    )


def headers(profile: dict[str, str], request_id: str, *, scope: str | None = None) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token(scope or profile['scope'])}",
        "Mcp-Client-Id": profile["host_id"],
        "MCP-Protocol-Version": "2026-07-28",
        "X-Request-ID": request_id,
        "Content-Type": "application/json",
    }


def rpc(method: str, params: dict[str, Any] | None = None, request_id: str = "certification-rpc") -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}


def run_profile(client: TestClient, profile_name: str, profile: dict[str, str]) -> dict[str, Any]:
    request_prefix = f"cert-{profile_name}"
    metadata = client.get("/.well-known/oauth-protected-resource/mcp")
    initialized = client.post("/mcp", json=rpc("initialize", request_id=f"{request_prefix}-initialize"), headers=headers(profile, f"{request_prefix}-initialize"))
    listed = client.post("/mcp", json=rpc("tools/list", request_id=f"{request_prefix}-tools"), headers=headers(profile, f"{request_prefix}-tools"))
    context_request_id = f"{request_prefix}-context"
    context = client.post(
        "/mcp",
        json=rpc("tools/call", {"name": "get_asset_context", "arguments": {"asset_id": "certification-asset", "purpose": "synthetic certification"}}, context_request_id),
        headers=headers(profile, context_request_id),
    )
    malformed = client.post(
        "/mcp",
        json=rpc("tools/call", {"name": "get_asset_context", "arguments": {"asset_id": "certification-asset", "purpose": "synthetic certification", "tenant_id": "foreign"}}, f"{request_prefix}-schema"),
        headers=headers(profile, f"{request_prefix}-schema"),
    )
    direct_mutation = client.post(
        "/mcp",
        json=rpc("tools/call", {"name": "execute_proposal", "arguments": {"proposal_id": "synthetic-proposal"}}, f"{request_prefix}-direct"),
        headers=headers(profile, f"{request_prefix}-direct"),
    )
    without_proposal_scope = client.post(
        "/mcp",
        json=rpc("tools/call", {"name": "request_certification_review", "arguments": {"asset_id": "certification-asset", "purpose": "synthetic review", "technical_version": 1}}, f"{request_prefix}-scope"),
        headers=headers(profile, f"{request_prefix}-scope", scope="catalog:read"),
    )
    proposal_status: int | None = None
    proposal_is_pending: bool | None = None
    if "governance:propose" in profile["scope"]:
        proposal = client.post(
            "/mcp",
            json=rpc("tools/call", {"name": "schedule_quality_check", "arguments": {"asset_id": "certification-asset", "purpose": "synthetic quality stewardship", "frequency": "daily", "rule_types": ["completeness"], "technical_version": 1}}, f"{request_prefix}-proposal"),
            headers=headers(profile, f"{request_prefix}-proposal"),
        )
        proposal_status = proposal.status_code
        proposal_is_pending = proposal.json().get("result", {}).get("structuredContent", {}).get("data", {}).get("status") == "pending_review"
    structured = context.json().get("result", {}).get("structuredContent", {})
    return {
        "profile": profile_name,
        "metadata_status": metadata.status_code,
        "initialize_status": initialized.status_code,
        "tools_match": {tool.get("name") for tool in listed.json().get("result", {}).get("tools", [])} == EXPECTED_TOOLS,
        "context_status": context.status_code,
        "context_request_id_propagated": context.headers.get("X-Request-ID") == context_request_id,
        "structured_result_complete": all(key in structured for key in ("policy", "provenance", "evidence", "timestamp", "confidence", "redactions")),
        "schema_status": malformed.status_code,
        "schema_safe": malformed.json().get("error", {}).get("data", {}).get("code") == "mcp_invalid_arguments" and "certification-asset" not in str(malformed.json()),
        "direct_mutation_status": direct_mutation.status_code,
        "direct_mutation_rejected": direct_mutation.json().get("error", {}).get("data", {}).get("code") == "mcp_method_not_found",
        "missing_scope_status": without_proposal_scope.status_code,
        "missing_scope_rejected": without_proposal_scope.status_code == 403 and not without_proposal_scope.json().get("result") and "certification-asset" not in str(without_proposal_scope.json()),
        "proposal_status": proposal_status,
        "proposal_is_pending": proposal_is_pending,
        "request_id": context_request_id,
    }


def main() -> int:
    evidence_dir = ROOT / "docs" / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = evidence_dir / "mcp-partner-certification-ledger.db"
    if ledger_path.exists():
        ledger_path.unlink()
    settings = Settings(
        auth_jwt_secret=SECRET,
        downstream_service_shared_secret="synthetic-certification-downstream-secret",
        mcp_internal_beta_enabled=True,
        mcp_allowed_tenants=TEST_TENANT,
        mcp_allowed_hosts=",".join(profile["host_id"] for profile in HOST_PROFILES.values()),
        mcp_allowed_origins="https://certification.internal",
        ledger_database_url=f"sqlite:///{ledger_path}",
    )
    ledger = ExecutionLedger(settings.ledger_database_url)
    app = create_app(McpApplication(settings=settings, client=SyntheticDownstream(), ledger=ledger))
    with TestClient(app) as client:
        profiles = [run_profile(client, name, profile) for name, profile in HOST_PROFILES.items()]
    with ledger.sessions() as session:
        entries = list(session.query(AgentExecution).order_by(AgentExecution.created_at).all())
    profile_request_ids = {profile["request_id"] for profile in profiles}
    ledger_by_request = {entry.request_id: entry for entry in entries}
    ledger_correlation = all(
        request_id in ledger_by_request
        and ledger_by_request[request_id].tenant_id == TEST_TENANT
        and ledger_by_request[request_id].host_id == HOST_PROFILES[profile["profile"]]["host_id"]
        for profile in profiles
        for request_id in [profile["request_id"]]
    )
    required_checks = [
        profile["metadata_status"] == 200
        and profile["initialize_status"] == 200
        and profile["tools_match"]
        and profile["context_status"] == 200
        and profile["context_request_id_propagated"]
        and profile["structured_result_complete"]
        and profile["schema_status"] == 422
        and profile["schema_safe"]
        and profile["direct_mutation_status"] == 404
        and profile["direct_mutation_rejected"]
        and profile["missing_scope_status"] == 403
        and profile["missing_scope_rejected"]
        for profile in profiles
    ]
    enterprise_profile = next(profile for profile in profiles if profile["profile"] == "enterprise-governed-host")
    artifact = {
        "certification_level": CERTIFICATION_LEVEL,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "local synthetic preflight only; no live OIDC, customer tenant, customer host, source credential, raw prompt, or governed result data",
        "profiles": profiles,
        "assertions": {
            "all_required_checks_passed": all(required_checks) and enterprise_profile["proposal_status"] == 200 and enterprise_profile["proposal_is_pending"] is True,
            "two_distinct_host_profiles": len({profile["profile"] for profile in profiles}) == 2,
            "proposal_tools_return_pending_intent_only": enterprise_profile["proposal_is_pending"] is True,
            "request_to_ledger_correlation": ledger_correlation,
            "ledger_entries_tenant_bound": all(entry.tenant_id == TEST_TENANT for entry in entries),
        },
        "correlation": {"request_ids": sorted(profile_request_ids), "ledger_entry_count": len(entries), "ledger_entry_found": ledger_correlation},
        "limitations": ["Synthetic profile validation only", "No live OIDC validation", "No external customer-host certification", "No customer data or production tenant"],
    }
    artifact["pass"] = all(artifact["assertions"].values())
    output = evidence_dir / "mcp-partner-certification-synthetic.json"
    output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(output)
    print(json.dumps(artifact, indent=2, sort_keys=True))
    return 0 if artifact["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

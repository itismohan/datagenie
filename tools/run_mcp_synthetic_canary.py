#!/usr/bin/env python3
"""Run a local synthetic MCP canary and write non-sensitive evidence artifacts.

This harness intentionally uses an in-process deterministic downstream adapter.
It proves gateway controls and telemetry wiring only; it is not a substitute for
an approved staging tenant, live OIDC, signed downstream services, or SLO data.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATEWAY = ROOT / "apps" / "mcp-gateway"
sys.path.insert(0, str(GATEWAY))

import jwt
from fastapi.testclient import TestClient
from prometheus_client import generate_latest

from app.core.config import Settings
from app.schemas import PolicyEvidence, PolicyPacket
from app.server import McpApplication, create_app
from app.services.execution_ledger import AgentExecution, ExecutionLedger


class SyntheticDownstream:
    async def close(self) -> None:
        return None

    async def evaluate_policy(self, _principal, _request_id, _asset_id, _purpose):
        return PolicyPacket(
            outcome="allow_with_obligations",
            rule_ids=["DG-POLICY-RBAC-ALLOW"],
            evidence=[PolicyEvidence(type="asset", reference="asset:synthetic-asset")],
            obligations=["handle_sensitive_data"],
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            decision_version="1.0.0",
        )

    async def search_assets(self, _principal, _request_id, _params):
        return {
            "items": [{"asset": {"id": "synthetic-asset", "name": "synthetic_payments"}, "policy": {"outcome": "allow"}}],
            "total": 1,
            "visible_total": 1,
            "facets": {},
            "index_fresh_at": datetime.now(timezone.utc).isoformat(),
        }

    async def asset_context(self, _principal, _request_id, _asset_id, _purpose):
        return {
            "asset": {
                "id": "synthetic-asset",
                "name": "synthetic_payments",
                "technical_metadata": {"must_not_escape": True},
                "columns": [],
            }
        }

    async def quality_evidence(self, _principal, _request_id, asset_id, _purpose, _history_limit):
        return {
            "asset_id": asset_id,
            "state": "current",
            "latest_technical_score": 95,
            "latest_explainable_at": datetime.now(timezone.utc).isoformat(),
            "runs": [],
            "incidents": [],
            "evidence": [{"type": "quality_run", "reference": f"quality:asset:{asset_id}"}],
        }

    async def lineage_impact(self, _principal, _request_id, asset_id, direction, depth, _purpose):
        return {"focal_asset_id": asset_id, "direction": direction, "depth": depth, "nodes": [{"id": asset_id}], "edges": []}


def token(secret: str, tenant_id: str = "internal-synthetic") -> str:
    return jwt.encode(
        {
            "sub": "synthetic-canary@internal",
            "tenant_id": tenant_id,
            "roles": ["analyst"],
            "scope": "catalog:read quality:read lineage:read",
            "aud": "datagenie-mcp",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        secret,
        algorithm="HS256",
    )


def headers(secret: str, tenant_id: str = "internal-synthetic") -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token(secret, tenant_id)}",
        "Mcp-Client-Id": "synthetic-approved-host",
        "MCP-Protocol-Version": "2026-07-28",
        "X-Request-ID": "synthetic-canary-0001",
        "Content-Type": "application/json",
    }


def rpc(method: str, params: dict | None = None, request_id: int = 1) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}


def main() -> int:
    evidence_dir = ROOT / "docs" / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    secret = "synthetic-canary-secret-that-is-longer-than-thirty-two-characters"
    ledger_path = evidence_dir / "mcp-synthetic-canary-ledger.db"
    if ledger_path.exists():
        ledger_path.unlink()
    settings = Settings(
        auth_jwt_secret=secret,
        downstream_service_shared_secret="synthetic-downstream-service-secret",
        mcp_internal_beta_enabled=True,
        mcp_allowed_tenants="internal-synthetic",
        mcp_allowed_hosts="synthetic-approved-host",
        mcp_allowed_origins="https://synthetic-host.internal",
        ledger_database_url=f"sqlite:///{ledger_path}",
    )
    ledger = ExecutionLedger(settings.ledger_database_url)
    app = create_app(McpApplication(settings=settings, client=SyntheticDownstream(), ledger=ledger))

    with TestClient(app) as client:
        initialized = client.post("/mcp", json=rpc("initialize"), headers=headers(secret))
        tools = client.post("/mcp", json=rpc("tools/list", request_id=2), headers=headers(secret))
        resources = client.post("/mcp", json=rpc("resources/list", request_id=3), headers=headers(secret))
        prompts = client.post("/mcp", json=rpc("prompts/list", request_id=4), headers=headers(secret))
        context = client.post(
            "/mcp",
            json=rpc("tools/call", {"name": "get_asset_context", "arguments": {"asset_id": "synthetic-asset", "purpose": "internal canary verification"}}, request_id=5),
            headers=headers(secret),
        )
        foreign = client.post("/mcp", json=rpc("initialize", request_id=6), headers=headers(secret, "foreign-tenant"))

    with ledger.sessions() as session:
        entries = list(session.query(AgentExecution).order_by(AgentExecution.created_at).all())
    metrics_text = generate_latest().decode("utf-8")
    metric_names = [
        "datagenie_mcp_tool_calls_total",
        "datagenie_mcp_policy_decisions_total",
        "datagenie_mcp_execution_ledger_write_failures_total",
        "datagenie_mcp_tenant_boundary_violations_total",
    ]
    observed_metrics = {name: any(line.startswith(name) for line in metrics_text.splitlines()) for name in metric_names}
    # Prometheus Python counters with no observed increments may be absent from a
    # scrape. The zero-value security counters are still registered in the
    # gateway module; only positive operational metrics are expected locally.
    required_observed_metrics = {
        "datagenie_mcp_tool_calls_total": observed_metrics["datagenie_mcp_tool_calls_total"],
        "datagenie_mcp_policy_decisions_total": observed_metrics["datagenie_mcp_policy_decisions_total"],
    }
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "local synthetic control verification only; no live OIDC, customer tenant, or downstream network traffic",
        "protocol": {
            "initialize_status": initialized.status_code,
            "tool_count": len(tools.json().get("result", {}).get("tools", [])),
            "resource_count": len(resources.json().get("result", {}).get("resources", [])),
            "prompt_count": len(prompts.json().get("result", {}).get("prompts", [])),
        },
        "structured_result": {
            "status": context.status_code,
            "contains_policy": bool(context.json().get("result", {}).get("structuredContent", {}).get("policy")),
            "technical_metadata_redacted": "technical_metadata" not in context.json().get("result", {}).get("structuredContent", {}).get("data", {}).get("asset", {}),
        },
        "negative_path": {"foreign_tenant_status": foreign.status_code, "foreign_tenant_result_payload": bool(foreign.json().get("result"))},
        "ledger": {
            "entry_count": len(entries),
            "all_tenant_bound": all(entry.tenant_id == "internal-synthetic" for entry in entries),
            "contains_raw_purpose": any("internal canary verification" in entry.input_digest for entry in entries),
            "operations": [entry.operation_name for entry in entries],
        },
        "metrics_registered": observed_metrics,
        "pass": initialized.status_code == 200
        and len(tools.json().get("result", {}).get("tools", [])) == 4
        and len(resources.json().get("result", {}).get("resources", [])) == 5
        and len(prompts.json().get("result", {}).get("prompts", [])) == 3
        and context.status_code == 200
        and foreign.status_code == 401
        and not foreign.json().get("result")
        and len(entries) >= 1
        and not any("internal canary verification" in entry.input_digest for entry in entries)
        and all(required_observed_metrics.values()),
    }
    output = evidence_dir / "mcp-synthetic-canary.json"
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(output)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

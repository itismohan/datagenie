import hashlib
import json
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from fastapi import HTTPException, status

from app.clients.datagenie import DataGenieClient, DownstreamForbidden, DownstreamUnavailable
from app.core.config import Settings, get_settings
from app.core.observability import (
    MCP_ERRORS,
    MCP_LEDGER_FAILURES,
    MCP_POLICY_DECISIONS,
    MCP_RESULT_BYTES,
    MCP_TOOL_CALLS,
    MCP_TOOL_LATENCY,
)
from app.schemas import (
    AssetArguments,
    LineageArguments,
    PolicyEvidence,
    PolicyPacket,
    Principal,
    QualityArguments,
    SearchArguments,
    StructuredResult,
)
from app.security.identity import require_scope
from app.services.execution_ledger import ExecutionLedger, LedgerUnavailable, make_ledger_record

TOOL_VERSION = "0.1.0"
TOOL_SCOPES = {
    "search_governed_assets": ("catalog:read",),
    "get_asset_context": ("catalog:read",),
    "get_quality_evidence": ("quality:read",),
    "analyze_lineage_impact": ("lineage:read",),
}


class McpToolError(RuntimeError):
    def __init__(self, code: str, message: str, status_code: int = status.HTTP_403_FORBIDDEN) -> None:
        self.code = code
        self.status_code = status_code
        super().__init__(message)


def _digest(arguments: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(arguments, separators=(",", ":"), sort_keys=True).encode()).hexdigest()


def _policy_or_error(policy: PolicyPacket) -> None:
    if policy.outcome in {"deny", "requires_human_approval"}:
        raise McpToolError("mcp_forbidden", "The shared DataGenie policy does not permit this tool call.")


def _result(
    request_id: str,
    policy: PolicyPacket | None,
    provenance: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    data: dict[str, Any],
    *,
    confidence: float,
    redactions: list[str] | None = None,
    truncated: bool = False,
) -> StructuredResult:
    now = datetime.now(timezone.utc)
    return StructuredResult(
        tool_version=TOOL_VERSION,
        request_id=request_id,
        generated_at=now,
        timestamp=now,
        provenance=provenance,
        evidence=[PolicyEvidence.model_validate(item) for item in evidence],
        policy=policy,
        obligations=list(policy.obligations) if policy else [],
        confidence=confidence,
        redactions=redactions or [],
        truncated=truncated,
        data=data,
    )


class ToolExecutor:
    def __init__(
        self,
        *,
        client: DataGenieClient,
        ledger: ExecutionLedger,
        settings: Settings | None = None,
    ) -> None:
        self.client = client
        self.ledger = ledger
        self.settings = settings if settings is not None else get_settings()

    async def execute(self, principal: Principal, request_id: str, name: str, arguments: dict[str, Any]) -> StructuredResult:
        if self.settings.mcp_kill_switch_enabled or name in self.settings.csv(self.settings.mcp_disabled_tools):
            raise McpToolError("tool_disabled", "This MCP tool is disabled for the internal beta.", status.HTTP_503_SERVICE_UNAVAILABLE)
        if name not in TOOL_SCOPES:
            raise McpToolError("mcp_method_not_found", "The requested MCP tool is not available in the read-only beta.", status.HTTP_404_NOT_FOUND)
        require_scope(principal, *TOOL_SCOPES[name])
        started = perf_counter()
        digest = _digest(arguments)
        policy: PolicyPacket | None = None
        result: StructuredResult | None = None
        error_code: str | None = None
        outcome = "allowed"
        try:
            if name == "search_governed_assets":
                parsed = SearchArguments.model_validate(arguments)
                downstream = await self.client.search_assets(
                    principal,
                    request_id,
                    parsed.model_dump(exclude_none=True),
                )
                items = downstream.get("items", [])
                result = _result(
                    request_id,
                    None,
                    [{"source": "catalog-api", "source_request_id": request_id, "retrieved_at": datetime.now(timezone.utc)}],
                    [{"type": "search_index", "reference": "catalog:index"}],
                    downstream,
                    confidence=0.9,
                    truncated=downstream.get("total", 0) > len(items),
                )
            elif name == "get_asset_context":
                parsed = AssetArguments.model_validate(arguments)
                policy = await self.client.evaluate_policy(principal, request_id, parsed.asset_id, parsed.purpose)
                _policy_or_error(policy)
                downstream = await self.client.asset_context(principal, request_id, parsed.asset_id, parsed.purpose)
                asset = downstream["asset"]
                redactions: list[str] = []
                asset.pop("technical_metadata", None)
                redactions.append("technical_metadata:bounded")
                if "columns" not in parsed.include:
                    asset.pop("columns", None)
                    redactions.append("columns:not_requested")
                if "quality" not in parsed.include:
                    asset.pop("quality_score", None)
                    asset.pop("quality_explainable_at", None)
                    redactions.append("quality:not_requested")
                result = _result(
                    request_id,
                    policy,
                    [{"source": "catalog-api", "source_request_id": request_id, "retrieved_at": datetime.now(timezone.utc)}],
                    policy.evidence,
                    {"asset": asset},
                    confidence=0.95,
                    redactions=redactions,
                )
            elif name == "get_quality_evidence":
                parsed = QualityArguments.model_validate(arguments)
                policy = await self.client.evaluate_policy(principal, request_id, parsed.asset_id, parsed.purpose)
                _policy_or_error(policy)
                downstream = await self.client.quality_evidence(principal, request_id, parsed.asset_id, parsed.purpose, parsed.history_limit)
                result = _result(
                    request_id,
                    policy,
                    [{"source": downstream["source"], "source_request_id": request_id, "retrieved_at": datetime.now(timezone.utc)}],
                    [*policy.evidence, *downstream["evidence"]],
                    downstream,
                    confidence=0.7 if downstream["state"] == "current" else 0.3,
                    redactions=["row_samples:never_returned", "source_secrets:never_returned"],
                )
            else:
                parsed = LineageArguments.model_validate(arguments)
                policy = await self.client.evaluate_policy(principal, request_id, parsed.asset_id, parsed.purpose)
                _policy_or_error(policy)
                downstream = await self.client.lineage_impact(principal, request_id, parsed.asset_id, parsed.direction, parsed.depth, parsed.purpose)
                nodes = downstream.get("nodes", [])
                edges = downstream.get("edges", [])
                truncated = len(nodes) > self.settings.mcp_max_lineage_nodes
                if truncated:
                    downstream["nodes"] = nodes[: self.settings.mcp_max_lineage_nodes]
                    downstream["edges"] = edges[: self.settings.mcp_max_lineage_nodes]
                result = _result(
                    request_id,
                    policy,
                    [{"source": "lineage-api", "source_request_id": request_id, "retrieved_at": datetime.now(timezone.utc)}],
                    [*policy.evidence, {"type": "lineage_graph", "reference": f"lineage:{parsed.asset_id}"}],
                    downstream,
                    confidence=0.8,
                    truncated=truncated,
                )
            return result
        except HTTPException as exc:
            outcome, error_code = "denied", str(exc.detail.get("code", "mcp_forbidden")) if isinstance(exc.detail, dict) else "mcp_forbidden"
            raise McpToolError(error_code, "The MCP token is not authorized for this tool.", exc.status_code) from exc
        except DownstreamForbidden as exc:
            outcome, error_code = "denied", "mcp_forbidden"
            raise McpToolError(error_code, "The requested governed resource is not available to this caller.") from exc
        except DownstreamUnavailable as exc:
            outcome, error_code = "error", "downstream_unavailable"
            raise McpToolError(error_code, "A required governed discovery dependency is unavailable.", status.HTTP_503_SERVICE_UNAVAILABLE) from exc
        except McpToolError as exc:
            outcome, error_code = "denied", exc.code
            raise
        except Exception as exc:
            outcome, error_code = "error", "mcp_invalid_arguments"
            raise McpToolError(error_code, "The MCP tool input did not pass validation.", status.HTTP_422_UNPROCESSABLE_ENTITY) from exc
        finally:
            duration = (perf_counter() - started) * 1000
            serialized_size = len(result.model_dump_json().encode()) if result else 0
            policy_outcome = policy.outcome if policy else None
            try:
                self.ledger.record(
                    make_ledger_record(
                        request_id=request_id,
                        tenant_id=principal.tenant_id,
                        actor_subject=principal.subject,
                        host_id=principal.host_id,
                        operation_kind="tool",
                        operation_name=name,
                        input_digest=digest,
                        policy_outcome=policy_outcome,
                        outcome=outcome,
                        result_count=len(result.data.get("items", [])) if result else 0,
                        result_bytes=serialized_size,
                        duration_ms=duration,
                        error_code=error_code,
                    )
                )
            except LedgerUnavailable as exc:
                MCP_LEDGER_FAILURES.labels(operation=name).inc()
                if result is not None:
                    raise McpToolError("ledger_unavailable", "The MCP execution record could not be persisted.", status.HTTP_503_SERVICE_UNAVAILABLE) from exc
            MCP_TOOL_CALLS.labels(kind="tool", operation=name, outcome=outcome, host=principal.host_id, tenant=principal.tenant_id).inc()
            MCP_TOOL_LATENCY.labels(operation=name).observe(duration / 1000)
            if policy:
                MCP_POLICY_DECISIONS.labels(operation=name, outcome=policy.outcome).inc()
            if result:
                MCP_RESULT_BYTES.labels(operation=name).observe(serialized_size)
            if error_code:
                MCP_ERRORS.labels(operation=name, code=error_code).inc()

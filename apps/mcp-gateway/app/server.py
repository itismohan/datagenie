import hashlib
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.clients.datagenie import DataGenieClient
from app.core.config import Settings, get_settings
from app.core.observability import MCP_ERRORS, MCP_RATE_LIMIT_DENIALS, MCP_TENANT_BOUNDARY_VIOLATIONS
from app.core.rate_limit import RateLimitExceeded, SlidingWindowRateLimiter
from app.core.tenant_context import bind_principal, reset_principal
from app.schemas import JsonRpcError, JsonRpcRequest, JsonRpcResponse, Principal, PromptGet, ResourceRead, ToolCall
from app.security.identity import AuthenticationError, validated_principal
from app.services.execution_ledger import ExecutionLedger, LedgerUnavailable, make_ledger_record
from app.services.tool_execution import McpToolError, TOOL_SCOPES, ToolExecutor


class McpApplication:
    def __init__(self, settings: Settings | None = None, client: DataGenieClient | None = None, ledger: ExecutionLedger | None = None) -> None:
        self.settings = settings if settings is not None else get_settings()
        self.client = client or DataGenieClient(self.settings)
        self.ledger = ledger or ExecutionLedger(self.settings.ledger_database_url)
        self.executor = ToolExecutor(client=self.client, ledger=self.ledger, settings=self.settings)
        self.limiter = SlidingWindowRateLimiter(self.settings.mcp_max_requests_per_minute)

    async def start(self) -> None:
        self.ledger.create_schema()

    async def close(self) -> None:
        await self.client.close()


_runtime: McpApplication | None = None


def runtime() -> McpApplication:
    if _runtime is None:
        raise RuntimeError("MCP gateway runtime has not been initialized.")
    return _runtime


def _json_error(request_id: str | int | None, code: int, message: str, safe_code: str, correlation_id: str) -> JsonRpcResponse:
    return JsonRpcResponse(
        id=request_id,
        error=JsonRpcError(code=code, message=message, data={"code": safe_code, "request_id": correlation_id}),
    )


def _metadata(settings: Settings) -> dict:
    endpoint = settings.mcp_resource_base_url
    return {
        "resource": endpoint,
        "authorization_servers": sorted(settings.csv(settings.mcp_authorization_servers)),
        "scopes_supported": ["catalog:read", "quality:read", "lineage:read"],
        "bearer_methods_supported": ["header"],
        "resource_documentation": f"{endpoint.rsplit('/mcp', 1)[0]}/docs/mcp-authorization-reference",
    }


def _tool_definitions() -> list[dict]:
    return [
        {
            "name": "search_governed_assets",
            "description": "Search tenant-visible governed metadata; returns structured provenance and policy evidence.",
            "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}, "purpose": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 50}}, "required": ["purpose"], "additionalProperties": False},
            "outputSchema": {"type": "object", "required": ["request_id", "provenance", "evidence", "timestamp", "confidence", "data"]},
        },
        {
            "name": "get_asset_context",
            "description": "Retrieve tenant-governed asset context without source secrets or row data.",
            "inputSchema": {"type": "object", "properties": {"asset_id": {"type": "string"}, "purpose": {"type": "string"}, "include": {"type": "array", "items": {"type": "string"}}}, "required": ["asset_id", "purpose"], "additionalProperties": False},
            "outputSchema": {"type": "object", "required": ["policy", "provenance", "evidence", "timestamp", "confidence", "data"]},
        },
        {
            "name": "get_quality_evidence",
            "description": "Retrieve explainable, freshness-aware quality evidence without raw data samples.",
            "inputSchema": {"type": "object", "properties": {"asset_id": {"type": "string"}, "purpose": {"type": "string"}, "history_limit": {"type": "integer", "minimum": 1, "maximum": 10}}, "required": ["asset_id", "purpose"], "additionalProperties": False},
            "outputSchema": {"type": "object", "required": ["policy", "provenance", "evidence", "timestamp", "confidence", "data"]},
        },
        {
            "name": "analyze_lineage_impact",
            "description": "Retrieve bounded governed lineage impact and typed provenance; never executes graph mutation.",
            "inputSchema": {"type": "object", "properties": {"asset_id": {"type": "string"}, "purpose": {"type": "string"}, "direction": {"type": "string", "enum": ["upstream", "downstream", "both"]}, "depth": {"type": "integer", "minimum": 1, "maximum": 3}}, "required": ["asset_id", "purpose"], "additionalProperties": False},
            "outputSchema": {"type": "object", "required": ["policy", "provenance", "evidence", "timestamp", "confidence", "data"]},
        },
    ]


def _resources() -> list[dict]:
    return [
        {"uri": "datagenie://catalog/assets/{asset_id}", "name": "Governed asset context", "mimeType": "application/json"},
        {"uri": "datagenie://catalog/domains/{domain_id}", "name": "Governance domain", "mimeType": "application/json"},
        {"uri": "datagenie://policy/assets/{asset_id}", "name": "Asset policy evidence", "mimeType": "application/json"},
        {"uri": "datagenie://quality/assets/{asset_id}/latest", "name": "Latest quality evidence", "mimeType": "application/json"},
        {"uri": "datagenie://lineage/assets/{asset_id}", "name": "Bounded lineage context", "mimeType": "application/json"},
    ]


def _prompts() -> list[dict]:
    return [
        {"name": "assess_data_for_use", "description": "Build evidence-cited data-use decision support without changing governance state."},
        {"name": "explain_lineage_impact", "description": "Build a bounded, provenance-aware lineage impact analysis."},
        {"name": "summarize_governed_asset", "description": "Build an evidence- and obligation-preserving asset summary for an audience."},
    ]


async def _resource_read(app: McpApplication, principal: Principal, request_id: str, params: dict) -> dict:
    read = ResourceRead.model_validate(params)
    parsed = urlparse(read.uri)
    if parsed.scheme != "datagenie":
        raise McpToolError("mcp_invalid_resource", "Only DataGenie resource URIs are available.", status.HTTP_422_UNPROCESSABLE_ENTITY)
    query = {key: values[-1] for key, values in parse_qs(parsed.query).items()}
    path = parsed.path.strip("/").split("/")
    host = parsed.netloc
    if host == "catalog" and len(path) == 2 and path[0] == "assets":
        result = await app.executor.execute(principal, request_id, "get_asset_context", {"asset_id": path[1], "purpose": query.get("purpose", "catalog context review"), "include": ["columns", "governance"]})
    elif host == "quality" and len(path) == 3 and path[0] == "assets" and path[2] == "latest":
        result = await app.executor.execute(principal, request_id, "get_quality_evidence", {"asset_id": path[1], "purpose": query.get("purpose", "quality evidence review")})
    elif host == "lineage" and len(path) == 2 and path[0] == "assets":
        result = await app.executor.execute(principal, request_id, "analyze_lineage_impact", {"asset_id": path[1], "purpose": query.get("purpose", "lineage impact analysis")})
    elif host == "policy" and len(path) == 2 and path[0] == "assets":
        policy = await app.client.evaluate_policy(principal, request_id, path[1], query.get("purpose", "policy context review"))
        now = datetime.now(timezone.utc)
        result = {
            "request_id": request_id,
            "tenant_bound": True,
            "timestamp": now.isoformat(),
            "provenance": [{"source": "catalog-policy", "retrieved_at": now.isoformat()}],
            "evidence": [item.model_dump() for item in policy.evidence],
            "policy": policy.model_dump(mode="json"),
            "obligations": policy.obligations,
            "confidence": 1.0,
            "data": {"asset_id": path[1]},
        }
    elif host == "catalog" and len(path) == 2 and path[0] == "domains":
        domain = await app.client.domain(principal, request_id, path[1])
        now = datetime.now(timezone.utc)
        result = {"request_id": request_id, "tenant_bound": True, "timestamp": now.isoformat(), "provenance": [{"source": "catalog-api", "retrieved_at": now.isoformat()}], "evidence": [{"type": "governance_domain", "reference": f"domain:{path[1]}"}], "policy": None, "obligations": [], "confidence": 0.95, "data": domain}
    else:
        raise McpToolError("mcp_invalid_resource", "The requested DataGenie resource is not available.", status.HTTP_404_NOT_FOUND)
    content = result.model_dump(mode="json") if hasattr(result, "model_dump") else result
    return {"contents": [{"uri": read.uri, "mimeType": "application/json", "text": json.dumps(content, separators=(",", ":"), default=str)}], "structuredContent": content}


def _record_non_tool_call(
    application: McpApplication,
    principal: Principal,
    request_id: str,
    method: str,
    params: dict,
    *,
    outcome: str,
    error_code: str | None = None,
) -> None:
    kind = "resource" if method.startswith("resources/") else "prompt" if method.startswith("prompts/") else "protocol"
    digest = hashlib.sha256(json.dumps(params, separators=(",", ":"), sort_keys=True).encode()).hexdigest()
    try:
        application.ledger.record(
            make_ledger_record(
                request_id=request_id,
                tenant_id=principal.tenant_id,
                actor_subject=principal.subject,
                host_id=principal.host_id,
                operation_kind=kind,
                operation_name=method,
                input_digest=digest,
                policy_outcome=None,
                outcome=outcome,
                error_code=error_code,
            )
        )
    except LedgerUnavailable as exc:
        raise McpToolError("ledger_unavailable", "The MCP execution record could not be persisted.", status.HTTP_503_SERVICE_UNAVAILABLE) from exc


def _prompt_response(params: dict, request_id: str) -> dict:
    prompt = PromptGet.model_validate(params)
    if prompt.name not in {item["name"] for item in _prompts()}:
        raise McpToolError("mcp_method_not_found", "The requested decision-support prompt is not available.", status.HTTP_404_NOT_FOUND)
    return {
        "description": "Decision-support prompt template. It cannot authorize or mutate DataGenie.",
        "messages": [{"role": "user", "content": {"type": "text", "text": f"Use {prompt.name} with the supplied governed evidence. Preserve policy obligations, provenance, timestamps, confidence, and redaction indicators. Arguments: {json.dumps(prompt.arguments, sort_keys=True)}"}}],
        "structuredContent": {"request_id": request_id, "prompt": prompt.name, "arguments": prompt.arguments, "requires_evidence_bearing_result": True, "may_mutate": False},
    }


def create_app(application: McpApplication | None = None) -> FastAPI:
    app_runtime = application if application is not None else McpApplication()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        global _runtime
        _runtime = app_runtime
        await app_runtime.start()
        yield
        await app_runtime.close()
        _runtime = None

    app = FastAPI(title=app_runtime.settings.app_name, version="0.1.0", lifespan=lifespan, docs_url=None, redoc_url=None)

    @app.get("/.well-known/oauth-protected-resource", include_in_schema=False)
    @app.get("/.well-known/oauth-protected-resource/mcp", include_in_schema=False)
    async def protected_resource_metadata() -> dict:
        return _metadata(app_runtime.settings)

    @app.get("/health/live", include_in_schema=False)
    async def liveness() -> dict[str, str]:
        return {"status": "live"}

    @app.get("/health/ready", include_in_schema=False)
    async def readiness() -> dict[str, str]:
        return {"status": "ready"}

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.post(app_runtime.settings.mcp_endpoint_path, include_in_schema=False)
    async def mcp(request: Request) -> JSONResponse:
        request_id = request.headers.get(app_runtime.settings.request_id_header) or str(uuid4())
        if not app_runtime.settings.mcp_internal_beta_enabled or app_runtime.settings.mcp_kill_switch_enabled:
            return JSONResponse(
                _json_error(None, -32003, "The internal MCP beta is disabled.", "tool_disabled", request_id).model_dump(),
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                headers={app_runtime.settings.request_id_header: request_id},
            )
        try:
            principal = validated_principal(
                request.headers.get("Authorization"),
                request.headers.get("Mcp-Client-Id"),
                app_runtime.settings,
            )
        except AuthenticationError as exc:
            return JSONResponse(
                _json_error(None, -32003, "Unauthorized MCP request.", "mcp_unauthorized", request_id).model_dump(),
                status_code=status.HTTP_401_UNAUTHORIZED,
                headers={
                    "WWW-Authenticate": f'Bearer resource_metadata="{app_runtime.settings.mcp_resource_base_url.rsplit("/mcp", 1)[0]}/.well-known/oauth-protected-resource" scope="catalog:read quality:read lineage:read"',
                    app_runtime.settings.request_id_header: request_id,
                },
            )
        origin = request.headers.get("Origin")
        allowed_origins = app_runtime.settings.csv(app_runtime.settings.mcp_allowed_origins)
        if origin and origin not in allowed_origins:
            return JSONResponse(_json_error(None, -32003, "Origin is not approved.", "mcp_origin_forbidden", request_id).model_dump(), status_code=status.HTTP_403_FORBIDDEN)
        version = request.headers.get("MCP-Protocol-Version")
        if version not in app_runtime.settings.supported_protocol_versions:
            return JSONResponse(_json_error(None, -32001, "Unsupported MCP protocol version.", "mcp_protocol_unsupported", request_id).model_dump(), status_code=status.HTTP_400_BAD_REQUEST, headers={"MCP-Protocol-Version": app_runtime.settings.supported_protocol_versions[-1]})
        try:
            app_runtime.limiter.check(f"{principal.host_id}:{principal.tenant_id}")
        except RateLimitExceeded as exc:
            MCP_RATE_LIMIT_DENIALS.labels(host=principal.host_id, tenant=principal.tenant_id).inc()
            return JSONResponse(_json_error(None, -32029, "MCP rate limit exceeded.", "rate_limit_exceeded", request_id).model_dump(), status_code=status.HTTP_429_TOO_MANY_REQUESTS, headers={"Retry-After": str(exc.retry_after_seconds)})
        try:
            payload = JsonRpcRequest.model_validate(await request.json())
        except Exception:
            return JSONResponse(_json_error(None, -32600, "Invalid JSON-RPC request.", "mcp_invalid_request", request_id).model_dump(), status_code=status.HTTP_400_BAD_REQUEST)
        token = bind_principal(principal)
        try:
            result: dict
            if payload.method == "initialize":
                result = {"protocolVersion": version, "capabilities": {"tools": {}, "resources": {}, "prompts": {}}, "serverInfo": {"name": "datagenie-governed-discovery", "version": "0.1.0"}, "instructions": "Internal-only, read-only governed discovery. Every result is structured and evidence-bearing."}
            elif payload.method == "tools/list":
                result = {"tools": _tool_definitions()}
            elif payload.method == "tools/call":
                call = ToolCall.model_validate(payload.params)
                structured = await app_runtime.executor.execute(principal, request_id, call.name, call.arguments)
                result = {"content": [{"type": "text", "text": json.dumps(structured.model_dump(mode="json"), separators=(",", ":"))}], "structuredContent": structured.model_dump(mode="json"), "isError": False}
            elif payload.method == "resources/list":
                result = {"resources": _resources()}
            elif payload.method == "resources/read":
                result = await _resource_read(app_runtime, principal, request_id, payload.params)
            elif payload.method == "prompts/list":
                result = {"prompts": _prompts()}
            elif payload.method == "prompts/get":
                result = _prompt_response(payload.params, request_id)
            else:
                return JSONResponse(_json_error(payload.id, -32601, "Method not found.", "mcp_method_not_found", request_id).model_dump(), status_code=status.HTTP_404_NOT_FOUND)
            if payload.method != "tools/call":
                _record_non_tool_call(app_runtime, principal, request_id, payload.method, payload.params, outcome="allowed")
            return JSONResponse(JsonRpcResponse(id=payload.id, result=result).model_dump(mode="json"), headers={app_runtime.settings.request_id_header: request_id, "MCP-Protocol-Version": version})
        except McpToolError as exc:
            MCP_ERRORS.labels(operation=payload.method, code=exc.code).inc()
            if payload.method != "tools/call":
                try:
                    _record_non_tool_call(app_runtime, principal, request_id, payload.method, payload.params, outcome="denied", error_code=exc.code)
                except McpToolError:
                    pass
            return JSONResponse(_json_error(payload.id, -32003, str(exc), exc.code, request_id).model_dump(), status_code=exc.status_code, headers={app_runtime.settings.request_id_header: request_id, "MCP-Protocol-Version": version})
        finally:
            reset_principal(token)

    return app

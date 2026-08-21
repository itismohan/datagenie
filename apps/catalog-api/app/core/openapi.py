from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


API_DESCRIPTION = """## DataGenie Catalog API

The DataGenie Catalog API provides tenant-isolated metadata discovery, stewardship,
governance, operational lineage integration boundaries, quality-aware search, and
customer operations. Every endpoint is versioned under `/api/v1`.

### Authentication and tenant boundary

Supply an OAuth/OIDC or HS256 bearer token in `Authorization: Bearer <token>`.
Outside local development, every token must include the configured tenant claim.
Responses, search facets, audit history, exports, retention policies, and webhook
operations are restricted to that tenant.

### Request correlation and errors

Clients may send `X-Request-ID`; otherwise the service generates one and returns it
on every response. Error responses use a stable envelope containing an application
`code`, a human-readable `message`, and the request ID required for support.

### Idempotency and rate limits

Use `Idempotency-Key` for supported mutating operations, especially source and
ingestion-job creation. Catalog endpoints return standard `RateLimit-*` and
`Retry-After` headers when request protection is active.
"""

OPENAPI_TAGS = [
    {"name": "Assets", "description": "Governed asset discovery, technical metadata, and steward curation."},
    {"name": "Sources", "description": "Tenant-scoped connector sources, capabilities, validation, and ingestion submission."},
    {"name": "Ingestion jobs", "description": "Durable connector execution history, retry, cancellation, and dead-letter replay."},
    {"name": "Glossary", "description": "Business-term stewardship and reviewed asset mappings."},
    {"name": "Governance", "description": "Domains, classification review, certification, discovery metrics, and reviewed suggestions."},
    {"name": "Search index", "description": "Persistent tenant-scoped index freshness, facets, and controlled reindex operations."},
    {"name": "Operations", "description": "Tenant-scoped exports, retention policies, webhook subscriptions, and delivery history."},
    {"name": "Audit events", "description": "Tenant-scoped audit evidence available to platform administrators."},
    {"name": "Policy decisions", "description": "Deterministic tenant-aware authorization decisions with rules, evidence, obligations, and expiry."},
    {"name": "Platform health", "description": "Liveness and readiness probes. Metrics are deliberately excluded from the public schema."},
]


def _error_response(description: str, code: str) -> dict:
    return {
        "description": description,
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/ErrorEnvelope"},
                "examples": {
                    code: {
                        "value": {
                            "error": {
                                "code": code,
                                "message": description,
                                "request_id": "b9ce11cc-4e68-4f4c-9e0f-4c1f0e2c6e2d",
                            }
                        }
                    }
                },
            }
        },
    }


def build_openapi(app: FastAPI) -> dict:
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version="3.1.0",
        summary="Tenant-isolated metadata governance and discovery platform",
        description=API_DESCRIPTION,
        routes=app.routes,
        tags=OPENAPI_TAGS,
    )
    schema["info"].update(
        {
            "contact": {"name": "DataGenie API Support", "url": "https://github.com/itismohan/datagenie/issues"},
            "license": {"name": "Proprietary"},
            "x-api-lifecycle": "stable",
        }
    )
    schema["servers"] = [{"url": "/", "description": "Current environment through the DataGenie TLS ingress"}]

    components = schema.setdefault("components", {})
    components.setdefault("securitySchemes", {})["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "JWT or OIDC access token with a tenant claim and one or more DataGenie roles.",
    }
    components.setdefault("schemas", {})["ErrorDetail"] = {
        "type": "object",
        "required": ["code", "message", "request_id"],
        "properties": {
            "code": {"type": "string", "description": "Stable machine-readable application error code."},
            "message": {"type": "string", "description": "Safe human-readable error message."},
            "request_id": {"type": "string", "description": "Correlation identifier for support and audit investigation."},
            "details": {"description": "Optional validation or domain-specific evidence."},
        },
    }
    components["schemas"]["ErrorEnvelope"] = {
        "type": "object",
        "required": ["error"],
        "properties": {"error": {"$ref": "#/components/schemas/ErrorDetail"}},
    }
    components.setdefault("parameters", {})["RequestId"] = {
        "name": "X-Request-ID",
        "in": "header",
        "required": False,
        "schema": {"type": "string", "maxLength": 128},
        "description": "Optional client correlation ID. The service generates and returns one when omitted.",
    }

    public_paths = {"/health", "/health/live", "/health/ready"}
    for path, path_item in schema.get("paths", {}).items():
        for method, operation in path_item.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            parameters = operation.setdefault("parameters", [])
            if not any(parameter.get("$ref") == "#/components/parameters/RequestId" for parameter in parameters):
                parameters.append({"$ref": "#/components/parameters/RequestId"})
            responses = operation.setdefault("responses", {})
            if path not in public_paths:
                operation["security"] = [{"BearerAuth": []}]
                responses.setdefault("401", _error_response("A valid bearer token is required.", "unauthorized"))
                responses.setdefault("403", _error_response("The authenticated principal is not authorized for this operation.", "forbidden"))
            responses.setdefault("422", _error_response("The request did not pass validation.", "validation_error"))
            responses.setdefault("429", _error_response("Too many requests. Retry after the supplied interval.", "rate_limit_exceeded"))
            responses.setdefault("500", _error_response("An unexpected server error occurred.", "internal_error"))

    app.openapi_schema = schema
    return app.openapi_schema

# DataGenie Catalog API Integration Guide

## Documentation entry points

The Catalog API is documented from its executable FastAPI contract. The interactive pages and raw specification are published through the same TLS ingress as the API, so the documentation always describes the deployed version.

| Resource | Path | Intended use |
|---|---|---|
| Swagger UI | `/api/docs` | Explore operations interactively, authorize a bearer token, and execute non-production requests. |
| ReDoc | `/api/redoc` | Read a structured, reference-oriented rendering of the API. |
| OpenAPI JSON | `/api/openapi.json` | Generate clients, validate requests, or import into API tooling. |
| Versioned repository artifact | `docs/openapi/catalog-api-v1.json` | Review contract changes in pull requests and use for deterministic client generation. |

> **Environment rule:** Use the interactive documentation against staging or a dedicated test tenant. Never place production bearer tokens, webhook secrets, or source credentials into public screenshots, browser extensions, or untrusted client generators.

## Versioning and compatibility

All supported business endpoints are prefixed with `/api/v1`. Additive fields, new optional query parameters, and new endpoints are non-breaking changes within v1. Renaming/removing a field, changing a field type, changing authorization semantics, or changing error-envelope structure requires a new major API version or an announced compatibility period.

The generated specification has `info.version = 1.0.0`. Clients should pin their generated SDK to a reviewed specification commit, tolerate unknown response fields, and use the returned request ID when opening a support case.[1]

| Change class | Client expectation | Provider process |
|---|---|---|
| Additive endpoint, optional field, or enum value | Clients should ignore unknown fields and handle new enum values safely. | Document in release notes and update the JSON artifact. |
| Deprecation | Existing behavior remains available through the announced window. | Mark OpenAPI operation/field deprecated, publish migration guidance, and track usage. |
| Breaking change | New major path/version is introduced. | Maintain the prior major version until the published retirement date. |

## Authentication, tenancy, and roles

Send a bearer token on every business operation. Outside local development, DataGenie validates either HS256 JWTs or OIDC/JWKS tokens and requires the configured `tenant_id` claim. The tenant is applied to database sessions and PostgreSQL RLS policies, so clients must never attempt to supply a tenant ID as a query parameter or request body override.[2]

```bash
export DATAGENIE_BASE_URL="https://catalog.example.com"
export DATAGENIE_TOKEN="<tenant-scoped-access-token>"

curl --fail-with-body \
  -H "Authorization: Bearer ${DATAGENIE_TOKEN}" \
  -H "Accept: application/json" \
  "${DATAGENIE_BASE_URL}/api/v1/assets/?q=payments&limit=25"
```

| Role | Typical API use |
|---|---|
| `platform_admin` | Tenant-scoped platform operations, audit history, retention, exports, and source management. |
| `data_steward` | Governance review, curation, domains, glossary workflows, classification decisions, and index maintenance. |
| `data_owner` | Owner-scoped curation and certified-data decisions. |
| `analyst` | Discovery, technical metadata, and approved governance context. |
| `read_only` | Read-only catalog discovery permitted by endpoint authorization. |

## Correlation, idempotency, and errors

Clients may provide `X-Request-ID` to correlate an operation across application logs, audit events, and support cases. If omitted, the service creates one and returns it in the response. Mutating endpoints that support replay use `Idempotency-Key`; reuse the same key only for the same authenticated caller, method, route, and request body.[3]

All platform errors use the following envelope:

```json
{
  "error": {
    "code": "validation_error",
    "message": "The request did not pass validation.",
    "request_id": "b9ce11cc-4e68-4f4c-9e0f-4c1f0e2c6e2d",
    "details": []
  }
}
```

| HTTP status | Example application code | Client action |
|---|---|---|
| `401` | `unauthorized` | Obtain a valid bearer token. |
| `403` | `forbidden` | Do not retry; request the required role or ownership approval. |
| `404` | Resource-specific not-found code | Treat as absent within the active tenant; do not infer another tenant’s existence. |
| `409` | `job_not_retryable` or `policy_requires_human_approval` | Re-read the resource state or use the documented eligible human approval workflow. |
| `422` | `validation_error` | Correct the request using `details`. |
| `429` | `rate_limit_exceeded` | Observe `Retry-After` and `RateLimit-*` headers with exponential backoff. |
| `503` | `connector_queue_unavailable` or `rate_limit_unavailable` | Retry only after a bounded delay; preserve the request ID. |
| `500` | `internal_error` | Retry idempotent reads cautiously and report the request ID if persistent. |

## Core workflow examples

### Discover governed data

`GET /api/v1/assets/` supports name, business term, owner, domain, tag, classification, quality, freshness, lifecycle, and source filters. Results include transparent `discovery_score`, tenant-scoped facets, and `index_fresh_at`.

```bash
curl --fail-with-body \
  -H "Authorization: Bearer ${DATAGENIE_TOKEN}" \
  "${DATAGENIE_BASE_URL}/api/v1/assets/?business_term=Revenue&domain=Finance&quality_min=90&explainable_quality_only=true"
```

### Evaluate a governed policy decision

`POST /api/v1/policy/decisions` evaluates a requested action against the authenticated caller, active tenant, current governed resource facts and an optional declared purpose. It does not execute the action. The service derives subject, roles and tenant from the bearer token; clients cannot supply tenant, role, outcome, rule, evidence or obligation overrides.

```bash
curl --fail-with-body -X POST \
  -H "Authorization: Bearer ${DATAGENIE_TOKEN}" \
  -H "Content-Type: application/json" \
  -H "X-Request-ID: policy-check-001" \
  -d '{
    "action": "asset.read",
    "resource": {"resource_type": "asset", "resource_id": "<asset-id>"},
    "purpose": "financial reporting analysis",
    "context": {}
  }' \
  "${DATAGENIE_BASE_URL}/api/v1/policy/decisions"
```

The response is one of `allow`, `deny`, `allow_with_obligations`, or `requires_human_approval`. It includes stable rule identifiers, safe evidence references, obligations, decision expiry and the request ID. A decision with obligations or required approval is not an execution permission unless the calling channel can preserve those semantics. Protected complex routes use this same evaluator before acting; the future MCP adapter must call the same policy interface and cannot introduce a more permissive policy path.

### Register and ingest a source

Source credentials are never sent as raw values. Supply a secret reference such as `vault://`, `aws-secretsmanager://`, or a development-only `env://` reference. Ingestion returns a queued job; poll the job resource rather than holding the request open.[4]

```bash
curl --fail-with-body -X POST \
  -H "Authorization: Bearer ${DATAGENIE_TOKEN}" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: source-finance-warehouse-001" \
  -d '{
    "name": "finance-warehouse",
    "source_type": "postgresql",
    "host": "warehouse.internal",
    "database_name": "analytics",
    "username": "catalog_reader",
    "secret_ref": "vault://datagenie/finance/warehouse-reader"
  }' \
  "${DATAGENIE_BASE_URL}/api/v1/sources/"
```

### Use operational controls

Data stewards and platform administrators can review index freshness, rebuild the active tenant’s index, configure retention, retrieve tenant-scoped exports, and create allowlisted webhook subscriptions. Webhook API responses intentionally omit signing-secret references.[5]

## Generating a client

Any OpenAPI 3.1-compatible generator can consume the exported JSON. The following command is illustrative; review generated code and keep tokens in runtime configuration rather than source control.

```bash
npx @openapitools/openapi-generator-cli generate \
  -i docs/openapi/catalog-api-v1.json \
  -g typescript-fetch \
  -o generated/datagenie-catalog-client
```

After generation, configure the generated client with the TLS ingress base URL and attach a tenant-scoped bearer token using the generator’s authentication hook. Regenerate only after reviewing the specification diff and compatibility notes.

## Contract validation in CI

The repository export script regenerates the JSON artifact from the application’s custom OpenAPI schema:

```bash
python3 apps/catalog-api/scripts/export_openapi.py
git diff --exit-code docs/openapi/catalog-api-v1.json
```

A CI guard should run these commands and fail when application routes change without an intentional specification update. OpenAPI regression tests additionally confirm the Swagger/ReDoc routes, `BearerAuth` scheme, reusable error envelope, request-ID parameter, and public health exceptions.[6]

## References

[1]: openapi/catalog-api-v1.json
[2]: ../apps/catalog-api/app/core/security.py
[3]: ../apps/catalog-api/app/services/idempotency_service.py
[4]: ../apps/catalog-api/app/api/v1/sources.py
[5]: ../apps/catalog-api/app/api/v1/operations.py
[6]: ../apps/catalog-api/tests/test_openapi_contract.py

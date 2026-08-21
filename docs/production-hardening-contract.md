# Production-Hardening Contract

## Scope of this increment

This increment establishes a production baseline for the Catalog API, which is the only service with durable customer-facing data flows. The deployment configuration also makes the platform service topology reproducible locally. The same request, configuration, security, and observability conventions are documented for the remaining APIs so they can adopt the foundation without changing client contracts.

## Configuration and secrets

Every runtime setting is supplied through the `DATAGENIE_` environment-variable namespace. The application will not use a hardcoded database URL, password, or signing key. Docker Compose supplies non-secret defaults only for local development and reads secrets from a local `.env` file that is excluded from version control. Production environments must inject values through their orchestration platform or a managed secret store.

| Setting | Purpose | Production rule |
|---|---|---|
| `DATAGENIE_DATABASE_URL` | Catalog database connection URL | Required; use a distinct least-privilege database principal |
| `DATAGENIE_AUTH_JWT_SECRET` | Token verification key for the initial HS256 implementation | Required and high entropy; replace with OIDC/JWKS integration before broad enterprise rollout |
| `DATAGENIE_AUTH_ENABLED` | Enables bearer-token enforcement | Must be `true` outside explicitly local development |
| `DATAGENIE_ENVIRONMENT` | Deployment environment name | One of `development`, `staging`, or `production` |
| `DATAGENIE_LOG_LEVEL` | Structured log threshold | Defaults to `INFO` |

## API conventions

The public Catalog API is versioned under `/api/v1`. Responses use pagination for collections. Every request receives or accepts an `X-Request-ID`, returned in the response and included in logs, audit events, and errors. Error payloads have a stable shape:

```json
{
  "error": {
    "code": "forbidden",
    "message": "The current role cannot update this asset.",
    "request_id": "..."
  }
}
```

Mutating `POST` and `PATCH` endpoints accept `Idempotency-Key`. The service records a keyed response for 24 hours and returns it for a repeated request from the same principal. This prevents a client retry from creating a second data source or ingestion job.

## Initial access model

| Role | Read assets | Register or run sources | Curate assets | Manage platform |
|---|---:|---:|---:|---:|
| `platform_admin` | Yes | Yes | Yes | Yes |
| `data_steward` | Yes | Yes | Yes | No |
| `data_owner` | Yes | No | Only assets assigned to that owner | No |
| `analyst` | Yes | No | No | No |
| `read_only` | Yes | No | No | No |

All bearer tokens have a subject and a list of roles. The initial implementation supports HS256 JWT verification to make the platform self-contained for local and staging environments. Production should replace the shared signing secret with OIDC issuer, audience, and JWKS validation while retaining the same principal and authorization interface.

## Audit and observability requirements

Every metadata mutation, source operation, and authorization failure records an immutable `AuditEvent` containing actor, roles, action, resource, outcome, request ID, timestamp, and sanitised metadata. Secrets, authorization headers, and raw credentials must not be written to logs or audit records.

The application emits JSON logs with request IDs, method, path, status, latency, and actor where available. It exposes `/health/live`, `/health/ready`, and `/metrics`. Readiness validates database connectivity. Platform error handlers provide stable error bodies and log unexpected exceptions with a request ID.

## Deployment gates

A locally reproducible platform includes PostgreSQL, Redis, the Catalog API, a connector worker placeholder, the remaining API boundaries, database migration execution, health checks, persistent database storage, and a profile-controlled observability stack. A backup script and a restore verification script provide a testable data-recovery path. CI validates formatting, service tests, migration application, and the Compose specification before changes can merge.

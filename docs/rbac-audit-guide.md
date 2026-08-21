# DataGenie RBAC and Audit Operations Guide

## Access model

The Catalog API requires bearer authentication outside local development. A valid access token contains a non-empty `sub`, an `exp`, and one or more supported roles. DataGenie accepts the roles `platform_admin`, `data_steward`, `data_owner`, `analyst`, and `read_only`. Unknown roles and malformed claims are rejected with a structured `401` response.

The service follows least privilege. Analysts and read-only users can discover catalog metadata but cannot operate connectors or modify governance records. Connector registration, validation, capability inspection, synchronization, job inspection, retry, and cancellation belong to platform administrators and data stewards. A data owner may edit only an asset whose `owner` exactly matches the token subject. The full permission matrix is maintained in the attached RBAC contract.

## Connector-management control points

| Endpoint group | Required role | Audit action |
|---|---|---|
| `GET /api/v1/sources` and `GET /api/v1/sources/{id}` | Platform administrator or data steward | `source.list`, `source.read` |
| `GET /api/v1/sources/{id}/capabilities` and `/sync-state` | Platform administrator or data steward | `source.capabilities`, `source.sync_state` |
| `POST /api/v1/sources` and `/{id}/validate` | Platform administrator or data steward | `source.create`, `source.validate` |
| `POST /api/v1/sources/{id}/ingestion-jobs` | Platform administrator or data steward | `ingestion_job.run` |
| `GET /api/v1/ingestion-jobs`, `/{id}`, `/{id}/retry`, and `/{id}/cancel` | Platform administrator or data steward | `ingestion_job.list`, `ingestion_job.read`, `ingestion_job.retry`, `ingestion_job.cancel` |

A denied request from an authenticated subject creates `authorization.denied`, including the protected route, HTTP method, request ID, actor, and accepted roles. Invalid or missing tokens do not produce a database event because they have no verified actor; the request ID remains available in structured logs and the client error response.

## Reviewing audit history

Only a platform administrator can retrieve audit history. The endpoint supports pagination and filters for actor, action, resource type, resource identifier, request ID, and outcome.

```bash
curl -H 'Authorization: Bearer ADMIN_ACCESS_TOKEN' \
  'http://localhost:8000/api/v1/audit-events/?actor_subject=steward@example.com&resource_type=data_source&limit=50'
```

To investigate a customer-reported issue, first collect the returned `X-Request-ID`, then query the audit endpoint with `request_id`. This connects the API response, JSON request logs, source operation, and any authorization denial without exposing connector credentials.

```bash
curl -H 'Authorization: Bearer ADMIN_ACCESS_TOKEN' \
  'http://localhost:8000/api/v1/audit-events/?request_id=REQUEST_ID'
```

## Sensitive-data rules

Audit metadata is recursively sanitized before persistence. Keys containing `secret`, `password`, `token`, `authorization`, `credential`, `connection_string`, or `private_key` are replaced with `[REDACTED]`, including nested objects and lists. Raw bearer tokens, source passwords, private keys, and `secret_ref` values must not be provided to the audit API or added to endpoint metadata.

The audit database should inherit production backup, restore, retention, and access-monitoring controls. Application users must not receive direct database read access. Grant audit-read access only through the restricted API role or through an approved operational investigation process.

## Production controls still required

This implementation verifies locally issued HS256 tokens for the current baseline. Before a broad enterprise rollout, integrate an OIDC identity provider with issuer, audience, and JWKS validation; provision role claims through the identity lifecycle; define a retention policy for audit events; alert on repeated authentication and authorization failures; and periodically test that audit records remain complete and redacted.

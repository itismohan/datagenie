# DataGenie Operations Runbook

## Purpose and ownership

This runbook defines the current controlled-pilot response procedures for DataGenie. It does **not** assign a named production on-call owner because no rotation, escalation channel, or response-time objective is configured in the repository. Those items remain mandatory shared-production launch gates.[1]

| Signal | Severity | First response | Escalate when |
|---|---|---|---|
| `DataGenieCatalogUnavailable` | Critical | Check catalog `/health/live`, `/health/ready`, container logs, database reachability, and the deployed revision. | Readiness remains failed for 10 minutes or metadata writes are unavailable. |
| `DataGenieCatalogElevatedServerErrors` | Warning | Use `X-Request-ID` to locate structured logs and audit activity; identify the route and dependency. | The threshold persists for 10 minutes or a critical workflow is affected. |
| `DataGenieRateLimitStoreFailure` | Critical | Check Redis health, network/DNS, database selection, and credentials. Request protection fails closed by default. | Redis cannot be restored promptly or catalog traffic is materially unavailable. |
| `DataGenieSustainedRateLimitRejections` | Warning | Confirm whether the pattern is abuse, retry storm, rollout regression, or expected demand. | Suspected abuse or sustained customer impact. |

## Health and observability

Catalog health is split into process liveness and database readiness. Lineage readiness verifies Neo4j. Health endpoints are exempt from rate limiting so orchestration can observe a rate-limit-store outage.

```bash
curl -fsS http://<catalog-host>/health/live
curl -fsS http://<catalog-host>/health/ready
curl -fsS http://<lineage-host>/health/live
curl -fsS http://<lineage-host>/health/ready
curl -fsS http://<catalog-host>/metrics | grep -E 'datagenie_(http|rate_limit)'
```

| Metric | Operational interpretation |
|---|---|
| `datagenie_http_requests_total` | Request volume and status-code rate by route and method. |
| `datagenie_http_request_duration_seconds` | Request-latency distribution by route and method. |
| `datagenie_rate_limit_rejections_total` | Requests rejected after a caller exceeded its distributed limit. |
| `datagenie_rate_limit_store_failures_total` | Redis rate-limit store failures, labelled by enforcement policy. |
| `datagenie_unhandled_errors_total` | Unexpected application errors grouped by class. |

Prometheus rules cover catalog availability, 5xx rate, rate-limit-store failure, and sustained rejections. Alert routing and dashboard delivery must be configured before customer scale; rule definitions alone are not an on-call service.[2]

## Rate-limit incident procedure

The catalog API uses Redis fixed-window counters. Limits are scoped to a hash of the bearer token when present and otherwise to client IP; raw bearer tokens are never written to Redis. Staging and production require rate limiting and reject a fail-open configuration.[3]

For a `429`, retain the `RateLimit-Limit`, `RateLimit-Remaining`, `Retry-After`, and `X-Request-ID` headers. Investigate caller pattern and retry behavior before raising a limit. Apply configuration changes only through approved deployment and record the customer impact.

For a `503` with `rate_limit_unavailable`, restore Redis before modifying enforcement. Fail-open is permitted only in local development and must never bypass production request protection.

## Migrations and rollback

Run Alembic as a deployment gate and capture the current revision, backup identifier, deployment version, and approver in the change record.

```bash
cd apps/catalog-api
DATAGENIE_DATABASE_URL='<postgresql-url>' alembic current
DATAGENIE_DATABASE_URL='<postgresql-url>' alembic upgrade head
DATAGENIE_DATABASE_URL='<postgresql-url>' alembic current
```

Prefer forward-compatible migrations. Application rollback must remain compatible with the already-applied schema. Do not downgrade production schema as an incident response unless the approved recovery plan authorizes data reversal and the incident owner accepts its impact.

## Backup and restore drill

Create a custom-format backup and restore it into an isolated temporary database. Retain the backup identifier, elapsed time, validation outcome, operator, and observed recovery point.

```bash
infra/scripts/backup-postgres.sh backups
infra/scripts/verify-postgres-restore.sh backups/<backup-file>.dump
```

A script is not evidence of recoverability. Before launch, execute this drill regularly against production-like backups and compare observed outcomes to approved RPO/RTO targets.[1]

## Tenant-isolation response

Treat any suspected cross-tenant response, audit event, or search facet as a **critical security incident**. Preserve the request ID, caller subject, token issuer metadata, tenant claim, affected record IDs, and SQL/application logs. Stop tenant onboarding, verify the active `app.tenant_id` value and PostgreSQL RLS policy with the non-owner application role, and preserve the database snapshot before making changes. Do not use an all-tenant maintenance bypass for incident investigation without security approval.

## Connector and quality-job response

Connector harvesting runs through a dedicated durable worker queue rather than the API process. For a failure, inspect job history, task ID, cursor, retry lineage, lease expiry, cancellation flag, error evidence, and source permissions. The worker retries with bounded exponential backoff and moves exhausted jobs to `dead_letter`; use replay only after the causal condition is corrected. For quality incidents, inspect rule version, evidence, severity, assignee, and comments before changing thresholds or resolving the incident.[4]

A `connector_queue_unavailable` response means the job record exists but task submission failed. Restore Redis or network access, then resubmit a reviewed job. A lost worker should be recoverable after its lease expires; verify that lease duration remains greater than hard task time limit.

## Search-index and webhook response

Use `GET /api/v1/search-index/status` to identify stale search documents and `POST /api/v1/search-index/reindex` during a controlled maintenance window. Record the tenant, before/after index counts, oldest index timestamp, and query validation results. A reindex endpoint is not a substitute for an index-lag SLO or a dedicated search engine at high scale.[5]

Webhook deliveries are durable outbox records. Inspect `GET /api/v1/operations/webhook-deliveries` for failures and dead letters. Verify the allowlisted hostname, external signing-secret reference, target availability, HMAC verification, and egress firewall before retrying. Never change a target to a private, loopback, link-local, or metadata-service address during incident response.[6]

## Incident evidence

Every incident record should contain UTC start/end time, affected customers, source or asset IDs, request IDs, deployed revision, action log, communications, root cause, follow-up owner, and due date. A named primary/secondary rotation, severity definitions, alert receiver, and post-incident review template are required before shared production launch.

## References

1. [Launch-readiness assessment][1]
2. [Prometheus alert rules][2]
3. [Catalog rate-limit implementation][3]
4. [Durable connector worker][4]
5. [Persistent search index][5]
6. [Production release architecture][6]

[1]: launch-readiness-assessment.md
[2]: ../infra/prometheus-alerts.yml
[3]: ../apps/catalog-api/app/core/rate_limit.py
[4]: ../apps/catalog-api/app/workers/tasks.py
[5]: ../apps/catalog-api/app/services/search_index_service.py
[6]: production-release-architecture.md

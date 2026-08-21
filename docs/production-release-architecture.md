# DataGenie Production Release Architecture

**Status:** Implementation baseline for controlled staging and production-readiness validation.

> **Release decision:** This implementation introduces the required technical boundaries for shared deployment, but production enablement remains conditional on a real PostgreSQL RLS verification, managed secret-store integration, a provisioned DNS/TLS domain, outbound-network policy enforcement, named on-call owners, and executed restore drills.

## Architecture boundary

DataGenie now treats the tenant claim as a mandatory data-plane boundary rather than an application convention. A validated `tenant_id` claim is bound to each request session, attached to every tenant-scoped row, applied by the ORM to reads and writes, and set as PostgreSQL `app.tenant_id` for row-level-security policies. The policies are enabled and forced for catalog, governance, audit, search, retention, and webhook tables.[1]

| Layer | Implemented control | Release condition |
|---|---|---|
| Identity | HS256 or OIDC/JWKS validation requires a tenant claim outside local development. | Identity provider must issue immutable tenant claims and prevent tenant selection by end users. |
| Persistence | Tenant keys, ORM predicates, write-key replacement, and forced PostgreSQL RLS policies. | Validate policy behavior using the non-owner application database role in staging. |
| Secrets | Sources and webhook signing credentials accept external references, not raw secrets. | Replace `env://` delivery resolution with a managed secret-store adapter before broad customer use. |
| Ingress | Caddy is the sole public catalog path and obtains TLS certificates for a configured public hostname. | Configure DNS, certificate contact, ingress firewall, and remove all direct service exposure. |
| Audit | Audit events have tenant keys and tenant-scoped reads. | Configure export retention, customer audit-export process, and review access regularly. |

## Durable connector execution

The API persists an ingestion job before it submits a worker task. Celery consumes the dedicated `connectors` queue using late acknowledgements, one-task prefetch, rejection on worker loss, hard/soft time limits, retries with exponential backoff, leases, cancellation flags, and dead-letter transitions.[2]

| Failure mode | Durable behavior | Operator action |
|---|---|---|
| Broker submission fails | The job remains recorded with a queue-submission error; API returns a correlated `503`. | Restore Redis or networking and submit a reviewed retry. |
| Connector fails | The worker records error evidence and schedules retry timing. | Correct source access/configuration; inspect job history and cursor before retry. |
| Retry budget exhausted | The job changes to `dead_letter`; worker error tracking receives an event. | Review evidence and use the controlled replay endpoint after remediation. |
| Worker disappears | The task is redelivered; a stale lease can be recovered by a later worker. | Investigate worker health and ensure lease duration exceeds hard task time limit. |
| Cancellation requested | The job is marked cancelled before or after connector execution boundary checks. | Confirm no cursor advanced unexpectedly; retry only as a new job. |

## Search and index operations

Catalog search remains authorization-preserving because the delegated search service forwards the caller token to catalog. The catalog now maintains tenant-scoped search documents alongside discovery and curation commits. Search returns facets calculated only from documents visible to the active tenant and returns the oldest matching index timestamp as `index_fresh_at`.[3]

| Operation | Endpoint | Expected use |
|---|---|---|
| Search catalog | `GET /api/v1/assets` | Standard discovery with facets, ranking, governance filters, and index freshness metadata. |
| Check index freshness | `GET /api/v1/search-index/status` | Detect stale documents before investigating discovery behavior. |
| Reindex active tenant | `POST /api/v1/search-index/reindex` | Run in a controlled maintenance window after migration, recovery, or index corruption. |

The initial index uses durable PostgreSQL-compatible document rows, not a separate search cluster. It is an appropriate controlled-scale stepping stone. Before high-volume analytical navigation, benchmark query and reindex duration, define an index-lag SLO, and decide whether to move the same outbox contract to a dedicated search engine.

## Customer operations and trust controls

Retention policies are tenant-scoped and can remove expired audit, discovery, or ingestion-job records after an operator applies the policy. Catalog and audit exports are tenant scoped and audited. Webhook subscriptions require HTTPS, an external secret reference, a public IP target, and an allowlisted host; deliveries use a durable outbox and HMAC-SHA256 signature.[4]

> **Webhook network safety:** URL validation does not replace egress firewall controls. Production network policy must block RFC1918, loopback, link-local, metadata-service, and other private destinations at the network layer to mitigate DNS rebinding and server-side request forgery.

| Customer-facing operation | Endpoint family | Safeguard |
|---|---|---|
| Catalog/audit export | `/api/v1/operations/exports/*` | Tenant filter and audit record; source credential references are never exported in source read models. |
| Retention policy | `/api/v1/operations/retention*` | Explicit active policy, bounded retention range, tenant-scoped deletion, and audit trail. |
| Webhook subscription | `/api/v1/operations/webhooks` | HTTPS target, hostname allowlist, external signing-secret reference, no secret returned by API. |
| Webhook delivery history | `/api/v1/operations/webhook-deliveries` | Tenant-scoped status, retry evidence, and dead-letter visibility. |

## Staging, progressive rollout, and rollback

The base Compose topology has a staging override that turns on production-style validation for the catalog API, migration job, and connector worker.[5] A production release should use the following progression.

| Step | Gate | Rollback point |
|---|---|---|
| 1. Preflight | Clean migration, unit suites, dependency audit, base/staging Compose validation, alert syntax check. | Stop before any migration. |
| 2. Backup | Create encrypted backup and restore it to an isolated target; record RPO/RTO evidence. | Restore isolated validation target; do not mutate production. |
| 3. Schema | Run forward-compatible migration gate while prior application image remains deployable. | Roll back application image only; do not downgrade schema without approved recovery plan. |
| 4. Canary | Route one internal tenant through TLS ingress and validate tenant boundary, worker completion, search freshness, and error tracking. | Route canary back to prior image; drain queue intentionally. |
| 5. Progressive enablement | Add tenants in cohorts with a named primary/secondary responder and alert receiver. | Pause new cohort; leave completed jobs/audit records intact for evidence. |
| 6. General availability | Publish retention, export, webhook, and support processes; measure SLOs. | Disable onboarding and investigate under incident process. |

## Required evidence before general availability

| Gate | Evidence owner |
|---|---|
| PostgreSQL RLS verification | Platform security: test with app role and cross-tenant attempts against staging database. |
| Managed secret integration | Platform security: secret-store adapter, rotation test, and no plaintext credential scan result. |
| TLS and ingress | Platform engineering: public DNS, trusted certificate, redirect/security policy, and direct-port denial test. |
| Worker recovery | Data platform: kill/restart drill proving lease recovery, dead-letter review, replay, and alert signal. |
| Observability | SRE/on-call: live alert routing, error-tracking project, dashboard, SLO objectives, and incident drill. |
| Search SLO | Product/data platform: defined index lag objective and reindex recovery timing for the largest pilot tenant. |
| Retention/export/webhook | Governance/security: approved data-handling policy, egress firewall test, export authorization test, and retention evidence. |

## References

[1]: ../apps/catalog-api/app/core/security.py
[2]: ../apps/catalog-api/app/workers/tasks.py
[3]: ../apps/catalog-api/app/services/search_index_service.py
[4]: ../apps/catalog-api/app/api/v1/operations.py
[5]: ../infra/docker-compose.staging.yml

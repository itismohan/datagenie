# DataGenie Launch-Readiness Assessment

**Assessment date:** 2026-08-21
**Scope:** Current `main` implementation, including catalog, connector, quality, lineage, and delegated-search services.
**Decision:** **Conditionally ready for a controlled multi-tenant staging canary, not general availability.** The repository now contains tenant-scoped persistence and RLS policy migrations, durable connector worker controls, TLS ingress configuration, error-tracking integration, a persistent search index, and customer-operability APIs. General availability remains gated on environment evidence rather than untested source code.

> **Release posture:** A shared staging canary may proceed after the evidence checklist in the production-release architecture is signed off. General availability must not proceed until PostgreSQL RLS is tested with a non-owner application role, managed secret resolution replaces environment-only delivery resolution, DNS/TLS and egress controls are deployed, restore drills are completed, and a staffed operational response model is active.[10]

## Capability assessment

| Capability | Current evidence | Assessment | Launch gate / next action |
|---|---|---|---|
| Persistence | PostgreSQL catalog models, Alembic migrations, indexes and constraints are present. Backup and isolated restore scripts exist and are syntax-checked in CI.[1] | **Partial** | Execute and retain a scheduled restore drill against a production-like backup; define RPO/RTO and backup retention. |
| Security | Tenant claim validation, tenant columns, ORM enforcement, forced PostgreSQL RLS migrations, per-tenant audit records, external secret references, TLS ingress configuration, rate limiting, and dependency scanning are implemented.[2] | **Conditional** | Test RLS as the non-owner application role, deploy DNS/TLS and egress rules, integrate a managed secret store, and certify least-privilege tenant roles. |
| Reliability | Connector harvesting now runs through a dedicated Celery worker with late acknowledgements, time limits, leases, cancellation, retry backoff, dead-letter transition, replay API, and durable job history.[3] | **Conditional** | Execute worker-loss and replay drills against staging Redis/PostgreSQL and add queue-depth alert routing. |
| API quality | APIs are versioned under `/api/v1`, expose OpenAPI through FastAPI, use pagination/filtering for catalog search, request IDs, a structured error envelope, and Redis-backed request limits with fail-closed production settings.[4] | **Partial** | Document compatibility/deprecation policy and add contract tests for all public services. |
| Observability | Structured request logs, correlation IDs, metrics, probes, Prometheus rules, runbooks, and privacy-preserving error-tracking initialization are implemented.[5] | **Partial** | Provision live error-tracking DSN, alert receiver, dashboards, SLOs, and named primary/secondary on-call owners. |
| Data governance | Ownership, stewardship, glossary review, reviewed classifications, certification, quality evidence, metadata history, retention policies, audited tenant-scoped exports, and human-reviewed suggestions are implemented.[6] | **Conditional** | Approve per-customer retention schedules and execute policy/application evidence before deletion. |
| Quality | Deterministic versioned rules, durable runs/results, incidents, comments and remediation state are implemented through async quality workers.[3] | **Ready for pilot** | Establish thresholds, escalation paths, and critical-asset coverage objectives per customer. |
| Search | Tenant-scoped persistent search documents, permission-aware facets, reindex/status APIs, freshness metadata, transparent relevance, and delegated authorization are implemented.[7] | **Conditional** | Set an index-lag SLO and benchmark/rehearse recovery for the largest pilot tenant before analytical-scale launch. |
| Operations | CI runs migrations/tests, Compose base/staging validation, Prometheus validation, and dependency scanning. TLS ingress and staging Compose topology are defined; rollout/runbook procedures are documented.[8] | **Conditional** | Execute restore, canary, rollback, and incident drills; establish approvals, alert routing, and named on-call ownership. |
| Customer trust | Tenant-scoped catalog/audit exports, retention controls, signed webhook outbox, secret-reference restrictions, and release architecture documentation are implemented.[9] | **Conditional** | Publish customer data-handling policy, support contacts/SLAs, managed-secret rollout, and egress-control test evidence. |

## Product-metric readiness

The platform has two implemented outcome measures: **discovery success**, based on a search followed by an asset view, certification request, or usage decision; and **critical-asset explainable-quality coverage**. These are useful first production metrics, but no representative baselines or targets are yet recorded. Other requested measures require event and operational telemetry that is not yet complete.

| Metric | Current collection status | Required launch action |
|---|---|---|
| Metadata coverage | Harvest jobs and discovered assets provide raw inputs. | Define a source-level numerator/denominator and publish by connector and source type. |
| Metadata completeness | Required fields exist, but no published aggregate KPI. | Calculate priority-asset coverage for owner, description, tag, classification, and freshness. |
| Search success rate | **Implemented** through discovery sessions. | Set a pilot baseline and target by customer/domain. |
| Quality trust | **Implemented** as critical assets with recent explainable quality evidence. | Establish criticality policy, time window and remediation targets. |
| Time to insight | Not instrumented end-to-end. | Correlate source registration, successful ingestion, first search and first asset-view timestamps. |
| Connector reliability | Job history exists. | Publish scheduled-run success ratio, latency and retry rate by connector. |
| Governance adoption | Governance records exist but no weekly-active-steward aggregate. | Add steward-action and approver activity metrics. |
| Platform reliability | Request metrics and health probes exist. | Publish availability, request-error, job-success and recovery-time SLOs with alerting. |

## Sequenced launch plan

| Priority | Release gate | Why it precedes customer scale |
|---|---|---|
| P0 | Tenant isolation, production secret management, TLS ingress and per-tenant audit boundaries | A shared deployment must prevent cross-customer data access by design, not convention. |
| P0 | Asynchronous connector execution, job timeouts, dead-letter/replay controls and alerting | Harvesting is customer-critical; an API process must not be the durable worker or the sole failure boundary. |
| P0 | Rate limiting, security regression tests, dependency scanning, production error tracking and on-call response | Public availability without abuse controls and ownership makes operational recovery unreliable. |
| P1 | Persistent search index, permission-aware facets, reindex strategy and index freshness SLO | Catalog search can serve pilots directly from PostgreSQL, but scale and analytical navigation need a controlled index. |
| P1 | Staging, progressive deploy/rollback, restore-drill evidence and operations runbooks | Reproducible deployment is necessary but insufficient without rehearsal and accountable operators. |
| P1 | Retention, export, webhooks and customer trust documentation | These complete customer-operability and governance commitments after isolation controls are in place. |

## Current implementation decision

This increment implements the requested P0/P1 architectural foundations without overstating operational readiness. Tenant isolation is enforced in application sessions and PostgreSQL policy migrations; connector work is durable and recoverable; ingress, dependency scanning, and error-tracking configuration are present; search has a tenant-scoped persistent index; and customer operations have retention, exports, and webhook outbox controls. The remaining gates are deployment evidence, managed-secret integration, egress controls, and staffed operations rather than missing API primitives.[10]

## Validation evidence for this increment

| Check | Result |
|---|---|
| Catalog unit and API regression suite | **24 passed**, including tenant isolation, tenant audit boundaries, durable queue submission/dead-letter behavior, persistent index facets, rate limiting, and secret-reference validation. |
| Quality, lineage, and delegated-search suites | **4**, **3**, and **2** tests passed in the preceding release validation; rerun remains required before production promotion. |
| Catalog migration chain | Applied successfully to a clean SQLite validation database through `20260821_09`. |
| Docker Compose topology | `docker compose --env-file .env -f infra/docker-compose.yml config -q` passed using the example environment. |
| Alert configuration structure | Four rules and the Prometheus YAML structure validated offline. CI now runs the official `promtool check config` command. |

The local Docker daemon was unavailable during this increment, so the containerised `promtool` command was not executed locally. The identical official validator is included in CI and remains a required merge check.[8]

## References

[1] [Catalog migrations and backup/restore validation][1]
2. [Catalog security and authorization implementation][2]
3. [Connector and quality worker implementation][3]
4. [Catalog API contract and error handling][4]
5. [Catalog and lineage health/observability implementation][5]
6. [Governance and lineage operational contract][6]
7. [Catalog-backed search delegation][7]
8. [Continuous integration workflow][8]
9. [Connector operations guide][9]
10. [Production release architecture][10]

[1]: ../infra/scripts/backup-postgres.sh
[2]: ../apps/catalog-api/app/core/security.py
[3]: ../apps/quality-api/app/workers/tasks.py
[4]: ../apps/catalog-api/app/main.py
[5]: operations-runbook.md
[6]: governance-lineage-contract.md
[7]: ../apps/search-api/app/services/search_service.py
[8]: ../.github/workflows/ci.yml
[9]: connector-framework-guide.md
[10]: production-release-architecture.md

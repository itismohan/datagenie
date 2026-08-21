# DataGenie Launch-Readiness Assessment

**Assessment date:** 2026-08-21
**Scope:** Current `main` implementation, including catalog, connector, quality, lineage, and delegated-search services.
**Decision:** **Not ready for a multi-tenant production launch.** The platform has a credible single-tenant, controlled-pilot foundation, but several launch gates remain open. This assessment treats the requested capability matrix as release acceptance criteria rather than a feature wishlist.

> **Release posture:** DataGenie can continue controlled pilots in isolated customer environments after operational review. A shared, multi-customer production launch must not proceed until tenant isolation, production secret/TLS controls, workload failure handling, rate limiting, and a staffed operational response model are evidenced.

## Capability assessment

| Capability | Current evidence | Assessment | Launch gate / next action |
|---|---|---|---|
| Persistence | PostgreSQL catalog models, Alembic migrations, indexes and constraints are present. Backup and isolated restore scripts exist and are syntax-checked in CI.[1] | **Partial** | Execute and retain a scheduled restore drill against a production-like backup; define RPO/RTO and backup retention. |
| Security | HS256 and OIDC/JWKS authentication, five RBAC roles, authorization-denial audit events, and external secret references are implemented. Connector-source validation rejects raw credentials at the API boundary.[2] | **Blocked** | Add tenant-scoped identity and storage enforcement. Use a managed secret store/envelope encryption for connector credentials, terminate TLS at production ingress, and validate least-privilege roles by tenant. |
| Reliability | Quality checks use Celery with retry backoff. Connector jobs have durable history, retries, idempotency and cancellation controls.[3] | **Partial** | Move connector harvesting off request paths; add per-job time limits, retry policies, dead-letter visibility and operator retry/replay procedures. |
| API quality | APIs are versioned under `/api/v1`, expose OpenAPI through FastAPI, use pagination/filtering for catalog search, request IDs, a structured error envelope, and Redis-backed request limits with fail-closed production settings.[4] | **Partial** | Document compatibility/deprecation policy and add contract tests for all public services. |
| Observability | Catalog exposes structured request logs, correlation IDs, Prometheus metrics, and liveness/readiness probes; lineage has graph-backed readiness. Launch alert rules and an operator runbook now cover availability, elevated 5xx rates, rate-limit failures, and sustained rejections.[5] | **Partial** | Add trace propagation/export, dashboard delivery, error tracking, SLOs, alert routing and named alert ownership. |
| Data governance | Ownership, stewardship, glossary review, reviewed classifications, certification, quality evidence, metadata history, and human-reviewed suggestions are implemented.[6] | **Partial** | Implement retention policies and policy enforcement; include governance/audit exports in the customer data-handling model. |
| Quality | Deterministic versioned rules, durable runs/results, incidents, comments and remediation state are implemented through async quality workers.[3] | **Ready for pilot** | Establish thresholds, escalation paths, and critical-asset coverage objectives per customer. |
| Search | Catalog has transparent relevance ranking and permission-aware access. The separate search API delegates to catalog rather than returning unauthorised stub data.[7] | **Partial** | Introduce a durable index, permission-aware facet aggregation, index lag SLOs, and reindex/recovery runbooks before scale launch. |
| Operations | CI exercises catalog migration/tests, service tests and Compose configuration. Migrations and operation guides exist.[8] | **Partial** | Establish separate staging, progressive deployment, tested rollback, formal runbooks, rotations, change approvals, and named on-call ownership. |
| Customer trust | Connector guidance covers least-privilege setup; governance and lineage workflows are documented.[9] | **Partial** | Publish data-handling and support policies; define support SLAs; add authorized metadata/audit export capabilities. |

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

## Immediate implementation decision

This increment added an API-level **rate-limiting foundation** with a Redis-backed distributed-store boundary, caller-safe identifiers, standard limit/retry headers, fail-closed store handling, and regression coverage. It reduces unauthenticated and authenticated abuse exposure without claiming to solve tenant isolation. Tenant isolation remains a P0 architectural gate and is intentionally recorded as unresolved rather than implemented superficially.

## Validation evidence for this increment

| Check | Result |
|---|---|
| Catalog unit and API regression suite | **16 passed**, including rate-limit headers, 429 correlation, Redis outage fail-closed behavior, staging configuration, and secret-reference validation. |
| Quality, lineage, and delegated-search suites | **4**, **3**, and **2** tests passed respectively. |
| Catalog migration chain | Applied successfully to a clean SQLite validation database through `20260821_05`. |
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

[1]: ../infra/scripts/backup-postgres.sh
[2]: ../apps/catalog-api/app/core/security.py
[3]: ../apps/quality-api/app/workers/tasks.py
[4]: ../apps/catalog-api/app/main.py
[5]: operations-runbook.md
[6]: governance-lineage-contract.md
[7]: ../apps/search-api/app/services/search_service.py
[8]: ../.github/workflows/ci.yml
[9]: connector-framework-guide.md

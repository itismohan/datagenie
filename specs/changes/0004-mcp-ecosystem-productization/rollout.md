# Rollout Plan: 0004-mcp-ecosystem-productization — MCP Ecosystem Productization

**Status:** Draft
**Release owner:** Product and platform owner (TBD)
**On-call owner:** SRE/on-call owner (TBD)

## Release strategy

| Stage | Audience | Enablement control | Entry criteria | Exit criteria |
|---|---|---|---|---|
| Local/CI | Engineering | Repository artifacts and synthetic harness | SDD review complete; tests pass. | Synthetic certification evidence produced. |
| Staging | Internal tenant administrators | Existing internal-beta tenant/host allowlists | Staging OIDC, ledger, and dashboard configured. | Tenant-admin onboarding walkthrough and support dry run pass. |
| Partner preflight | Approved prospective hosts | Test tenant only | Partner signs testing/data-handling expectations. | Certification harness output is reviewed and accepted. |
| Internal canary | Named tenant and approved hosts | Existing MCP beta and per-tool controls | Security, governance, and operations sign-off. | SLOs, audit samples, and no-bypass checks pass. |
| Customer onboarding | Eligible customers | Explicit tenant/host allowlist | Two distinct approved external host submissions complete. | Steady-state support and deprecation process operational. |

## Compatibility and communication

The onboarding pack and lifecycle policy ship before partner testing begins. Changes to certified tool semantics, required fields, authorization, redaction, or error codes follow the published compatibility policy. Support publishes release notes and direct notices to affected certified-host contacts before a deprecation window begins.

## Observability and success criteria

| Signal | Expected range | Alert threshold | Dashboard/runbook |
|---|---|---|---|
| Certification harness outcome | All required synthetic assertions pass. | Any required assertion fails. | `docs/mcp-partner-certification.md` |
| Request-to-ledger correlation | Every harness tool request has a matching tenant-bound ledger entry. | Missing entry or tenant mismatch. | `docs/mcp-tenant-admin-onboarding.md` |
| MCP tool error rate | Existing internal beta target remains below 1% per 15-minute window. | At or above 1%. | `docs/mcp-beta-operations-dashboard.md` |
| Ledger persistence failures | Zero. | Greater than zero. | `docs/mcp-beta-operations-dashboard.md` |
| Tenant boundary violations | Zero. | Greater than zero. | `docs/mcp-internal-canary-runbook.md` |

## Rollback and kill switch

| Trigger | Immediate action | Data remediation | Communication owner |
|---|---|---|---|
| Certification, scope, or tenant-isolation failure | Stop onboarding and disable the affected tenant or tool using existing gateway controls. | Preserve minimized ledger and certification evidence; investigate without requesting secrets. | Security and on-call owner |
| Support correlation failure | Stop new partner preflight approvals. | Restore ledger availability and repeat the dry run. | Operations owner |
| Incompatible host behavior | Keep the host on test tenant; do not widen scopes or enable customer access. | Publish corrective compatibility guidance or update the helper/harness after review. | Product owner |
| Unsafe feedback/domain-pack proposal | Decline or defer intake; do not add generic tool capability. | Record product/security rationale in the feedback decision. | Product and governance owner |

## Release evidence

The release record must include synthetic certification artifact, staging OIDC result, two external-host submissions, tenant-admin walkthrough, support request-ID-to-ledger dry run, dashboard results, security review, domain-pack intake process owner, and final revision.

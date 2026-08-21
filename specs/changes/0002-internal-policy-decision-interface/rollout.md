# Rollout Plan: 0002-internal-policy-decision-interface — Internal Policy Decision Interface

**Status:** Draft
**Release owner:** TBD
**On-call owner:** TBD

## Staged rollout

| Stage | Scope | Entry criteria | Required evidence |
|---|---|---|---|
| Development | Evaluator and policy endpoint behind an internal feature setting. | Contract/design/security review approved. | Unit rules and contract tests. |
| Staging shadow mode | Initial routes evaluate and audit without changing authorization outcome. | Tenant/RBAC fixtures available. | Existing route vs evaluator outcome comparison with all differences reviewed. |
| Staging enforce mode | Asset read/curate, quality update, classification review and certification decision respect policy outcome. | Shadow differences resolved; audit/metrics available. | Route integration, matrix and forced-audit-failure tests. |
| Internal API/UI canary | Named internal tenant and approved operators. | Staging SLO/alert/ledger validation passed. | Sampled decisions agree with UI/API behavior and no tenant leakage. |
| MCP adapter enablement | Approved internal MCP host only. | REST/UI canary stable; parity fixture and security review pass. | Exact REST/private-adapter parity evidence. |

## Migration

This release reuses the existing tenant-scoped `audit_events` table and adds no new persistent entity unless implementation evidence requires a dedicated policy record. An additive API/router/service deployment is safe to roll back by disabling enforcement and retaining historical audit events. If a migration becomes necessary, it must be forward-safe, include tenant/RLS treatment, and be rehearsed separately before enforcement.

## Monitoring and alerts

| Signal | Expected behavior | Alert trigger |
|---|---|---|
| Policy decisions by action/outcome | Visible without tenant/subject/resource labels. | Sudden deny/approval/unavailable anomaly. |
| Policy evaluator latency | Bounded p95 per action. | Sustained p95 above approved budget. |
| Audit write failures | Zero in enforce mode. | Any failure blocks protected mutation and pages owner. |
| Route-policy discrepancies | Zero after shadow approval. | Any new discrepancy blocks progression. |
| Tenant boundary violations | Zero. | Immediate rollback/incident response. |

## Rollback

| Trigger | Immediate action | Recovery condition |
|---|---|---|
| Unauthorized allow, cross-tenant disclosure, or missing audit | Disable policy enforcement and affected route/adapter; preserve correlation evidence. | Security review and corrected matrix regression. |
| Unexpected business denial | Return to shadow mode for affected action; preserve auditable decisions. | Rule/evidence review and product-owner approval. |
| Audit/policy dependency outage | Fail closed for protected complex actions; show correlated safe failure. | Durable audit operation verified. |
| MCP parity discrepancy | Keep MCP adapter disabled; REST/UI remains canonical. | Identical fixture outcome/rule/evidence verification. |

## Exit criteria

The same normalized decision must be observable and semantically consistent through UI/API and private MCP adapter harnesses. No MCP-specific authorization code may grant a result that the REST/UI evaluator denies, obligates or requires human approval. The release evidence must include owner sign-off for tenant security, governance semantics, operations and product behavior.

# Rollout Plan: 0001-mcp-read-only-governed-discovery — MCP Read-Only Governed Discovery

**Status:** Draft
**Release owner:** TBD
**On-call owner:** TBD

## Release strategy

The MCP gateway is introduced behind a disabled-by-default feature flag. Exposure is controlled independently by environment, host/client, tenant, resource and tool. The pilot starts with a synthetic internal tenant, then a named internal tenant with approved test assets, and does not expand to customer canary until all security and observability evidence is complete.

| Stage | Audience | Enablement control | Entry criteria | Exit criteria |
|---|---|---|---|---|
| Local/CI | Engineering | Test config | Contracts and test plan approved. | Unit, contract, tenant-negative and static checks pass. |
| Staging | Internal engineering | Environment + host allowlist | OIDC/resource metadata, private-service routing and dashboards deployed. | End-to-end host discovery and tool test passes. |
| Synthetic canary | Internal synthetic tenant | Tenant + all read tools | Security review and adversarial tests pass. | Audit ledger samples, SLOs and kill switch verified. |
| Internal tenant canary | Named non-customer tenant | Tenant + selected tools | Synthetic canary exit criteria pass. | Product, security, governance and on-call sign-off. |
| Customer beta | Explicitly approved design partners | Per-tenant + per-tool flags | Separate customer readiness review. | Stable evidence across approved hosts/tenants. |

## Migration and compatibility

The gateway owns a new tenant-scoped execution ledger and task-handle persistence model. Migrations must be forward-safe, indexed on tenant/time/tool, and deploy before gateway traffic is enabled. Existing catalog/quality/lineage APIs remain unchanged; the gateway is additive and can be disabled without reversing their data model. MCP schema changes are `0.x` and host-allowlisted through beta.

## Observability and success criteria

| Signal | Expected range | Alert threshold | Dashboard/runbook |
|---|---|---|---|
| `mcp_tool_calls_total` | Visible by tenant/tool/outcome without sensitive labels. | Sudden denial/error anomaly. | MCP operations dashboard. |
| `mcp_tool_duration_seconds` | Published per-tool p95 budget. | Sustained p95 over budget. | MCP latency panel and runbook. |
| `mcp_policy_decisions_total` | All calls produce allowed/denied/obligation result. | Policy errors or unexplained decisions > 0. | Policy decision panel. |
| `mcp_execution_ledger_write_failures_total` | Zero. | Any non-zero in canary. | Audit integrity alert. |
| `mcp_tenant_boundary_violations_total` | Zero. | Any non-zero; immediate kill switch. | Security incident runbook. |
| `mcp_response_truncations_total` | Bounded and explainable. | Unexpected surge. | Product/limit tuning review. |

## Rollback and kill switch

| Trigger | Immediate action | Data remediation | Communication owner |
|---|---|---|---|
| Cross-tenant or unauthorized exposure suspicion | Disable global gateway ingress and affected tenant/tool flag; preserve logs/ledger. | Incident triage, credential/session review, tenant impact analysis. | Security/on-call. |
| Tool audit ledger failure | Disable affected tools; return safe unavailable result. | Restore durable audit path and backfill only from safe correlated records. | Platform/on-call. |
| Policy dependency failure | Fail closed; disable tool if error persists. | Restore policy service and validate decisions before re-enable. | Platform/on-call. |
| Latency/queue exhaustion | Reduce depth/result/quota or disable expensive lineage tool. | Drain/recover tasks; tune capacity after review. | SRE/on-call. |
| Host incompatibility | Remove host from allowlist; preserve evidence. | Correct client contract/consent behavior. | Product/platform. |

## Release evidence

The pilot cannot leave internal staging until required evidence in `evidence.md` is complete. The customer beta is a separate decision that requires stable internal tenant evidence, independent security review, named support/on-call ownership, documented customer data handling, and host onboarding guidance.

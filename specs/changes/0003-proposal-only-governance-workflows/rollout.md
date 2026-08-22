# Rollout: 0003-proposal-only-governance-workflows

## Stages

| Stage | Audience | Enablement | Entry criteria | Exit criteria |
|---|---|---|---|---|
| Local/CI | Engineering | Tests only | Migration, aggregate, and contracts implemented. | Functional, race, tenant, and MCP tool-surface tests pass. |
| Staging inbox | Internal stewards | Proposal API and HTML inbox; MCP proposal tools disabled | Policy/audit/tenant controls deployed. | Stewards can review synthetic proposals and inspect evidence. |
| Internal MCP proposal canary | One approved tenant/host | `governance:propose` scope and three proposal tools only | Inbox, audit, nonce, and recheck tests pass. | Review, reject, approve, and blocked-execution samples accepted by governance/security. |
| Expanded internal beta | Additional internal hosts after review | Explicit host/tenant allowlists | Initial canary has zero bypass, tenant, or audit failures. | Stable success/latency/approval metrics and on-call sign-off. |

## Configuration and migration

Apply the catalog migration before enabling proposal creation. The inbox and REST endpoints are additive. MCP proposal tools remain disabled until the existing internal MCP canary enablement controls, approved host, tenant, OIDC scopes, and service delegation are operational. The database migration is forward-only; rollback is by disabling proposal creation and retaining records for audit rather than deleting proposal history.

## Rollback

| Trigger | Immediate action | Safe state |
|---|---|---|
| Inbox or execution defect | Disable proposal execution endpoint and MCP proposal tools. | Proposals remain visible; no direct writes are enabled. |
| Policy or audit dependency failure | Fail closed and disable creation/review/execution. | Existing pending proposals remain unchanged. |
| Nonce/hash/recheck bypass suspicion | Disable MCP gateway proposal tools and catalog execution route; preserve logs and proposal/audit rows. | Security review before re-enable. |
| Unexpected volume or latency | Keep inbox read-only and throttle/disable proposal creation. | No pending proposal auto-executes. |

## Operational signals

Monitor proposal creations, decisions, executions, blocks, expiry, idempotency replays/conflicts, audit failures, and execution latency with low-cardinality labels by proposal type and outcome. Alert on any audit failure, tenant boundary violation, hash/nonce mismatch anomaly, duplicate execution attempt, or execution after a terminal proposal state.

## Release gate

No model may bypass the inbox. A named data steward must demonstrate review, rejection, approval, and confirmation execution on synthetic proposals. Product, security, governance, and on-call owners must accept a sampled proposal/audit trail and the stale/duplicate/revoked/cancelled negative evidence before internal MCP proposal tools are enabled.

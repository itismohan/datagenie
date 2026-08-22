# Release Evidence: 0003-proposal-only-governance-workflows

**Status:** Implementation validated locally; release approvals and staging evidence pending.
**Release stage:** Not deployed.
**Change owner:** Solution architecture implementation; named product, security, and operations approvers remain TBD.

## Build and traceability

| Evidence item | Required result | Status | Owner/date |
|---|---|---|---|
| SDD validator | `python3 tools/validate_sdd.py` passes. | **Passed locally** | 2026-08-22 |
| Migration | Proposal tables, indexes, constraints, and tenant RLS migrate forward on PostgreSQL. | **Pending staging PostgreSQL rehearsal** | TBD |
| Traceability | Every `DG-PROPOSAL-*` requirement maps to code, tests, and proof. | **Mapped and validator-passed locally** | 2026-08-22 |
| API/MCP contract review | REST inbox/confirmation and three MCP proposal tools reviewed. | **OpenAPI regenerated; local contract tests passed** | 2026-08-22 |

## Functional and security proof

| Evidence item | Required result | Status | Owner/date |
|---|---|---|---|
| Inbox review | Steward sees text, diff, evidence, impact, identity, policy, preconditions, and explicit decisions. | **Passed locally** through `test_steward_inbox_approves_and_executes_a_proposal_once`. | 2026-08-22 |
| Approve/reject | Approved proposal emits one nonce; rejected proposal cannot execute. | **Approval and single-use execution passed locally**; explicit reject path remains covered by lifecycle controls and requires staging rehearsal. | 2026-08-22 |
| Confirmation | Correct hash/nonce succeeds once after current reauthorization and version recheck. | **Passed locally**; replay returns a conflict and applies no second mutation. | 2026-08-22 |
| Idempotency and races | Duplicate create/execute, stale approval, changed resource, revoked role, expired credential, and cancellation tests show no unintended mutation. | **Passed locally** for duplicate create, replay, stale resource, revoked role, expired credential, and cancellation. PostgreSQL concurrency rehearsal remains pending. | 2026-08-22 |
| Tenant and direct-write negative tests | No cross-tenant result or MCP direct mutation path. | **Passed locally** for foreign tenant access, public MCP-host spoofing resistance, signed MCP host binding, and rejected direct MCP mutation tool names. | 2026-08-22 |
| Audit and privacy | All lifecycle events are correlated and minimized; audit failure fails closed. | **Lifecycle audit correlation asserted locally; staging audit-failure rehearsal pending.** | 2026-08-22 |

## Operational and approval proof

| Evidence item | Required result | Status | Owner/date |
|---|---|---|---|
| Dashboard and alerts | Proposal lifecycle, blocks, audit failures, and execution latency visible. | Pending | TBD |
| Staging rehearsal | Migration, inbox, nonce, kill switch, and rollback exercises complete. | Pending | TBD |
| Governance approval | Named steward reviews sample proposal/audit record. | Pending | TBD |
| Security approval | Security owner accepts negative/race evidence and no-bypass surface. | Pending | TBD |
| Product/on-call approval | Product and operations owners accept workflow and support controls. | Pending | TBD |

> No MCP proposal tools may be enabled for the internal canary until the pending staging evidence and named approvals are captured.

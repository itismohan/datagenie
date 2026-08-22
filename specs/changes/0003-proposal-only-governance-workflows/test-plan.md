# Test Plan: 0003-proposal-only-governance-workflows

## Test matrix

| Requirement coverage | Test scenario | Expected proof |
|---|---|---|
| DG-PROPOSAL-001, 004 | Create proposal and render/list steward inbox | Complete diff, evidence, impact, initiator/model/host, policy, versions, expiry, and safe action controls are visible only in tenant. |
| DG-PROPOSAL-002 | Repeat same idempotency key/body | Same proposal is returned; exactly one row exists. |
| DG-PROPOSAL-002 | Reuse idempotency key with changed body | Conflict; no second proposal. |
| DG-PROPOSAL-003 | Denied policy or audit failure during creation | No proposal is persisted. |
| DG-PROPOSAL-005 | Approve then use wrong/expired/replayed nonce or mismatched hash | No execution and terminal/audit state remains safe. |
| DG-PROPOSAL-006 | Approve, then mutate resource technical version | Execution blocks with precondition failure and no proposed write. |
| DG-PROPOSAL-006 | Approve, then revoke approver role or use expired credential | Execution blocks with authorization failure and no proposed write. |
| DG-PROPOSAL-007 | Execute each of the three typed proposal kinds | Only the declared typed effect occurs; no arbitrary payload is honored. |
| DG-PROPOSAL-008 | MCP tools list/call | Exactly the three proposal tools appear; each creates only a proposal and cannot execute or approve. |
| DG-PROPOSAL-009 | Inspect audit events and failure injection | Lifecycle events contain safe correlation/evidence and no token, raw prompt, nonce, or secret; audit fault blocks transitions. |
| DG-PROPOSAL-010 | Concurrent confirmation calls | One mutation and one execution record; remaining caller receives deterministic terminal/replay response. |
| DG-PROPOSAL-010 | Cancelled proposal/job before confirmation | Execution fails safely and creates no mutation/job. |

## Adversarial checks

The suite includes tenant injection, extra diff fields, arbitrary URL/SQL/cron payloads, initiator impersonation, host/model identity override, proposal hash substitution, stale certification state, expired proposal, cancellation race, and MCP direct-write name attempts. Tests use both unit-level service invocation and API-level authenticated requests with SQLite for deterministic concurrency behavior. PostgreSQL integration checks validate the migration and tenant RLS policy separately in CI/staging.

## Exit evidence

The test record must show a steward review response, rejection, approval with nonce issuance, one successful confirmation execution, and every listed negative/race case producing no unintended resource mutation. The MCP contract snapshot must show no direct-write or approval/execute tools.

# Threat Model: 0003-proposal-only-governance-workflows

## Assets and trust boundaries

The protected assets are governed metadata, certification state, quality scheduling intent, tenant boundaries, policy evidence, steward decisions, confirmation nonces, and audit records. MCP hosts and models are untrusted initiators: their declared text, evidence, and requested diff are data, not authority. Catalog API policy evaluation, tenant-scoped database sessions, authenticated human stewards, and the durable audit store are trusted enforcement boundaries.

| Threat | Mitigation | Verification |
|---|---|---|
| Cross-tenant proposal visibility or execution | Tenant-scoped ORM/RLS, no caller-supplied tenant, tenant recheck under transaction lock. | Foreign-tenant proposal lookup and confirmation tests return no result/no mutation. |
| Agent bypasses inbox through direct mutation | MCP advertises only proposal tools; catalog delegated API exposes proposal creation only. | Tool-surface test denies direct mutation tool names and private paths. |
| Prompt injection changes authority or diff | Strict typed diff schemas, `extra=forbid`, canonical hashing, no arbitrary HTTP/SQL/commands. | Malicious extra fields and instruction-like evidence tests are rejected. |
| Approval replay or nonce theft | Random nonce stored only as digest, bound to approver/hash/approval version, short expiry, single use. | Replay, wrong hash, wrong approver, and expired nonce tests produce no mutation. |
| Stale review applies after resource changes | Expected resource versions/status stored at creation and rechecked at execution. | Asset update/certification state change after approval blocks execution. |
| Revoked role or expired credential executes approval | Current authenticated principal and current role are checked at confirmation execution. | Revoked steward and expired token tests block execution. |
| Concurrent confirmations cause duplicate write | Row lock, terminal transition check, transactional execution, idempotent confirmation semantics. | Parallel confirmation test yields one executed proposal and one safe replay/conflict. |
| Cancellation races execution | Cancellation locks proposal and terminal state is checked within executor transaction. | Cancel-before-execute and concurrent cancellation tests prevent write. |
| Audit outage hides governance action | Proposal creation, review, and execution require audit persistence and fail closed. | Audit fault-injection tests produce no lifecycle transition. |
| Sensitive evidence leaks in inbox or audit | Store structured references/safe evidence; sanitize audit metadata; do not store tokens/raw prompts/secrets. | Redaction and ledger/audit inspection tests confirm absence. |

## Residual risk

A legitimate steward can still approve an unsuitable change. The inbox reduces this risk by presenting source identity, structured diff, evidence, policy outcome, impact, and current version preconditions, but governance judgment remains human responsibility. Bulk or high-impact changes remain out of scope for this first workflow.

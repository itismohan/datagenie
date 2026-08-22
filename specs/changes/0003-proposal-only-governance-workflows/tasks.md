# Implementation Tasks: Proposal-Only Governance Workflows

**Change ID:** 0003-proposal-only-governance-workflows

| Order | Work item | Requirement coverage |
|---|---|---|
| 1 | Add proposal enums, aggregate model, indexes, tenant RLS migration, and generated model registry wiring. | DG-PROPOSAL-001, 009, 010 |
| 2 | Add typed proposal schemas, canonical diff hashing, policy snapshot capture, idempotent creation, and safe source identity handling. | DG-PROPOSAL-001, 002, 003, 007 |
| 3 | Build steward inbox list/detail, approve, reject, cancel, confirmation, and transaction-safe execution APIs. | DG-PROPOSAL-004, 005, 006, 009, 010 |
| 4 | Implement the minimal server-rendered inbox and explicit approval/rejection controls. | DG-PROPOSAL-004 |
| 5 | Add signed MCP proposal adapter/client and exactly three proposal-only tools; retain read-only discovery tools and deny all direct writes. | DG-PROPOSAL-008 |
| 6 | Add functional, role, idempotency, stale version, revoked role, expiry, cancellation, concurrency, audit, and MCP surface tests. | DG-PROPOSAL-002 through DG-PROPOSAL-010 |
| 7 | Update OpenAPI, observability, rollout/evidence records, validate SDD, run regression suites, and collect internal approval evidence. | All |

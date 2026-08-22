# Change Proposal: 0003-proposal-only-governance-workflows — Proposal-Only Governance Workflows

**Status:** Implementation validated locally; release approvals pending.
**Owner:** DataGenie platform and governance teams.
**Related changes:** `0001-mcp-read-only-governed-discovery`, `0002-internal-policy-decision-interface`

## Problem

DataGenie can currently provide governed discovery and deterministic policy decisions, but several governance routes still mutate state directly. An AI host, automation, or UI integration must not be able to apply a governance-impacting change merely because it can call a write endpoint. Stewards need a durable, explainable inbox that shows what would change, why it was suggested, what policy decided, and whether the target resource is still the version that was reviewed.

## Proposed outcome

Introduce a generic, tenant-scoped `GovernanceProposal` aggregate. A proposal records a canonical structured diff, source evidence, initiator and MCP host identity, captured policy result, impacted resource version preconditions, immutable proposal hash, expiry, and audit relations. The only MCP mutation-oriented tools will create proposals: `create_governance_proposal`, `request_certification_review`, and `schedule_quality_check`.

A human steward reviews the proposal through an approval inbox, rejects it, or approves it. Approval does not itself mutate the resource. Execution requires a confirmation nonce and exact proposal hash, then re-evaluates the current steward authorization, tenant context, credential validity, policy result, proposal expiry, approval state, cancellation state, and resource-version preconditions in one transaction. Any failed recheck invalidates or safely declines the proposal rather than applying a partial mutation.

## Scope

The first implementation supports three typed changes: metadata curation of a governed asset, certification review request creation, and quality-check scheduling request creation. It exposes JSON REST inbox APIs suitable for the existing DataGenie UI and a minimal server-rendered HTML inbox page for steward review. The page shows proposal text, structured diff, evidence, impact, initiator/model/host identity, policy result, preconditions, and approve/reject controls.

| Included | Explicitly excluded |
|---|---|
| Durable tenant-scoped proposals, approvals, rejections, expiry, cancellation, execution and audit relations | Direct MCP calls that mutate assets, certification decisions, quality rules, connectors, secrets, or arbitrary jobs |
| Idempotent proposal creation and confirmation-bound execution | Autonomous approval, silent execution, or execution based on model-generated free text alone |
| Policy snapshot at creation and re-evaluation at execution | A separate authorization universe for MCP |
| Version checks for affected assets and certification targets | Multi-step bulk execution or customer-facing canary enablement |
| One internal steward inbox page and REST APIs | Replacing all historical direct REST governance endpoints in this bounded change |

## Success criteria

A steward can reliably inspect and decide agent-created change proposals without hidden context. A rejected, expired, stale, duplicated, cancelled, role-revoked, or version-mismatched proposal never changes a governed resource. Every outcome is tenant-scoped and auditable. MCP can create only proposals and cannot bypass the inbox or confirmation protocol.

## Release decision

This change is eligible only for the existing internal MCP beta. Promotion requires the test, evidence, and approval gates defined in `evidence.md`; customer exposure is out of scope.

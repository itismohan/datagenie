# Proposal: 0002-internal-policy-decision-interface — Internal Policy Decision Interface

**Status:** Draft
**Owner:** Data Platform and Governance
**Technical owner:** Solution Architecture
**Target release:** Internal policy foundation
**Related specifications:** `specs/platform/tenant-isolation.md`, `specs/domains/governance-approval.md`, `specs/domains/quality-evidence.md`, `specs/domains/api-compatibility.md`, `specs/changes/0001-mcp-read-only-governed-discovery/`

## Problem

Complex authorization decisions are currently distributed between route-level role dependencies and local ownership checks. This protects simple endpoints but cannot consistently express tenant scope, data classification, lifecycle/certification state, stewardship, quality freshness, declared purpose, rule provenance, obligations, decision expiry, and audit evidence. Building equivalent logic exclusively for the MCP gateway would create a divergent policy universe and introduce authorization shortcuts.

## Desired outcome

DataGenie will expose a single internal synchronous interface:

```text
evaluate_access(subject, tenant, action, resource, purpose, context) -> PolicyDecision
```

The interface evaluates deterministic rules using existing RBAC and governed metadata facts, returns an explainable decision, emits a tenant-scoped audit record, and is called by complex REST paths before they execute a protected action. MCP will call the same interface through its private catalog-policy adapter when it is implemented.

## Scope

| In scope | Out of scope |
|---|---|
| Typed internal contract and deterministic evaluator in the catalog API service. | A new external policy engine, policy language, or customer-configurable rules UI. |
| Decisions: `allow`, `deny`, `allow_with_obligations`, `requires_human_approval`. | Automated approval or mutation of governance/certification state. |
| Rules from validated principal roles/tenant, asset classification, lifecycle/certification, owner/steward assignment, quality freshness, purpose and action. | Replacing every simple role-protected route in this release. |
| A policy decision API for UI/API clients and private service reuse. | An MCP-only or model-driven authorization path. |
| Policy audit events, metric signals, rule/evidence references, expiry and role × tenant × asset × classification × purpose × action tests. | Persisting raw request context, token values, credentials, data rows, or unrestricted prompts. |
| Initial integration with asset read, asset curate, quality evidence update, classification review and certification decision routes. | General availability of write-capable MCP tools. |

## Decision principles

The policy evaluator is a decision layer, not a bypass. Existing tenant isolation remains enforced by the session/RLS boundary, and existing RBAC remains a mandatory rule input. A policy result never expands an actor’s underlying tenant scope or role. A `requires_human_approval` result does not perform the requested action; it states the eligible approver class and evidence required to advance through the pre-existing governance workflow.

## Success measures

| Measure | Exit expectation |
|---|---|
| Contract consistency | UI/API and private MCP adapter receive the same result for the same normalized input and current facts. |
| Tenant isolation | Foreign-tenant resource lookup yields a safe result without resource-existence disclosure. |
| Explainability | All decisions contain stable rule IDs, evidence references, correlation ID and expiry. |
| Auditability | All evaluations produce a tenant-scoped, minimized policy audit event. |
| No shortcuts | Integrated REST paths call the evaluator; tests prove no MCP-specific authorization branch grants access. |

## Dependencies and assumptions

The catalog service is the authoritative initial evaluator because it already has tenant-aware asset, governance, classification, certification and quality summary facts. Quality freshness is derived from `Asset.quality_explainable_at`; detailed quality evidence remains in the quality service and can be attached by a later adapter. Rule configuration is code-owned and versioned in this initial release.

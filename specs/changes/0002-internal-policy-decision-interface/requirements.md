# Requirements: 0002-internal-policy-decision-interface — Internal Policy Decision Interface

**Status:** Draft
**Source proposal:** [proposal.md](proposal.md)

## Requirement: DG-POLICY-001 — Canonical internal contract

The catalog policy service SHALL expose one typed interface, `evaluate_access(subject, tenant, action, resource, purpose, context)`, and return a structured `PolicyDecision`. Callers SHALL not directly evaluate individual policy rules or supply an authoritative tenant value.

| Input | Required interpretation |
|---|---|
| `subject` | Validated principal identity and roles from the authenticated request or trusted service context. |
| `tenant` | Server-derived active tenant; supplied mismatch is denied and auditable. |
| `action` | Stable lower-case dotted capability, such as `asset.read`, `asset.curate`, `quality_evidence.update`, `classification.review`, or `certification.decide`. |
| `resource` | Typed target reference containing resource type and identifier; evaluator resolves tenant-scoped authoritative facts. |
| `purpose` | Bounded declared business purpose; required for governed data access and decision support, optional only for administration actions explicitly configured as purpose-independent. |
| `context` | Bounded supplemental facts, including request ID and optional approved workflow/reference identifiers; cannot override protected resource facts. |

## Requirement: DG-POLICY-002 — Structured and explainable decision

Every evaluation SHALL return `allow`, `deny`, `allow_with_obligations`, or `requires_human_approval`, alongside stable rule IDs, evidence references, obligations, decision timestamp, expiry, decision version and request correlation ID. A decision cannot be represented as authoritative without at least one evaluated rule and evidence reference.

## Requirement: DG-POLICY-003 — Tenant and RBAC non-bypass

The evaluator SHALL derive tenant context from the validated principal/session, preserve ORM/RLS enforcement, and apply existing RBAC as a mandatory baseline. A caller cannot obtain access through purpose, context, ownership or an MCP client identity when RBAC or tenant policy denies it.

### Negative scenario: Foreign tenant resource

Given a tenant A subject requests a tenant B asset, when `evaluate_access` resolves the resource, then it returns a safe deny/not-found-compatible result with the tenant-bound resource reference omitted from the response and records a minimized audit event.

## Requirement: DG-POLICY-004 — Deterministic governed rules

The initial rule set SHALL deterministically evaluate asset classification, lifecycle/certification status, owner/steward assignment, quality freshness, declared purpose and action in addition to RBAC and tenant scope. Rule inputs use current persisted facts and code-owned versioned thresholds; no model inference or unreviewed external data may influence a result.

### Minimum rule behavior

| Condition | Required result |
|---|---|
| Valid role and tenant can read a non-deprecated, non-sensitive asset for a declared purpose. | `allow`. |
| Valid analyst/read-only role requests a restricted classification without a permitted purpose. | `deny`. |
| Valid permitted reader requests sensitive classified asset for an allowed purpose. | `allow_with_obligations`, requiring governed handling acknowledgement and evidence citation. |
| Data owner curates their own active asset. | `allow`. |
| Data owner curates another owner’s asset. | `deny`. |
| Steward or platform administrator curates an active asset. | `allow`. |
| A governance-impacting action needs an existing approval workflow or eligible steward decision. | `requires_human_approval`; the evaluator never executes the approval. |
| Certification-dependent use has stale/missing explainable quality evidence. | `allow_with_obligations` or `requires_human_approval` according to the action rule, never an unexplained authoritative allow. |
| Deprecated asset data use. | `deny`, except approved remediation/administration action rules. |

## Requirement: DG-POLICY-005 — Policy decision audit event

Every evaluation SHALL persist a tenant-scoped, credential-safe policy decision audit event containing subject, roles, action, resource type and safe resource reference, normalized purpose digest/classification, result, rule IDs, evidence references, expiry, decision version, request ID and duration. Raw tokens, raw secrets, raw prompts and unrestricted context are prohibited from audit storage.

## Requirement: DG-POLICY-006 — REST/UI integration

The existing catalog REST API SHALL expose a policy decision endpoint for authorized UI/API clients and progressively route complex guarded operations through the same evaluator. Initial integrated operations are asset read, asset curate, quality-evidence update, classification review and certification decision. Existing route checks remain defense-in-depth and must not grant access when policy denies it.

## Requirement: DG-POLICY-007 — Shared MCP enforcement path

The future MCP gateway SHALL use the catalog policy adapter/contract, with action/purpose/resource inputs mapped to the same `evaluate_access` semantics. It SHALL not introduce independent authorization logic, tenant override rules, or a policy result that is more permissive than REST/UI behavior.

## Requirement: DG-POLICY-008 — Decision matrix proof

Automated tests SHALL cover role × tenant × asset owner/steward × classification × lifecycle/certification × quality freshness × purpose × action combinations sufficient to prove all four decision outcomes, redaction/minimization, expiry, request correlation and the absence of MCP-specific shortcuts.

## Non-functional requirements

| ID | Requirement | Acceptance measure |
|---|---|---|
| DG-POLICY-NFR-001 | Availability | Evaluator failure fails closed for protected actions and emits a correlated safe error. |
| DG-POLICY-NFR-002 | Determinism | Identical normalized inputs and persisted facts yield the same decision/rule set until the explicit expiry. |
| DG-POLICY-NFR-003 | Observability | Metrics expose count, outcome, rule, action and latency without raw sensitive labels. |
| DG-POLICY-NFR-004 | Compatibility | Contract is versioned and additive changes preserve existing policy consumers. |

## Traceability

See [traceability.yaml](traceability.yaml). All implementation, test and release proof must be completed before the policy interface becomes a dependency for MCP access decisions.

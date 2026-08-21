# Contracts: 0002-internal-policy-decision-interface — Internal Policy Decision Interface

**Status:** Draft
**Compatibility owner:** Platform API

## Contract inventory

| ID | Interface | Version | Change type |
|---|---|---|---|
| DG-POLICY-CONTRACT-001 | Typed internal `evaluate_access` service contract | 1.0.0 | Added |
| DG-POLICY-CONTRACT-002 | REST `POST /api/v1/policy/decisions` | 1.0.0 | Added |
| DG-POLICY-CONTRACT-003 | `policy.decision` audit event metadata | 1.0.0 | Added |
| DG-POLICY-CONTRACT-004 | Future private catalog-policy adapter for MCP | 1.0.0 | Added semantic adapter; no MCP transport exposed by this change. |

## Internal request contract

| Field | Type | Validation | Authority |
|---|---|---|---|
| `subject` | `Principal` | Required validated subject/role set. | Security layer only. |
| `tenant` | string | Must equal active principal/session tenant. | Security/session only. |
| `action` | string | Supported explicit capability. | Caller proposes; evaluator validates. |
| `resource` | `PolicyResource` | `resource_type`, `resource_id`; existing resource facts are server-resolved. | Caller identifies; evaluator resolves. |
| `purpose` | string/null | Normalized bounded declaration; action determines whether required. | Caller proposes; evaluator classifies. |
| `context` | `PolicyContext` | Request ID plus allowlisted workflow data; bounded and non-authoritative. | Caller proposes; evaluator validates. |

## Response contract

```json
{
  "outcome": "allow_with_obligations",
  "decision_version": "1.0.0",
  "rule_ids": ["DG-POLICY-RBAC-ALLOW", "DG-POLICY-CLASSIFICATION-OBLIGATION"],
  "evidence": [
    {"type": "tenant", "reference": "active-tenant"},
    {"type": "asset", "reference": "asset:metadata-version:17"},
    {"type": "classification", "reference": "classification:payment_data"}
  ],
  "obligations": ["cite_governance_evidence", "handle_sensitive_data"],
  "expires_at": "2026-08-22T12:00:00Z",
  "request_id": "...",
  "resource_visible": true
}
```

| Outcome | Contract semantics |
|---|---|
| `allow` | Requested action may proceed under existing transaction and RBAC controls. |
| `deny` | Requested action must not proceed. Safe response excludes non-visible resource facts. |
| `allow_with_obligations` | Requested action may proceed only when the calling channel is capable of preserving and surfacing all listed obligations. The route must reject if it cannot satisfy them. |
| `requires_human_approval` | Requested action must not proceed; caller must use the existing governed approval workflow. |

## Initial action vocabulary

| Action | Resource type | Purpose required | Rule families |
|---|---|---|---|
| `asset.read` | `asset` | Yes | Tenant, RBAC, lifecycle, classification, quality. |
| `asset.curate` | `asset` | No | Tenant, RBAC, ownership/stewardship, lifecycle. |
| `quality_evidence.update` | `asset` | No | Tenant, RBAC, stewardship, lifecycle. |
| `classification.review` | `classification_finding` | No | Tenant, RBAC, stewardship, governed asset facts. |
| `certification.decide` | `certification_request` | No | Tenant, RBAC, stewardship, lifecycle, quality freshness, approval workflow. |

## REST API contract

`POST /api/v1/policy/decisions` accepts:

```json
{
  "action": "asset.read",
  "resource": {"resource_type": "asset", "resource_id": "uuid"},
  "purpose": "financial reporting analysis",
  "context": {"workflow_id": "optional-approved-workflow"}
}
```

The endpoint derives subject and tenant from authentication. The request body cannot set roles, subject, tenant, evidence, outcome, decision version or obligations. It returns `200` with a structured decision for evaluated requests, `403` only for caller inability to use the decision interface, and safe validation/correlation errors for malformed input. A non-allow decision is a policy response, not an execution result.

## Audit event contract

Each evaluation emits `AuditEvent(action="policy.decision", resource_type=<target>)` with outcome equal to the policy outcome and the following safe metadata:

| Metadata field | Stored representation |
|---|---|
| `policy_action` | Stable action string. |
| `decision_version` | Semantic policy bundle version. |
| `rule_ids` | Ordered stable rule identifiers. |
| `evidence_references` | Safe typed references only. |
| `obligations` | Stable obligation codes. |
| `expires_at` | UTC ISO timestamp. |
| `purpose_digest` | SHA-256 digest; no raw purpose text. |
| `purpose_category` | Bounded `declared`, `missing`, or `not_required`. |
| `resource_visible` | Boolean. |
| `duration_ms` | Rounded evaluator duration. |

## Compatibility policy

Action additions, optional evidence fields and optional obligations are additive. Changed action semantics, outcome meaning, rule identifier removal/renaming, additional mandatory obligation, response field removal, or audit metadata semantic change requires a versioned SDD change and compatibility review. Future MCP schemas reference this semantic contract rather than replicate it.

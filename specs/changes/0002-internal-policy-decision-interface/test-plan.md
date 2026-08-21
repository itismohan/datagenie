# Test Plan: 0002-internal-policy-decision-interface — Internal Policy Decision Interface

**Status:** Draft
**Quality owner:** TBD

## Requirement coverage

| Requirement | Test scope | Required proof |
|---|---|---|
| DG-POLICY-001 | Unit/contract | One typed entry point accepts only normalized inputs; tenant cannot be caller-overridden. |
| DG-POLICY-002 | Unit/API | Each decision outcome contains decision version, rules, evidence, expiry and request ID. |
| DG-POLICY-003 | Integration/security | Cross-tenant, missing/invalid purpose and unsupported RBAC cases deny without resource disclosure. |
| DG-POLICY-004 | Unit/integration | Deterministic rule matrix covers classification, lifecycle, ownership, stewardship and quality freshness. |
| DG-POLICY-005 | Integration/audit | Every evaluation records minimized safe event; forced audit failure blocks protected mutation. |
| DG-POLICY-006 | API/integration | Initial routes execute policy before action and preserve existing safe error conventions. |
| DG-POLICY-007 | Contract/parity | REST/UI and private adapter fixture inputs produce identical semantic result; no transport-specific allow. |
| DG-POLICY-008 | Matrix/regression | Role × tenant × asset × classification × purpose × action matrix proves each decision state. |

## Core decision matrix

| Role | Tenant/resource | Asset fact | Purpose/action | Expected outcome | Key rule evidence |
|---|---|---|---|---|---|
| Analyst | Same tenant | Active, unclassified, current quality | Declared analysis / `asset.read` | `allow` | RBAC, tenant, lifecycle. |
| Read-only | Same tenant | Payment classified | Missing purpose / `asset.read` | `deny` | Classification/purpose. |
| Analyst | Same tenant | Payment classified | Declared approved analysis / `asset.read` | `allow_with_obligations` | Classification, purpose, handling obligation. |
| Analyst | Foreign tenant | Any | Any / `asset.read` | `deny`, non-visible | Tenant scope. |
| Data owner | Same tenant | Owner matches subject | `asset.curate` | `allow` | Owner assignment. |
| Data owner | Same tenant | Owner differs | `asset.curate` | `deny` | Owner assignment. |
| Data steward | Same tenant | Active asset | `quality_evidence.update` | `allow` | Steward role. |
| Analyst | Same tenant | Deprecated asset | Declared use / `asset.read` | `deny` | Lifecycle. |
| Data steward | Same tenant | Certification candidate with stale quality | `certification.decide` | `requires_human_approval` | Quality freshness, workflow. |
| Platform admin | Same tenant | Payment classified | Declared use / `asset.read` | `allow_with_obligations` | Classification obligation; administrator role does not bypass handling rules. |

## Adversarial and failure tests

| Scenario | Expected result |
|---|---|
| Context includes `tenant_id`, `roles`, `outcome=allow` or fabricated rule/evidence fields. | Ignored/rejected; cannot affect result. |
| Purpose contains token/password-like content. | Decision may validate/deny; audit stores digest/category only and never raw content. |
| Foreign and nonexistent IDs are evaluated. | Protected response details remain indistinguishable; no resource facts leak. |
| Audit transaction fails. | Protected route returns correlated unavailable error and does not mutate state. |
| Rule bundle differs only by code version. | Decision reports exact version and deterministic fixtures change only under reviewed expected update. |
| Private MCP adapter fixture and REST policy endpoint use same principal/resource/facts. | Same outcome, rules, obligations and expiry class. |

## Test locations

| Location | Purpose |
|---|---|
| `apps/catalog-api/tests/test_policy_service.py` | Pure evaluator rules, expiry, evidence and context sanitization. |
| `apps/catalog-api/tests/test_policy_api.py` | Policy endpoint, audit events, cross-tenant safe response and contract fields. |
| `apps/catalog-api/tests/test_policy_route_integration.py` | Asset/governance routes enforce evaluator before effects. |
| `apps/catalog-api/tests/test_policy_matrix.py` | Table-driven role/tenant/asset/classification/purpose/action regression matrix. |
| `apps/catalog-api/tests/test_rbac_audit.py` | Existing RBAC audit regression and owner-curation parity. |

## Completion evidence

Release evidence records CI command outputs, policy matrix report, contract snapshot, audit minimization sample, cross-channel parity fixture, migration result, dashboard/alert verification and owner approvals.

# Release Evidence: 0002-internal-policy-decision-interface — Internal Policy Decision Interface

**Status:** Implementation validated; operational rollout pending
**Release stage:** Development validation complete
**Change owner:** TBD

> This completion record must be updated with immutable run links, command output identifiers, metrics and named approvers before any rollout-stage promotion.

## Build and contract evidence

| Evidence | Required result | Link/identifier | Status |
|---|---|---|---|
| SDD validator | `python3 tools/validate_sdd.py` passes. | Local validation after implementation | Complete |
| Policy contract snapshot | Input/output/action schema reviewed and stable. | `contracts.md`; `tests/test_policy_api.py` | Complete |
| OpenAPI contract export | Policy endpoint appears in generated versioned API contract without unintended drift. | `docs/openapi/catalog-api-v1.json` regenerated locally | Complete |
| Static/dependency checks | No unresolved release-blocking finding. | Pending CI run | Pending |

## Functional and security evidence

| Evidence | Required result | Link/identifier | Status |
|---|---|---|---|
| Deterministic rule suite | All tested facts produce documented outcome/rule/evidence/expiry. | `tests/test_policy_api.py` | Complete |
| Matrix suite | Role × tenant × asset owner/steward × classification × purpose × action cases pass. | `tests/test_policy_matrix.py` — 6 parameterized cases | Complete |
| Tenant-negative cases | Foreign and nonexistent resources do not leak distinguishable protected details. | `tests/test_policy_api.py`; `tests/test_policy_adapter.py` | Complete for current catalog resources |
| Context/purpose minimization | Context cannot override rules; audit output stores no raw purpose/token/secret content. | `tests/test_policy_api.py` | Complete |
| Route enforcement | Integrated routes call policy before effects; obligations/approval outcomes cannot mutate. | `tests/test_policy_route_integration.py` | Complete for initial routes |
| Audit failure safety | Forced policy audit failure blocks protected mutation. | `tests/test_policy_route_integration.py` | Complete |
| REST/adapter parity | Same normalized fixture yields same semantic decision. | `tests/test_policy_adapter.py` | Complete |

## Operational evidence

| Evidence | Required result | Link/identifier | Status |
|---|---|---|---|
| Policy metrics/dashboard | Outcome/action/rule family/latency available without sensitive labels. | Pending | Pending |
| Alerts | Audit failure, policy unavailable, route discrepancy and tenant violation alerts exercised. | Pending | Pending |
| Shadow comparison | All route/evaluator differences reviewed and resolved before enforcement. | Pending | Pending |
| Rollback rehearsal | Per-action enforcement disable and MCP adapter disable exercised. | Pending | Pending |

## Approval record

| Approval | Required owner | Name/date | Outcome |
|---|---|---|---|
| Deterministic rule semantics | Data governance steward | Pending | Pending |
| Tenant/security controls | Security owner | Pending | Pending |
| API contract and compatibility | Platform API owner | Pending | Pending |
| Operational readiness | SRE/on-call owner | Pending | Pending |
| UI/API and adapter parity exit gate | Product owner | Pending | Pending |

## Exceptions and residual risks

| ID | Risk or exception | Approval | Expiry/mitigation |
|---|---|---|---|
| None recorded | Update before release if an exception is requested. | N/A | N/A |

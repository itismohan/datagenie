# Implementation Tasks: Internal Policy Decision Interface

**Change ID:** 0002-internal-policy-decision-interface
**Status:** In progress

| Sequence | Work package | Requirement coverage | Completion criterion |
|---|---|---|---|
| 1 | Add typed policy input, decision, evidence and outcome schemas. | DG-POLICY-001, DG-POLICY-002 | Contract fields and validation tests pass. |
| 2 | Implement deterministic evaluator and stable policy rule bundle. | DG-POLICY-003, DG-POLICY-004 | Table-driven matrix produces documented outcomes/rules. |
| 3 | Add policy audit helper and bounded Prometheus metrics. | DG-POLICY-005 | Every evaluation creates minimized correlated evidence. |
| 4 | Expose decision-support REST endpoint and private adapter. | DG-POLICY-001, DG-POLICY-006, DG-POLICY-007 | Same normalized input receives same semantic decision. |
| 5 | Wire evaluator into initial complex asset/governance routes. | DG-POLICY-006 | Deny/approval outcomes stop effects; allow path preserves workflow. |
| 6 | Add security/regression matrix and verify OpenAPI/SDD evidence. | DG-POLICY-008 | Tenant, context, audit failure and parity tests pass. |
| 7 | Complete evidence, shadow/enforcement review, and named owner approvals. | DG-POLICY-001 through DG-POLICY-008 | Release decision is traceable without hidden context. |

No task in this change may add a write-capable MCP tool, customer-configurable rule language, raw policy context persistence, token forwarding, a tenant override, or a route-specific policy bypass.

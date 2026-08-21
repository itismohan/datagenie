# Implementation Tasks: MCP Read-Only Governed Discovery

**Change ID:** 0001-mcp-read-only-governed-discovery
**Status:** Planned

## Delivery sequence

| Sequence | Work package | Traceability | Completion condition |
|---|---|---|---|
| 1 | Approve proposal, design, contract, threat model and pilot host. | DG-MCP-READ-001 through DG-MCP-READ-009 | Named product, security, governance and operations owners approve the baseline. |
| 2 | Establish the MCP gateway service, TLS/private routing and configuration contract. | DG-MCP-READ-001, DG-MCP-READ-008, DG-MCP-READ-009 | Gateway advertises only the approved five read-only tools and safe discovery metadata. |
| 3 | Implement OAuth/OIDC MCP audience validation, tenant binding, host allowlist and policy integration. | DG-MCP-READ-001, DG-MCP-READ-006 | Valid identity/policy matrix and cross-tenant negative tests pass. |
| 4 | Implement governed search and asset-context adapters plus response redaction. | DG-MCP-READ-002, DG-MCP-READ-003 | Bounded evidence-bearing results contain neither raw data nor secrets. |
| 5 | Implement quality evidence and bounded/asynchronous lineage adapters. | DG-MCP-READ-004, DG-MCP-READ-005, DG-MCP-READ-008 | Quality state semantics and lineage task ownership tests pass. |
| 6 | Implement the minimized agent execution ledger, metrics, dashboards, alerts and kill controls. | DG-MCP-READ-007, DG-MCP-READ-008 | Every request is correlated/audited and operational controls are rehearsed. |
| 7 | Complete approved-host compatibility, adversarial/security, migration and canary evidence. | DG-MCP-READ-001 through DG-MCP-READ-009 | `evidence.md` is completed and reviewers can trace every requirement to proof. |

## Explicit guardrail

No task may add a write-capable tool, generic SQL/HTTP tool, raw data retrieval, source credential access, export, governance approval, certification action, ingestion operation or quality scheduling action. Such a change requires a separately approved SDD change.

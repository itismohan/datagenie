# Test Plan: 0001-mcp-read-only-governed-discovery — MCP Read-Only Governed Discovery

**Status:** Draft
**Quality owner:** TBD

## Requirement coverage matrix

| Requirement ID | Test level | Scenario | Test location | Required outcome |
|---|---|---|---|---|
| DG-MCP-READ-001 | Integration/security | Valid, missing, foreign-tenant, expired, wrong-audience and wrong-scope token matrix. | `apps/mcp-gateway/tests/test_identity.py` | Gateway derives tenant only from validated token and safely denies invalid identity. |
| DG-MCP-READ-002 | Contract/integration | Filtered search with tenant-visible assets, facets, ranking, purpose and bounds. | `apps/mcp-gateway/tests/test_governed_search.py` | No hidden/cross-tenant asset; result evidence is complete. |
| DG-MCP-READ-003 | Contract/integration | Asset context with classifications, columns and restricted fields. | `apps/mcp-gateway/tests/test_asset_context.py` | Redaction and no raw data/secret exposure. |
| DG-MCP-READ-004 | Integration | Recent, stale, failed and low-quality quality-evidence cases. | `apps/mcp-gateway/tests/test_quality_evidence.py` | Explanation distinguishes quality states correctly. |
| DG-MCP-READ-005 | Integration/performance | Typed lineage traversal, depth/result limit and async fallback. | `apps/mcp-gateway/tests/test_lineage_impact.py` | Provenance/confidence preserved; work stays bounded. |
| DG-MCP-READ-006 | Integration/security | Asset and purpose policy decision with allow, deny, obligations, stale evidence and tenant-negative cases. | `apps/mcp-gateway/tests/test_data_use_policy.py` | The decision is explainable, fails closed and has no mutation side effect. |
| DG-MCP-READ-007 | Integration/audit | Tool invocation and denied call ledger records. | `apps/mcp-gateway/tests/test_execution_ledger.py` | Tenant-bound correlation/evidence without raw sensitive content. |
| DG-MCP-READ-008 | Resilience | Timeout, rate limit, cancellation, downstream failure and task-handle ownership. | `apps/mcp-gateway/tests/test_resilience.py` | Safe bounded response and recoverable task semantics. |
| DG-MCP-READ-009 | Security | Mutation/SQL/HTTP/secret tool enumeration and invocation attempts. | `apps/mcp-gateway/tests/test_read_only_surface.py` | No prohibited tool exists or can be invoked. |

## Mandatory validation categories

| Category | Minimum proof |
|---|---|
| MCP interoperability | The approved internal host initializes, discovers capabilities, authorizes, calls each tool, reads each resource and renders structured errors. |
| Tenant-negative | For each resource/tool/task, caller A cannot retrieve, infer, poll, cancel or cache caller B’s data. |
| Authorization/policy | Scope × role × purpose × classification matrix includes allow, deny and obligation outcomes, and proves that policy-check calls do not persist an approval. |
| Contract | JSON schema validates input/output; contract snapshots detect breaking changes. |
| Prompt injection | Malicious asset description/glossary/lineage values cannot alter tool policy, request external access or trigger unapproved calls. |
| SSRF/egress | Metadata/discovery URLs reject private, link-local, non-HTTPS production and unsafe redirect targets. |
| Performance | Define p95 latency and result/depth quotas per tool; test overload/rate limit behavior. |
| Operational recovery | Downstream errors, task timeout, cancellation, worker loss and kill switch are verified with auditable outcomes. |

## Test data and environment

Use synthetic tenant A and tenant B metadata/quality/lineage fixtures with distinctive identifiers, classifications and ownership. Use only secret placeholders and mock/approved OIDC/JWKS endpoints. The integration environment must use PostgreSQL tenant enforcement and must never use customer production data.

## Acceptance evidence

Before beta, record exact test commands/CI evidence, OpenAPI/MCP schema validation, host compatibility result, security review, sampled ledger review, alert/dashboard checks, latency/error figures and tenant-owner sign-off in `evidence.md`.

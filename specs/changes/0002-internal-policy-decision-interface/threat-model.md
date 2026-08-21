# Threat Model: 0002-internal-policy-decision-interface — Internal Policy Decision Interface

**Status:** Draft
**Security owner:** TBD
**Related design:** [design.md](design.md)

## Trust boundaries

The evaluator sits after bearer-token validation and before governed action execution. It receives trusted identity and tenant context from `Principal`/session state, untrusted action/resource/purpose/context values from REST/UI callers, and tenant-scoped persisted metadata through the ORM/RLS boundary. The future MCP adapter is an untrusted transport boundary that must translate into the same trusted policy inputs, not a separate authorization authority.

## Protected assets

| Asset | Protection requirement |
|---|---|
| Cross-tenant metadata and existence information | Tenant-resolved lookups, `resource_visible=false` safe result, RLS and tenant-negative tests. |
| Governance mutation rights | Existing RBAC plus policy rule evaluation before mutation; obligations/approval cannot be interpreted as allow. |
| Sensitive classification, owner/steward and quality facts | Only structured safe evidence references/derived values in output and audit. |
| Policy audit integrity | Evaluation/audit is in the protected transaction path; audit failure fails closed for protected actions. |
| Tokens, secrets and raw context | Never put in decision, evidence, metric labels or audit metadata. |

## Threats and mitigations

| Threat | Attack path | Mitigation | Required test |
|---|---|---|---|
| Tenant override | Caller sends a foreign tenant in policy request/context. | Derive active tenant from authenticated principal/session; deny mismatch; never query by caller tenant. | Tenant A cannot evaluate/retrieve tenant B asset. |
| Role bypass | Caller asserts role/action eligibility in context or uses an MCP identity shortcut. | Ignore caller authority claims; use validated `Principal`; preserve RBAC baseline. | Context/MCP claims cannot turn a deny into allow. |
| Resource existence oracle | Caller probes foreign IDs and compares policy response details. | Safe non-visible result with no factual evidence or resource attributes. | Foreign/nonexistent responses are indistinguishable in protected fields. |
| Context injection | Caller puts instructions, rule identifiers or protected facts in `context`. | Strict schema/allowlist; context cannot override resource facts/rules; store digest/classification only. | Malicious context yields validation deny or unchanged decision. |
| Prompt leakage through purpose | User places secrets/data in declared purpose. | Length/character bounds, digest/classification storage only, audit sanitization. | Audit has no raw purpose or credential-like values. |
| Stale quality allow | Missing/stale quality fact is treated as a valid certification decision. | Rule explicitly produces obligation/approval outcome, never authoritative allow. | Missing/stale test matrix. |
| Approval semantic bypass | Route treats `requires_human_approval` as permission. | Route adapter maps it to safe non-success response and preserves workflow. | Mutation not executed for approval outcome. |
| Audit evasion | Evaluation succeeds without durable decision record. | Persist event before action; fail closed when audit persistence fails. | Forced audit failure causes no mutation. |
| Rule drift across channels | MCP duplicates/changes policy logic. | One service/contract; cross-channel parity fixtures and contract version. | UI/API and adapter return identical decision. |

## Security acceptance criteria

The evaluator cannot be released to an MCP consumer until cross-tenant, wrong-role, context injection, stale-quality, classification-purpose, human-approval, audit-minimization and REST/MCP parity tests pass. An incident involving tenant disclosure, permissive context override or missing decision audit event is a release-blocking failure.

# Proposal: 0001-mcp-read-only-governed-discovery — MCP Read-Only Governed Discovery

**Status:** Draft
**Owner:** Product and Data Platform
**Technical owner:** Solution Architecture
**Target release:** Internal MCP beta
**Related domain specifications:** `specs/platform/tenant-isolation.md`, `specs/domains/governance-approval.md`, `specs/domains/quality-evidence.md`, `specs/platform/api-compatibility.md`

## Problem and opportunity

Enterprise AI hosts and agents need governed data context, but direct database tools and generic catalog integrations cannot reliably answer whether a result belongs to the requesting tenant, whether it is certified and current, what quality evidence supports it, what downstream impact exists, or why it may be used. DataGenie already holds these controls in separate domain services but does not expose a focused, standards-based agent interface.

## Desired outcome

An authorized internal AI host can use a tenant-scoped MCP endpoint to search governed assets, retrieve governed asset context, retrieve explainable quality evidence, analyze lineage impact, and check applicable data-use policy. Each response is bounded and contains structured provenance/policy context suitable for an AI assistant without exposing raw data, secrets, cross-tenant metadata, or governance mutation capability.

Success is measured by correct tenant filtering, evidence completeness, tool reliability, and reviewer ability to trace every tool call to actor, tenant, policy decision, evidence version, and request correlation.

## Scope

| In scope | Out of scope |
|---|---|
| A standalone MCP gateway deployed behind the existing TLS boundary. | Exposing all REST endpoints as MCP tools. |
| OAuth/OIDC tenant binding, audience/scope validation, tool audit ledger and rate limits. | Generic SQL execution, raw table data retrieval, arbitrary HTTP, secret access or direct metadata changes. |
| Read-only `search_governed_assets`, `get_asset_context`, `get_quality_evidence`, `analyze_lineage_impact`, and `check_data_use_policy` tools. | Governance approval, certification decision, ingestion submission, quality scheduling, export and webhook write tools. |
| Evidence-bearing responses with classification-aware redaction and result/depth limits. | Replacing the existing REST API, UI, workers, quality engine or lineage service. |
| Resources and prompts that guide safe discovery. | Customer-wide general availability or multi-host certification. |

## Affected surfaces

| Surface | Change type | Contract or specification impact |
|---|---|---|
| Agent integration | Added | Versioned MCP resource/prompt/tool schemas and client onboarding guidance. |
| Identity/policy | Added | MCP audience, scopes, tenant propagation, policy decision and audit contract. |
| Catalog, quality and lineage services | Reused | Private service calls remain the domain source of truth; no direct database access. |
| Operations | Added | Tool metrics, latency/error SLOs, per-tenant kill switch and incident runbook. |

## Stakeholders and approval

| Role | Named owner | Required decision |
|---|---|---|
| Product owner | TBD | Internal beta problem, outcome and pilot audience. |
| Solution architect | TBD | Gateway boundaries and contract design. |
| Security owner | TBD | OAuth/OIDC, threat model, egress and consent controls. |
| Data governance steward | TBD | Evidence semantics and redaction expectations. |
| SRE/on-call owner | TBD | Deployment, SLOs, alerts and kill switch. |

## Assumptions, dependencies, and open questions

| Type | Item | Owner | Resolution required by |
|---|---|---|---|
| Assumption | Existing catalog/OIDC tenant controls can be reused through private service calls. | Platform | Design approval |
| Dependency | Equivalent tenant-bound contracts for quality and lineage must be proven before those tools are enabled. | Data platform | Before canary |
| Open question | Which internal AI host is the first supported MCP client and what confirmation/consent UX does it provide? | Product/Security | Before implementation |
| Open question | Which OAuth provider will issue MCP audience-scoped tokens and protected-resource metadata? | Identity | Before implementation |

## Decision record

This proposal is intentionally read-only. No governance or operational mutation will be added until the pilot produces traceable tenancy, policy, audit, evidence and reliability results and a separate proposal is approved.

# Requirements: 0001-mcp-read-only-governed-discovery — MCP Read-Only Governed Discovery

**Status:** Draft
**Source proposal:** [proposal.md](proposal.md)
**Domain specifications:** `specs/platform/tenant-isolation.md`, `specs/domains/governance-approval.md`, `specs/domains/quality-evidence.md`, `specs/platform/api-compatibility.md`

## User story: Governed agent discovery

As an authorized analyst using an approved AI host, I want to discover data assets and understand their quality, lineage, certification and policy context so that I can make a safe data-use decision without manually joining several services.

### Requirement: DG-MCP-READ-001 — Tenant-bound MCP identity

The MCP gateway SHALL validate the caller’s OAuth/OIDC bearer token, require an MCP-specific audience and configured tenant claim, derive the active tenant server-side, and apply that identity to every resource, prompt, tool, downstream request, durable audit record and cache key.

##### Acceptance scenario: Valid tenant-scoped call

- **GIVEN** an approved host presents a valid token issued for the DataGenie MCP audience with `catalog:read`
- **WHEN** it invokes `search_governed_assets`
- **THEN** the gateway calls downstream services only with a trusted tenant-bound actor context
- **AND** the response and audit event contain the same tenant and correlation identity.

##### Negative scenario: Cross-tenant parameter attempt

- **GIVEN** a caller is authorized for tenant A
- **WHEN** it includes tenant B in a tool input, resource URI, state handle or cached request key
- **THEN** tenant B is ignored/rejected and no tenant B identity, asset or existence information is disclosed.

### Requirement: DG-MCP-READ-002 — Governed asset discovery

The gateway SHALL expose `search_governed_assets` as a read-only tool supporting bounded governed filters and returning only tenant-visible, authorization-permitted results with certification, owner/domain, classification, quality freshness, index freshness and transparent ranking/evidence fields.

##### Acceptance scenario: Evidence-bearing search

- **GIVEN** a permitted analyst declares an allowed business purpose and governed search filters
- **WHEN** the tool searches the active tenant index
- **THEN** it returns a bounded structured result set, result facets and index freshness
- **AND** it explains applicable policy obligations and result provenance.

### Requirement: DG-MCP-READ-003 — Asset context without raw data exposure

The gateway SHALL expose `get_asset_context` as a read-only tool/resource that returns governed technical metadata, column contracts, glossary mappings, stewardship, classification, certification and metadata version evidence, applying role/classification redaction and never returning raw source credential values or row-level samples.

### Requirement: DG-MCP-READ-004 — Explainable quality evidence

The gateway SHALL expose `get_quality_evidence` as a read-only tool/resource that returns recent quality runs, rule versions, thresholds, result evidence, incident state and freshness. It SHALL distinguish missing/stale/failed checks from low-quality results and SHALL NOT represent unexplained scores as authoritative.

### Requirement: DG-MCP-READ-005 — Lineage impact evidence

The gateway SHALL expose `analyze_lineage_impact` as a bounded read-only tool that returns typed upstream/downstream impact with provenance, confidence, timestamps, depth/result limits and owner/consumer context subject to tenant and authorization policy.

### Requirement: DG-MCP-READ-006 — Data-use policy check

The gateway SHALL expose `check_data_use_policy` as a read-only tool that evaluates a caller-declared use purpose against the tenant-bound asset, classification, certification, ownership, retention and governance policy context. It SHALL return an explainable `allow`, `deny`, or `allow_with_obligations` result with rule/evidence references and SHALL NOT create or alter a governance approval, certification, retention setting, export, or consent record.

##### Acceptance scenario: Policy decision with obligations

- **GIVEN** a permitted analyst identifies an asset and a declared business purpose
- **WHEN** the tool evaluates applicable policy
- **THEN** it returns a decision, policy/rule references, classification, evidence freshness and applicable obligations
- **AND** it writes an audit-safe decision packet bound to the active tenant and caller.

##### Negative scenario: Policy decision cannot be proven

- **GIVEN** policy evidence is unavailable, stale beyond a configured safety limit, or belongs to a different tenant
- **WHEN** a caller requests a policy check
- **THEN** the gateway fails closed with a correlated safe response and does not imply that use is approved.

### Requirement: DG-MCP-READ-007 — Evidence, policy and audit packet

Every tool result SHALL contain structured request correlation, tool version, response timestamp, evidence/provenance references, policy decision or obligations where applicable, and redaction indicators. Every invocation SHALL create a tenant-scoped agent execution ledger entry containing host/client identity, caller identity, tool/input digest, result classification/size, policy result, outcome, duration and correlation ID without persisting unrestricted raw content.

### Requirement: DG-MCP-READ-008 — Bounded and recoverable operation

Every tool SHALL have documented input schema, output schema, explicit authorization/scope requirement, result/depth limit, timeout, rate/quota behavior, safe error model and cancellation behavior. Expensive lineage operations SHALL return a durable task handle/status resource rather than block the host beyond the defined synchronous budget.

### Requirement: DG-MCP-READ-009 — Read-only safety guarantee

The initial MCP release SHALL not expose tools capable of creating, approving, mutating, exporting, scheduling, ingesting, delivering webhooks, resolving secrets or executing arbitrary SQL/HTTP. Attempts to invoke unavailable or unauthorized actions SHALL return correlated, safe denial responses and audit evidence.

## Non-functional requirements

| ID | Requirement | Acceptance measure |
|---|---|---|
| DG-MCP-NFR-001 | Security and tenancy | Cross-tenant, stale-token, wrong-audience, wrong-scope and state-handle negative tests pass for each tool/resource. |
| DG-MCP-NFR-002 | Reliability | Tool timeouts, policy errors and downstream errors return bounded correlated results; no request process executes unbounded graph work. |
| DG-MCP-NFR-003 | Observability | Tool-call, denial, latency, result-size, policy-decision and error metrics/dashboard/alerts are available per tenant/tool without sensitive labels. |
| DG-MCP-NFR-004 | Compatibility | MCP capability/schema changes are versioned and documented; host interoperability tests run against the approved client. |
| DG-MCP-NFR-005 | Privacy | Classification/redaction tests prove no raw row data, source secret, hidden asset or unauthorized evidence is returned. |

## Explicit non-goals

The pilot SHALL NOT perform governance changes, certification decisions, ownership assignments, source registration, ingestion, quality scheduling, data export, webhook creation, direct SQL, generic HTTP execution, secret resolution, model-hosted conversational memory or customer GA onboarding.

## Requirement traceability

See [traceability.yaml](traceability.yaml). Every requirement must map to source, tests, contracts and release evidence before the pilot can move beyond an internal canary.

# Contracts: 0001-mcp-read-only-governed-discovery — MCP Read-Only Governed Discovery

**Status:** Draft
**Compatibility owner:** Platform API

## Contract inventory

| ID | Interface | Artifact path | Version | Change class | Consumer impact |
|---|---|---|---|---|---|
| DG-MCP-CONTRACT-001 | MCP server capability contract | `contracts/mcp-governed-discovery.schema.json` | `0.1.0` | Added | Approved internal host only. |
| DG-MCP-CONTRACT-002 | OAuth/OIDC protected resource | Gateway well-known metadata | `0.1.0` | Added | Host obtains MCP-specific audience/scopes. |
| DG-MCP-CONTRACT-003 | Agent execution audit event | `contracts/agent-execution-event.schema.json` | `0.1.0` | Added | Internal audit/observability consumers. |

## MCP tool contract

### `search_governed_assets`

| Concern | Contract |
|---|---|
| Input | `query`, optional governed filters (`business_term`, `owner`, `domain`, `tag`, `classification`, `quality_min`, `freshness`, `certification_status`, `source`), `purpose`, `limit` (1–50). |
| Output | Asset summaries, facets, index freshness, transparent ranking fields, policy obligations, provenance and correlation envelope. |
| Authorization | `catalog:read`; tenant from token; policy check for visible assets and purpose. |
| Side effect | None. |
| Bounds | Max 50 assets; bounded facet cardinality; request timeout/rate limit. |

### `get_asset_context`

| Concern | Contract |
|---|---|
| Input | `asset_id`, optional bounded `include` set, `purpose`. |
| Output | Governed metadata, column contracts, glossary and stewardship links, classification/certification/version evidence, redaction indicators. |
| Authorization | `catalog:read`; asset/purpose policy check. |
| Side effect | None. |
| Bounds | One asset; no row samples, source secrets or unrestricted historical payloads. |

### `get_quality_evidence`

| Concern | Contract |
|---|---|
| Input | `asset_id`, optional bounded history count and `purpose`. |
| Output | Recent explainable runs, rule versions/thresholds, incident state, freshness and evidence references. |
| Authorization | `quality:read`; asset/purpose policy check. |
| Side effect | None. |
| Bounds | Bounded run/incident history; sensitive evidence redacted. |

### `analyze_lineage_impact`

| Concern | Contract |
|---|---|
| Input | `asset_id`, `direction`, `depth` (1–3 for synchronous request), optional impact mode and `purpose`. |
| Output | Typed graph/impact summary, provenance, confidence, timestamps, owner/consumer context, truncation/task handle if needed. |
| Authorization | `lineage:read`; asset/purpose policy check. |
| Side effect | None. |
| Bounds | Node/edge count and depth limits; durable task for greater work. |

### `check_data_use_policy`

| Concern | Contract |
|---|---|
| Input | `asset_id`, declared `purpose`, optional bounded `intended_consumers` and `retention_window`. |
| Output | `allow`, `deny`, or `allow_with_obligations`; evaluated rule IDs, evidence references/freshness, classification, certification, retention and redaction indicators. |
| Authorization | `policy:read`; tenant from token; asset/purpose policy check. |
| Side effect | None; no governance approval, consent, retention, export or certification mutation. |
| Bounds | One asset and one declared purpose; policy decision expires at documented evidence/policy TTL. |

## Resources and prompts

| Primitive | Identifier | Contract |
|---|---|---|
| Resource | `datagenie://catalog/assets/{asset_id}` | Principal-specific governed asset context; never shared-cache across tenants. |
| Resource | `datagenie://quality/assets/{asset_id}/latest` | Latest explainable quality evidence with freshness state. |
| Resource | `datagenie://lineage/assets/{asset_id}` | Bounded typed lineage summary. |
| Prompt | `assess_data_for_use` | Requires asset/business intent and purpose; produces evidence-cited decision support, no mutation. |
| Prompt | `explain_lineage_impact` | Requires asset and analysis goal; produces a provenance/confidence-aware narrative. |

## Common response and errors

Every successful result includes `request_id`, `tool_version`, `tenant_bound: true`, `generated_at`, `policy`, `evidence`, and explicit `redactions`/`truncated` fields where relevant. Errors use stable code, safe message and request ID.

| Code | Meaning | Client behavior |
|---|---|---|
| `mcp_unauthorized` | Token missing/invalid/wrong audience. | Reauthorize for the MCP resource. |
| `mcp_forbidden` | Scope, role, tenant or policy denied action. | Do not retry without a changed authorization/purpose. |
| `policy_unavailable` | Safe policy decision cannot be made. | Treat as deny; retry later. |
| `result_limit_exceeded` | Query/graph requested more than policy permits. | Narrow filters/depth or poll durable task if offered. |
| `downstream_unavailable` | Catalog/quality/lineage/policy dependency unavailable. | Bounded retry; retain request ID. |
| `tool_disabled` | Tenant/host/tool kill switch active. | Contact administrator; no fallback execution. |

## Compatibility and deprecation plan

The pilot uses a `0.x` MCP contract restricted to approved internal hosts. Additive optional fields/tools may be introduced after contract review. Input/output semantic changes, changed authorization, altered redaction, removal or rename require a new version and host compatibility validation. A customer-facing stable contract is not declared until the canary exit gate is met.

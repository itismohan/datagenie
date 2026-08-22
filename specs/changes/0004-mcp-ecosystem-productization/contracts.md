# Contracts: 0004-mcp-ecosystem-productization — MCP Ecosystem Productization

## Published artifacts

| Artifact | Path | Audience | Compatibility commitment |
|---|---|---|---|
| Tenant-admin onboarding pack | `docs/mcp-tenant-admin-onboarding.md` | Tenant administrators and security reviewers | Operational guidance versioned with MCP release notes. |
| MCP lifecycle policy | `docs/mcp-versioning-and-deprecation-policy.md` | Hosts, partners, support, and product | Defines compatibility and retirement rules for certified contracts. |
| Partner certification guide | `docs/mcp-partner-certification.md` | Host implementers and certification reviewers | Documents synthetic preflight and external certification evidence. |
| Domain-pack intake policy | `docs/mcp-domain-pack-governance.md` | Product, governance, security, and customers | Requires approved feedback and an SDD change before delivery. |
| Python helper | `clients/python/datagenie_mcp.py` | Python enterprise hosts | Optional standard Streamable HTTP JSON-RPC helper. |
| TypeScript helper | `clients/typescript/src/index.ts` | TypeScript enterprise hosts | Optional standard Streamable HTTP JSON-RPC helper. |
| Certification artifact | `docs/evidence/mcp-partner-certification-synthetic.json` | Reviewers and support | Sanitized synthetic preflight result; not partner certification. |

## Scope matrix

| Scope | Permitted tools | Administrator guidance |
|---|---|---|
| `catalog:read` | `search_governed_assets`, `get_asset_context` | Request only for discovery needs. |
| `quality:read` | `get_quality_evidence` | Request only when explainable quality evidence is required. |
| `lineage:read` | `analyze_lineage_impact` | Request only for bounded impact analysis. |
| `governance:propose` | `create_governance_proposal`, `request_certification_review`, `schedule_quality_check` | Proposal creation only; a human steward approves and confirms execution outside MCP. |

A host must request only the scopes required for its enabled functions. No scope permits direct certification, proposal approval, proposal execution, asset update, arbitrary query, secret retrieval, or quality-job dispatch through MCP.

## Helper request contract

Both helpers issue an ordinary Streamable HTTP JSON-RPC request:

```json
{
  "jsonrpc": "2.0",
  "id": "caller-generated-request-id",
  "method": "tools/call",
  "params": {
    "name": "get_asset_context",
    "arguments": {"asset_id": "asset-123", "purpose": "financial reporting analysis"}
  }
}
```

The caller supplies the endpoint, `Authorization: Bearer <token>`, `Mcp-Client-Id`, `MCP-Protocol-Version`, and `X-Request-ID`. Helpers may generate a JSON-RPC ID but must preserve the caller’s request ID. Responses remain the standard gateway JSON-RPC envelope; helpers do not normalize or hide `structuredContent`.

## Certification artifact contract

```json
{
  "certification_level": "synthetic_preflight",
  "generated_at": "RFC3339 timestamp",
  "profiles": ["generic-streamable-http", "enterprise-governed-host"],
  "assertions": {"all_required_checks_passed": true},
  "correlation": {"request_id": "synthetic identifier", "ledger_entry_found": true},
  "limitations": ["No live OIDC or external customer-host validation"]
}
```

The artifact must not include bearer tokens, OAuth client secrets, raw request purposes, raw tool results, source secrets, production hostnames, or customer tenant identifiers.

## Compatibility and deprecation rules

The MCP gateway advertises a negotiated protocol version and returns a `tool_version` in structured successful results. Additive optional result fields and new separately scoped tools are non-breaking only when existing tool semantics, authorization behavior, redaction, bounds, error codes, and required input fields remain unchanged. Removing or renaming a tool, making an optional input required, narrowing previously permitted access, changing result semantics/redaction, or changing a stable error code is breaking.

Breaking changes require a new documented contract major or a compatibility path with migration guidance. Deprecations require a published replacement, an announced retirement date, release-note entry, and usage review with certified hosts before removal. The internal-beta default deprecation notice is at least 90 days; a shorter period requires an approved time-bound security exception and direct notice to affected approved hosts.

## Domain-pack intake contract

A request is eligible for triage only when it has customer approval to use the feedback, a defined domain owner, business outcome, evidence/decision need, affected scope, risk assessment, and support contact. Product publishes the decision to accept, defer, decline, or request evidence. Accepted requests create an SDD change and cannot add a generic tool without a security and governance review.

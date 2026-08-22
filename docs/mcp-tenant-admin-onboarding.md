# DataGenie MCP Tenant-Admin Onboarding Pack

This pack is for a tenant administrator who is enabling an **approved enterprise MCP host** for the DataGenie internal beta. It is intentionally a configuration and verification guide, not an automatic enablement process. Customer onboarding remains disabled until the product release gate is approved.

> **Safety rule:** A host may discover governed metadata and create steward-reviewable proposals. It cannot use MCP to certify an asset, approve or execute a proposal, update metadata directly, dispatch a quality job, access source secrets, or bypass tenant policy.

## 1. Eligibility and preflight

Before registration, identify the tenant, named host product and operator, business owner, security contact, support contact, intended MCP tools, and a dedicated non-production test tenant. Obtain written approval for the host to process the specified metadata categories and evidence references. Do not use a production tenant, production bearer token, source credential, row data, or a personal account during onboarding.

| Required input | Minimum acceptable value | Why it matters |
|---|---|---|
| Tenant identifier | A named test tenant approved for MCP beta use | The gateway binds every call and ledger entry to the token tenant. |
| Host identifier | Stable, approved, non-secret host/client ID | The gateway host allowlist prevents unreviewed clients from connecting. |
| Owner and support contact | Named business owner and operational contact | Required for deprecation notices, incidents, and certification review. |
| Intended tools | Exact discovery and/or proposal-intent tool list | Enables least-privilege scope selection. |
| Data-handling approval | Allowed metadata classifications, logging policy, retention, and export controls | Governs what the host may receive and retain. |
| Test plan | Synthetic test asset and expected request-ID evidence | Supports safe onboarding and troubleshooting. |

## 2. OAuth application registration

Register an OAuth/OIDC application with the organization’s approved authorization server. Configure DataGenie MCP as a distinct protected resource audience, rather than reusing a broad catalog API token. The exact issuer, client authentication method, redirect URI, and consent policy are owned by the organization’s authorization-server administrator.

| Registration field | Required configuration |
|---|---|
| Resource audience | `datagenie-mcp` unless the deployed gateway publishes a different required audience. |
| Tenant claim | The configured tenant claim must contain the approved test tenant ID. Hosts must not send tenant overrides in tool arguments. |
| Role claim | Use only DataGenie roles assigned by the tenant administrator; do not trust host-supplied role text. |
| Scope claim | Use the scope matrix below. Request the smallest set required by enabled features. |
| Client/host identity | Configure the approved host ID supplied as `Mcp-Client-Id`; keep it stable for audit and allowlist review. |
| Token lifetime | Use the organization’s short-lived access-token standard. The host must renew tokens normally; it must not cache expired credentials. |
| Redirect/origin controls | Register only approved HTTPS redirect/origin values when the host type uses them. |

The tenant administrator provides the following deployment values through approved configuration management, never source code or a shared chat message:

```text
DATAGENIE_MCP_RESOURCE_URL=https://<approved-gateway>/mcp
DATAGENIE_MCP_HOST_ID=<approved-host-id>
DATAGENIE_TEST_TENANT_ID=<approved-test-tenant>
```

## 3. Scope matrix and governance boundary

| Scope | Tool surface | Typical use | Explicitly not authorized |
|---|---|---|---|
| `catalog:read` | `search_governed_assets`, `get_asset_context` | Governed discovery and contextual metadata. | Raw rows, source credentials, tenant override, direct metadata update. |
| `quality:read` | `get_quality_evidence` | Explainable quality, incidents, freshness, and evidence references. | Quality-job dispatch, rule changes, raw samples. |
| `lineage:read` | `analyze_lineage_impact` | Bounded upstream/downstream impact analysis. | Graph mutation, arbitrary traversal, data export. |
| `governance:propose` | `create_governance_proposal`, `request_certification_review`, `schedule_quality_check` | Creates a pending proposal for human steward review. | Approval, confirmation, execution, certification decision, direct asset mutation. |

A host should start with discovery-only scopes. Add `governance:propose` only after the tenant’s named data steward has reviewed the proposal-only workflow and understands that a confirmation nonce is never exposed to or accepted from MCP.

## 4. Compatible host profile

DataGenie supports standards-compliant hosts that can use Streamable HTTP JSON-RPC, OAuth/OIDC bearer tokens, protected-resource metadata, request headers, and structured JSON results. The host must preserve policy obligations and redaction indicators rather than converting a response into unsupported authority.

| Capability | Required behavior | Verification |
|---|---|---|
| Transport | Send JSON-RPC POST requests to `/mcp`; negotiate a gateway-supported `MCP-Protocol-Version`. | `initialize` returns a negotiated version. |
| Resource discovery | Read `/.well-known/oauth-protected-resource/mcp` or the canonical protected-resource URL. | Metadata contains resource and authorization-server information. |
| Authentication | Send its own bearer token and `Mcp-Client-Id`; do not forward tokens downstream. | Gateway returns safe `401` on invalid token/host/audience. |
| Correlation | Send a unique `X-Request-ID` per user-visible operation and retain it with the host audit record. | Same ID appears in a gateway response and execution ledger entry. |
| Schema handling | Respect `tools/list` schemas and reject/repair invalid arguments. | Extra or malformed arguments return structured validation errors. |
| Governance | Treat proposal responses as pending intent only and route users to steward review. | No helper or host flow attempts direct approval/execution. |
| Error handling | Preserve gateway error code and request ID; use bounded retry only for documented transient errors. | Denial/schema calls do not retry with broader scope or altered tenant. |

## 5. Test-tenant walkthrough

1. Confirm the host ID and test tenant are in the gateway allowlist and that the beta is enabled only for the test environment.
2. Obtain a short-lived token with `catalog:read` and call `initialize` using the configured protocol version.
3. Call `tools/list` and verify the seven documented tools. Record the returned/request `X-Request-ID`.
4. Use a synthetic or approved test asset with `get_asset_context`. Confirm the structured response contains provenance, policy, evidence, timestamp, confidence, and redaction indicators.
5. With a separate token that lacks `governance:propose`, call a proposal tool and verify the safe denial. Do not broaden the token automatically.
6. If proposal intent is in scope, create a test proposal and have a named steward inspect it in the approval inbox. The steward, not the host, performs any approval or confirmation exercise.
7. Run the partner certification harness and attach its sanitized JSON evidence to the onboarding review.

## 6. Data-handling expectations

The host may receive only DataGenie’s governed response fields, including policy evidence, obligations, metadata summaries, and redaction indicators. A tenant administrator must define how the host stores, displays, retains, and deletes these results. The host must not treat descriptions, evidence text, prompt content, or source-system metadata as instructions to change scopes, disable controls, reveal credentials, or bypass the steward inbox.

| Prohibited practice | Required alternative |
|---|---|
| Logging bearer tokens, source credentials, raw rows, raw prompts, or full response payloads by default | Log safe request ID, tenant, host ID, tool name, status/error code, and timestamp. |
| Using production customer data for certification | Use synthetic data or an explicitly approved test tenant. |
| Persisting a policy result as a future execution authorization | Re-evaluate through the documented workflow; preserve current obligations. |
| Treating AI-generated text as a governance decision | Create a proposal with evidence and require steward review. |
| Forwarding the bearer token to downstream tools or plugins | Keep token use at the MCP resource boundary. |

## 7. Support investigation

When a host user reports a tool result, collect only the minimum safe facts below. Do **not** request a bearer token, client secret, source credential, raw prompt, raw data row, or unrestricted response body.

| Support field | Example | Use |
|---|---|---|
| Request ID | `host-2026-08-22-00017` | Primary lookup key for gateway logs, policy record, and ledger entry. |
| Tenant and host ID | `test-finance`, `enterprise-governed-host` | Confirms expected isolation and allowlist context. |
| Tool and timestamp | `get_asset_context`, UTC time | Narrows ledger and metric investigation. |
| HTTP/JSON-RPC status and safe code | `403`, `mcp_forbidden` | Determines whether retry or authorization review is appropriate. |
| Protocol version and helper version | `2026-07-28`, `datagenie-mcp-helper/0.1` | Identifies compatibility/deprecation context. |
| Sanitized certification artifact | Synthetic preflight JSON | Confirms baseline host behavior without exposing sensitive data. |

An authorized DataGenie operator searches the minimized execution ledger by request ID, confirms tenant and host binding, inspects operation name/outcome/error code/duration, and correlates the safe policy outcome. A missing ledger entry is a fail-closed operational incident: stop onboarding or affected tool traffic and preserve available evidence for security and operations review.

## 8. Completion checklist

| Check | Tenant administrator | DataGenie reviewer |
|---|---:|---:|
| Approved host ID, test tenant, owner, and support contact recorded | ☐ | ☐ |
| OAuth audience, claims, and least-privilege scopes reviewed | ☐ | ☐ |
| Data-handling expectation accepted | ☐ | ☐ |
| `initialize`, discovery, scope-negative, and schema-negative tests completed | ☐ | ☐ |
| Request-ID-to-ledger support dry run completed | ☐ | ☐ |
| Synthetic certification artifact reviewed | ☐ | ☐ |
| External-host certification and staging approvals recorded before customer enablement | ☐ | ☐ |

## References

[1] [DataGenie MCP authorization reference](mcp-authorization-reference.md)
[2] [DataGenie MCP partner certification](mcp-partner-certification.md)
[3] [DataGenie MCP versioning and deprecation policy](mcp-versioning-and-deprecation-policy.md)
[4] [DataGenie MCP internal canary runbook](mcp-internal-canary-runbook.md)

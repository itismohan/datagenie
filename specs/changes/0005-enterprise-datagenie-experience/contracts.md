# Contracts: 0005-enterprise-datagenie-experience — Enterprise DataGenie Experience

## Frontend runtime configuration

| Variable | Required | Behavior |
|---|---:|---|
| `VITE_DATAGENIE_API_BASE_URL` | No | Catalog API base URL. Defaults to `http://localhost:8000` for local development only. |
| `VITE_DATAGENIE_ACCESS_TOKEN` | No | Caller-provided bearer token used only for request authorization; never persisted by the UI. |
| `VITE_DATAGENIE_TENANT_LABEL` | No | Non-authoritative display label for local/runtime context. The backend token remains authoritative. |

## Catalog loading contract

The catalog workspace uses `GET {apiBaseUrl}/api/v1/assets?limit=50`, with `Authorization` only when a runtime token exists and `X-Request-ID` for correlation. The response must be a list or a list-like `items` envelope. Network, authentication, validation, and server errors produce a safe UI notice with the request ID; the interface does not attempt to infer, override, or retry under a different tenant.

## Governance presentation contract

| UI element | Allowed behavior | Prohibited behavior |
|---|---|---|
| Proposal card | Show pending status, source, policy snapshot, evidence, impact, and a route to steward inbox. | Approve, execute, transmit confirmation nonce, or imply the proposal has changed the governed asset. |
| Quality panel | Show score/context, freshness, rules/incidents, evidence, and remediation owner. | Present a score as authoritative without context or trigger a quality job directly. |
| Lineage panel | Show bounded direction/depth, confidence, and affected consumers. | Perform graph mutation or imply unbounded completeness. |
| Admin posture | Show non-secret tenant/control status and support guidance. | Display OAuth secrets, bearer tokens, source credentials, or security-sensitive internals. |

## Support-correlation contract

The UI displays the current request ID for the latest catalog request and documents that support needs request ID, tenant label, workspace/tool, timestamp, and safe error code. It must not capture bearer tokens, client secrets, source credentials, raw rows, unrestricted prompts, or approval nonces.

## Compatibility

The user interface is additive over existing Catalog API, policy, quality, lineage, and proposal contracts. It makes no client-side authorization decision and remains compatible with unknown API response fields. Any future client-side write workflow requires a separate contract, policy review, and SDD change.

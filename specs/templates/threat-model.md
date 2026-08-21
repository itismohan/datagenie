# Threat Model: {{CHANGE_ID}} — {{TITLE}}

**Status:** Draft | Reviewed | Approved
**Security owner:** {{SECURITY_OWNER}}
**Related design:** [design.md](design.md)

## Scope and trust boundaries

Describe actors, assets, entry points, data flows, tenant boundaries, identity providers, workers, queues, external services, and egress paths. Include a diagram when the change crosses a trust boundary.

## Protected assets

| Asset | Sensitivity | Owner | Required protection |
|---|---|---|---|
| {{ASSET}} | {{CLASSIFICATION}} | {{OWNER}} | {{CONTROL}} |

## Threat analysis

| Threat / misuse case | Attack path | Impact | Required control | Verification |
|---|---|---|---|---|
| Cross-tenant access | {{PATH}} | Unauthorized metadata or action | Tenant context and negative tests | {{TEST}} |
| Authorization bypass | {{PATH}} | Unauthorized governance or operation | Scope/RBAC/policy revalidation | {{TEST}} |
| Secret disclosure | {{PATH}} | Credential compromise | Secret references and redaction | {{TEST}} |
| Prompt injection or tool abuse | {{PATH}} | Unsafe agent action or data exfiltration | Tool bounds, consent, output controls | {{TEST}} |
| SSRF / unsafe egress | {{PATH}} | Internal service access | Host allowlist and egress controls | {{TEST}} |
| Replay or race condition | {{PATH}} | Duplicate/stale mutation | Idempotency and version preconditions | {{TEST}} |
| Availability exhaustion | {{PATH}} | Resource depletion | Rate, quota, timeout, queue bounds | {{TEST}} |

## Security requirements

List requirement IDs from `requirements.md` and the exact controls that satisfy them. Include token audience and scope rules where an API/MCP path is involved.

## Residual risk and acceptance

| Residual risk | Compensating control | Accepted by | Review/expiry date |
|---|---|---|---|
| {{RISK}} | {{CONTROL}} | {{OWNER}} | {{DATE}} |

## Security test evidence

Link automated negative tests, dependency scans, secret scans, authorization matrix tests, and any required adversarial validation.

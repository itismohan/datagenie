# Internal MCP Governed-Discovery Canary Runbook

This runbook controls the first **internal-only** deployment of the read-only DataGenie MCP discovery gateway. It permits exactly one named non-customer tenant and one approved internal MCP host through the opt-in `mcp-beta` profile. The general public ingress must not route to the gateway.

> **Stop condition:** Set `DATAGENIE_MCP_KILL_SWITCH_ENABLED=true` immediately if a cross-tenant result, authorization inconsistency, unexpected host, ledger failure, or metrics failure is suspected. Preserve request IDs, gateway logs, the durable ledger, and Prometheus samples. Do not delete evidence during an incident.

## Preflight

Copy `infra/mcp-canary.env.example` into the protected staging configuration process. Inject `DATAGENIE_MCP_GATEWAY_SERVICE_SHARED_SECRET` through the managed secret store, with the same value supplied to the MCP gateway and catalog, quality, and lineage services. Never put the secret, live tenant identifier, bearer token, or host client identifier in source control or release evidence.

| Control | Required value | Verification |
|---|---|---|
| Profile | `mcp-beta` only | `docker compose --profile mcp-beta config -q` passes. |
| Enablement | `DATAGENIE_MCP_INTERNAL_BETA_ENABLED=true` | Gateway `/health/ready` returns `200`. |
| Emergency stop | Kill switch initially `false` | Toggling to `true` returns a safe disabled response before dispatch. |
| Scope | One internal tenant and one host only | Both allowlist variables contain one approved value. |
| Identity | OIDC issuer, audience, JWKS, tenant, role, and scope claims configured | Wrong audience, host, and tenant return no result payload. |
| Service identity | Same delegated-service secret on all four services | Tampered service packet is rejected. |
| Ledger | PostgreSQL ledger URL | A tool call creates a minimized durable record. |

## Staging deployment

Run this only in the approved staging environment after protected values have been injected.

```bash
docker compose \
  --env-file /secure/path/mcp-canary.env \
  -f infra/docker-compose.yml \
  -f infra/docker-compose.staging.yml \
  --profile mcp-beta up -d --build mcp-gateway prometheus
```

Confirm that `mcp-gateway` has no host port and is only on `datagenie-internal`. Confirm PostgreSQL, catalog, quality, lineage, gateway, and Prometheus health before issuing an MCP request.

## Canary sequence

Use a test token for the approved internal tenant and host. Retain one request ID per step.

| Step | Action | Pass condition | Evidence |
|---|---|---|---|
| 1 | `initialize` | Supported protocol and read-only instructions returned. | Response and request ID. |
| 2 | `tools/list`, `resources/list`, `prompts/list` | Four tools, five resources, three prompts; no mutation/export/SQL/arbitrary HTTP. | Serialized lists and response hash. |
| 3 | `search_governed_assets` | Tenant-visible metadata with provenance and policy evidence. | Result count, size, policy outcomes. |
| 4 | `get_asset_context` | No source secret or raw row; obligations/redactions available. | Redaction indicators and ledger sample. |
| 5 | `get_quality_evidence` | Bounded explainable quality evidence with no raw samples. | Run IDs, state, response size. |
| 6 | `analyze_lineage_impact` | Bounded depth/result size with provenance and confidence. | Node/edge count and latency. |
| 7 | Foreign tenant, wrong audience, wrong host, injected `tenant_id`, and mutation tool | Safe denial without a governed payload. | Negative responses and metrics delta. |
| 8 | Kill switch | Safe unavailable response before tool dispatch. | Config change, response, and restart/reload record. |

## Signal and approval gates

Use `docs/mcp-beta-operations-dashboard.md` to check tool calls, denials, policy decisions, result bytes, latency, errors, ledger failures, rate-limit denials, and tenant-boundary violations. The automated gates require **zero** ledger write failures and tenant-boundary violations, an error rate below one percent, p95 at or below two seconds for search/context/quality, and p95 at or below five seconds for lineage over the agreed measurement window.

| Required approver | Required review |
|---|---|
| Product owner | Confirms the restricted workflow and result presentation are useful. |
| Security owner | Reviews negative paths, service delegation, and a minimized ledger sample. |
| Governance owner | Reviews evidence, obligations, classifications, and redaction. |
| On-call/SRE owner | Confirms dashboards, alerts, kill switch, and escalation route. |

Update `specs/changes/0001-mcp-read-only-governed-discovery/evidence.md` with immutable deployment identifiers, measured staging SLOs, retained request IDs, ledger sample reference, and named approval records. The beta remains **not approved for staging traffic** until these records are complete.

# Release Evidence: 0001-mcp-read-only-governed-discovery — MCP Read-Only Governed Discovery

**Status:** Implementation validated; internal canary approval pending
**Release stage:** Not deployed; internal-only beta profile prepared
**Change owner:** TBD

> This artifact is intentionally a completion record. It MUST be updated with immutable links, command output identifiers, approvers and measured results before promotion from each rollout stage.

## Build and traceability evidence

| Evidence item | Required result | Link or identifier | Status | Owner/date |
|---|---|---|---|---|
| SDD validator | `python3 tools/validate_sdd.py` passes. | Local command passed after final traceability update | Complete locally | TBD |
| Requirements-to-code trace | Each `DG-MCP-READ-*` requirement maps to merged source and tests. | `traceability.yaml`; `apps/mcp-gateway/` | Complete locally | TBD |
| Contract review | MCP schema and compatibility review approved. | Protected-resource metadata, JSON-RPC tool/resource/prompt surface, and `contracts.md` updated | Owner approval pending | TBD |
| Dependency/security scan | No unresolved release-blocking finding. | Pending CI run | Pending | TBD |

## Test evidence

| Test category | Required result | CI run/link | Status | Owner/date |
|---|---|---|---|---|
| Unit and contract schema tests | All pass. | Local: catalog `42 passed`, quality `4 passed`, lineage `3 passed`, gateway `10 passed`; SDD validator passed | Complete locally | TBD |
| Approved-host interoperability | Initialize, authorize, list tools/resources/prompts and call allowed tools. | `apps/mcp-gateway/tests/test_transport.py`; `test_jsonrpc_tools.py` | Complete locally | TBD |
| Tenant-negative matrix | No cross-tenant content, inference, handle polling/cancellation or cache leakage. | `test_transport.py::test_adversarial_identity_and_input_attempts_do_not_leak_results` | Complete locally for beta surface | TBD |
| Token/audience/scope matrix | Invalid/missing/expired/wrong-audience/wrong-scope safely denied. | Host, foreign tenant and wrong-audience coverage implemented; expiry/scope CI expansion pending | Partial | TBD |
| Redaction/privacy tests | No raw data, credential, secret or unauthorized restricted evidence. | `test_tool_execution.py`; `test_jsonrpc_tools.py` | Complete locally for context/tool response fixtures | TBD |
| Prompt-injection/SSRF tests | Malicious content/URLs cannot trigger privilege or egress abuse. | No arbitrary URL/HTTP/SQL tools are advertised; formal hostile-metadata canary test pending | Partial | TBD |
| Resilience tests | Timeout, failure, rate-limit, cancellation and kill switch produce bounded results. | Kill-switch and rate limit code/test coverage; downstream timeout canary pending | Partial | TBD |

## Operational evidence

| Evidence item | Required result | Link or identifier | Status | Owner/date |
|---|---|---|---|---|
| Migration rehearsal | Forward migration and rollback/disable procedure verified in staging. | Compose beta profile validates; staging execution pending | Pending staging | TBD |
| Dashboard | Tool calls, latency, denials, policy, ledger and errors visible. | `docs/mcp-beta-operations-dashboard.md`; Prometheus scrape job added | Prepared; not exercised in staging | TBD |
| Alerts | Boundary violation, ledger failure, policy outage and SLO alert routes tested. | `infra/prometheus-alerts.yml` | Defined; notification route test pending | TBD |
| Kill switch | Global, tenant and per-tool disable controls tested. | Global and per-tool configuration; global test implemented | Partial: tenant-specific switch not needed for one-tenant beta | TBD |
| Ledger sampling | Security/governance sample confirms tenant, policy, correlation and minimization. | Pending | Pending | TBD |
| Canary SLOs | Measured p95, error/denial and result-bound figures meet approved budgets. | Pending | Pending | TBD |

## Approval record

| Decision | Required approver | Name/date | Outcome | Notes |
|---|---|---|---|---|
| Design and contract | Solution architect | Pending | Pending | |
| Threat model | Security owner | Pending | Pending | |
| Governance evidence/redaction | Data steward | Pending | Pending | |
| Operational readiness | SRE/on-call | Pending | Pending | |
| Internal canary | Product owner | Pending | Pending | |

## Deviations and residual risks

| ID | Deviation/risk | Impact | Approval | Expiry/mitigation |
|---|---|---|---|---|
| None recorded | Update if a release exception is requested. | N/A | N/A | N/A |

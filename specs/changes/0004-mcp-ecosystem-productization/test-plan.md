# Test Plan: 0004-mcp-ecosystem-productization — MCP Ecosystem Productization

## Test matrix

| Area | Scenario | Expected result | Evidence |
|---|---|---|---|
| Onboarding pack | Scope, host, test-tenant, data-handling, and support sections are present. | Administrator has a complete least-privilege self-service checklist. | Documentation contract test. |
| Lifecycle policy | Additive, deprecated, breaking, notice, retirement, and exception rules are present. | A certified host can determine upgrade behavior. | Documentation contract test. |
| Python helper | Allowed tool call produces standard JSON-RPC request with caller request ID. | No proprietary protocol or hidden credential behavior. | Unit test with recording transport. |
| TypeScript helper | Source has same allowlist and standard envelope semantics. | Tool map excludes direct governance mutation and confirmation operations. | Static contract test. |
| Helper safety | Unknown or direct-mutation tool name is requested. | Local validation rejects before network dispatch. | Unit test. |
| Certification harness | Generic Streamable HTTP profile and enterprise governed-host profile run the test matrix. | Both receive valid initialization and structured governed response. | Sanitized JSON artifact. |
| Auth and scope | Missing `governance:propose` calls a proposal tool. | Gateway returns safe authorization denial with request ID. | Harness assertion. |
| Schema and errors | Extra field or malformed tool arguments are submitted. | Gateway returns structured validation error and exposes no asset payload. | Harness assertion. |
| Proposal-only boundary | A direct mutation operation is called. | Gateway returns method-not-found; no direct mutation occurs. | Harness and unit tests. |
| Support correlation | A known request ID is issued through a tool call. | A tenant-bound ledger entry contains that request ID and operation name. | Harness assertion and runbook review. |
| Domain-pack governance | Documentation is reviewed for required approved-feedback and SDD controls. | No automatic feedback ingestion or generic-tool path exists. | Documentation contract test. |

## Test data and environment

All test runs use synthetic hosts, the `internal-certification` tenant, synthetic asset identifiers, fixed non-secret shared values, and an in-process gateway/downstream adapter. No live OIDC issuer, customer tenant, production data, source credentials, customer feedback, or production gateway is used. Evidence artifacts are replaced on every run and may contain only the fields defined in `contracts.md`.

## External validation

Before customer enablement, the release owner must record two external host submissions with distinct host products or deployment teams, a staging OIDC proof, tenant-admin onboarding walkthrough, and support dry run. The synthetic harness proves the product contract and regression behavior but does not waive these tests.

## Acceptance evidence

Run `python3 tools/run_mcp_partner_certification.py`, `pytest -q` for the new helper/certification tests, the existing catalog and MCP suites, and `python3 tools/validate_sdd.py`. Record exact results and the generated artifact in `evidence.md`.

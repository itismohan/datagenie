# Test Plan: {{CHANGE_ID}} — {{TITLE}}

**Status:** Draft | Approved | Evidence complete
**Quality owner:** {{QUALITY_OWNER}}

## Requirement coverage matrix

| Requirement ID | Test level | Scenario | Test location | Required outcome |
|---|---|---|---|---|
| DG-{{DOMAIN}}-001 | Unit / contract / integration / E2E / security | {{SCENARIO}} | {{PATH}} | {{OUTCOME}} |

## Mandatory test categories

| Category | Required when | Minimum proof |
|---|---|---|
| Unit | All behavior | Deterministic behavior and boundary cases. |
| Contract | Public API/event/MCP/data contract changes | Schema, compatibility, errors, and examples. |
| Integration | Persistence, workers, connectors, or cross-service behavior | Realistic service/database path. |
| Tenant-negative | Any tenant-scoped resource | Caller cannot list, retrieve, infer, mutate, replay, or cache another tenant’s data. |
| Authorization/policy | Protected operation | Role/scope/purpose denial and allowed behavior. |
| Migration | Schema/migration changes | Upgrade from previous revision and constraint/index validation. |
| Recovery | Durable/asynchronous/outbound work | Timeout, cancellation, retry, dead-letter, and replay. |
| Adversarial | AI/MCP/external input or egress | Prompt injection, misuse, SSRF, scope escalation, stale approval and result-bound tests. |
| Performance | Material query/job/graph path | Documented latency, capacity, timeout, and result-limit evidence. |

## Test data and environment

Describe synthetic or approved test data, tenant separation, secret handling, external dependencies, feature flags, and cleanup. Production data SHALL NOT be copied into test artifacts without an approved handling process.

## Acceptance evidence

Record exact commands, CI job URLs, output summary, reviewer, date, and known limitations in `evidence.md`. A test failure may only be waived using a time-bounded constitution exception.

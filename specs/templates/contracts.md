# Contracts: {{CHANGE_ID}} — {{TITLE}}

**Status:** Draft | Approved
**Compatibility owner:** {{API_OWNER}}

## Contract inventory

| ID | Interface | Artifact path | Version | Change class | Consumer impact |
|---|---|---|---|---|---|
| {{CONTRACT_ID}} | REST / event / data / MCP | {{PATH}} | {{VERSION}} | Additive / deprecated / breaking | {{IMPACT}} |

## Contract requirements

Every public contract SHALL define its owner, version, authorization, tenant behavior, request/input schema, response/output schema, error model, result bounds, correlation/idempotency behavior, data classification/redaction, observability, and compatibility decision.

## REST/API contract checklist

| Concern | Requirement |
|---|---|
| OpenAPI | Update the executable OpenAPI contract and committed artifact. |
| Authentication | Specify role/scope and tenant binding. |
| Errors | Use the platform error envelope and stable application codes. |
| Bounds | Define pagination/filtering/result-size/timeouts. |
| Mutation safety | Define idempotency, concurrency/version preconditions, audit and rollback semantics. |

## Event contract checklist

| Concern | Requirement |
|---|---|
| Identity | Event ID, tenant ID, actor/initiator, correlation ID, schema version. |
| Delivery | Producer, consumer, ordering, retry, dead-letter/replay behavior. |
| Data | Schema, classification, redaction, retention and replay safety. |

## MCP contract checklist

| Concern | Requirement |
|---|---|
| Primitive | Resource, prompt, tool, task, or interactive application. |
| Identity | Required OAuth/OIDC scopes, tenant binding, audience, host/client evidence. |
| Tool safety | Side-effect class, dry-run/preview, confirmation, idempotency, timeout, cancellation, quota. |
| Output | Structured evidence, provenance, policy decision, confidence, redaction and size bound. |
| Audit | Tool name/version, input/output digest, policy result, approval state, correlation ID. |

## Compatibility and deprecation plan

Describe consumer discovery, release note, migration route, compatibility window, telemetry, and retirement criteria. A breaking change must name the major contract version and affected consumer owners.
